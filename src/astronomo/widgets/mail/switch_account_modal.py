"""Switch account modal for GMAP mail."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView

from astronomo.gmap_accounts import GmapAccount, GmapAccountManager


class SwitchAccountModal(ModalScreen[GmapAccount | None]):
    """Modal for switching between GMAP mail accounts.

    Returns the selected GmapAccount, or None if cancelled.
    Dismisses with the string "deleted" if current account was removed.
    """

    DEFAULT_CSS = """
    SwitchAccountModal {
        align: center middle;
    }

    SwitchAccountModal > Container {
        width: 65;
        height: auto;
        max-height: 40%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    SwitchAccountModal ListView {
        margin-top: 1;
    }

    SwitchAccountModal ListItem {
        height: 2;
    }

    SwitchAccountModal .account-info {
        width: 1fr;
    }

    SwitchAccountModal .account-name {
        text-style: bold;
    }

    SwitchAccountModal .account-address {
        color: $text-muted;
    }

    SwitchAccountModal .delete-btn {
        min-width: 0;
        height: 1;
        background: $error;
        color: $text;
        border: none;
    }

    SwitchAccountModal .delete-btn:hover {
        background: $error 80%;
    }

    SwitchAccountModal .button-row {
        align: center middle;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        accounts: list[GmapAccount],
        account_manager: GmapAccountManager,
        current_account: GmapAccount | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.accounts = accounts
        self.account_manager = account_manager
        self.current_account = current_account
        self._deleted_current = False

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Switch Account"
        with container:
            yield Label("Select an account:")
            list_view = ListView(id="account-list")
            # 2 rows per item, capped at 18 rows for scrolling
            list_view.styles.height = min(len(self.accounts) * 2, 18)
            with list_view:
                for account in self.accounts:
                    yield self._make_item(account)

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")

    def _make_item(self, account: GmapAccount) -> ListItem:
        is_current = (
            self.current_account is not None and account.id == self.current_account.id
        )
        prefix = "> " if is_current else "  "
        address = f"{account.mailbox}@{account.hostname}"
        return ListItem(
            Horizontal(
                Vertical(
                    Label(f"{prefix}{account.name}", classes="account-name"),
                    Label(f"  {address}", classes="account-address"),
                    classes="account-info",
                ),
                Button("X", classes="delete-btn", id=f"del-{account.id}"),
            ),
            id=f"account-{account.id}",
        )

    def on_mount(self) -> None:
        """Focus the account list."""
        self.query_one("#account-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle account selection."""
        item_id = event.item.id
        if item_id and item_id.startswith("account-"):
            account_id = item_id[len("account-") :]
            for account in self.accounts:
                if account.id == account_id:
                    self.dismiss(account)
                    return

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
            return

        if event.button.id and event.button.id.startswith("del-"):
            event.stop()
            account_id = event.button.id[len("del-") :]
            self._delete_account(account_id)

    def _delete_account(self, account_id: str) -> None:
        """Remove an account after confirmation."""
        account = next((a for a in self.accounts if a.id == account_id), None)
        if account is None:
            return

        self.account_manager.remove_account(account_id)
        self.accounts = [a for a in self.accounts if a.id != account_id]

        # Track if we deleted the current account
        if self.current_account and account_id == self.current_account.id:
            self._deleted_current = True

        # Remove the ListItem from the UI
        try:
            item = self.query_one(f"#account-{account_id}", ListItem)
            item.remove()
        except Exception:
            pass

        # Update ListView height
        list_view = self.query_one("#account-list", ListView)
        list_view.styles.height = max(len(self.accounts) * 2, 2)

        self.app.notify(f"Removed account: {account.name}")

        # If no accounts left, close modal
        if not self.accounts:
            self.dismiss(None)

    def action_cancel(self) -> None:
        if self._deleted_current:
            # Signal that current account was removed
            first = self.accounts[0] if self.accounts else None
            self.dismiss(first)
        else:
            self.dismiss(None)
