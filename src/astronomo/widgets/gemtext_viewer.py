"""GemtextViewer widget for displaying interactive Gemtext content."""

from rich.text import Text
from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from astronomo.parser import GemtextLine, GemtextLink, LineType


class GemtextViewer(Static):
    """A widget for displaying Gemtext with interactive, navigable links.

    Features:
    - Inline link display with highlighting
    - Keyboard navigation (arrows, j/k, tab, enter)
    - Mouse click support
    - Smart label display (label if present, else URL)
    - Styled rendering for all Gemtext elements
    """

    DEFAULT_CSS = """
    GemtextViewer {
        width: 1fr;
    }
    """

    class LinkActivated(Message):
        """Message sent when a link is activated."""

        def __init__(self, link: GemtextLink) -> None:
            self.link = link
            super().__init__()

    # Reactive properties
    current_link_index: reactive[int] = reactive(-1, init=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lines: list[GemtextLine] = []
        self.links: list[GemtextLink] = []
        self._link_line_numbers: dict[int, int] = {}  # Map link index to line number
        self.can_focus = True

    def update_content(self, lines: list[GemtextLine]) -> None:
        """Update the displayed content with parsed Gemtext lines."""
        self.lines = lines

        # Extract links and their positions
        self.links = []
        self._link_line_numbers = {}
        for line_num, line in enumerate(lines):
            if isinstance(line, GemtextLink):
                link_index = len(self.links)
                self.links.append(line)
                self._link_line_numbers[link_index] = line_num

        # Set initial link selection
        self.current_link_index = 0 if self.links else -1
        self.update(self._build_content())

    def _build_content(self) -> Text:
        """Build the Gemtext content with styling."""
        if not self.lines:
            return Text("No content to display", style="dim")

        output = Text()

        for line_num, line in enumerate(self.lines):
            line_text = self._render_line(line, line_num)
            output.append(line_text)
            output.append("\n")

        return output

    def _render_line(self, line: GemtextLine, line_num: int) -> Text:
        """Render a single Gemtext line with appropriate styling."""
        # Check if this line is the currently selected link
        is_selected = False
        if isinstance(line, GemtextLink):
            link_index = self._get_link_index_by_line(line_num)
            is_selected = link_index == self.current_link_index

        if line.line_type == LineType.LINK:
            assert isinstance(line, GemtextLink)
            return self._render_link(line, is_selected)
        elif line.line_type == LineType.HEADING_1:
            return Text(line.content, style="bold magenta")
        elif line.line_type == LineType.HEADING_2:
            return Text(line.content, style="bold cyan")
        elif line.line_type == LineType.HEADING_3:
            return Text(line.content, style="bold yellow")
        elif line.line_type == LineType.LIST_ITEM:
            return Text(f"  • {line.content}", style="default")
        elif line.line_type == LineType.BLOCKQUOTE:
            return Text(f"┃ {line.content}", style="italic dim")
        elif line.line_type == LineType.PREFORMATTED:
            return Text(line.content, style="on #1a1a1a")
        else:  # TEXT
            return Text(line.content, style="default")

    def _render_link(self, link: GemtextLink, is_selected: bool) -> Text:
        """Render a link with appropriate styling based on selection state."""
        text = Text()

        if is_selected:
            # Selected link: bright cyan, underlined, with indicator
            text.append("▶ ", style="bold bright_cyan")
            text.append(link.content, style="bold bright_cyan underline")
        else:
            # Normal link: blue, no underline
            text.append("  ", style="default")
            text.append(link.content, style="blue")

        return text

    def _get_link_index_by_line(self, line_num: int) -> int:
        """Get link index from line number, or -1 if not a link."""
        for link_idx, ln in self._link_line_numbers.items():
            if ln == line_num:
                return link_idx
        return -1

    def next_link(self) -> None:
        """Navigate to the next link."""
        if not self.links:
            return

        if self.current_link_index < len(self.links) - 1:
            self.current_link_index += 1
        else:
            # Wrap around to first link
            self.current_link_index = 0

    def prev_link(self) -> None:
        """Navigate to the previous link."""
        if not self.links:
            return

        if self.current_link_index > 0:
            self.current_link_index -= 1
        else:
            # Wrap around to last link
            self.current_link_index = len(self.links) - 1

    def activate_current_link(self) -> None:
        """Activate the currently selected link."""
        if self.links and 0 <= self.current_link_index < len(self.links):
            link = self.links[self.current_link_index]
            self.post_message(self.LinkActivated(link))

    def get_current_link(self) -> GemtextLink | None:
        """Get the currently selected link, or None if no link selected."""
        if self.links and 0 <= self.current_link_index < len(self.links):
            return self.links[self.current_link_index]
        return None

    def on_click(self, event: events.Click) -> None:
        """Handle mouse clicks on links."""
        # Calculate which link was clicked based on y position
        # Since each line is rendered with a newline, the y coordinate
        # corresponds to the line number in self.lines

        clicked_line = event.y
        if 0 <= clicked_line < len(self.lines):
            line = self.lines[clicked_line]
            if isinstance(line, GemtextLink):
                # Find the index of this link
                link_index = self._get_link_index_by_line(clicked_line)
                if link_index >= 0:
                    self.current_link_index = link_index
                    self.activate_current_link()

    def watch_current_link_index(self, old_index: int, new_index: int) -> None:
        """React to link selection changes."""
        # Refresh display when selection changes
        self.update(self._build_content())

        # Update status bar with current link URL (if parent app supports it)
        current_link = self.get_current_link()
        if current_link:
            # The app can watch for this or we can emit a message
            pass
