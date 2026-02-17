"""Add account modal for GMAP mail."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from astronomo.gmap_accounts import GmapAccount, GmapAccountManager
from astronomo.identities import IdentityManager


class AddAccountModal(ModalScreen[GmapAccount | None]):
    """Modal for adding a GMAP mail account."""

    DEFAULT_CSS = """
    AddAccountModal {
        align: center middle;
    }

    AddAccountModal > Container {
        width: 70;
        height: auto;
        max-height: 85%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    AddAccountModal .field-label {
        margin-top: 1;
    }

    AddAccountModal Input {
        width: 100%;
    }

    AddAccountModal Select {
        width: 100%;
    }

    AddAccountModal .button-row {
        align: center middle;
        padding-top: 1;
    }

    AddAccountModal .hint {
        color: $text-muted;
        padding-top: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        account_manager: GmapAccountManager,
        identity_manager: IdentityManager,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.account_manager = account_manager
        self.identity_manager = identity_manager

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Add GMAP Account"
        with container:
            yield Label("Account Name:", classes="field-label")
            yield Input(placeholder="e.g., Personal Mail", id="name-input")

            yield Label("GMAP Server Hostname:", classes="field-label")
            yield Input(placeholder="e.g., mail.example.com", id="hostname-input")

            yield Label("Port:", classes="field-label")
            yield Input(value="1960", id="port-input")

            yield Label("Mailbox Name:", classes="field-label")
            yield Input(
                placeholder="e.g., alice (from certificate USER_ID)",
                id="mailbox-input",
            )

            yield Label("Identity (Client Certificate):", classes="field-label")
            yield Select(
                self._get_identity_options(),
                id="identity-select",
                prompt="Select an identity...",
            )
            yield Label(
                "Import a Misfin certificate via Settings > Certificates first",
                classes="hint",
            )

            yield Label("GMAP Address (for sent mail):", classes="field-label")
            yield Input(
                placeholder="Leave empty for gmap@hostname",
                id="gmap-address-input",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Add Account", variant="primary", id="save-btn")

    def _get_identity_options(self) -> list[tuple[str, str]]:
        """Get available identities as select options."""
        identities = self.identity_manager.get_all_identities()
        options = []
        for identity in identities:
            label = f"{identity.name} ({identity.fingerprint[:16]}...)"
            options.append((label, identity.id))
        return options

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self._save_account()

    def _save_account(self) -> None:
        """Validate and save the new account."""
        name = self.query_one("#name-input", Input).value.strip()
        hostname = self.query_one("#hostname-input", Input).value.strip()
        port_str = self.query_one("#port-input", Input).value.strip()
        mailbox = self.query_one("#mailbox-input", Input).value.strip()
        gmap_address = self.query_one("#gmap-address-input", Input).value.strip()

        identity_select = self.query_one("#identity-select", Select)
        identity_id = (
            str(identity_select.value) if identity_select.value != Select.NULL else ""
        )

        # Validation
        if not name:
            self.app.notify("Account name is required", severity="error")
            return
        if not hostname:
            self.app.notify("Hostname is required", severity="error")
            return

        try:
            port = int(port_str)
        except ValueError:
            self.app.notify("Port must be a number", severity="error")
            return

        if not identity_id:
            self.app.notify("Please select an identity certificate", severity="error")
            return

        account = self.account_manager.add_account(
            name=name,
            hostname=hostname,
            port=port,
            mailbox=mailbox,
            identity_id=identity_id,
            gmap_address=gmap_address,
        )
        self.dismiss(account)

    def action_cancel(self) -> None:
        self.dismiss(None)
