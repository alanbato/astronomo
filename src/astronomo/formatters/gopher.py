"""Gopher protocol response formatter.

Fetches resources from Gopher servers and formats the response
as Gemtext for display in the GemtextViewer.
"""

from dataclasses import dataclass, field
from urllib.parse import urlparse

from mototli.client import GopherClient
from mototli.protocol import GopherItem

from astronomo.parser import GemtextLine, GemtextLink, parse_gemtext


@dataclass
class GopherFetchResult:
    """Result of a Gopher fetch operation.

    Attributes:
        content: Parsed Gemtext lines for display
        requires_search: True if this is a search item requiring user input
        search_prompt: Prompt to show for search input
        is_binary: True if this is a binary download
        binary_data: Raw binary data for downloads
        filename: Suggested filename for downloads
    """

    content: list[GemtextLine] = field(default_factory=list)
    requires_search: bool = False
    search_prompt: str | None = None
    is_binary: bool = False
    binary_data: bytes | None = None
    filename: str | None = None


def build_gopher_url(item: GopherItem) -> str:
    """Build a gopher:// URL from a GopherItem.

    Args:
        item: The Gopher menu item

    Returns:
        A properly formatted gopher:// URL
    """
    port_suffix = f":{item.port}" if item.port != 70 else ""
    return (
        f"gopher://{item.hostname}{port_suffix}/{item.item_type.value}{item.selector}"
    )


def format_gopher_menu(items: list[GopherItem]) -> list[GemtextLine]:
    """Convert Gopher directory listing to Gemtext lines.

    Maps Gopher item types to appropriate Gemtext representations:
    - Informational (i): Plain text
    - Directory (1): Link with [DIR] prefix
    - Text (0): Link with [TXT] prefix
    - Search (7): Link with [SEARCH] prefix
    - Binary (9, g, I): Link with [BIN] or [IMG] prefix
    - External (h, T): Plain text with [EXT] prefix

    Args:
        items: List of GopherItem objects from the server

    Returns:
        List of GemtextLine objects for display
    """
    lines: list[GemtextLine] = []

    for item in items:
        if item.item_type.is_informational:
            # Type 'i' - display as plain text
            lines.extend(parse_gemtext(item.display_text))
        elif item.item_type.is_directory:
            # Type '1' - directory link
            url = build_gopher_url(item)
            lines.append(
                GemtextLink(
                    raw=f"=> {url} [DIR] {item.display_text}",
                    url=url,
                    label=f"[DIR] {item.display_text}",
                )
            )
        elif item.item_type.is_text:
            # Type '0' - text file link
            url = build_gopher_url(item)
            lines.append(
                GemtextLink(
                    raw=f"=> {url} [TXT] {item.display_text}",
                    url=url,
                    label=f"[TXT] {item.display_text}",
                )
            )
        elif item.item_type.is_search:
            # Type '7' - search (will trigger InputModal)
            url = build_gopher_url(item)
            lines.append(
                GemtextLink(
                    raw=f"=> {url} [SEARCH] {item.display_text}",
                    url=url,
                    label=f"[SEARCH] {item.display_text}",
                )
            )
        elif item.item_type.is_binary:
            # Types '9', 'g', 'I' - binary/image
            url = build_gopher_url(item)
            indicator = "[IMG]" if item.item_type.value in ("g", "I") else "[BIN]"
            lines.append(
                GemtextLink(
                    raw=f"=> {url} {indicator} {item.display_text}",
                    url=url,
                    label=f"{indicator} {item.display_text}",
                )
            )
        elif item.item_type.is_external:
            # Telnet, HTML - mark as external
            url = build_gopher_url(item)
            # For HTML links (type 'h'), extract the actual URL if embedded
            if item.item_type.value == "h" and item.selector.startswith("URL:"):
                url = item.selector[4:]  # Strip "URL:" prefix
            lines.append(
                GemtextLink(
                    raw=f"=> {url} [EXT] {item.display_text}",
                    url=url,
                    label=f"[EXT] {item.display_text}",
                )
            )

    return lines


def parse_gopher_url(url: str) -> tuple[str, int, str, str]:
    """Parse a gopher:// URL into components.

    Gopher URLs have the format: gopher://host[:port]/Tselector
    where T is a single character item type.

    Args:
        url: The gopher:// URL to parse

    Returns:
        Tuple of (host, port, item_type, selector)
    """
    parsed = urlparse(url)

    # Extract host and port
    if ":" in parsed.netloc:
        host, port_str = parsed.netloc.split(":", 1)
        port = int(port_str)
    else:
        host = parsed.netloc
        port = 70

    # Parse path: /Tselector where T is item type
    path = parsed.path
    if len(path) >= 2 and path[0] == "/":
        item_type = path[1]
        selector = path[2:] if len(path) > 2 else ""
    else:
        # Default to directory if no type specified
        item_type = "1"
        selector = path.lstrip("/")

    return host, port, item_type, selector


async def fetch_gopher(
    url: str,
    timeout: int = 30,
    search_query: str | None = None,
) -> GopherFetchResult:
    """Fetch and format a Gopher resource.

    Handles different Gopher item types:
    - Directory (1): Returns formatted menu
    - Text (0): Returns preformatted text
    - Search (7): Returns search prompt or results
    - Binary (9, g, I): Returns binary data for download

    Args:
        url: The gopher:// URL to fetch
        timeout: Request timeout in seconds
        search_query: Search query for type 7 items

    Returns:
        GopherFetchResult with content and metadata

    Raises:
        ConnectionError: If connection to the server fails
        TimeoutError: If the request times out
    """
    host, port, item_type, selector = parse_gopher_url(url)

    async with GopherClient(timeout=float(timeout)) as client:
        if item_type == "7":  # Search
            if search_query is None:
                return GopherFetchResult(
                    content=[],
                    requires_search=True,
                    search_prompt="Enter search query",
                )
            response = await client.get(
                host, selector, port=port, search_query=search_query
            )
            return GopherFetchResult(content=format_gopher_menu(response.items))

        elif item_type == "0":  # Text file
            text = await client.get_text(host, selector, port=port)
            # get_text returns a string directly
            gemtext = f"```\n{text}\n```"
            return GopherFetchResult(content=parse_gemtext(gemtext))

        elif item_type in ("9", "g", "I"):  # Binary/Image
            data = await client.get_binary(host, selector, port=port)
            # get_binary returns bytes directly
            filename = selector.split("/")[-1] or "download"
            return GopherFetchResult(
                content=parse_gemtext(f"# Binary Download\n\nFile: {filename}"),
                is_binary=True,
                binary_data=data,
                filename=filename,
            )

        else:  # Directory or unknown - treat as directory
            response = await client.get(host, selector, port=port)
            return GopherFetchResult(content=format_gopher_menu(response.items))
