"""Finger protocol response formatter.

Fetches user information from Finger servers and formats
the response as Gemtext for display in the GemtextViewer.
"""

from urllib.parse import urlparse

from mapilli import FingerClient

from astronomo.parser import GemtextLine, parse_gemtext


async def fetch_finger(url: str, timeout: int = 30) -> list[GemtextLine]:
    """Fetch and format a Finger response as Gemtext.

    Supports two URL formats:
    - finger://user@host - User query at host
    - finger://host/user - User query via path

    Args:
        url: The finger:// URL to fetch
        timeout: Request timeout in seconds

    Returns:
        List of GemtextLine objects for display

    Raises:
        ConnectionError: If connection to the server fails
        TimeoutError: If the request times out
    """
    parsed = urlparse(url)

    # Handle finger://user@host and finger://host/user formats
    if "@" in parsed.netloc:
        # finger://user@host format
        query, host = parsed.netloc.rsplit("@", 1)
    else:
        # finger://host/user format
        host = parsed.netloc
        query = parsed.path.lstrip("/") if parsed.path else ""

    async with FingerClient(timeout=float(timeout)) as client:
        response = await client.query(query, host=host)

    # Format as preformatted Gemtext
    title = f"{query}@{host}" if query else host
    gemtext = f"# Finger: {title}\n\n```\n{response.body}\n```"
    return parse_gemtext(gemtext)
