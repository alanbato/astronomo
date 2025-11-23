"""GemtextViewer widget for displaying interactive Gemtext content."""

from pathlib import Path

from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from astronomo.parser import GemtextLine, GemtextLink, LineType


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


class GemtextTextWidget(GemtextLineWidget):
    """Widget for plain text lines."""

    DEFAULT_CSS = """
    GemtextTextWidget {
        color: $text;
    }
    """

    def compose(self):
        return []

    def render(self) -> str:
        return self.line.content


class GemtextHeading1Widget(GemtextLineWidget):
    """Widget for level 1 headings."""

    DEFAULT_CSS = """
    GemtextHeading1Widget {
        background: $primary-muted;
        color: $text-primary;
        text-style: bold;
    }
    """

    def render(self) -> str:
        return self.line.content


class GemtextHeading2Widget(GemtextLineWidget):
    """Widget for level 2 headings."""

    DEFAULT_CSS = """
    GemtextHeading2Widget {
        background: $secondary-muted;
        color: $text-secondary;
        text-style: bold;
    }
    """

    def render(self) -> str:
        return self.line.content


class GemtextHeading3Widget(GemtextLineWidget):
    """Widget for level 3 headings."""

    DEFAULT_CSS = """
    GemtextHeading3Widget {
        color: $foreground-muted;
    }
    """

    def render(self) -> str:
        return self.line.content


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
        return f"{self.PADDING}{self.LIST_BULLET} {self.line.content}"


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
        return f"{self.QUOTE_PREFIX} {self.line.content}"


class GemtextPreformattedWidget(GemtextLineWidget):
    """Widget for preformatted text blocks."""

    DEFAULT_CSS = """
    GemtextPreformattedWidget {
        background: $background-lighten-1;
        color: $text-muted;
    }
    """

    def render(self) -> str:
        return self.line.content


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
        assert isinstance(self.line, GemtextLink)
        return self.line

    def render(self) -> str:
        prefix = self.LINK_INDICATOR if self.has_class("-selected") else ""
        return f"{prefix}{self.line.content}"

    def on_click(self) -> None:
        """Handle click on link."""
        parent = self.parent
        if isinstance(parent, GemtextViewer):
            parent.action_activate_link_by_index(self.link_index)


# --- Line Widget Factory ---


def create_line_widget(line: GemtextLine, link_index: int = -1) -> GemtextLineWidget:
    """Create the appropriate widget for a Gemtext line.

    Args:
        line: The parsed Gemtext line
        link_index: For links, the index in the link list (-1 for non-links)

    Returns:
        A widget appropriate for the line type
    """
    match line.line_type:
        case LineType.LINK:
            assert isinstance(line, GemtextLink)
            return GemtextLinkWidget(line, link_index)
        case LineType.HEADING_1:
            return GemtextHeading1Widget(line)
        case LineType.HEADING_2:
            return GemtextHeading2Widget(line)
        case LineType.HEADING_3:
            return GemtextHeading3Widget(line)
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

    CSS_PATH = Path("gemtext_viewer.tcss")

    BINDINGS = [
        ("left", "prev_link", "Prev Link"),
        ("right", "next_link", "Next Link"),
        ("enter", "activate_link", "Activate Link"),
        ("backspace", "navigate_back", "Back"),
        ("shift+backspace", "navigate_forward", "Forward"),
    ]

    # Reactive properties
    current_link_index: reactive[int] = reactive(-1, init=False)

    class LinkActivated(Message):
        """Message sent when a link is activated."""

        def __init__(self, link: GemtextLink) -> None:
            self.link = link
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

    def update_content(self, lines: list[GemtextLine]) -> None:
        """Update the displayed content with parsed Gemtext lines."""
        self.lines = lines

        # Remove old content widgets
        for widget in self.query(GemtextLineWidget):
            widget.remove()

        # Build new widgets
        self._link_widgets = []
        widgets: list[GemtextLineWidget] = []
        link_idx = 0

        for line in lines:
            if line.line_type == LineType.LINK:
                widget = create_line_widget(line, link_idx)
                assert isinstance(widget, GemtextLinkWidget)
                self._link_widgets.append(widget)
                link_idx += 1
            else:
                widget = create_line_widget(line)
            widgets.append(widget)

        # Mount all widgets
        self.mount(*widgets)

        # Set initial link selection (triggers watch_current_link_index)
        self.current_link_index = 0 if self._link_widgets else -1

    @property
    def link_indices(self) -> list[int]:
        """Get list of link indices (for compatibility with tests)."""
        return list(range(len(self._link_widgets)))

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

    def activate_current_link(self) -> None:
        """Activate the currently selected link."""
        if self._link_widgets and 0 <= self.current_link_index < len(
            self._link_widgets
        ):
            link_widget = self._link_widgets[self.current_link_index]
            self.post_message(self.LinkActivated(link_widget.link))

    def action_prev_link(self) -> None:
        """Action: Navigate to the previous link."""
        self.prev_link()

    def action_next_link(self) -> None:
        """Action: Navigate to the next link."""
        self.next_link()

    def action_activate_link(self) -> None:
        """Action: Activate the currently selected link."""
        self.activate_current_link()

    def action_activate_link_by_index(self, index: int) -> None:
        """Action: Activate a specific link by its index (used by click handler)."""
        self.current_link_index = index
        self.activate_current_link()

    def action_navigate_back(self) -> None:
        """Action: Navigate back in history."""
        self.post_message(self.NavigateBack())

    def action_navigate_forward(self) -> None:
        """Action: Navigate forward in history."""
        self.post_message(self.NavigateForward())

    def get_current_link(self) -> GemtextLink | None:
        """Get the currently selected link, or None if no link selected."""
        if self._link_widgets and 0 <= self.current_link_index < len(
            self._link_widgets
        ):
            return self._link_widgets[self.current_link_index].link
        return None

    def _scroll_to_link(self, link_widget: GemtextLinkWidget) -> None:
        """Scroll to make the link widget visible."""
        # Check if link is already visible (with some padding)
        link_top = link_widget.virtual_region.y
        link_bottom = link_top + link_widget.virtual_region.height
        viewport_top = self.scroll_y
        viewport_height = self.scrollable_content_region.height
        viewport_bottom = viewport_top + viewport_height

        padding = 3  # lines of context

        # Only scroll if the link is not fully visible with padding
        if link_top < viewport_top + padding:
            # Link is above viewport - scroll up to show it with padding
            self.scroll_to(y=max(0, link_top - padding), animate=False, force=True)
        elif link_bottom > viewport_bottom - padding:
            # Link is below viewport - scroll down to show it with padding
            target_y = link_bottom - viewport_height + padding
            self.scroll_to(y=max(0, target_y), animate=False, force=True)

    def watch_current_link_index(self, old_index: int, new_index: int) -> None:
        """React to link selection changes."""
        # Deselect old link
        if 0 <= old_index < len(self._link_widgets):
            self._link_widgets[old_index].remove_class("-selected")
            self._link_widgets[old_index].refresh()

        # Select new link and scroll to it
        if 0 <= new_index < len(self._link_widgets):
            link_widget = self._link_widgets[new_index]
            link_widget.add_class("-selected")
            link_widget.refresh()

            # Scroll to the link after refresh to ensure layout is complete
            self.call_after_refresh(self._scroll_to_link, link_widget)
