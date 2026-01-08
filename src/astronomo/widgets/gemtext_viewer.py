"""GemtextViewer widget for displaying interactive Gemtext content."""

from typing import TYPE_CHECKING

from rich.text import Text
from textual.containers import Center, VerticalScroll
from textual.content import Content
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from astronomo.emoji_utils import translate_emoji
from astronomo.parser import (
    GemtextHeading,
    GemtextLine,
    GemtextLink,
    GemtextPreformatted,
    LineType,
)
from astronomo.syntax import highlight_code, normalize_language

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo


# --- Line Widget Classes ---


class GemtextLineWidget(Static):
    """Base widget for a single line of Gemtext content."""

    DEFAULT_CSS = """
    GemtextLineWidget {
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, line: GemtextLine, **kwargs) -> None:
        super().__init__(**kwargs)
        self.line = line

    def _process_emoji(self, content: str) -> str:
        """Translate emoji to text if show_emoji config is disabled.

        Args:
            content: The text content to process.

        Returns:
            Content with emoji translated to text descriptions if disabled,
            otherwise unchanged.
        """
        try:
            app: Astronomo = self.app  # type: ignore[assignment]
            if app.config_manager.config.appearance.show_emoji:
                return content
            return translate_emoji(content)
        except AttributeError:
            return content  # App not available (e.g., in tests)


class GemtextTextWidget(GemtextLineWidget):
    """Widget for plain text lines."""

    DEFAULT_CSS = """
    GemtextTextWidget {
        color: $text;
    }
    """

    def render(self) -> str:
        return self._process_emoji(self.line.content)


class GemtextHeadingWidget(GemtextLineWidget):
    """Widget for headings (levels 1-3)."""

    DEFAULT_CSS = """
    GemtextHeadingWidget {
        text-style: bold;
    }

    GemtextHeadingWidget.-level-1 {
        background: $primary-muted;
        color: $text-primary;
    }

    GemtextHeadingWidget.-level-2 {
        background: $secondary-muted;
        color: $text-secondary;
    }

    GemtextHeadingWidget.-level-3 {
        background: transparent;
        color: $foreground-muted;
        text-style: none;
    }
    """

    def __init__(self, line: GemtextHeading, **kwargs) -> None:
        super().__init__(line, **kwargs)
        self.add_class(f"-level-{line.level}")

    def render(self) -> str:
        return self._process_emoji(self.line.content)


class GemtextListItemWidget(GemtextLineWidget):
    """Widget for list items."""

    DEFAULT_CSS = """
    GemtextListItemWidget {
        color: $text;
    }
    """

    LIST_BULLET = "•"
    PADDING = "  "

    def render(self) -> str:
        content = self._process_emoji(self.line.content)
        return f"{self.PADDING}{self.LIST_BULLET} {content}"


class GemtextBlockquoteWidget(GemtextLineWidget):
    """Widget for blockquotes."""

    DEFAULT_CSS = """
    GemtextBlockquoteWidget {
        color: $text;
        text-style: italic;
    }
    """

    QUOTE_PREFIX = "┃"

    def render(self) -> str:
        content = self._process_emoji(self.line.content)
        return f"{self.QUOTE_PREFIX} {content}"


class GemtextPreformattedWidget(GemtextLineWidget):
    """Widget for preformatted text blocks with optional syntax highlighting."""

    DEFAULT_CSS = """
    GemtextPreformattedWidget {
        background: $background-lighten-1;
        color: $text-muted;
    }
    """

    def __init__(self, line: GemtextLine, **kwargs) -> None:
        super().__init__(line, **kwargs)
        # Preformatted blocks should not be width-constrained
        self.add_class("-full-width")

    def render(self) -> Text | Content:
        content = self.line.content

        # Always preserve ANSI escape codes if present (server-provided coloring)
        if "\x1b[" in content or "\033[" in content:
            return Text.from_ansi(content)

        # Check if syntax highlighting is enabled in config
        # Access config through the app if available
        try:
            app: Astronomo = self.app  # type: ignore[assignment]
            if not app.config_manager.syntax_highlighting:
                return Content(content)
        except AttributeError:
            # App or config not available (e.g., in tests), proceed with highlighting
            pass

        # Get language from alt_text if available
        language = None
        if isinstance(self.line, GemtextPreformatted):
            language = normalize_language(self.line.alt_text)

        # Apply syntax highlighting with auto-detection fallback
        return highlight_code(content, language)


class GemtextLinkWidget(GemtextLineWidget):
    """Widget for links with selection support."""

    DEFAULT_CSS = """
    GemtextLinkWidget {
        color: $text-accent;
        text-style: underline;
        padding-left: 2;
    }

    GemtextLinkWidget.-selected {
        background: $accent-muted;
        padding-left: 0;
    }
    """

    LINK_INDICATOR = "▶ "

    def __init__(self, line: GemtextLink, link_index: int, **kwargs) -> None:
        super().__init__(line, **kwargs)
        self.link_index = link_index

    @property
    def link(self) -> GemtextLink:
        """Get the link data."""
        if not isinstance(self.line, GemtextLink):
            raise TypeError(f"Expected GemtextLink, got {type(self.line).__name__}")
        return self.line

    def render(self) -> str:
        prefix = self.LINK_INDICATOR if self.has_class("-selected") else ""
        content = self._process_emoji(self.line.content)
        return f"{prefix}{content}"

    def on_click(self, event) -> None:
        """Handle click on link.

        Ctrl+click or middle-click opens in a new tab.
        """
        parent = self.parent
        # Check for center wrapper
        if isinstance(parent, Center):
            parent = parent.parent
        if isinstance(parent, GemtextViewer):
            # Detect Ctrl key or middle mouse button for new tab
            new_tab = event.ctrl or event.button == 2
            parent.action_activate_link_by_index(self.link_index, new_tab=new_tab)


# --- Line Widget Factory ---


def create_line_widget(line: GemtextLine, link_index: int = -1) -> GemtextLineWidget:
    """Create the appropriate widget for a Gemtext line.

    Args:
        line: The parsed Gemtext line
        link_index: For links, the index in the link list (-1 for non-links)

    Returns:
        A widget appropriate for the line type

    Raises:
        TypeError: If line type doesn't match expected class
    """
    match line.line_type:
        case LineType.LINK | LineType.INPUT_LINK:
            if not isinstance(line, GemtextLink):
                raise TypeError(
                    f"Link type requires GemtextLink, got {type(line).__name__}"
                )
            return GemtextLinkWidget(line, link_index)
        case LineType.HEADING_1 | LineType.HEADING_2 | LineType.HEADING_3:
            if not isinstance(line, GemtextHeading):
                raise TypeError(
                    f"Heading type requires GemtextHeading, got {type(line).__name__}"
                )
            return GemtextHeadingWidget(line)
        case LineType.LIST_ITEM:
            return GemtextListItemWidget(line)
        case LineType.BLOCKQUOTE:
            return GemtextBlockquoteWidget(line)
        case LineType.PREFORMATTED:
            return GemtextPreformattedWidget(line)
        case _:
            return GemtextTextWidget(line)


# --- Main Viewer ---


class GemtextViewer(VerticalScroll):
    """A widget for displaying Gemtext with interactive, navigable links.

    Features:
    - Styled rendering for all Gemtext elements
    - Keyboard navigation for links
    - Mouse click support
    - Smart label display (label if present, else URL)
    """

    BINDINGS = [
        ("left", "prev_link", "Prev Link"),
        ("right", "next_link", "Next Link"),
        ("enter", "activate_link", "Activate Link"),
        ("ctrl+enter", "activate_link_new_tab", "Open in New Tab"),
        ("backspace", "navigate_back", "Back"),
        ("shift+backspace", "navigate_forward", "Forward"),
    ]

    # Reactive properties
    current_link_index: reactive[int] = reactive(-1, init=False)

    class LinkActivated(Message):
        """Message sent when a link is activated.

        Attributes:
            link: The GemtextLink that was activated
            new_tab: Whether to open in a new tab (Ctrl+click, middle-click, or Ctrl+Enter)
        """

        def __init__(self, link: GemtextLink, new_tab: bool = False) -> None:
            self.link = link
            self.new_tab = new_tab
            super().__init__()

    class NavigateBack(Message):
        """Message sent when the user wants to navigate back."""

    class NavigateForward(Message):
        """Message sent when the user wants to navigate forward."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lines: list[GemtextLine] = []
        self.can_focus = True
        self._link_widgets: list[GemtextLinkWidget] = []
        self._skip_initial_scroll = False  # Flag to skip scroll on initial content load

    def _get_link_widget(self, index: int) -> GemtextLinkWidget | None:
        """Get link widget at index, or None if index is invalid."""
        if 0 <= index < len(self._link_widgets):
            return self._link_widgets[index]
        return None

    def rerender_content(self) -> None:
        """Re-render the current content without fetching from network.

        Useful when display settings change (e.g., emoji mode).
        """
        if self.lines:
            self.update_content(self.lines)

    def apply_width_constraint(self) -> None:
        """Apply max content width from config by re-rendering content.

        This is called when the setting changes to apply the new width.
        """
        if self.lines:
            self.update_content(self.lines)

    def update_content(self, lines: list[GemtextLine]) -> None:
        """Update the displayed content with parsed Gemtext lines."""
        self.lines = lines

        # Remove all old content (line widgets, Center wrappers, and image widgets)
        for widget in list(self.children):
            widget.remove()

        # Get max width setting
        max_width = 0
        try:
            app: Astronomo = self.app  # type: ignore[assignment]
            max_width = app.config_manager.max_content_width
        except AttributeError:
            pass

        # Build new widgets
        self._link_widgets = []
        to_mount: list[GemtextLineWidget | Center] = []
        link_idx = 0

        for line in lines:
            if line.line_type in (LineType.LINK, LineType.INPUT_LINK):
                widget = create_line_widget(line, link_idx)
                if isinstance(widget, GemtextLinkWidget):
                    self._link_widgets.append(widget)
                link_idx += 1
            else:
                widget = create_line_widget(line)

            # Apply width constraint and centering
            if widget.has_class("-full-width") or max_width == 0:
                # Full width - no centering needed
                to_mount.append(widget)
            else:
                # Wrap in Center container for horizontal centering
                widget.styles.width = max_width
                centered = Center(widget)
                centered.styles.width = "100%"
                centered.styles.height = "auto"
                to_mount.append(centered)

        # Mount all widgets
        self.mount(*to_mount)

        # Scroll to top for new content
        self.scroll_to(y=0, animate=False)

        # Set initial link selection WITHOUT triggering scroll-to-link
        self._skip_initial_scroll = True
        self.current_link_index = 0 if self._link_widgets else -1
        self._skip_initial_scroll = False

    def next_link(self) -> None:
        """Navigate to the next link."""
        if not self._link_widgets:
            return

        if self.current_link_index < len(self._link_widgets) - 1:
            self.current_link_index += 1
        else:
            self.current_link_index = 0

    def prev_link(self) -> None:
        """Navigate to the previous link."""
        if not self._link_widgets:
            return

        if self.current_link_index > 0:
            self.current_link_index -= 1
        else:
            self.current_link_index = len(self._link_widgets) - 1

    def activate_current_link(self, new_tab: bool = False) -> None:
        """Activate the currently selected link.

        Args:
            new_tab: Whether to open in a new tab
        """
        link_widget = self._get_link_widget(self.current_link_index)
        if link_widget:
            self.post_message(self.LinkActivated(link_widget.link, new_tab=new_tab))

    def action_prev_link(self) -> None:
        """Action: Navigate to the previous link."""
        self.prev_link()

    def action_next_link(self) -> None:
        """Action: Navigate to the next link."""
        self.next_link()

    def action_activate_link(self) -> None:
        """Action: Activate the currently selected link."""
        self.activate_current_link()

    def action_activate_link_new_tab(self) -> None:
        """Action: Activate the currently selected link in a new tab."""
        self.activate_current_link(new_tab=True)

    def action_activate_link_by_index(self, index: int, new_tab: bool = False) -> None:
        """Action: Activate a specific link by its index (used by click handler).

        Args:
            index: The link index to activate
            new_tab: Whether to open in a new tab
        """
        self.current_link_index = index
        self.activate_current_link(new_tab=new_tab)

    def action_navigate_back(self) -> None:
        """Action: Navigate back in history."""
        self.post_message(self.NavigateBack())

    def action_navigate_forward(self) -> None:
        """Action: Navigate forward in history."""
        self.post_message(self.NavigateForward())

    def get_current_link(self) -> GemtextLink | None:
        """Get the currently selected link, or None if no link selected."""
        link_widget = self._get_link_widget(self.current_link_index)
        return link_widget.link if link_widget else None

    def _scroll_to_link(self, link_widget: GemtextLinkWidget) -> None:
        """Scroll to make the link widget visible."""
        link_top = link_widget.virtual_region.y
        link_bottom = link_top + link_widget.virtual_region.height
        viewport_top = self.scroll_y
        viewport_height = self.scrollable_content_region.height
        viewport_bottom = viewport_top + viewport_height

        padding = 3  # lines of context when scrolling

        # Only scroll if the link is not fully visible (ignore padding for this check)
        link_fully_visible = link_top >= viewport_top and link_bottom <= viewport_bottom
        if link_fully_visible:
            return  # No need to scroll

        # Link is not fully visible, scroll to show it with padding for context
        if link_top < viewport_top:
            # Link is above viewport - scroll up to show it with padding
            self.scroll_to(y=max(0, link_top - padding), animate=False, force=True)
        else:
            # Link is below viewport - scroll down to show it with padding
            target_y = link_bottom - viewport_height + padding
            self.scroll_to(y=max(0, target_y), animate=False, force=True)

    def watch_current_link_index(self, old_index: int, new_index: int) -> None:
        """React to link selection changes."""
        # Deselect old link
        old_widget = self._get_link_widget(old_index)
        if old_widget:
            old_widget.remove_class("-selected")

        # Select new link and scroll to it
        new_widget = self._get_link_widget(new_index)
        if new_widget:
            new_widget.add_class("-selected")
            # Skip scroll on initial content load (we want to show top of page)
            if not self._skip_initial_scroll:
                self.call_after_refresh(self._scroll_to_link, new_widget)
