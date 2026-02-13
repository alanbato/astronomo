"""Message preview panel for the mail screen."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static

from astronomo.mail_cache import CachedMessage
from astronomo.parser import parse_gemtext


class MessageHeaderWidget(Static):
    """Widget displaying message metadata headers."""

    DEFAULT_CSS = """
    MessageHeaderWidget {
        width: 100%;
        height: auto;
        padding: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    MessageHeaderWidget .header-label {
        color: $text-muted;
    }

    MessageHeaderWidget .header-value {
        text-style: bold;
    }
    """

    def __init__(
        self,
        *,
        sender: str = "",
        recipients: str = "",
        date_str: str = "",
        tags: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._sender = sender
        self._recipients = recipients
        self._date_str = date_str
        self._tags = tags or []

    def compose(self) -> ComposeResult:
        if self._sender:
            yield Label(f"From: {self._sender}")
        if self._recipients:
            yield Label(f"To: {self._recipients}")
        if self._date_str:
            yield Label(f"Date: {self._date_str}")
        if self._tags:
            tags_str = ", ".join(self._tags)
            yield Label(f"Tags: {tags_str}", classes="header-label")


class MessageBodyWidget(Static):
    """Widget displaying the gemtext body of a message."""

    DEFAULT_CSS = """
    MessageBodyWidget {
        width: 100%;
        height: auto;
        padding: 1;
    }
    """

    def __init__(self, body: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._body = body

    def compose(self) -> ComposeResult:
        # Parse the gemtext body and render each line
        lines = parse_gemtext(self._body)
        for line in lines:
            yield Label(line.raw)


class MessagePreviewPanel(VerticalScroll, can_focus=True):
    """Right panel showing full message preview."""

    BORDER_TITLE = "Message"

    DEFAULT_CSS = """
    MessagePreviewPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
    }

    MessagePreviewPanel:focus {
        border: solid $accent;
    }

    MessagePreviewPanel .empty-message {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }

    MessagePreviewPanel .loading-message {
        padding: 1;
        text-align: center;
        color: $text-muted;
    }

    MessagePreviewPanel .error-message {
        padding: 1;
        color: $error;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_msgid: str | None = None

    def show_placeholder(self) -> None:
        """Show placeholder when no message is selected."""
        self.remove_children()
        self.current_msgid = None
        self.mount(Label("Select a message to read", classes="empty-message"))

    def show_loading(self) -> None:
        """Show loading state."""
        self.remove_children()
        self.mount(Label("Loading message...", classes="loading-message"))

    def show_error(self, error: str) -> None:
        """Show error message."""
        self.remove_children()
        self.mount(Label(f"Error: {error}", classes="error-message"))

    def show_message(self, message: CachedMessage) -> None:
        """Display a full message with headers and body.

        Args:
            message: The cached message to display
        """
        self.remove_children()
        self.current_msgid = message.msgid

        try:
            parsed = message.parse()

            # Extract header fields eagerly so compose() doesn't need to parse
            sender = parsed.senders[0].long_form if parsed.senders else ""
            recipients = (
                ", ".join(r.long_form for r in parsed.recipients)
                if parsed.recipients
                else ""
            )
            date_str = (
                parsed.timestamps[0].strftime("%Y-%m-%d %H:%M UTC")
                if parsed.timestamps
                else ""
            )

            self.mount(
                MessageHeaderWidget(
                    sender=sender,
                    recipients=recipients,
                    date_str=date_str,
                    tags=message.tags,
                )
            )
            self.mount(MessageBodyWidget(parsed.body))

        except Exception as e:
            self.show_error(f"Failed to render message: {e}")

    def compose(self) -> ComposeResult:
        yield Label("Select a message to read", classes="empty-message")
