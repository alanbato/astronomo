"""Create Identity modal for Astronomo."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from astronomo.identities import Identity, IdentityManager


class CreateIdentityModal(ModalScreen[Identity | None]):
    """Modal screen for creating a new identity.

    Args:
        manager: IdentityManager instance
    """

    CSS_PATH = Path(__file__).parent / "certificates.tcss"

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    VALIDITY_OPTIONS = [
        ("30 days", 30),
        ("90 days", 90),
        ("1 year", 365),
        ("2 years", 730),
        ("5 years", 1825),
    ]

    def __init__(self, manager: IdentityManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Create New Identity"
        with container:
            yield Label("Identity name:", classes="field-label")
            yield Input(placeholder="My Identity", id="name-input")

            yield Label("Hostname for certificate:", classes="field-label")
            yield Input(placeholder="localhost", id="hostname-input")
            yield Label(
                "Used in the certificate's Common Name (CN)",
                classes="field-hint",
            )

            yield Label("Valid for:", classes="field-label")
            yield Select(
                options=self.VALIDITY_OPTIONS,
                value=365,
                id="validity-select",
                allow_blank=False,
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Create", variant="primary", id="create-btn")

    def on_mount(self) -> None:
        """Focus the name input on mount."""
        self.query_one("#name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "create-btn":
            self._create_identity()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in inputs."""
        # If in name input, move to hostname
        if event.input.id == "name-input":
            self.query_one("#hostname-input", Input).focus()
        elif event.input.id == "hostname-input":
            self._create_identity()

    def _create_identity(self) -> None:
        """Create the identity and dismiss."""
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            name = "New Identity"

        hostname = self.query_one("#hostname-input", Input).value.strip()
        if not hostname:
            hostname = "localhost"

        validity_select = self.query_one("#validity-select", Select)
        validity_value = validity_select.value
        valid_days = validity_value if isinstance(validity_value, int) else 365

        identity = self.manager.create_identity(
            name=name,
            hostname=hostname,
            valid_days=valid_days,
        )

        self.dismiss(identity)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
