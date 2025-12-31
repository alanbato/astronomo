"""Confirm Delete modal for Astronomo."""

from pathlib import Path

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

    CSS_PATH = Path(__file__).parent / "certificates.tcss"

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
        container = Container()
        container.border_title = "Delete Identity"
        with container:
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
