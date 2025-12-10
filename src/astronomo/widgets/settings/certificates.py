"""Certificates settings tab for managing client identities."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, Static

from astronomo.identities import Identity, IdentityManager, LagrangeImportResult

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo


class IdentityListItem(Static):
    """Widget displaying a single identity with action buttons."""

    DEFAULT_CSS = """
    IdentityListItem {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
        layout: horizontal;
    }

    IdentityListItem:hover {
        background: $surface-lighten-1;
    }

    IdentityListItem .identity-details {
        width: 1fr;
        height: auto;
    }

    IdentityListItem .identity-name {
        text-style: bold;
    }

    IdentityListItem .identity-info {
        color: $text-muted;
    }

    IdentityListItem .identity-expired {
        color: $error;
        text-style: bold;
    }

    IdentityListItem .identity-expiring-soon {
        color: $warning;
    }

    IdentityListItem .action-buttons {
        width: auto;
        height: auto;
        align: right middle;
    }

    IdentityListItem .action-buttons Button {
        min-width: 8;
        margin-left: 1;
    }
    """

    class EditRequested(Message):
        """Message sent when edit button is clicked."""

        def __init__(self, identity: Identity) -> None:
            self.identity = identity
            super().__init__()

    class DeleteRequested(Message):
        """Message sent when delete button is clicked."""

        def __init__(self, identity: Identity) -> None:
            self.identity = identity
            super().__init__()

    class ManageUrlsRequested(Message):
        """Message sent when URLs button is clicked."""

        def __init__(self, identity: Identity) -> None:
            self.identity = identity
            super().__init__()

    def __init__(self, identity: Identity, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.identity = identity

    def compose(self) -> ComposeResult:
        # Left side: identity details
        with Vertical(classes="identity-details"):
            yield Label(self.identity.name, classes="identity-name")

            # Fingerprint (truncated)
            short_fp = self.identity.fingerprint[:32] + "..."
            yield Label(f"Fingerprint: {short_fp}", classes="identity-info")

            # Expiration with status
            expiry_text, expiry_class = self._format_expiration()
            yield Label(expiry_text, classes=expiry_class)

            # URL count
            url_count = len(self.identity.url_prefixes)
            url_text = f"URL associations: {url_count}"
            yield Label(url_text, classes="identity-info")

        # Right side: action buttons in horizontal row
        with Horizontal(classes="action-buttons"):
            yield Button("Edit", variant="default", id=f"edit-{self.identity.id}")
            yield Button("URLs", variant="default", id=f"urls-{self.identity.id}")
            yield Button("Delete", variant="error", id=f"delete-{self.identity.id}")

    def _format_expiration(self) -> tuple[str, str]:
        """Format expiration date and return (text, css_class)."""
        if self.identity.expires_at is None:
            return "Expires: Unknown", "identity-info"

        now = datetime.now(timezone.utc)
        expires = self.identity.expires_at
        # Ensure expires is timezone-aware for comparison
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if expires < now:
            return f"Expired: {expires.strftime('%Y-%m-%d')}", "identity-expired"

        days_remaining = (expires - now).days
        if days_remaining <= 30:
            return (
                f"Expires: {expires.strftime('%Y-%m-%d')} ({days_remaining} days)",
                "identity-expiring-soon",
            )

        return f"Expires: {expires.strftime('%Y-%m-%d')}", "identity-info"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses and emit appropriate messages."""
        button_id = event.button.id or ""

        if button_id.startswith("edit-"):
            self.post_message(self.EditRequested(self.identity))
        elif button_id.startswith("delete-"):
            self.post_message(self.DeleteRequested(self.identity))
        elif button_id.startswith("urls-"):
            self.post_message(self.ManageUrlsRequested(self.identity))

        event.stop()


class CertificatesSettings(Static):
    """Certificates settings section for managing client identities."""

    DEFAULT_CSS = """
    CertificatesSettings {
        height: 100%;
        width: 100%;
    }

    CertificatesSettings VerticalScroll {
        height: 1fr;
    }

    CertificatesSettings .button-row-top {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    CertificatesSettings .button-row-top Button {
        margin-right: 1;
    }

    CertificatesSettings .empty-state {
        padding: 2;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, identity_manager: IdentityManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.identity_manager = identity_manager

    def compose(self) -> ComposeResult:
        with Horizontal(classes="button-row-top"):
            yield Button(
                "+ Create New Identity",
                variant="primary",
                id="create-identity-btn",
            )
            yield Button(
                "Import Certificate",
                variant="default",
                id="import-custom-btn",
            )
            yield Button(
                "Import from Lagrange",
                variant="default",
                id="import-lagrange-btn",
            )

        with VerticalScroll(id="identity-list", can_focus=False):
            yield from self._compose_identity_list()

    def _compose_identity_list(self) -> ComposeResult:
        """Compose the list of identity items."""
        identities = self.identity_manager.get_all_identities()

        if not identities:
            yield Label(
                "No identities yet. Create one to get started.",
                classes="empty-state",
            )
        else:
            for identity in identities:
                yield IdentityListItem(identity, id=f"identity-item-{identity.id}")

    async def refresh_list(self) -> None:
        """Refresh the identity list after changes."""
        scroll = self.query_one("#identity-list", VerticalScroll)
        await scroll.remove_children()

        identities = self.identity_manager.get_all_identities()

        if not identities:
            await scroll.mount(
                Label(
                    "No identities yet. Create one to get started.",
                    classes="empty-state",
                )
            )
        else:
            for identity in identities:
                await scroll.mount(
                    IdentityListItem(identity, id=f"identity-item-{identity.id}")
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create-identity-btn":
            self._show_create_modal()
            event.stop()
        elif event.button.id == "import-custom-btn":
            self._show_import_custom_modal()
            event.stop()
        elif event.button.id == "import-lagrange-btn":
            self._show_import_modal()
            event.stop()

    def _show_create_modal(self) -> None:
        """Show the create identity modal."""
        from astronomo.widgets.certificates import CreateIdentityModal

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            CreateIdentityModal(self.identity_manager),
            callback=self._on_identity_created,
        )

    async def _on_identity_created(self, identity: Identity | None) -> None:
        """Handle identity creation result."""
        if identity is not None:
            await self.refresh_list()

    def _show_import_custom_modal(self) -> None:
        """Show the import custom certificate modal."""
        from astronomo.widgets.certificates import ImportCustomModal

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            ImportCustomModal(self.identity_manager),
            callback=self._on_custom_import_complete,
        )

    async def _on_custom_import_complete(self, identity: Identity | None) -> None:
        """Handle custom import completion."""
        if identity is not None:
            await self.refresh_list()

    def _show_import_modal(self) -> None:
        """Show the import from Lagrange modal."""
        from astronomo.widgets.certificates import ImportLagrangeModal

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            ImportLagrangeModal(self.identity_manager),
            callback=self._on_import_complete,
        )

    async def _on_import_complete(self, result: LagrangeImportResult | None) -> None:
        """Handle import completion."""
        if result is not None and result.imported:
            await self.refresh_list()

    def on_identity_list_item_edit_requested(
        self, event: IdentityListItem.EditRequested
    ) -> None:
        """Handle edit button click."""
        from astronomo.widgets.certificates import EditIdentityModal

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            EditIdentityModal(self.identity_manager, event.identity),
            callback=self._on_edit_complete,
        )

    async def _on_edit_complete(self, result: bool | None) -> None:
        """Handle edit modal result."""
        if result:
            await self.refresh_list()

    def on_identity_list_item_delete_requested(
        self, event: IdentityListItem.DeleteRequested
    ) -> None:
        """Handle delete button click."""
        from astronomo.widgets.certificates import ConfirmDeleteModal

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            ConfirmDeleteModal(self.identity_manager, event.identity),
            callback=self._on_delete_complete,
        )

    async def _on_delete_complete(self, result: bool | None) -> None:
        """Handle delete confirmation result."""
        if result:
            await self.refresh_list()

    def on_identity_list_item_manage_urls_requested(
        self, event: IdentityListItem.ManageUrlsRequested
    ) -> None:
        """Handle URLs button click."""
        from astronomo.widgets.certificates import ManageUrlsModal

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            ManageUrlsModal(self.identity_manager, event.identity),
            callback=self._on_urls_modal_closed,
        )

    async def _on_urls_modal_closed(self, _result: None) -> None:
        """Handle URLs modal close."""
        # Always refresh since URL changes are saved immediately
        await self.refresh_list()
