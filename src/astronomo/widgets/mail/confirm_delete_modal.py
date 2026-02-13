"""Confirm delete modal for GMAP mail."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmDeleteMailModal(ModalScreen[bool]):
    """Modal for confirming permanent message deletion.

    Returns True if confirmed, False/None if cancelled.
    """

    DEFAULT_CSS = """
    ConfirmDeleteMailModal {
        align: center middle;
    }

    ConfirmDeleteMailModal > Container {
        width: 50;
        height: auto;
        border: thick $error;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDeleteMailModal .warning-message {
        padding: 1;
        background: $error 10%;
        border: solid $error;
        margin-bottom: 1;
    }

    ConfirmDeleteMailModal .button-row {
        align: center middle;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(self, msgid: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.msgid = msgid

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Confirm Delete"
        with container:
            yield Label(
                "This will permanently delete the message. "
                "This action cannot be undone.",
                classes="warning-message",
            )
            yield Label(f"Message ID: {self.msgid}")

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Delete", variant="error", id="delete-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "delete-btn":
            self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
