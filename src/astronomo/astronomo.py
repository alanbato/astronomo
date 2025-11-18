from nauyaca.client import GeminiClient
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from astronomo.response_handler import format_response


class Astronomo(App[None]):
    """A Gemini browser for the terminal."""

    CSS = """
    Input {
        dock: top;
        margin: 1;
    }

    #content {
        height: 1fr;
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        yield Input(
            placeholder="Enter a Gemini URL (e.g., gemini://geminiprotocol.net/)",
            id="url-input",
        )
        yield VerticalScroll(
            Static(
                "Welcome to Astronomo! Enter a Gemini URL above to get started.",
                id="content",
            )
        )
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle URL submission and fetch Gemini content."""
        url = event.value.strip()
        if not url:
            return

        # Add gemini:// prefix if not present
        if not url.startswith("gemini://"):
            url = f"gemini://{url}"

        content = self.query_one("#content", Static)
        content.update(f"Fetching: {url}\n\nPlease wait...")

        # Error handling is done in get_url
        self.get_url(url)

    @work(exclusive=True)
    async def get_url(self, url: str) -> None:
        """Fetch and display a Gemini resource."""
        import asyncio

        content = self.query_one("#content", Static)

        try:
            # Fetch the Gemini resource
            async with GeminiClient(timeout=30, max_redirects=5) as client:
                response = await client.get(url)

            # Format and display the response
            formatted_content = format_response(url, response)
            content.update(formatted_content)
        except asyncio.TimeoutError:
            content.update(
                f"# Timeout Error\n\n"
                f"The request to `{url}` timed out after 30 seconds.\n\n"
                f"The server may be down or not responding. Please try again later."
            )
        except Exception as e:
            content.update(
                f"# Error\n\n" f"Failed to fetch `{url}`:\n\n" f"```\n{e!r}\n```"
            )


if __name__ == "__main__":
    app = Astronomo()
    app.run()
