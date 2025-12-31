"""Edit Identity modal for Astronomo.

Provides rename and certificate regeneration functionality.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from astronomo.identities import Identity, IdentityManager


class EditIdentityModal(ModalScreen[bool]):
    """Modal screen for editing an identity (rename and regenerate).

    Args:
        manager: IdentityManager instance
        identity: The identity to edit
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

    def __init__(
        self,
        manager: IdentityManager,
        identity: Identity,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.identity = identity
        self._name_changed = False

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Edit Identity"
        with container:
            # Rename section
            yield Label("Name:", classes="field-label")
            yield Input(
                value=self.identity.name,
                placeholder="Identity name",
                id="name-input",
            )

            # Regenerate section
            yield Label("Regenerate Certificate", classes="section-title")
            yield Static(
                "Warning: Regenerating creates a new certificate with a new "
                "fingerprint. Servers that trusted the old certificate will "
                "need to re-authorize this identity.",
                classes="warning-text",
            )

            with Vertical(classes="regenerate-section"):
                yield Label("Hostname:", classes="field-label")
                yield Input(
                    placeholder="localhost",
                    id="hostname-input",
                )
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

                with Horizontal(classes="regenerate-row"):
                    yield Button(
                        "Regenerate Certificate",
                        variant="warning",
                        id="regenerate-btn",
                    )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Focus the name input on mount and select all text."""
        name_input = self.query_one("#name-input", Input)
        name_input.focus()
        name_input.action_select_all()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Track if name was changed."""
        if event.input.id == "name-input":
            self._name_changed = event.value != self.identity.name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "save-btn":
            self._save_changes()
        elif event.button.id == "regenerate-btn":
            self._regenerate_certificate()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in name input."""
        if event.input.id == "name-input":
            self._save_changes()

    def _save_changes(self) -> None:
        """Save name change and dismiss."""
        new_name = self.query_one("#name-input", Input).value.strip()

        if new_name and new_name != self.identity.name:
            self.manager.rename_identity(self.identity.id, new_name)
            self.dismiss(True)
        else:
            # No changes or empty name
            self.dismiss(self._name_changed)

    def _regenerate_certificate(self) -> None:
        """Regenerate the certificate."""
        hostname = self.query_one("#hostname-input", Input).value.strip()
        if not hostname:
            hostname = "localhost"

        validity_select = self.query_one("#validity-select", Select)
        validity_value = validity_select.value
        valid_days = validity_value if isinstance(validity_value, int) else 365

        # Also save name if changed
        new_name = self.query_one("#name-input", Input).value.strip()
        if new_name and new_name != self.identity.name:
            self.manager.rename_identity(self.identity.id, new_name)

        self.manager.regenerate_certificate(
            identity_id=self.identity.id,
            hostname=hostname,
            valid_days=valid_days,
        )

        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)
