import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import (
    quote,
    urljoin,
    urlparse,
    urlunparse,
    uses_netloc,
    uses_relative,
)

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from nauyaca.client import GeminiClient
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, Input

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder
from astronomo.config import ConfigManager
from astronomo.feeds import FeedManager
from astronomo.history import HistoryEntry, HistoryManager
from astronomo.identities import Identity, IdentityManager
from astronomo.parser import LineType, parse_gemtext
from astronomo.response_handler import format_response
from astronomo.screens import FeedsScreen, SettingsScreen
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
    QuickNavigationModal,
    SaveSnapshotModal,
    SessionIdentityModal,
    SessionIdentityResult,
)

# Register gemini as a valid URL scheme for proper urljoin behavior
if "gemini" not in uses_relative:
    uses_relative.append("gemini")
if "gemini" not in uses_netloc:
    uses_netloc.append("gemini")

# Sentinel value for session identity choice "not yet prompted"
_NOT_YET_PROMPTED = object()


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
        ("ctrl+s", "save_snapshot", "Save Snapshot"),
        ("ctrl+k", "quick_navigation", "Quick Nav"),
        ("ctrl+j", "open_feeds", "Feeds"),
        ("ctrl+comma", "toggle_settings", "Settings"),
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
        self.feeds = FeedManager()
        self.identities = IdentityManager()
        self._navigating_history = False  # Flag to prevent history loops
        self._initial_url = initial_url
        # Session identity choices (persisted to disk with remember_choice mode)
        # Key: URL prefix, Value: Identity or None (anonymous)
        self._session_identity_choices: dict[str, Identity | None] = {}
        self._session_choices_path = (
            self.config_manager.config_dir / "session_choices.toml"
        )
        self._load_session_choices()

    def compose(self) -> ComposeResult:
        """Compose the main browsing UI."""
        yield Header()
        with Horizontal(id="nav-bar"):
            yield Button("\u25c0", id="back-button", disabled=True)
            yield Button("\u25b6", id="forward-button", disabled=True)
            yield Input(id="url-input")
            yield Button("\u2699", id="settings-button")
        with Horizontal(id="main-content"):
            yield GemtextViewer(id="content")
            yield BookmarksSidebar(self.bookmarks, id="bookmarks-sidebar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the viewer with a welcome message or load initial URL."""
        viewer = self.query_one("#content", GemtextViewer)

        # Use initial URL from command line, or fall back to configured home page
        url = self._initial_url or self.config_manager.home_page

        if url:
            # Auto-prefix gemini:// if not present
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
        skip_session_prompt: bool = False,
    ) -> None:
        """Fetch and display a Gemini resource.

        Args:
            url: The URL to fetch
            add_to_history: Whether to add this fetch to history (default True)
            identity: Optional identity to use (overrides auto-selection)
            skip_session_prompt: If True, skip session identity modal (internal use)
        """
        import asyncio

        viewer = self.query_one("#content", GemtextViewer)

        # Save current page state to history before navigating away
        if not self._navigating_history and add_to_history:
            self._update_current_history_state()

        # Session identity selection: prompt user before making request
        if identity is None and not skip_session_prompt:
            choice = self._get_session_identity_choice(url)

            if choice is _NOT_YET_PROMPTED:
                # Check if any identities match this URL
                matching = self.identities.get_all_identities_for_url(url)
                if matching:
                    prompt_behavior = self.config_manager.identity_prompt

                    if prompt_behavior == "remember_choice":
                        # Never prompt - proceed without identity
                        # (User must explicitly select via status 60 or settings)
                        pass
                    elif prompt_behavior == "when_ambiguous":
                        if len(matching) == 1:
                            # Auto-select the only matching identity
                            identity = matching[0]
                            # Store in session memory for consistency
                            prefix = self._get_session_prefix_for_url(url)
                            self._session_identity_choices[prefix] = identity
                            self._save_session_choice(prefix, identity)
                        else:
                            # Multiple matches - show modal
                            self.call_later(
                                self._handle_session_identity_prompt,
                                url,
                                matching,
                                add_to_history,
                            )
                            return
                    else:  # "every_time"
                        # Always show modal
                        self.call_later(
                            self._handle_session_identity_prompt,
                            url,
                            matching,
                            add_to_history,
                        )
                        return
            elif isinstance(choice, Identity):
                # User previously chose an identity for this session
                identity = choice
            # else: choice is None means "anonymous" was chosen, proceed without identity

        # Determine which identity to use (if any)
        # Note: If identity is already set (from session or parameter), use it
        # Otherwise fall back to auto-selection (shouldn't happen with session prompts)
        selected_identity = identity

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

    def action_toggle_settings(self) -> None:
        """Toggle settings modal on/off."""
        if isinstance(self.screen, SettingsScreen):
            self.pop_screen()
        else:
            self.push_screen(SettingsScreen())

    def action_quick_navigation(self) -> None:
        """Toggle quick navigation modal for fuzzy finding."""
        # If already open, close it
        if isinstance(self.screen, QuickNavigationModal):
            self.pop_screen()
            return

        def handle_result(url: str | None) -> None:
            if url is not None:
                # Navigate to the selected URL
                url_input = self.query_one("#url-input", Input)
                url_input.value = url
                self.get_url(url)

        self.push_screen(
            QuickNavigationModal(
                bookmark_manager=self.bookmarks,
                history_manager=self.history,
            ),
            handle_result,
        )

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
                # Remember the URL prefix if requested (persistent)
                if result.remember:
                    parsed = urlparse(url)
                    url_prefix = f"{parsed.scheme}://{parsed.netloc}/"
                    self.identities.add_url_prefix(result.identity.id, url_prefix)

                # Also update session choice so subsequent requests use this identity
                session_prefix = self._get_session_prefix_for_url(url)
                self._session_identity_choices[session_prefix] = result.identity
                self._save_session_choice(session_prefix, result.identity)

                # Retry with the selected identity
                self.get_url(url, identity=result.identity, skip_session_prompt=True)

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
                # Update session choice
                session_prefix = self._get_session_prefix_for_url(url)
                self._session_identity_choices[session_prefix] = result.identity
                self._save_session_choice(session_prefix, result.identity)
                # Retry with the new identity
                self.get_url(url, identity=result.identity, skip_session_prompt=True)

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
                # Update session choice
                session_prefix = self._get_session_prefix_for_url(url)
                self._session_identity_choices[session_prefix] = result.identity
                self._save_session_choice(session_prefix, result.identity)
                # Retry with the regenerated identity
                self.get_url(url, identity=result.identity, skip_session_prompt=True)
            elif result.action == "switch" and result.identity is not None:
                # Update session choice
                session_prefix = self._get_session_prefix_for_url(url)
                self._session_identity_choices[session_prefix] = result.identity
                self._save_session_choice(session_prefix, result.identity)
                # Retry with the new identity
                self.get_url(url, identity=result.identity, skip_session_prompt=True)

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

    def _get_session_prefix_for_url(self, url: str) -> str:
        """Get host-level prefix for session identity storage.

        Args:
            url: The URL to get the prefix for

        Returns:
            URL prefix in the form "scheme://host/"
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/"

    def _load_session_choices(self) -> None:
        """Load persisted session identity choices from disk."""
        if not self._session_choices_path.exists():
            return

        try:
            with open(self._session_choices_path, "rb") as f:
                data = tomllib.load(f)

            choices = data.get("choices", {})
            for prefix, identity_id in choices.items():
                if identity_id == "anonymous":
                    self._session_identity_choices[prefix] = None
                else:
                    # Look up the identity by ID
                    identity = self.identities.get_identity(identity_id)
                    if identity and self.identities.is_identity_valid(identity.id):
                        self._session_identity_choices[prefix] = identity
                    # If identity not found or invalid, skip it (will re-prompt)
        except (tomllib.TOMLDecodeError, OSError):
            # If file is corrupted, start fresh
            pass

    def _save_session_choice(self, prefix: str, identity: Identity | None) -> None:
        """Save a session identity choice to disk.

        Args:
            prefix: The URL prefix (e.g., "gemini://example.com/")
            identity: The chosen identity, or None for anonymous
        """
        # Load existing choices
        choices: dict[str, Any] = {}
        if self._session_choices_path.exists():
            try:
                with open(self._session_choices_path, "rb") as f:
                    data = tomllib.load(f)
                choices = data.get("choices", {})
            except (tomllib.TOMLDecodeError, OSError):
                pass

        # Update with the new choice
        if identity is None:
            choices[prefix] = "anonymous"
        else:
            choices[prefix] = identity.id

        # Write back
        self.config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._session_choices_path, "wb") as f:
            tomli_w.dump({"choices": choices}, f)

    def _get_session_identity_choice(self, url: str) -> Identity | None | object:
        """Get the session's identity choice for a URL.

        Args:
            url: The URL to check

        Returns:
            - Identity: User chose this identity for this prefix
            - None: User chose "anonymous" (no identity)
            - _NOT_YET_PROMPTED: No choice made yet for this prefix
        """
        prefix = self._get_session_prefix_for_url(url)

        if prefix in self._session_identity_choices:
            choice = self._session_identity_choices[prefix]
            if choice is None:
                return None  # Anonymous choice

            # Validate the identity is still usable
            if self.identities.is_identity_valid(choice.id):
                return choice
            else:
                # Identity expired/invalid - remove from session and re-prompt
                del self._session_identity_choices[prefix]
                return _NOT_YET_PROMPTED

        return _NOT_YET_PROMPTED

    def _handle_session_identity_prompt(
        self,
        url: str,
        matching_identities: list[Identity],
        add_to_history: bool,
    ) -> None:
        """Show session identity selection modal and handle result.

        Args:
            url: The URL being navigated to
            matching_identities: List of identities that match the URL
            add_to_history: Whether to add the navigation to history
        """

        def handle_result(result: SessionIdentityResult | None) -> None:
            if result is None or result.cancelled:
                # User cancelled - stay on current page
                return

            # Store the session choice
            prefix = self._get_session_prefix_for_url(url)
            self._session_identity_choices[prefix] = result.identity
            self._save_session_choice(prefix, result.identity)

            # Re-fetch with the chosen identity (or None for anonymous)
            self.get_url(
                url,
                add_to_history=add_to_history,
                identity=result.identity,
                skip_session_prompt=True,
            )

        self.push_screen(
            SessionIdentityModal(
                manager=self.identities,
                url=url,
                matching_identities=matching_identities,
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
        elif event.button.id == "settings-button":
            self.action_toggle_settings()

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

    def action_save_snapshot(self) -> None:
        """Save a snapshot of the current page."""
        if not self.current_url:
            self.notify("No page loaded. Navigate to a page first.", severity="warning")
            return

        # Get the viewer to access current content
        viewer = self.query_one("#content", GemtextViewer)
        if not viewer.lines:
            self.notify("No content to save. The page is empty.", severity="warning")
            return

        # Determine snapshot directory (config or default)
        snapshot_dir_str = self.config_manager.snapshots_directory
        if snapshot_dir_str:
            snapshot_dir = Path(snapshot_dir_str).expanduser()
        else:
            # Default: ~/.local/share/astronomo/snapshots
            snapshot_dir = Path.home() / ".local" / "share" / "astronomo" / "snapshots"

        # Ensure directory exists
        try:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            self.notify(
                f"Cannot create directory: {snapshot_dir}. Permission denied.",
                severity="error",
            )
            return
        except OSError as e:
            self.notify(f"Cannot create directory: {e}", severity="error")
            return

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Try to create a meaningful filename from the URL
        parsed = urlparse(self.current_url)
        hostname = parsed.netloc or "page"
        # Clean up hostname to be filesystem-safe: keep only alphanumeric, dots, hyphens, underscores
        hostname = re.sub(r"[^\w.-]", "_", hostname)
        # Prevent directory traversal
        hostname = hostname.replace("..", "__")
        # Limit length to reasonable filesystem bound
        hostname = hostname[:100]

        filename = f"{hostname}_{timestamp}.gmi"
        save_path = snapshot_dir / filename

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                try:
                    # Reconstruct the original gemtext from parsed lines
                    gemtext_lines = [line.raw for line in viewer.lines]
                    content = "\n".join(gemtext_lines)

                    # Write to file
                    save_path.write_text(content, encoding="utf-8")

                    self.notify(
                        f"Saved to {save_path.name}",
                        title="Snapshot Saved",
                        severity="information",
                    )
                except PermissionError:
                    self.notify(
                        f"Cannot write to {snapshot_dir}. Permission denied.",
                        severity="error",
                    )
                except OSError as e:
                    self.notify(f"Failed to save snapshot: {e}", severity="error")

        self.push_screen(
            SaveSnapshotModal(url=self.current_url, save_path=save_path),
            handle_result,
        )

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

    # --- Feeds ---

    def action_open_feeds(self) -> None:
        """Open the feeds screen."""
        self.push_screen(FeedsScreen(self.feeds))


if __name__ == "__main__":
    app = Astronomo()
    app.run()
