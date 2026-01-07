"""Nex protocol response formatter.

Fetches resources from Nex servers and formats the response
as Gemtext for display in the GemtextViewer.

Nex is a simple protocol using TCP on port 1900. Directory listings
use Gemtext-like syntax (=> url label), so responses can be parsed
directly as Gemtext.
"""

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urlparse

from astronomo.parser import GemtextLine, parse_gemtext


@dataclass
class NexFetchResult:
    """Result of a Nex fetch operation.

    Attributes:
        content: Parsed Gemtext lines for display
        is_binary: True if this is a binary download
        binary_data: Raw binary data for downloads
        filename: Suggested filename for downloads
    """

    content: list[GemtextLine] = field(default_factory=list)
    is_binary: bool = False
    binary_data: bytes | None = None
    filename: str | None = None


def _is_binary_content(data: bytes) -> bool:
    """Detect if response data is binary (not text).

    Uses heuristics to determine if content is binary:
    - Contains null bytes (common in binary files)
    - High percentage of non-printable characters
    - Cannot be decoded as UTF-8

    Args:
        data: The response bytes to check

    Returns:
        True if content appears to be binary, False otherwise
    """
    # Empty content is not binary
    if not data:
        return False

    # Check for null bytes (strong indicator of binary)
    if b"\x00" in data[:1024]:  # Check first 1KB
        return True

    # Try UTF-8 decode - if it completely fails, it's likely binary
    try:
        text = data.decode("utf-8")
        # Check percentage of non-printable characters
        if len(text) > 0:
            non_printable = sum(
                1 for c in text[:1000] if ord(c) < 32 and c not in "\n\r\t"
            )
            if non_printable / min(len(text), 1000) > 0.3:  # >30% non-printable
                return True
    except UnicodeDecodeError:
        # Cannot decode as UTF-8 at all -> likely binary
        return True

    return False


async def fetch_nex(url: str, timeout: int = 30) -> NexFetchResult:
    """Fetch and format a Nex response.

    Handles both text content (directories, documents) and binary files.
    Binary files are detected by checking for null bytes and non-UTF8 content.

    Nex protocol:
    - TCP connection on port 1900 (default)
    - Send: "<path>\r\n"
    - Receive: response until EOF
    - Directory listings use Gemtext format (=> url label)

    Args:
        url: The nex:// URL to fetch
        timeout: Request timeout in seconds

    Returns:
        NexFetchResult with content and metadata

    Raises:
        ConnectionError: If connection to the server fails
        TimeoutError: If the request times out
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or 1900
    path = parsed.path or "/"

    try:
        # Wrap entire operation in single timeout
        async def _fetch_with_timeout():
            reader, writer = await asyncio.open_connection(host, port)
            try:
                # Send request: path + CRLF
                request = f"{path}\r\n"
                writer.write(request.encode("utf-8"))
                await writer.drain()

                # Read response until EOF
                return await reader.read()
            finally:
                # Always close connection
                writer.close()
                await writer.wait_closed()

        response_bytes = await asyncio.wait_for(_fetch_with_timeout(), timeout=timeout)

        # Detect if content is binary
        if _is_binary_content(response_bytes):
            # Binary file - prepare for download
            filename = path.split("/")[-1] or "download"
            return NexFetchResult(
                content=parse_gemtext(f"# Binary Download\n\nFile: {filename}"),
                is_binary=True,
                binary_data=response_bytes,
                filename=filename,
            )

        # Text content - decode and parse
        try:
            response = response_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            response = response_bytes.decode("latin-1", errors="replace")

        # Nex directory listings use Gemtext-like format (=> lines)
        # Parse directly as Gemtext
        return NexFetchResult(content=parse_gemtext(response))

    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Connection to {host}:{port} timed out") from e
    except OSError as e:
        raise ConnectionError(f"Failed to connect to {host}:{port}: {e}") from e
