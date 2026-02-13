"""Mail settings panel for Astronomo."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, Static

from astronomo.gmap_accounts import GmapAccount, GmapAccountManager


class AccountListItem(Static):
    """Widget displaying a GMAP account in the settings list."""

    DEFAULT_CSS = """
    AccountListItem {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
        layout: horizontal;
    }

    AccountListItem:hover {
        background: $surface-lighten-1;
    }

    AccountListItem .account-details {
        width: 1fr;
        height: auto;
    }

    AccountListItem .account-name {
        text-style: bold;
    }

    AccountListItem .account-info {
        color: $text-muted;
    }

    AccountListItem .action-buttons {
        width: auto;
        height: auto;
        align: right middle;
    }
    """

    def __init__(self, account: GmapAccount, **kwargs) -> None:
        super().__init__(**kwargs)
        self.account = account

    def compose(self) -> ComposeResult:
        with Vertical(classes="account-details"):
            yield Label(self.account.name, classes="account-name")
            address = f"{self.account.mailbox}@{self.account.hostname}"
            yield Label(address, classes="account-info")
            if self.account.last_sync:
                sync_str = self.account.last_sync.strftime("%Y-%m-%d %H:%M")
                yield Label(f"Last sync: {sync_str}", classes="account-info")

        with Horizontal(classes="action-buttons"):
            yield Button("Delete", variant="error", id=f"delete-{self.account.id}")


class MailSettings(Static):
    """Mail settings tab showing GMAP accounts and preferences."""

    DEFAULT_CSS = """
    MailSettings {
        height: 100%;
        width: 100%;
    }

    MailSettings VerticalScroll {
        height: 1fr;
    }

    MailSettings .section-header {
        height: auto;
        padding-bottom: 1;
    }

    MailSettings .section-title {
        text-style: bold;
        border-bottom: solid $primary;
    }

    MailSettings .section-description {
        color: $text-muted;
    }

    MailSettings .empty-state {
        padding: 2;
        text-align: center;
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(
        self,
        account_manager: GmapAccountManager,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.account_manager = account_manager

    def compose(self) -> ComposeResult:
        with Vertical(classes="section-header"):
            yield Label("GMAP Mail Accounts", classes="section-title")
            yield Label(
                "Manage your GMAP mail accounts. "
                "Import certificates via the Certificates tab first.",
                classes="section-description",
            )

        with VerticalScroll(id="account-list", can_focus=False):
            yield from self._compose_accounts()

    def _compose_accounts(self) -> ComposeResult:
        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            yield Label(
                "No GMAP accounts configured.\nUse Ctrl+E > Ctrl+A to add an account.",
                classes="empty-state",
            )
            return

        for account in accounts:
            yield AccountListItem(account)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle account action buttons."""
        button_id = event.button.id or ""
        if button_id.startswith("delete-"):
            account_id = button_id.removeprefix("delete-")
            self._delete_account(account_id)

    def _delete_account(self, account_id: str) -> None:
        """Delete an account."""
        if self.account_manager.remove_account(account_id):
            self.app.notify("Account removed")
            self._refresh_list()

    def _refresh_list(self) -> None:
        """Refresh the account list."""
        scroll = self.query_one("#account-list", VerticalScroll)
        scroll.remove_children()
        for widget in self._compose_accounts():
            scroll.mount(widget)
