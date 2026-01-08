"""Spartan protocol response formatter.

Fetches resources from Spartan servers and formats the response
as Gemtext for display in the GemtextViewer.

Spartan is a minimalist protocol on port 300 with single-digit status codes.
It supports text and binary transfers with MIME type detection.
"""

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from teyaotlani import get

from astronomo.parser import GemtextLine, parse_gemtext


def _contains_ansi_codes(text: str) -> bool:
    """Check if text contains ANSI escape codes.

    Some Spartan servers return ASCII art with ANSI color codes.
    We detect these so we can wrap them in preformatted blocks
    for proper color rendering in Textual.

    Args:
        text: Text to check

    Returns:
        True if text contains ANSI codes
    """
    # Check for ANSI escape sequences (e.g., \x1b[38;5;178m)
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return bool(ansi_escape.search(text))


@dataclass
class SpartanFetchResult:
    """Result of a Spartan fetch operation.

    Attributes:
        content: Parsed Gemtext lines for display
        is_redirect: True if this is a redirect response (status 3)
        redirect_url: Target URL for redirect
        is_binary: True if this is a binary download
        binary_data: Raw binary data for downloads
        filename: Suggested filename for downloads
        mime_type: MIME type from server response
        final_url: Final URL after following redirects
    """

    content: list[GemtextLine] = field(default_factory=list)
    is_redirect: bool = False
    redirect_url: str | None = None
    is_binary: bool = False
    binary_data: bytes | None = None
    filename: str | None = None
    mime_type: str = "text/gemini"
    final_url: str = ""


async def fetch_spartan(
    url: str,
    timeout: int = 30,
    data: str | None = None,
) -> SpartanFetchResult:
    """Fetch and format a Spartan resource.

    Handles status codes:
    - 2: Success (with MIME type in meta)
    - 3: Redirect (returns redirect URL for app to follow)
    - 4: Client error (returns error page)
    - 5: Server error (returns error page)

    Args:
        url: The spartan:// URL to fetch
        timeout: Request timeout in seconds
        data: Optional data to upload (for input links =:)

    Returns:
        SpartanFetchResult with content and metadata

    Raises:
        ConnectionError: If connection to the server fails
        TimeoutError: If the request times out
    """
    try:
        # Use teyaotlani library to fetch Spartan resource
        # Use upload() for input links with data, get() for read-only
        if data is not None:
            from teyaotlani import upload

            response = await upload(url, data, timeout=float(timeout))
        else:
            response = await get(url, timeout=float(timeout))

        # Status 2: Success
        if response.status == 2:
            mime_type = response.mime_type or "text/gemini"

            # Binary content detection via MIME type
            if not mime_type.startswith("text/"):
                # Binary file - prepare for download
                parsed_url = urlparse(url)
                filename = parsed_url.path.split("/")[-1] or "download"

                # Ensure body is bytes
                body = response.body
                if isinstance(body, str):
                    body = body.encode("utf-8")

                return SpartanFetchResult(
                    content=parse_gemtext(
                        f"# Binary Download\n\nFile: {filename}\nType: {mime_type}"
                    ),
                    is_binary=True,
                    binary_data=body,
                    filename=filename,
                    mime_type=mime_type,
                    final_url=url,
                )

            # Text content - decode if necessary
            body = response.body
            if isinstance(body, bytes):
                charset = response.charset or "utf-8"
                try:
                    decoded_body = body.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    decoded_body = body.decode("utf-8", errors="replace")
                body = decoded_body

            # Empty body check
            if not body or not body.strip():
                return SpartanFetchResult(
                    content=parse_gemtext("(empty response)"),
                    mime_type=mime_type,
                    final_url=url,
                )

            # If content contains ANSI codes, wrap in preformatted block
            # so Textual can render the colors properly
            if _contains_ansi_codes(body):
                body = f"```\n{body}\n```"

            # Parse as Gemtext (default for Spartan)
            return SpartanFetchResult(
                content=parse_gemtext(body),
                mime_type=mime_type,
                final_url=url,
            )

        # Status 3: Redirect
        elif response.status == 3:
            redirect_url = response.redirect_url
            if not redirect_url:
                # No redirect URL provided - show error
                error_text = (
                    "# Redirect Error\n\n"
                    "Server returned redirect status but no redirect URL was provided."
                )
                return SpartanFetchResult(
                    content=parse_gemtext(error_text),
                    final_url=url,
                )

            # Resolve relative redirect URLs
            if not redirect_url.startswith(
                ("spartan://", "gemini://", "gopher://", "finger://", "nex://")
            ):
                redirect_url = urljoin(url, redirect_url)

            # Return redirect result for app layer to handle
            return SpartanFetchResult(
                content=parse_gemtext(f"# Redirecting...\n\n=> {redirect_url}"),
                is_redirect=True,
                redirect_url=redirect_url,
                final_url=url,
            )

        # Status 4: Client error
        elif response.status == 4:
            error_msg = response.meta or "Bad request"
            error_text = (
                f"# Client Error (4)\n\n"
                f"The server rejected your request:\n\n"
                f"{error_msg}\n\n"
                f"URL: {url}"
            )
            return SpartanFetchResult(
                content=parse_gemtext(error_text),
                final_url=url,
            )

        # Status 5: Server error
        elif response.status == 5:
            error_msg = response.meta or "Server error"
            error_text = (
                f"# Server Error (5)\n\n"
                f"The server encountered an error:\n\n"
                f"{error_msg}\n\n"
                f"URL: {url}"
            )
            return SpartanFetchResult(
                content=parse_gemtext(error_text),
                final_url=url,
            )

        else:
            # Unknown status code
            error_text = (
                f"# Unknown Status\n\n"
                f"Server returned unknown status code: {response.status}\n\n"
                f"URL: {url}"
            )
            return SpartanFetchResult(
                content=parse_gemtext(error_text),
                final_url=url,
            )

    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Request to {url} timed out") from e
    except OSError as e:
        raise ConnectionError(f"Failed to connect to {url}: {e}") from e
