"""Message list panel for the mail screen."""

import humanize

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Label, Static

from astronomo.mail_cache import CachedMessage


class MessageWidget(Static, can_focus=True):
    """Widget displaying a single message in the list."""

    DEFAULT_CSS = """
    MessageWidget {
        width: 100%;
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
    }

    MessageWidget:hover {
        background: $surface;
    }

    MessageWidget:focus {
        border: solid $accent;
        background: $surface;
    }

    MessageWidget.-unread .msg-subject {
        text-style: bold;
    }

    MessageWidget.-read {
        color: $text-muted;
    }

    MessageWidget .msg-subject {
        width: 100%;
        height: auto;
    }

    MessageWidget .msg-preview {
        color: $text-muted;
        padding-top: 0;
    }

    MessageWidget .msg-meta {
        color: $text-muted;
        padding-top: 0;
    }
    """

    BINDINGS = [
        Binding("up", "focus_previous_item", "Previous", show=False),
        Binding("down", "focus_next_item", "Next", show=False),
        Binding("enter", "select_item", "Open", show=False),
    ]

    def __init__(
        self,
        message: CachedMessage,
        is_unread: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.cached_message = message
        self.is_unread = is_unread
        if is_unread:
            self.add_class("-unread")
        else:
            self.add_class("-read")

        # Set border title to relative time
        if message.timestamp:
            try:
                self.border_title = humanize.naturaltime(message.timestamp)
            except Exception:
                self.border_title = ""

    def on_focus(self) -> None:
        """Auto-select this message when focused (click or keyboard)."""
        panel = self.screen.query_one("#message-panel", MessageListPanel)
        panel.post_message(MessageListPanel.MessageSelected(self.cached_message.msgid))

    def action_focus_previous_item(self) -> None:
        """Focus the previous message, staying within the message panel."""
        items = list(self.screen.query("MessageWidget"))
        if not items:
            return
        idx = items.index(self) if self in items else 0
        if idx > 0:
            items[idx - 1].focus()

    def action_focus_next_item(self) -> None:
        """Focus the next message, staying within the message panel."""
        items = list(self.screen.query("MessageWidget"))
        if not items:
            return
        idx = items.index(self) if self in items else len(items) - 1
        if idx < len(items) - 1:
            items[idx + 1].focus()

    def action_select_item(self) -> None:
        """Select/activate this message."""
        panel = self.screen.query_one("#message-panel", MessageListPanel)
        panel.post_message(MessageListPanel.MessageSelected(self.cached_message.msgid))

    def compose(self) -> ComposeResult:
        indicator = "\u25cf " if self.is_unread else "  "
        subject = self.cached_message.subject or "(No subject)"
        yield Label(f"{indicator}{subject}", classes="msg-subject")

        # Body preview
        preview = self.cached_message.body_preview
        if preview:
            if len(preview) > 60:
                preview = preview[:57] + "..."
            yield Label(f"  {preview}", classes="msg-preview")

        # Sender info
        sender = self.cached_message.sender or "Unknown"
        # Truncate long sender addresses
        if len(sender) > 40:
            sender = sender[:37] + "..."
        yield Label(f"  {sender}", classes="msg-meta")


class MessageListPanel(VerticalScroll):
    """Center panel showing messages in the selected tag."""

    BORDER_TITLE = "Messages"

    DEFAULT_CSS = """
    MessageListPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
    }

    MessageListPanel:focus-within {
        border: solid $accent;
    }

    MessageListPanel .panel-title {
        text-style: bold;
        padding: 0 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    MessageListPanel .loading-message {
        padding: 1;
        text-align: center;
        color: $text-muted;
    }

    MessageListPanel .error-message {
        padding: 1;
        color: $error;
    }

    MessageListPanel .empty-message {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    class MessageSelected(Message):
        """Emitted when a message is selected."""

        def __init__(self, msgid: str) -> None:
            self.msgid = msgid
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_tag: str | None = None
        self.current_messages: list[CachedMessage] = []

    def show_placeholder(self) -> None:
        """Show placeholder when no tag is selected."""
        self.remove_children()
        self.current_tag = None
        self.current_messages = []
        self.mount(Label("Select a tag to view messages", classes="empty-message"))

    def show_loading(self, tag: str) -> None:
        """Show loading state while syncing."""
        self.remove_children()
        self.current_tag = tag
        self.mount(Label(f"Loading {tag}...", classes="loading-message"))

    def show_error(self, error: str) -> None:
        """Show error message."""
        self.remove_children()
        self.mount(Label(f"Error: {error}", classes="error-message"))

    def show_messages(
        self,
        tag: str,
        messages: list[CachedMessage],
    ) -> None:
        """Display messages for a tag.

        Args:
            tag: Tag name being displayed
            messages: List of cached messages to display
        """
        self.remove_children()
        self.current_tag = tag
        self.current_messages = messages

        self.mount(Label(f"{tag} ({len(messages)})", classes="panel-title"))

        if not messages:
            self.mount(Label("No messages", classes="empty-message"))
            return

        for msg in messages:
            is_unread = "Unread" in msg.tags
            self.mount(MessageWidget(msg, is_unread=is_unread))

    def on_click(self, event) -> None:
        """Focus clicked message widget (triggers selection via on_focus)."""
        widget = event.widget
        while widget and not isinstance(widget, MessageWidget):
            widget = widget.parent

        if isinstance(widget, MessageWidget):
            widget.focus()
