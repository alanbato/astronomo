from pathlib import Path
from urllib.parse import urljoin, uses_netloc, uses_relative

from nauyaca.client import GeminiClient
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, Input

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder
from astronomo.history import HistoryEntry, HistoryManager
from astronomo.parser import LineType, parse_gemtext
from astronomo.response_handler import format_response
from astronomo.widgets import (
    AddBookmarkModal,
    BookmarksSidebar,
    EditItemModal,
    GemtextViewer,
)

# Register gemini as a valid URL scheme for proper urljoin behavior
if "gemini" not in uses_relative:
    uses_relative.append("gemini")
if "gemini" not in uses_netloc:
    uses_netloc.append("gemini")


class Astronomo(App[None]):
    """A Gemini browser for the terminal."""

    CSS_PATH = Path("astronomo_app.tcss")

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+b", "toggle_bookmarks", "Bookmarks"),
        ("ctrl+d", "add_bookmark", "Add Bookmark"),
    ]

    def __init__(self, initial_url: str | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_url: str = ""
        self.history = HistoryManager(max_size=100)
        self.bookmarks = BookmarkManager()
        self._navigating_history = False  # Flag to prevent history loops
        self._initial_url = initial_url  # Store for use in on_mount

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        with Horizontal(id="nav-bar"):
            yield Button("◀", id="back-button", disabled=True)
            yield Button("▶", id="forward-button", disabled=True)
            yield Input(
                placeholder="Enter a Gemini URL (e.g., gemini://geminiprotocol.net/)",
                id="url-input",
            )
        with Horizontal(id="main-content"):
            yield GemtextViewer(id="content")
            yield BookmarksSidebar(self.bookmarks, id="bookmarks-sidebar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the viewer with a welcome message or load initial URL."""
        viewer = self.query_one("#content", GemtextViewer)

        if self._initial_url:
            # Auto-prefix gemini:// if not present
            url = self._initial_url
            if not url.startswith("gemini://"):
                url = f"gemini://{url}"

            # Update URL input
            url_input = self.query_one("#url-input", Input)
            url_input.value = url

            # Show loading message and fetch
            loading_text = f"# Fetching\n\n{url}\n\nPlease wait..."
            viewer.update_content(parse_gemtext(loading_text))
            viewer.focus()
            self.get_url(url)
        else:
            # Show welcome message
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
    async def get_url(self, url: str, add_to_history: bool = True) -> None:
        """Fetch and display a Gemini resource.

        Args:
            url: The URL to fetch
            add_to_history: Whether to add this fetch to history (default True)
        """
        import asyncio

        viewer = self.query_one("#content", GemtextViewer)

        # Save current page state to history before navigating away
        if not self._navigating_history and add_to_history:
            self._update_current_history_state()

        try:
            # Fetch the Gemini resource
            async with GeminiClient(timeout=30, max_redirects=5) as client:
                response = await client.get(url)

            # Store current URL for relative link resolution
            self.current_url = url

            # Format and display the response (now returns list[GemtextLine])
            parsed_lines = format_response(url, response)
            viewer.update_content(parsed_lines)

            # Save successful response to history (only status 20-29)
            if (
                not self._navigating_history
                and add_to_history
                and response.is_success()
            ):
                entry = HistoryEntry(
                    url=url,
                    content=parsed_lines,
                    scroll_position=0,
                    link_index=0,
                    status=response.status,
                    meta=response.meta,
                    mime_type=response.mime_type or "text/gemini",
                )
                self.history.push(entry)
                self._update_navigation_buttons()
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

    def on_gemtext_viewer_navigate_back(
        self, message: GemtextViewer.NavigateBack
    ) -> None:
        """Handle back navigation request from viewer."""
        self.action_navigate_back()

    def on_gemtext_viewer_navigate_forward(
        self, message: GemtextViewer.NavigateForward
    ) -> None:
        """Handle forward navigation request from viewer."""
        self.action_navigate_forward()

    def action_refresh(self) -> None:
        """Refresh the current page by re-fetching the URL."""
        if not self.current_url:
            return

        # Re-fetch the current URL without adding to history
        self.get_url(self.current_url, add_to_history=False)

    def _update_current_history_state(self) -> None:
        """Update the current history entry with current scroll/link state."""
        current_entry = self.history.current()
        if current_entry:
            viewer = self.query_one("#content", GemtextViewer)
            # Update the entry in place (dataclass fields are mutable)
            current_entry.scroll_position = viewer.scroll_y
            current_entry.link_index = viewer.current_link_index

    def _restore_from_history(self, entry: HistoryEntry) -> None:
        """Restore UI state from a history entry."""
        # Set flag to prevent recursive history operations
        self._navigating_history = True

        try:
            # Update current URL
            self.current_url = entry.url

            # Update URL input
            url_input = self.query_one("#url-input", Input)
            url_input.value = entry.url

            # Update content viewer
            viewer = self.query_one("#content", GemtextViewer)
            viewer.update_content(entry.content)

            # Restore scroll position and link selection
            viewer.scroll_y = entry.scroll_position
            viewer.current_link_index = entry.link_index
        finally:
            self._navigating_history = False

    def _update_navigation_buttons(self) -> None:
        """Update the enabled/disabled state of navigation buttons."""
        back_button = self.query_one("#back-button", Button)
        forward_button = self.query_one("#forward-button", Button)

        back_button.disabled = not self.history.can_go_back()
        forward_button.disabled = not self.history.can_go_forward()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "back-button":
            self.action_navigate_back()
        elif event.button.id == "forward-button":
            self.action_navigate_forward()

    def action_navigate_back(self) -> None:
        """Navigate back in history."""
        if not self.history.can_go_back():
            return

        # Update current state before moving
        self._update_current_history_state()

        # Navigate back
        entry = self.history.go_back()
        if entry:
            self._restore_from_history(entry)
            self._update_navigation_buttons()

    def action_navigate_forward(self) -> None:
        """Navigate forward in history."""
        if not self.history.can_go_forward():
            return

        # Update current state before moving
        self._update_current_history_state()

        # Navigate forward
        entry = self.history.go_forward()
        if entry:
            self._restore_from_history(entry)
            self._update_navigation_buttons()

    # --- Bookmarks ---

    def action_toggle_bookmarks(self) -> None:
        """Toggle the bookmarks sidebar visibility."""
        sidebar = self.query_one("#bookmarks-sidebar", BookmarksSidebar)
        sidebar.toggle_class("-visible")
        if sidebar.has_class("-visible"):
            sidebar.focus()

    def action_add_bookmark(self) -> None:
        """Open the Add Bookmark modal for the current page."""
        if not self.current_url:
            return

        # Try to get a title from the current page content
        suggested_title = self._get_page_title() or self.current_url

        def handle_result(bookmark: Bookmark | None) -> None:
            if bookmark:
                # Refresh the sidebar to show the new bookmark
                sidebar = self.query_one("#bookmarks-sidebar", BookmarksSidebar)
                sidebar.refresh_tree()

        self.push_screen(
            AddBookmarkModal(
                manager=self.bookmarks,
                url=self.current_url,
                suggested_title=suggested_title,
            ),
            handle_result,
        )

    def _get_page_title(self) -> str | None:
        """Extract the page title from the current content (first H1)."""
        viewer = self.query_one("#content", GemtextViewer)
        for line in viewer.lines:
            if line.line_type == LineType.HEADING_1:
                return line.content
        return None

    def on_bookmarks_sidebar_bookmark_selected(
        self, message: BookmarksSidebar.BookmarkSelected
    ) -> None:
        """Handle bookmark selection from sidebar."""
        url = message.bookmark.url

        # Update URL input and navigate
        url_input = self.query_one("#url-input", Input)
        url_input.value = url
        self.get_url(url)

    def on_bookmarks_sidebar_delete_requested(
        self, message: BookmarksSidebar.DeleteRequested
    ) -> None:
        """Handle delete request from sidebar."""
        item = message.item
        if isinstance(item, Bookmark):
            self.bookmarks.remove_bookmark(item.id)
        elif isinstance(item, Folder):
            self.bookmarks.remove_folder(item.id)

        # Refresh sidebar
        sidebar = self.query_one("#bookmarks-sidebar", BookmarksSidebar)
        sidebar.refresh_tree()

    def on_bookmarks_sidebar_edit_requested(
        self, message: BookmarksSidebar.EditRequested
    ) -> None:
        """Handle edit request from sidebar."""

        def handle_result(changed: bool | None) -> None:
            if changed:
                # Refresh the sidebar to show the updated name
                sidebar = self.query_one("#bookmarks-sidebar", BookmarksSidebar)
                sidebar.refresh_tree()

        self.push_screen(
            EditItemModal(
                manager=self.bookmarks,
                item=message.item,
            ),
            handle_result,
        )

    def on_bookmarks_sidebar_new_folder_requested(
        self, message: BookmarksSidebar.NewFolderRequested
    ) -> None:
        """Handle new folder request from sidebar."""
        # For now, create a folder with a default name
        # TODO: Implement folder name input modal
        folder_count = len(self.bookmarks.folders) + 1
        self.bookmarks.add_folder(f"New Folder {folder_count}")

        # Refresh sidebar
        sidebar = self.query_one("#bookmarks-sidebar", BookmarksSidebar)
        sidebar.refresh_tree()


if __name__ == "__main__":
    app = Astronomo()
    app.run()
