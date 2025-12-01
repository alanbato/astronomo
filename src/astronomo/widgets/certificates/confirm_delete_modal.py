"""Confirm Delete modal for Astronomo."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from astronomo.identities import Identity, IdentityManager


class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal screen for confirming identity deletion.

    Args:
        manager: IdentityManager instance
        identity: The identity to delete
    """

    DEFAULT_CSS = """
    ConfirmDeleteModal {
        align: center middle;
    }

    ConfirmDeleteModal > Container {
        width: 55;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDeleteModal .modal-title {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        padding-bottom: 1;
        color: $error;
    }

    ConfirmDeleteModal .identity-name {
        text-style: bold;
        padding: 1 0;
        text-align: center;
    }

    ConfirmDeleteModal .warning-text {
        color: $text-muted;
        padding: 1 0;
    }

    ConfirmDeleteModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    ConfirmDeleteModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: IdentityManager,
        identity: Identity,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.identity = identity

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Delete Identity", classes="modal-title")

            yield Static(
                "Are you sure you want to delete this identity?",
            )
            yield Label(f'"{self.identity.name}"', classes="identity-name")

            yield Static(
                "This will permanently remove the certificate, private key, "
                "and all URL associations.",
                classes="warning-text",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Delete", variant="error", id="delete-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "delete-btn":
            self._delete_identity()

    def _delete_identity(self) -> None:
        """Delete the identity and dismiss."""
        self.manager.remove_identity(self.identity.id)
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)
