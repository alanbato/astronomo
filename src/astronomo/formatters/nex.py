"""Nex protocol response formatter.

Fetches resources from Nex servers and formats the response
as Gemtext for display in the GemtextViewer.

Nex is a simple protocol using TCP on port 1900. Directory listings
use Gemtext-like syntax (=> url label), so responses can be parsed
directly as Gemtext.
"""

import asyncio
from urllib.parse import urlparse

from astronomo.parser import GemtextLine, parse_gemtext


async def fetch_nex(url: str, timeout: int = 30) -> list[GemtextLine]:
    """Fetch and format a Nex response as Gemtext.

    Nex protocol:
    - TCP connection on port 1900 (default)
    - Send: "<path>\r\n"
    - Receive: response until EOF
    - Directory listings use Gemtext format (=> url label)

    Args:
        url: The nex:// URL to fetch
        timeout: Request timeout in seconds

    Returns:
        List of GemtextLine objects for display

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

        # Decode response
        try:
            response = response_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            response = response_bytes.decode("latin-1", errors="replace")

        # Nex directory listings use Gemtext-like format (=> lines)
        # Parse directly as Gemtext
        return parse_gemtext(response)

    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Connection to {host}:{port} timed out") from e
    except OSError as e:
        raise ConnectionError(f"Failed to connect to {host}:{port}: {e}") from e
