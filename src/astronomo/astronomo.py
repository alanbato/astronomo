from urllib.parse import urljoin, uses_netloc, uses_relative

from nauyaca.client import GeminiClient
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input

from astronomo.parser import parse_gemtext
from astronomo.response_handler import format_response
from astronomo.widgets import GemtextViewer

# Register gemini as a valid URL scheme for proper urljoin behavior
if "gemini" not in uses_relative:
    uses_relative.append("gemini")
if "gemini" not in uses_netloc:
    uses_netloc.append("gemini")


class Astronomo(App[None]):
    """A Gemini browser for the terminal."""

    CSS = """
    Input {
        dock: top;
        margin: 1;
    }

    VerticalScroll {
        height: 1fr;
    }

    #content {
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("left", "prev_link", "◀ Prev Link"),
        ("right", "next_link", "Next Link ▶"),
        ("enter", "activate_link", "Activate Link"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_url: str = ""

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        yield Input(
            placeholder="Enter a Gemini URL (e.g., gemini://geminiprotocol.net/)",
            id="url-input",
        )
        yield VerticalScroll(GemtextViewer(id="content"))
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the viewer with a welcome message."""
        viewer = self.query_one("#content", GemtextViewer)
        welcome_text = (
            "# Welcome to Astronomo!\n\nEnter a Gemini URL above to get started."
        )
        viewer.update_content(parse_gemtext(welcome_text))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle URL submission and fetch Gemini content."""
        url = event.value.strip()
        if not url:
            return

        # Add gemini:// prefix if not present
        if not url.startswith("gemini://"):
            url = f"gemini://{url}"

        viewer = self.query_one("#content", GemtextViewer)
        loading_text = f"# Fetching\n\n{url}\n\nPlease wait..."
        viewer.update_content(parse_gemtext(loading_text))

        # Shift focus to content viewer
        viewer.focus()

        # Error handling is done in get_url
        self.get_url(url)

    @work(exclusive=True)
    async def get_url(self, url: str) -> None:
        """Fetch and display a Gemini resource."""
        import asyncio

        viewer = self.query_one("#content", GemtextViewer)

        try:
            # Fetch the Gemini resource
            async with GeminiClient(timeout=30, max_redirects=5) as client:
                response = await client.get(url)

            # Store current URL for relative link resolution
            self.current_url = url

            # Format and display the response (now returns list[GemtextLine])
            parsed_lines = format_response(url, response)
            viewer.update_content(parsed_lines)
        except asyncio.TimeoutError:
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after 30 seconds.\n\n"
                f"The server may be down or not responding. Please try again later."
            )
            viewer.update_content(parse_gemtext(error_text))
        except Exception as e:
            error_text = f"# Error\n\nFailed to fetch {url}:\n\n{e!r}"
            viewer.update_content(parse_gemtext(error_text))

    def on_gemtext_viewer_link_activated(
        self, message: GemtextViewer.LinkActivated
    ) -> None:
        """Handle link activation from the viewer."""
        link_url = message.link.url

        # Resolve relative URLs
        if not link_url.startswith("gemini://"):
            # Relative URL - resolve it against current URL
            link_url = urljoin(self.current_url, link_url)

        # Update URL input and fetch
        url_input = self.query_one("#url-input", Input)
        url_input.value = link_url
        self.get_url(link_url)

    def action_next_link(self) -> None:
        """Navigate to the next link in the page."""
        viewer = self.query_one("#content", GemtextViewer)
        viewer.next_link()

    def action_prev_link(self) -> None:
        """Navigate to the previous link in the page."""
        viewer = self.query_one("#content", GemtextViewer)
        viewer.prev_link()

    def action_activate_link(self) -> None:
        """Activate the currently selected link."""
        viewer = self.query_one("#content", GemtextViewer)
        viewer.activate_current_link()


if __name__ == "__main__":
    app = Astronomo()
    app.run()
