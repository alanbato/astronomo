"""GemtextViewer widget for displaying interactive Gemtext content."""

from pathlib import Path

from textual.containers import VerticalScroll
from textual.content import Content
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from astronomo.parser import GemtextLine, GemtextLink, LineType


class GemtextContent(Static):
    """Static widget that displays styled Gemtext content."""

    def action_activate_link_by_index(self, index: int) -> None:
        """Forward link activation to parent GemtextViewer."""
        parent = self.parent
        if isinstance(parent, GemtextViewer):
            parent.action_activate_link_by_index(index)


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

    # UI constants for prefixes
    LINK_INDICATOR = "▶"
    PADDING = "  "
    LIST_BULLET = "•"
    QUOTE_PREFIX = "┃"

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
        self.link_indices: list[int] = []  # Maps link index to line index
        self.can_focus = True
        self._content_widget: GemtextContent | None = None

    def compose(self):
        """Create the content widget."""
        self._content_widget = GemtextContent(id="content")
        yield self._content_widget

    def update_content(self, lines: list[GemtextLine]) -> None:
        """Update the displayed content with parsed Gemtext lines."""
        self.lines = lines

        # Build link index map
        self.link_indices = []
        for line_idx, line in enumerate(lines):
            if line.line_type == LineType.LINK:
                self.link_indices.append(line_idx)

        # Set initial link selection
        self.current_link_index = 0 if self.link_indices else -1

        # Build and display content
        self._refresh_content()

    def _build_content(self) -> Content:
        """Build a Content object with all styled content."""
        parts: list[Content] = []
        current_link_idx = 0

        for line_idx, line in enumerate(self.lines):
            # Check if this is a link and track its index
            link_index = -1
            if line.line_type == LineType.LINK:
                link_index = current_link_idx
                current_link_idx += 1

            # Check if this is the selected link
            is_selected = bool(
                line.line_type == LineType.LINK
                and self.current_link_index >= 0
                and link_index == self.current_link_index
            )

            # Get content for this line (includes newline)
            parts.append(self._get_line_content(line, is_selected, link_index))

        return Content.assemble(*parts)

    def _get_line_markup(
        self, line_type: LineType, is_selected: bool, link_index: int = -1
    ) -> str:
        """Get the markup template for a line type."""
        if line_type == LineType.LINK:
            if is_selected:
                return f"[$text-accent on $accent-muted @click=activate_link_by_index({link_index})]$link_indicator [underline]$content[/underline][/]\n"
            else:
                return f"$padding[$text-accent @click=activate_link_by_index({link_index})][underline]$content[/underline][/]\n"

        elif line_type == LineType.HEADING_1:
            return "[$text-primary on $primary-muted][bold]$content[/][/]\n"

        elif line_type == LineType.HEADING_2:
            return "[$text-secondary on $secondary-muted][bold]$content[/][/]\n"

        elif line_type == LineType.HEADING_3:
            return "[$foreground-muted]$content[/]\n"

        elif line_type == LineType.LIST_ITEM:
            return "[$text]$padding$bullet $content[/]\n"

        elif line_type == LineType.BLOCKQUOTE:
            return "[$text]$quote_prefix [italic]$content[/][/]\n"

        elif line_type == LineType.PREFORMATTED:
            return "[$text-muted on $background-lighten-1]$content[/]\n"

        else:
            return "[$text]$content[/]\n"

    def _get_line_content(
        self, line: GemtextLine, is_selected: bool = False, link_index: int = -1
    ) -> Content:
        """Get the styled Content for a line."""
        markup = self._get_line_markup(line.line_type, is_selected, link_index)
        return Content.from_markup(
            markup,
            content=line.content,
            padding=self.PADDING,
            link_indicator=self.LINK_INDICATOR,
            bullet=self.LIST_BULLET,
            quote_prefix=self.QUOTE_PREFIX,
        )

    def _refresh_content(self) -> None:
        """Rebuild and display the content."""
        if self._content_widget is not None:
            text = self._build_content()
            self._content_widget.update(text)

    def next_link(self) -> None:
        """Navigate to the next link."""
        if not self.link_indices:
            return

        if self.current_link_index < len(self.link_indices) - 1:
            self.current_link_index += 1
        else:
            self.current_link_index = 0

    def prev_link(self) -> None:
        """Navigate to the previous link."""
        if not self.link_indices:
            return

        if self.current_link_index > 0:
            self.current_link_index -= 1
        else:
            self.current_link_index = len(self.link_indices) - 1

    def activate_current_link(self) -> None:
        """Activate the currently selected link."""
        if self.link_indices and 0 <= self.current_link_index < len(self.link_indices):
            line_idx = self.link_indices[self.current_link_index]
            link = self.lines[line_idx]
            assert isinstance(link, GemtextLink)
            self.post_message(self.LinkActivated(link))

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
        if self.link_indices and 0 <= self.current_link_index < len(self.link_indices):
            line_idx = self.link_indices[self.current_link_index]
            link = self.lines[line_idx]
            assert isinstance(link, GemtextLink)
            return link
        return None

    def watch_current_link_index(self, old_index: int, new_index: int) -> None:
        """React to link selection changes."""
        # Rebuild content to show new selection
        self._refresh_content()

        # Scroll to the selected link
        if 0 <= new_index < len(self.link_indices):
            line_idx = self.link_indices[new_index]
            self.scroll_to(y=line_idx, animate=False)
