from pathlib import Path
from urllib.parse import (
    quote,
    urljoin,
    urlparse,
    urlunparse,
    uses_netloc,
    uses_relative,
)

from nauyaca.client import GeminiClient
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, Input

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder
from astronomo.config import ConfigManager
from astronomo.history import HistoryEntry, HistoryManager
from astronomo.identities import Identity, IdentityManager
from astronomo.parser import LineType, parse_gemtext
from astronomo.response_handler import format_response
from astronomo.widgets import (
    AddBookmarkModal,
    BookmarksSidebar,
    EditItemModal,
    GemtextViewer,
    IdentityErrorModal,
    IdentityErrorResult,
    IdentityResult,
    IdentitySelectModal,
    InputModal,
)

# Register gemini as a valid URL scheme for proper urljoin behavior
if "gemini" not in uses_relative:
    uses_relative.append("gemini")
if "gemini" not in uses_netloc:
    uses_netloc.append("gemini")


def build_query_url(base_url: str, query: str) -> str:
    """Build URL with query string, replacing any existing query.

    Args:
        base_url: The base URL (may already have a query string)
        query: The user input to encode and append

    Returns:
        URL with the encoded query string
    """
    parsed = urlparse(base_url)
    encoded_query = quote(query)
    new_url = urlunparse(parsed._replace(query=encoded_query))
    return new_url


class Astronomo(App[None]):
    """A Gemini browser for the terminal."""

    CSS_PATH = Path("astronomo_app.tcss")

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+b", "toggle_bookmarks", "Bookmarks"),
        ("ctrl+d", "add_bookmark", "Add Bookmark"),
    ]

    def __init__(
        self,
        initial_url: str | None = None,
        config_path: Path | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        # Load configuration FIRST (before other managers)
        self.config_manager = ConfigManager(config_path=config_path)

        # Apply theme from config
        self.theme = self.config_manager.theme

        self.current_url: str = ""
        self.history = HistoryManager(max_size=100)
        self.bookmarks = BookmarkManager()
        self.identities = IdentityManager()
        self._navigating_history = False  # Flag to prevent history loops
        self._initial_url = initial_url  # Store for use in on_mount

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        with Horizontal(id="nav-bar"):
            yield Button("◀", id="back-button", disabled=True)
            yield Button("▶", id="forward-button", disabled=True)
            yield Input(
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
    async def get_url(
        self,
        url: str,
        add_to_history: bool = True,
        identity: Identity | None = None,
    ) -> None:
        """Fetch and display a Gemini resource.

        Args:
            url: The URL to fetch
            add_to_history: Whether to add this fetch to history (default True)
            identity: Optional identity to use (overrides auto-selection)
        """
        import asyncio

        viewer = self.query_one("#content", GemtextViewer)

        # Save current page state to history before navigating away
        if not self._navigating_history and add_to_history:
            self._update_current_history_state()

        # Determine which identity to use (if any)
        selected_identity = identity or self.identities.get_identity_for_url(url)

        # Build client arguments
        client_kwargs: dict = {
            "timeout": self.config_manager.timeout,
            "max_redirects": self.config_manager.max_redirects,
        }

        if selected_identity:
            client_kwargs["client_cert"] = selected_identity.cert_path
            client_kwargs["client_key"] = selected_identity.key_path

        try:
            # Fetch the Gemini resource using configured values
            async with GeminiClient(**client_kwargs) as client:
                response = await client.get(url)

            # Check for input request (status 10/11) BEFORE formatting
            if 10 <= response.status < 20:
                # Schedule modal to show after worker completes
                self.call_later(
                    self._handle_input_request,
                    url,
                    response.meta or "Input required",
                    response.status == 11,  # sensitive input
                )
                return  # Don't continue to format_response

            # Handle certificate required (status 60)
            if response.status == 60:
                self.call_later(
                    self._handle_certificate_required,
                    url,
                    response.meta or "Certificate required",
                )
                return

            # Handle certificate not authorized (status 61)
            if response.status == 61:
                self.call_later(
                    self._handle_certificate_not_authorized,
                    url,
                    response.meta or "Not authorized",
                    selected_identity,
                )
                return

            # Handle certificate not valid (status 62)
            if response.status == 62:
                self.call_later(
                    self._handle_certificate_not_valid,
                    url,
                    response.meta or "Certificate not valid",
                    selected_identity,
                )
                return

            # Handle redirects that weren't followed automatically
            # (e.g., when max_redirects was exceeded or redirect failed)
            if response.is_redirect() and response.redirect_url:
                redirect_url = response.redirect_url
                # Resolve relative redirect URLs
                if not redirect_url.startswith("gemini://"):
                    redirect_url = urljoin(url, redirect_url)
                # Update URL bar
                url_input = self.query_one("#url-input", Input)
                url_input.value = redirect_url
                # Follow the redirect (let the new URL determine if a cert is needed)
                self.get_url(redirect_url, add_to_history=add_to_history)
                return

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
            timeout = self.config_manager.timeout
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after {timeout} seconds.\n\n"
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

    def _handle_input_request(self, url: str, prompt: str, sensitive: bool) -> None:
        """Handle a status 10/11 input request by showing modal.

        Args:
            url: The URL that requested input
            prompt: The prompt text from the server
            sensitive: True for status 11 (password/sensitive input)
        """

        def handle_input_result(user_input: str | None) -> None:
            if user_input is not None:
                # Build new URL with query and fetch
                new_url = build_query_url(url, user_input)
                url_input = self.query_one("#url-input", Input)
                url_input.value = new_url
                self.get_url(new_url)
            # If None (cancelled), stay on current page - do nothing

        self.push_screen(
            InputModal(prompt=prompt, url=url, sensitive=sensitive),
            handle_input_result,
        )

    def _handle_certificate_required(self, url: str, message: str) -> None:
        """Handle status 60: certificate required.

        Args:
            url: The URL that requires authentication
            message: The server's META message
        """

        def handle_result(result: IdentityResult | None) -> None:
            if result is not None:
                # Remember the URL prefix if requested
                if result.remember:
                    parsed = urlparse(url)
                    url_prefix = f"{parsed.scheme}://{parsed.netloc}/"
                    self.identities.add_url_prefix(result.identity.id, url_prefix)

                # Retry with the selected identity
                self.get_url(url, identity=result.identity)

        self.push_screen(
            IdentitySelectModal(
                manager=self.identities,
                url=url,
                message=message,
            ),
            handle_result,
        )

    def _handle_certificate_not_authorized(
        self, url: str, message: str, current_identity: Identity | None
    ) -> None:
        """Handle status 61: certificate not authorized.

        Args:
            url: The URL that rejected the certificate
            message: The server's META message
            current_identity: The identity that was used (if any)
        """

        def handle_result(result: IdentityErrorResult | None) -> None:
            if result is None:
                return

            if result.action == "switch" and result.identity is not None:
                # Retry with the new identity
                self.get_url(url, identity=result.identity)

        self.push_screen(
            IdentityErrorModal(
                manager=self.identities,
                url=url,
                message=message,
                error_type="not_authorized",
                current_identity=current_identity,
            ),
            handle_result,
        )

    def _handle_certificate_not_valid(
        self, url: str, message: str, current_identity: Identity | None
    ) -> None:
        """Handle status 62: certificate not valid.

        Args:
            url: The URL that reported the invalid certificate
            message: The server's META message
            current_identity: The identity that was used (if any)
        """

        def handle_result(result: IdentityErrorResult | None) -> None:
            if result is None:
                return

            if result.action == "regenerate" and result.identity is not None:
                # Retry with the regenerated identity
                self.get_url(url, identity=result.identity)
            elif result.action == "switch" and result.identity is not None:
                # Retry with the new identity
                self.get_url(url, identity=result.identity)

        self.push_screen(
            IdentityErrorModal(
                manager=self.identities,
                url=url,
                message=message,
                error_type="not_valid",
                current_identity=current_identity,
            ),
            handle_result,
        )

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
