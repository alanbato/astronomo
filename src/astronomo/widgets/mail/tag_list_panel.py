"""Tag list panel for the mail screen."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

# Standard tags in display order
REQUIRED_TAGS = ["Inbox", "Archive", "Sent", "Drafts", "Trash"]


class TagWidget(Static):
    """Widget displaying a tag with unread count badge."""

    DEFAULT_CSS = """
    TagWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    TagWidget:hover {
        background: $surface;
    }

    TagWidget.-selected {
        background: $accent-muted;
    }

    TagWidget.-has-unread {
        text-style: bold;
    }
    """

    def __init__(
        self,
        tag: str,
        count: int = 0,
        unread: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.tag = tag
        self.count = count
        self.unread = unread
        if unread > 0:
            self.add_class("-has-unread")

    def render(self) -> str:
        badge = f" ({self.unread})" if self.unread > 0 else ""
        indicator = "\u25cf " if self.unread > 0 else "  "
        return f"{indicator}{self.tag}{badge}"


class TagListPanel(VerticalScroll, can_focus=True):
    """Left panel showing tags with unread counts."""

    BORDER_TITLE = "Tags"

    DEFAULT_CSS = """
    TagListPanel {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    TagListPanel:focus {
        border: solid $accent;
    }

    TagListPanel .empty-message {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }

    TagListPanel .section-separator {
        width: 100%;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    TagListPanel .account-label {
        width: 100%;
        height: auto;
        padding: 0 1;
        text-style: bold;
        color: $text;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }
    """

    selected_index: reactive[int] = reactive(0, init=False)

    class TagSelected(Message):
        """Emitted when a tag is selected."""

        def __init__(self, tag: str) -> None:
            self.tag = tag
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tags: list[str] = []
        self._tag_counts: dict[str, int] = {}
        self._unread_counts: dict[str, int] = {}
        self._account_label: str = ""

    def refresh_list(
        self,
        account_label: str = "",
        tag_counts: dict[str, int] | None = None,
        unread_counts: dict[str, int] | None = None,
        custom_tags: list[str] | None = None,
    ) -> None:
        """Refresh the tag list display.

        Args:
            account_label: Account name to show at top
            tag_counts: Dict mapping tag to message count
            unread_counts: Dict mapping tag to unread count
            custom_tags: Additional custom tags beyond REQUIRED_TAGS
        """
        if tag_counts is not None:
            self._tag_counts = tag_counts
        if unread_counts is not None:
            self._unread_counts = unread_counts
        if account_label:
            self._account_label = account_label

        self.remove_children()
        self._tags = []

        # Account label
        if self._account_label:
            self.mount(Label(self._account_label, classes="account-label"))

        # Required tags
        for tag in REQUIRED_TAGS:
            count = self._tag_counts.get(tag, 0)
            unread = self._unread_counts.get(tag, 0)
            self._tags.append(tag)
            self.mount(TagWidget(tag, count=count, unread=unread))

        # Separator and custom tags
        extra_tags = custom_tags or []
        # Also include any tags from counts that aren't required
        for tag in self._tag_counts:
            if tag not in REQUIRED_TAGS and tag not in extra_tags and tag != "Unread":
                extra_tags.append(tag)

        if extra_tags:
            self.mount(Label("\u2500" * 18, classes="section-separator"))
            for tag in sorted(extra_tags):
                count = self._tag_counts.get(tag, 0)
                unread = self._unread_counts.get(tag, 0)
                self._tags.append(tag)
                self.mount(TagWidget(tag, count=count, unread=unread))

        if not self._tags:
            self.mount(Label("No tags", classes="empty-message"))
            return

        self._update_selection()

    def _update_selection(self) -> None:
        """Update the visual selection."""
        for widget in self.query("TagWidget"):
            widget.remove_class("-selected")

        widgets = list(self.query("TagWidget"))
        if widgets and 0 <= self.selected_index < len(widgets):
            widgets[self.selected_index].add_class("-selected")

    def get_selected_tag(self) -> str | None:
        """Get the currently selected tag."""
        if 0 <= self.selected_index < len(self._tags):
            return self._tags[self.selected_index]
        return None

    def move_selection(self, delta: int) -> None:
        """Move the selection by delta positions."""
        if not self._tags:
            return

        self.selected_index = max(
            0, min(len(self._tags) - 1, self.selected_index + delta)
        )
        self._update_selection()

    def activate_item(self) -> None:
        """Activate the selected tag."""
        tag = self.get_selected_tag()
        if tag:
            self.post_message(self.TagSelected(tag))

    def compose(self) -> ComposeResult:
        yield Label("No account selected", classes="empty-message")
