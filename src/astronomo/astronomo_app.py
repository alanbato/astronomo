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
from nauyaca.security.tofu import CertificateChangedError, TOFUDatabase
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, Input

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder
from astronomo.config import ConfigManager
from astronomo.feeds import FeedManager
from astronomo.history import HistoryEntry, HistoryManager
from astronomo.identities import Identity, IdentityManager
from astronomo.media_detector import MediaDetector
from astronomo.parser import GemtextLine, LineType, parse_gemtext
from astronomo.response_handler import format_response
from astronomo.widgets.gemtext_image import CHAFA_AVAILABLE
from astronomo.screens import FeedsScreen, SettingsScreen
from astronomo.tabs import Tab, TabManager
from astronomo.widgets import (
    AddBookmarkModal,
    BookmarksSidebar,
    CertificateChangedModal,
    CertificateChangedResult,
    CertificateDetailsModal,
    CertificateDetailsResult,
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
    TabBar,
)

# Register URL schemes for proper urljoin behavior
for scheme in ("gemini", "gopher", "finger", "nex", "spartan"):
    if scheme not in uses_relative:
        uses_relative.append(scheme)
    if scheme not in uses_netloc:
        uses_netloc.append(scheme)

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
        # Tab management
        ("ctrl+t", "new_tab", "New Tab"),
        ("ctrl+w", "close_tab", "Close Tab"),
        ("ctrl+tab", "next_tab", "Next Tab"),
        ("ctrl+shift+tab", "prev_tab", "Prev Tab"),
        ("ctrl+1", "jump_to_tab_1", ""),
        ("ctrl+2", "jump_to_tab_2", ""),
        ("ctrl+3", "jump_to_tab_3", ""),
        ("ctrl+4", "jump_to_tab_4", ""),
        ("ctrl+5", "jump_to_tab_5", ""),
        ("ctrl+6", "jump_to_tab_6", ""),
        ("ctrl+7", "jump_to_tab_7", ""),
        ("ctrl+8", "jump_to_tab_8", ""),
        ("ctrl+9", "jump_to_tab_9", ""),
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

        # Tab management - replaces single-page state
        self.tab_manager = TabManager(max_tabs=20)
        self.bookmarks = BookmarkManager()
        self.feeds = FeedManager()
        self.identities = IdentityManager()
        self._navigating_history = False  # Flag to prevent history loops
        self._initial_url = initial_url

        # Image cache for inline image display
        from astronomo.image_cache import ImageCache

        self.image_cache = ImageCache()
        # Global session identity choices (shared across tabs, persisted to disk)
        self._global_session_identity_choices: dict[str, Identity | None] = {}
        self._session_choices_path = (
            self.config_manager.config_dir / "session_choices.toml"
        )
        self._load_session_choices()

    # --- Tab State Properties (delegate to active tab) ---

    @property
    def current_url(self) -> str:
        """Get the current URL from the active tab."""
        tab = self.tab_manager.current_tab()
        return tab.url if tab else ""

    @current_url.setter
    def current_url(self, value: str) -> None:
        """Set the current URL on the active tab."""
        tab = self.tab_manager.current_tab()
        if tab:
            tab.url = value

    @property
    def history(self) -> HistoryManager:
        """Get the history manager for the active tab."""
        tab = self.tab_manager.current_tab()
        if tab:
            return tab.history
        # Return an empty manager if no tab (shouldn't happen in practice)
        return HistoryManager(max_size=100)

    @property
    def _session_identity_choices(self) -> dict[str, Identity | None]:
        """Get global session identity choices (shared across all tabs)."""
        return self._global_session_identity_choices

    def compose(self) -> ComposeResult:
        """Compose the main browsing UI."""
        yield Header()
        yield TabBar(id="tab-bar")
        with Horizontal(id="nav-bar"):
            yield Button("\u25c0", id="back-button", disabled=True)
            yield Button("\u25b6", id="forward-button", disabled=True)
            url_input = Input(id="url-input")
            url_input.border_title = "Address"
            yield url_input
            yield Button("\u2699", id="settings-button")
        with Horizontal(id="main-content"):
            yield GemtextViewer(id="content")
            yield BookmarksSidebar(self.bookmarks, id="bookmarks-sidebar")
        yield Footer()

    def _get_welcome_content(self) -> list[GemtextLine]:
        """Generate the welcome message with starry night ASCII art.

        Returns:
            List of parsed Gemtext lines for the welcome screen
        """
        starry_night = """\
   '                                                   o         .:'                           '       '
        _|_     '                     .                      _.::'                  \\                        o  o   .
         |                 '     '              +           (_.'           .         \\  .      +
 '              o       o                                                         '   *                        +    |
                                   |              |          .   +         +              +                       --o--
                                 - o -      .    -+-                                                        '       |
                                   |              |                   +          / '                '
                                               '                                /        o
                                                                               *
                    .         .      .                 |                                    '                          +
                                '                    - o -                                    .               .
           .                  +                        |                            .
                                                                                                       .
   *                    +~~   o                                     .       .            '
                                                                                                         .
          o                                                               .          '
                              .                    '  *                                        _..
              o                                                                              '`-. `.
   .                                   .   '                |                        .           \\  \\
                   .                          +           --o--                          '       |  |                  .
          .                                                 |                  +                 /  /   o
                                             '                          '            .:'  +  _.-`_.`           +
                                                                  +              _.::'        '''                '
. *                                         .                                   (_.'
                                              \\                     .:'                                '
                                               \\   .            _.::'       '      o   /
   +        ' o                   /             *         .    (_.'    *              /  _|_
                 ~~+      .      /                                                   *    |           '  .      +
       .                        *           +        +       +
                                    +                                                            .                      """
        welcome_text = (
            "# Welcome to Astronomo!\n\n"
            "```\n" + starry_night + "\n```\n\n"
            "Enter a URL above to get started.\n\n"
            "Supported protocols: Gemini, Gopher, Finger, Nex, Spartan"
        )
        return parse_gemtext(welcome_text)

    def on_mount(self) -> None:
        """Initialize the viewer with a welcome message or load initial URL."""
        viewer = self.query_one("#content", GemtextViewer)

        # Use initial URL from command line, or fall back to configured home page
        url = self._initial_url or self.config_manager.home_page

        # Create initial tab
        initial_title = "New Tab"
        if url:
            url = self._normalize_url(url)
            initial_title = urlparse(url).netloc or url[:20]
        self.tab_manager.create_tab(url=url or "", title=initial_title)
        self._update_tab_bar()

        if url:
            # Update URL input
            url_input = self.query_one("#url-input", Input)
            url_input.value = url

            # Show loading message and fetch
            loading_text = f"# Fetching\n\n{url}\n\nPlease wait..."
            viewer.update_content(parse_gemtext(loading_text))
            viewer.focus()
            self.get_url(url)
        else:
            # Show welcome message with starry night ASCII art
            viewer.update_content(self._get_welcome_content())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle URL submission and fetch content."""
        url = event.value.strip()
        if not url:
            return

        # Normalize URL with smart scheme detection
        url = self._normalize_url(url)

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
        search_query: str | None = None,
        spartan_data: str | None = None,
    ) -> None:
        """Fetch and display a resource via any supported protocol.

        Args:
            url: The URL to fetch
            add_to_history: Whether to add this fetch to history (default True)
            identity: Optional identity to use (overrides auto-selection, Gemini only)
            skip_session_prompt: If True, skip session identity modal (internal use)
            search_query: Search query for Gopher type 7 items
        """
        import asyncio

        viewer = self.query_one("#content", GemtextViewer)
        parsed = urlparse(url)
        scheme = parsed.scheme.lower() or "gemini"

        # Save current page state to history before navigating away
        if not self._navigating_history and add_to_history:
            self._update_current_history_state()

        # Route to appropriate protocol handler
        if scheme == "gopher":
            await self._fetch_gopher(url, viewer, add_to_history, search_query)
            return
        elif scheme == "finger":
            await self._fetch_finger(url, viewer, add_to_history)
            return
        elif scheme == "spartan":
            await self._fetch_spartan(
                url, viewer, add_to_history, spartan_data=spartan_data
            )
            return
        elif scheme == "nex":
            await self._fetch_nex(url, viewer, add_to_history)
            return
        elif scheme != "gemini":
            error = f"# Unsupported Protocol\n\nScheme '{scheme}' is not supported."
            viewer.update_content(parse_gemtext(error))
            return

        # Gemini protocol handling continues below...

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

            # Handle binary content (non-text MIME types) or images detected by extension
            mime_type = response.mime_type or "text/gemini"

            # Check for binary content OR image URL (servers may return text/gemini for images)
            is_image_url = MediaDetector.is_image(mime_type, url)
            if not mime_type.startswith("text/") or is_image_url:
                parsed_url = urlparse(url)
                filename = parsed_url.path.split("/")[-1] or "download"

                # Ensure body is bytes
                body = response.body
                if isinstance(body, str):
                    body = body.encode("utf-8")

                # Try to display image inline if enabled
                if (
                    body
                    and is_image_url
                    and self.config_manager.show_images
                    and CHAFA_AVAILABLE
                ):
                    # Display image inline
                    result = await self._handle_image_display(
                        url, filename, body, mime_type, viewer, add_to_history
                    )
                    if result:
                        return  # Successfully displayed image
                    # If image display failed, fall through to download

                # Binary file - download to ~/Downloads
                if body:
                    filepath = await self._handle_binary_download(
                        filename, body, mime_type
                    )
                    # Show success message with Open link
                    success_text = (
                        f"# Download Complete\n\n"
                        f"File: {filepath.name}\n"
                        f"Type: {mime_type}\n\n"
                        f"Saved to ~/Downloads\n\n"
                        f"=> file://{filepath} 📂 Open File"
                    )
                    parsed_lines = parse_gemtext(success_text)
                    viewer.update_content(parsed_lines)

                    # Update state and history
                    self.current_url = url
                    url_input = self.query_one("#url-input", Input)
                    url_input.value = url

                    if not self._navigating_history and add_to_history:
                        entry = HistoryEntry(
                            url=url,
                            content=parsed_lines,
                            scroll_position=0,
                            link_index=0,
                            status=response.status,
                            meta=response.meta,
                            mime_type=mime_type,
                        )
                        self.history.push(entry)
                        self._update_navigation_buttons()
                else:
                    error_text = (
                        f"# Error\n\nEmpty response body for binary file: {url}"
                    )
                    self._display_error_page(url, error_text, viewer, add_to_history)
                return

            # Store current URL for relative link resolution
            # Use response.url (final URL after redirects) for correct resolution
            final_url = response.url or url
            self.current_url = final_url

            # Update URL bar
            url_input = self.query_one("#url-input", Input)
            url_input.value = final_url

            # Format and display the response (now returns list[GemtextLine])
            parsed_lines = format_response(final_url, response)
            viewer.update_content(parsed_lines)

            # Save successful response to history (only status 20-29)
            if (
                not self._navigating_history
                and add_to_history
                and response.is_success()
            ):
                entry = HistoryEntry(
                    url=final_url,
                    content=parsed_lines,
                    scroll_position=0,
                    link_index=0,
                    status=response.status,
                    meta=response.meta,
                    mime_type=response.mime_type or "text/gemini",
                )
                self.history.push(entry)
                self._update_navigation_buttons()
                # Update tab title from page content
                self._update_tab_title()
        except asyncio.TimeoutError:
            timeout = self.config_manager.timeout
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after {timeout} seconds.\n\n"
                f"The server may be down or not responding. Please try again later."
            )
            self._display_error_page(url, error_text, viewer, add_to_history)
        except CertificateChangedError as e:
            # TOFU violation - server certificate has changed
            self.call_later(
                self._handle_certificate_changed,
                url,
                e.hostname,
                e.port,
                e.old_fingerprint,
                e.new_fingerprint,
            )
        except Exception as e:
            error_text = f"# Error\n\nFailed to fetch {url}:\n\n{e!r}"
            self._display_error_page(url, error_text, viewer, add_to_history)

    def on_gemtext_viewer_link_activated(
        self, message: GemtextViewer.LinkActivated
    ) -> None:
        """Handle link activation from the viewer."""
        link_url = message.link.url
        parsed = urlparse(link_url)

        # Check if it's an absolute URL with a supported scheme
        if parsed.scheme in ("gemini", "gopher", "finger", "nex", "spartan"):
            pass  # Use as-is
        elif parsed.scheme in ("http", "https"):
            self._open_external_link(link_url)
            return
        elif parsed.scheme == "file":
            # Local file - open with system default application
            self._open_local_file(parsed.path)
            return
        elif parsed.scheme:
            self.notify(f"Unsupported scheme: {parsed.scheme}", severity="warning")
            return
        else:
            # Relative URL - resolve against current URL
            link_url = urljoin(self.current_url, link_url)
            parsed = urlparse(link_url)

        # Check if this is a Spartan input link (=:)
        if message.link.is_input_link and parsed.scheme == "spartan":
            # Show input modal for Spartan input links
            prompt = message.link.label or "Enter data"
            self.call_later(
                self._handle_spartan_input,
                link_url,
                prompt,
                message.link.label,
                message.new_tab,
            )
            return

        if message.new_tab:
            # Open link in a new tab
            self._open_in_new_tab(link_url)
        else:
            # Update URL input and fetch in current tab
            url_input = self.query_one("#url-input", Input)
            url_input.value = link_url
            self.get_url(link_url)

    def on_gemtext_image_widget_download_requested(self, message) -> None:
        """Handle image download button from image widget."""
        # Use image data from the widget (already in memory)
        self.call_later(
            self._download_cached_image,
            message.filename,
            message.image_data,
        )

    async def _download_cached_image(self, filename: str, data: bytes) -> None:
        """Download a cached image to ~/Downloads.

        Args:
            filename: Suggested filename
            data: Image data
        """
        await self._handle_binary_download(filename, data, None)

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

    def _handle_certificate_changed(
        self,
        url: str,
        hostname: str,
        port: int,
        old_fingerprint: str,
        new_fingerprint: str,
    ) -> None:
        """Handle TOFU violation: server certificate has changed.

        Args:
            url: The URL being accessed
            hostname: The server hostname
            port: The server port
            old_fingerprint: The previously trusted fingerprint
            new_fingerprint: The new certificate fingerprint
        """
        # Get host info from TOFU database for details modal
        tofu_db = TOFUDatabase()
        host_info = tofu_db.get_host_info(hostname, port)
        first_seen = host_info.get("first_seen") if host_info else None
        last_seen = host_info.get("last_seen") if host_info else None

        def handle_result(result: CertificateChangedResult | None) -> None:
            if result is None:
                return

            if result.action == "accept":
                self._accept_changed_certificate(url, hostname, port, new_fingerprint)
            elif result.action == "details":
                self._show_certificate_details(
                    url,
                    hostname,
                    port,
                    old_fingerprint,
                    new_fingerprint,
                    first_seen,
                    last_seen,
                )
            # "reject" action: do nothing, just leave the error displayed

        self.push_screen(
            CertificateChangedModal(
                hostname=hostname,
                port=port,
                old_fingerprint=old_fingerprint,
                new_fingerprint=new_fingerprint,
            ),
            handle_result,
        )

    def _show_certificate_details(
        self,
        url: str,
        hostname: str,
        port: int,
        old_fingerprint: str,
        new_fingerprint: str,
        first_seen: str | None,
        last_seen: str | None,
    ) -> None:
        """Show detailed certificate comparison modal.

        Args:
            url: The URL being accessed
            hostname: The server hostname
            port: The server port
            old_fingerprint: The previously trusted fingerprint
            new_fingerprint: The new certificate fingerprint
            first_seen: When the host was first trusted
            last_seen: When the host was last accessed
        """

        def handle_result(result: CertificateDetailsResult | None) -> None:
            if result is None:
                return

            if result.action == "accept":
                self._accept_changed_certificate(url, hostname, port, new_fingerprint)
            # "reject" action: do nothing

        self.push_screen(
            CertificateDetailsModal(
                hostname=hostname,
                port=port,
                old_fingerprint=old_fingerprint,
                new_fingerprint=new_fingerprint,
                first_seen=first_seen,
                last_seen=last_seen,
            ),
            handle_result,
        )

    def _accept_changed_certificate(
        self, url: str, hostname: str, port: int, new_fingerprint: str
    ) -> None:
        """Accept a changed certificate and retry the request.

        This revokes the old trust and retries the request. The retry will
        encounter a "first use" scenario and auto-trust the certificate.

        Security note: If the certificate changes again between revoke and
        retry (e.g., MITM attack), the user will see another warning modal
        because CertificateChangedError or a new first-use prompt will occur.
        This is the expected TOFU behavior.

        Args:
            url: The URL to retry
            hostname: The server hostname
            port: The server port
            new_fingerprint: The new certificate fingerprint the user reviewed
        """
        try:
            tofu_db = TOFUDatabase()
            tofu_db.revoke(hostname, port)
            self.notify(
                f"Trusting new certificate for {hostname}:{port}",
                severity="information",
            )
        except Exception as e:
            self.notify(
                f"Failed to update trust database: {e}",
                severity="error",
            )
            return

        # Retry the request - it will be treated as first use and auto-trusted
        self.get_url(url)

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

    # -------------------------------------------------------------------------
    # Protocol Handlers (Finger, Gopher)
    # -------------------------------------------------------------------------

    async def _fetch_finger(
        self, url: str, viewer: GemtextViewer, add_to_history: bool
    ) -> None:
        """Fetch and display a Finger resource.

        Args:
            url: The finger:// URL to fetch
            viewer: The GemtextViewer to update
            add_to_history: Whether to add to history
        """
        import asyncio

        from astronomo.formatters.finger import fetch_finger

        try:
            parsed_lines = await fetch_finger(url, timeout=self.config_manager.timeout)

            self.current_url = url
            self.query_one("#url-input", Input).value = url
            viewer.update_content(parsed_lines)

            if not self._navigating_history and add_to_history:
                entry = HistoryEntry(
                    url=url,
                    content=parsed_lines,
                    scroll_position=0,
                    link_index=0,
                    status=20,
                    meta="",
                    mime_type="text/plain",
                )
                self.history.push(entry)
                self._update_navigation_buttons()
                self._update_tab_title()
        except asyncio.TimeoutError:
            timeout = self.config_manager.timeout
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after {timeout} seconds.\n\n"
                f"The server may be down or not responding."
            )
            self._display_error_page(url, error_text, viewer, add_to_history)
        except Exception as e:
            error_text = f"# Error\n\nFailed to fetch {url}:\n\n{e!r}"
            self._display_error_page(url, error_text, viewer, add_to_history)

    async def _fetch_nex(
        self, url: str, viewer: GemtextViewer, add_to_history: bool
    ) -> None:
        """Fetch and display a Nex resource.

        Args:
            url: The nex:// URL to fetch
            viewer: The GemtextViewer to update
            add_to_history: Whether to add to history
        """
        import asyncio

        from astronomo.formatters.nex import fetch_nex

        try:
            result = await fetch_nex(url, timeout=self.config_manager.timeout)

            # Handle binary download
            if result.is_binary and result.binary_data:
                filename = result.filename or "download"
                filepath = await self._handle_binary_download(
                    filename, result.binary_data
                )
                # Show success message with Open link
                success_text = (
                    f"# Download Complete\n\n"
                    f"File: {filepath.name}\n\n"
                    f"Saved to ~/Downloads\n\n"
                    f"=> file://{filepath} 📂 Open File"
                )
                parsed_lines = parse_gemtext(success_text)
                self.current_url = url
                self.query_one("#url-input", Input).value = url
                viewer.update_content(parsed_lines)

                if not self._navigating_history and add_to_history:
                    entry = HistoryEntry(
                        url=url,
                        content=parsed_lines,
                        scroll_position=0,
                        link_index=0,
                        status=20,
                        meta="",
                        mime_type="application/octet-stream",
                    )
                    self.history.push(entry)
                    self._update_navigation_buttons()
                return

            # Normal text content
            self.current_url = url
            self.query_one("#url-input", Input).value = url
            viewer.update_content(result.content)

            if not self._navigating_history and add_to_history:
                entry = HistoryEntry(
                    url=url,
                    content=result.content,
                    scroll_position=0,
                    link_index=0,
                    status=20,
                    meta="",
                    mime_type="text/plain",
                )
                self.history.push(entry)
                self._update_navigation_buttons()
                self._update_tab_title()
        except asyncio.TimeoutError:
            timeout = self.config_manager.timeout
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after {timeout} seconds.\n\n"
                f"The server may be down or not responding."
            )
            self._display_error_page(url, error_text, viewer, add_to_history)
        except Exception as e:
            error_text = f"# Error\n\nFailed to fetch {url}:\n\n{e!r}"
            self._display_error_page(url, error_text, viewer, add_to_history)

    async def _fetch_spartan(
        self,
        url: str,
        viewer: GemtextViewer,
        add_to_history: bool,
        redirect_count: int = 0,
        spartan_data: str | None = None,
    ) -> None:
        """Fetch and display a Spartan resource.

        Args:
            url: The spartan:// URL to fetch
            viewer: The GemtextViewer to update
            add_to_history: Whether to add to history
            redirect_count: Number of redirects followed so far (internal)
            spartan_data: Optional data to upload (for input links =:)
        """
        import asyncio

        from astronomo.formatters.spartan import fetch_spartan

        try:
            result = await fetch_spartan(
                url,
                timeout=self.config_manager.timeout,
                data=spartan_data,
            )

            # Handle redirect - track redirect count to prevent loops
            if result.is_redirect and result.redirect_url:
                if redirect_count >= self.config_manager.max_redirects:
                    error_text = (
                        f"# Too Many Redirects\n\n"
                        f"Exceeded maximum of {self.config_manager.max_redirects} redirects.\n\n"
                        f"The server may be misconfigured or there may be a redirect loop."
                    )
                    self._display_error_page(url, error_text, viewer, add_to_history)
                    return
                # Don't pass spartan_data on redirect (only send data on initial request)
                await self._fetch_spartan(
                    result.redirect_url,
                    viewer,
                    add_to_history,
                    redirect_count + 1,
                    spartan_data=None,
                )
                return

            # Handle binary download
            if result.is_binary and result.binary_data:
                filename = result.filename or "download"
                filepath = await self._handle_binary_download(
                    filename, result.binary_data, result.mime_type
                )
                # Show success message with Open link
                success_text = (
                    f"# Download Complete\n\n"
                    f"File: {filepath.name}\n"
                    f"Type: {result.mime_type}\n\n"
                    f"Saved to ~/Downloads\n\n"
                    f"=> file://{filepath} 📂 Open File"
                )
                parsed_lines = parse_gemtext(success_text)
                self.current_url = result.final_url
                self.query_one("#url-input", Input).value = result.final_url
                viewer.update_content(parsed_lines)

                if not self._navigating_history and add_to_history:
                    entry = HistoryEntry(
                        url=result.final_url,
                        content=parsed_lines,
                        scroll_position=0,
                        link_index=0,
                        status=20,
                        meta="",
                        mime_type=result.mime_type,
                    )
                    self.history.push(entry)
                    self._update_navigation_buttons()
                return

            # Normal text content
            self.current_url = result.final_url
            self.query_one("#url-input", Input).value = result.final_url
            viewer.update_content(result.content)

            if not self._navigating_history and add_to_history:
                entry = HistoryEntry(
                    url=result.final_url,
                    content=result.content,
                    scroll_position=0,
                    link_index=0,
                    status=20,
                    meta="",
                    mime_type=result.mime_type,
                )
                self.history.push(entry)
                self._update_navigation_buttons()
                self._update_tab_title()
        except asyncio.TimeoutError:
            timeout = self.config_manager.timeout
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after {timeout} seconds.\n\n"
                f"The server may be down or not responding."
            )
            self._display_error_page(url, error_text, viewer, add_to_history)
        except Exception as e:
            error_text = f"# Error\n\nFailed to fetch {url}:\n\n{e!r}"
            self._display_error_page(url, error_text, viewer, add_to_history)

    async def _fetch_gopher(
        self,
        url: str,
        viewer: GemtextViewer,
        add_to_history: bool,
        search_query: str | None,
    ) -> None:
        """Fetch and display a Gopher resource.

        Args:
            url: The gopher:// URL to fetch
            viewer: The GemtextViewer to update
            add_to_history: Whether to add to history
            search_query: Search query for type 7 items
        """
        import asyncio

        from astronomo.formatters.gopher import fetch_gopher

        try:
            result = await fetch_gopher(
                url,
                timeout=self.config_manager.timeout,
                search_query=search_query,
            )

            # Handle search input required (type 7)
            if result.requires_search:
                self.call_later(
                    self._handle_gopher_search,
                    url,
                    result.search_prompt or "Search",
                )
                return

            # Handle binary download
            if result.is_binary and result.binary_data:
                filename = result.filename or "download"
                filepath = await self._handle_binary_download(
                    filename, result.binary_data
                )
                # Show success message with Open link
                success_text = (
                    f"# Download Complete\n\n"
                    f"File: {filepath.name}\n\n"
                    f"Saved to ~/Downloads\n\n"
                    f"=> file://{filepath} 📂 Open File"
                )
                parsed_lines = parse_gemtext(success_text)
                self.current_url = url
                self.query_one("#url-input", Input).value = url
                viewer.update_content(parsed_lines)

                if not self._navigating_history and add_to_history:
                    entry = HistoryEntry(
                        url=url,
                        content=parsed_lines,
                        scroll_position=0,
                        link_index=0,
                        status=20,
                        meta="",
                        mime_type="application/octet-stream",
                    )
                    self.history.push(entry)
                    self._update_navigation_buttons()
                return

            self.current_url = url
            self.query_one("#url-input", Input).value = url
            viewer.update_content(result.content)

            if not self._navigating_history and add_to_history:
                entry = HistoryEntry(
                    url=url,
                    content=result.content,
                    scroll_position=0,
                    link_index=0,
                    status=20,
                    meta="",
                    mime_type="text/gopher",
                )
                self.history.push(entry)
                self._update_navigation_buttons()
                self._update_tab_title()
        except asyncio.TimeoutError:
            timeout = self.config_manager.timeout
            error_text = (
                f"# Timeout Error\n\n"
                f"The request to {url} timed out after {timeout} seconds.\n\n"
                f"The server may be down or not responding."
            )
            self._display_error_page(url, error_text, viewer, add_to_history)
        except Exception as e:
            error_text = f"# Error\n\nFailed to fetch {url}:\n\n{e!r}"
            self._display_error_page(url, error_text, viewer, add_to_history)

    def _handle_gopher_search(self, url: str, prompt: str) -> None:
        """Handle Gopher type 7 search by showing InputModal.

        Args:
            url: The search URL to submit to
            prompt: The prompt to show the user
        """

        def on_result(query: str | None) -> None:
            if query is not None:
                self.get_url(url, search_query=query)

        self.push_screen(
            InputModal(prompt=prompt, url=url, sensitive=False),
            on_result,
        )

    def _handle_spartan_input(
        self, url: str, prompt: str, label: str | None, new_tab: bool = False
    ) -> None:
        """Handle Spartan input link by showing InputModal.

        Args:
            url: The Spartan URL to submit data to
            prompt: The prompt text (from link label)
            label: The link label for display
            new_tab: Whether to open result in a new tab
        """

        def on_result(data: str | None) -> None:
            if data is not None:
                # Validate 10KB limit (Spartan spec)
                byte_count = len(data.encode("utf-8"))
                if byte_count > 10240:  # 10KB = 10240 bytes
                    self.notify(
                        f"Input too large ({byte_count} bytes). Spartan limit is 10KB (10240 bytes).",
                        severity="error",
                        timeout=5,
                    )
                    return

                if new_tab:
                    self._open_in_new_tab(url, spartan_data=data)
                else:
                    self.get_url(url, spartan_data=data)

        self.push_screen(
            InputModal(
                prompt=prompt,
                url=url,
                label=label,
                sensitive=False,
                max_bytes=10240,
            ),
            on_result,
        )

    async def _handle_binary_download(
        self, filename: str, data: bytes, mime_type: str | None = None
    ) -> Path:
        """Handle binary download - saves to ~/Downloads.

        Args:
            filename: Suggested filename for the download
            data: Binary data to save
            mime_type: Optional MIME type to infer extension if filename lacks one

        Returns:
            Path to the saved file
        """
        import mimetypes

        download_dir = Path("~/Downloads").expanduser()
        download_dir.mkdir(parents=True, exist_ok=True)

        # If filename has no extension, try to add one based on MIME type
        if mime_type and "." not in filename:
            ext = mimetypes.guess_extension(mime_type)
            if ext:
                filename = filename + ext

        filepath = download_dir / filename
        counter = 1
        while filepath.exists():
            stem, suffix = filepath.stem, filepath.suffix
            filepath = download_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        filepath.write_bytes(data)
        self.notify(f"Downloaded: {filepath}", severity="information")
        return filepath

    async def _handle_image_display(
        self,
        url: str,
        filename: str,
        image_data: bytes,
        mime_type: str,
        viewer: "GemtextViewer",
        add_to_history: bool,
    ) -> bool:
        """Display image inline with Chafa rendering.

        Args:
            url: Original image URL
            filename: Image filename
            image_data: Raw image bytes
            mime_type: MIME type of the image
            viewer: GemtextViewer widget to display in
            add_to_history: Whether to add to history

        Returns:
            True if image was successfully displayed, False otherwise
        """
        try:
            from astronomo.widgets.gemtext_image import GemtextImageWidget

            # Cache the image for future access
            self.image_cache.put(url, image_data)

            # Create image widget
            image_widget = GemtextImageWidget(
                url=url,
                filename=filename,
                image_data=image_data,
                mime_type=mime_type,
            )

            # Create a heading and mount the widget
            # We'll convert this to Gemtext format for consistency
            from astronomo.parser import GemtextHeading, GemtextLine, LineType

            heading = GemtextHeading(
                raw=f"# {filename}", level=1, content=f" {filename}"
            )
            text_line = GemtextLine(
                line_type=LineType.TEXT,
                content="",
                raw="",
            )

            # Clear viewer and add image
            viewer.lines = [heading, text_line]
            viewer.query("GemtextLineWidget, Center, GemtextImageWidget").remove()

            # Mount the image widget directly
            viewer.mount(image_widget)

            # Update state and history
            self.current_url = url
            url_input = self.query_one("#url-input", Input)
            url_input.value = url

            if not self._navigating_history and add_to_history:
                # Store minimal info in history (image reloaded from cache)
                entry = HistoryEntry(
                    url=url,
                    content=[heading, text_line],
                    scroll_position=0,
                    link_index=0,
                    mime_type=mime_type,
                )
                self.history.push(entry)
                self._update_navigation_buttons()

            return True

        except Exception as e:
            self.notify(f"Failed to display image: {e}", severity="warning")
            return False

    def _open_external_link(self, url: str) -> None:
        """Open HTTP/HTTPS links in system browser.

        Args:
            url: The URL to open
        """
        import subprocess
        import sys

        try:
            if sys.platform == "darwin":
                subprocess.run(["open", url], check=True)
            elif sys.platform == "win32":
                subprocess.run(["start", url], shell=True, check=True)
            else:  # Linux/BSD
                subprocess.run(["xdg-open", url], check=True)
            self.notify(f"Opened in browser: {url}", severity="information")
        except Exception as e:
            self.notify(f"Failed to open browser: {e}", severity="error")

    def _open_local_file(self, filepath: str) -> None:
        """Open a local file with the system's default application.

        Args:
            filepath: Path to the file to open
        """
        import subprocess
        import sys

        # Verify file exists
        path = Path(filepath)
        if not path.exists():
            self.notify(f"File not found: {filepath}", severity="error")
            return

        try:
            if sys.platform == "darwin":
                subprocess.run(["open", filepath], check=True)
            elif sys.platform == "win32":
                subprocess.run(["start", "", filepath], shell=True, check=True)
            else:  # Linux/BSD
                subprocess.run(["xdg-open", filepath], check=True)
            self.notify(f"Opened: {path.name}", severity="information")
        except Exception as e:
            self.notify(f"Failed to open file: {e}", severity="error")

    def _display_error_page(
        self,
        url: str,
        error_text: str,
        viewer: GemtextViewer,
        add_to_history: bool,
    ) -> None:
        """Display an error page with proper history management.

        Args:
            url: The URL that caused the error
            error_text: The error message in Gemtext format
            viewer: The GemtextViewer to update
            add_to_history: Whether to add to history
        """
        parsed_lines = parse_gemtext(error_text)
        viewer.update_content(parsed_lines)

        # Update state
        self.current_url = url
        url_input = self.query_one("#url-input", Input)
        url_input.value = url

        # Add to history so user can navigate back
        if not self._navigating_history and add_to_history:
            entry = HistoryEntry(
                url=url,
                content=parsed_lines,
                scroll_position=0,
                link_index=0,
                status=0,  # Error status
                meta="error",
                mime_type="text/gemini",
            )
            self.history.push(entry)
            self._update_navigation_buttons()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL, auto-detecting scheme if not present.

        Detection rules:
        1. Already has scheme -> return as-is
        2. Contains @ but no / before it -> finger:// (user@host pattern)
        3. Hostname starts with "gopher." or :70 port -> gopher://
        4. Hostname starts with "nex." or :1900 port -> nex://
        5. Default -> gemini://

        Args:
            url: The URL to normalize

        Returns:
            URL with appropriate scheme prefix
        """
        if "://" in url:
            return url  # Already has scheme

        # finger://user@host pattern
        if "@" in url and "/" not in url.split("@")[0]:
            return f"finger://{url}"

        # gopher.* or :70 port
        if url.startswith("gopher.") or ":70" in url:
            return f"gopher://{url}"

        # spartan.* or :300 port
        if url.startswith("spartan.") or ":300" in url:
            return f"spartan://{url}"

        # nex.* or :1900 port
        if url.startswith("nex.") or ":1900" in url:
            return f"nex://{url}"

        # Default to Gemini
        return f"gemini://{url}"

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

            # Check if this was an image - if so, recreate widget from cache
            from astronomo.media_detector import MediaDetector

            if MediaDetector.is_image(entry.mime_type, entry.url):
                # Try to restore image from cache
                cached_image_data = self.image_cache.get(entry.url)
                if cached_image_data:
                    # Extract filename from URL
                    from urllib.parse import urlparse

                    parsed_url = urlparse(entry.url)
                    filename = parsed_url.path.split("/")[-1] or "image"

                    # Recreate the image widget
                    from astronomo.widgets.gemtext_image import GemtextImageWidget

                    viewer.lines = entry.content
                    viewer.query(
                        "GemtextLineWidget, Center, GemtextImageWidget"
                    ).remove()
                    image_widget = GemtextImageWidget(
                        url=entry.url,
                        filename=filename,
                        image_data=cached_image_data,
                        mime_type=entry.mime_type,
                    )
                    viewer.mount(image_widget)
                else:
                    # Image not in cache, just show the text content
                    viewer.update_content(entry.content)
            else:
                # Regular content - restore normally
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

    # --- Tab Management ---

    def _update_tab_bar(self) -> None:
        """Refresh the tab bar with current tabs."""
        tab_bar = self.query_one("#tab-bar", TabBar)
        tabs = self.tab_manager.all_tabs()
        current = self.tab_manager.current_tab()
        tab_bar.update_tabs(tabs, current.id if current else "")

    def _update_tab_title(self) -> None:
        """Update the current tab's title from page content."""
        tab = self.tab_manager.current_tab()
        if not tab:
            return

        # Get title from page H1 or use URL hostname
        title = self._get_page_title()
        if not title:
            parsed = urlparse(tab.url)
            title = parsed.netloc or tab.url[:20] or "New Tab"

        # Truncate long titles
        if len(title) > 20:
            title = title[:17] + "..."

        tab.title = title
        self._update_tab_bar()

    def _save_current_tab_state(self) -> None:
        """Save current viewer state to active tab."""
        tab = self.tab_manager.current_tab()
        if not tab:
            return

        viewer = self.query_one("#content", GemtextViewer)
        tab.viewer_state.scroll_position = viewer.scroll_y
        tab.viewer_state.link_index = viewer.current_link_index
        tab.viewer_state.content = viewer.lines.copy()

    def _restore_tab_state(self, tab: Tab) -> None:
        """Restore viewer state from a tab."""
        viewer = self.query_one("#content", GemtextViewer)
        url_input = self.query_one("#url-input", Input)

        # Restore URL
        url_input.value = tab.url

        # Restore content
        if tab.viewer_state.content:
            viewer.update_content(tab.viewer_state.content)
            # Restore scroll position and link selection
            viewer.scroll_y = tab.viewer_state.scroll_position
            viewer.current_link_index = tab.viewer_state.link_index
        else:
            # Empty tab - show welcome or loading
            if tab.url:
                loading_text = f"# Fetching\n\n{tab.url}\n\nPlease wait..."
                viewer.update_content(parse_gemtext(loading_text))
            else:
                # Show welcome message with starry night ASCII art
                viewer.update_content(self._get_welcome_content())

        # Update navigation buttons for this tab's history
        self._update_navigation_buttons()

    def _switch_to_tab(self, tab_id: str) -> None:
        """Switch to a specific tab, saving current state first."""
        # Save current tab state before switching
        self._save_current_tab_state()

        # Switch to new tab
        tab = self.tab_manager.switch_to_tab(tab_id)
        if tab:
            self._restore_tab_state(tab)
            self._update_tab_bar()
            # Focus the content viewer
            viewer = self.query_one("#content", GemtextViewer)
            viewer.focus()

    def action_new_tab(self) -> None:
        """Create a new empty tab."""
        if not self.tab_manager.can_create_tab():
            self.notify("Maximum number of tabs reached", severity="warning")
            return

        # Save current tab state before creating new one
        self._save_current_tab_state()

        # Create and switch to new tab
        tab = self.tab_manager.create_tab(url="", title="New Tab")
        self._restore_tab_state(tab)
        self._update_tab_bar()

        # Focus URL input for immediate typing
        url_input = self.query_one("#url-input", Input)
        url_input.focus()

    def _open_in_new_tab(self, url: str, spartan_data: str | None = None) -> None:
        """Open a URL in a new tab.

        Args:
            url: The URL to open in the new tab
            spartan_data: Optional data for Spartan input links
        """
        if not self.tab_manager.can_create_tab():
            self.notify("Maximum number of tabs reached", severity="warning")
            return

        # Save current tab state
        self._save_current_tab_state()

        # Create new tab with the URL and switch to it
        parsed = urlparse(url)
        title = parsed.netloc or url[:20] or "Loading..."
        tab = self.tab_manager.create_tab(url=url, title=title)
        self._restore_tab_state(tab)
        self._update_tab_bar()

        # Fetch the URL in the new tab
        self.get_url(url, spartan_data=spartan_data)

    def action_close_tab(self) -> None:
        """Close the current tab."""
        if not self.tab_manager.can_close_tab():
            self.notify("Cannot close the last tab", severity="warning")
            return

        current = self.tab_manager.current_tab()
        if not current:
            return

        # Close and get next tab
        next_tab = self.tab_manager.close_tab(current.id)
        if next_tab:
            self._restore_tab_state(next_tab)
        self._update_tab_bar()

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        self._save_current_tab_state()
        tab = self.tab_manager.next_tab()
        if tab:
            self._restore_tab_state(tab)
            self._update_tab_bar()

    def action_prev_tab(self) -> None:
        """Switch to the previous tab."""
        self._save_current_tab_state()
        tab = self.tab_manager.prev_tab()
        if tab:
            self._restore_tab_state(tab)
            self._update_tab_bar()

    def _action_jump_to_tab(self, index: int) -> None:
        """Jump to tab by index (0-based)."""
        if index >= self.tab_manager.tab_count():
            return
        self._save_current_tab_state()
        tab = self.tab_manager.switch_to_index(index)
        if tab:
            self._restore_tab_state(tab)
            self._update_tab_bar()

    def action_jump_to_tab_1(self) -> None:
        """Jump to tab 1."""
        self._action_jump_to_tab(0)

    def action_jump_to_tab_2(self) -> None:
        """Jump to tab 2."""
        self._action_jump_to_tab(1)

    def action_jump_to_tab_3(self) -> None:
        """Jump to tab 3."""
        self._action_jump_to_tab(2)

    def action_jump_to_tab_4(self) -> None:
        """Jump to tab 4."""
        self._action_jump_to_tab(3)

    def action_jump_to_tab_5(self) -> None:
        """Jump to tab 5."""
        self._action_jump_to_tab(4)

    def action_jump_to_tab_6(self) -> None:
        """Jump to tab 6."""
        self._action_jump_to_tab(5)

    def action_jump_to_tab_7(self) -> None:
        """Jump to tab 7."""
        self._action_jump_to_tab(6)

    def action_jump_to_tab_8(self) -> None:
        """Jump to tab 8."""
        self._action_jump_to_tab(7)

    def action_jump_to_tab_9(self) -> None:
        """Jump to tab 9."""
        self._action_jump_to_tab(8)

    # --- Tab Bar Event Handlers ---

    def on_tab_bar_tab_selected(self, message: TabBar.TabSelected) -> None:
        """Handle tab selection from tab bar."""
        self._switch_to_tab(message.tab_id)

    def on_tab_bar_tab_close_requested(self, message: TabBar.TabCloseRequested) -> None:
        """Handle tab close request from tab bar."""
        if not self.tab_manager.can_close_tab():
            self.notify("Cannot close the last tab", severity="warning")
            return

        # If closing the active tab, handle same as action_close_tab
        current = self.tab_manager.current_tab()
        if current and current.id == message.tab_id:
            self.action_close_tab()
        else:
            # Closing a non-active tab
            self.tab_manager.close_tab(message.tab_id)
            self._update_tab_bar()

    def on_tab_bar_new_tab_requested(self, message: TabBar.NewTabRequested) -> None:
        """Handle new tab request from tab bar."""
        self.action_new_tab()


if __name__ == "__main__":
    app = Astronomo()
    app.run()
