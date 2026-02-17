"""Mail screen for Astronomo.

Provides a full-screen three-pane interface for GMAP mail:
tags sidebar | message list | message preview.
"""

import logging
from datetime import UTC, datetime

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Label

from astronomo.gmap_accounts import GmapAccount, GmapAccountManager
from astronomo.gmap_client import (
    GmapAuthError,
    GmapClient,
    GmapError,
    GmapNotFoundError,
    GmapTempFailure,
)
from astronomo.identities import IdentityManager
from astronomo.mail_cache import MailCache
from astronomo.widgets.mail.message_list_panel import MessageListPanel
from astronomo.widgets.mail.message_preview_panel import MessagePreviewPanel
from astronomo.widgets.mail.tag_list_panel import REQUIRED_TAGS, TagListPanel

logger = logging.getLogger(__name__)

# Tags to sync from the server
SYNC_TAGS = ["Inbox", "Archive", "Sent", "Drafts", "Trash", "Unread"]


class MailScreen(Screen):
    """Full-screen three-pane mail interface."""

    DEFAULT_CSS = """
    MailScreen {
        background: $background;
    }

    MailScreen #mail-header {
        height: auto;
        width: 100%;
        padding: 1;
        background: $surface;
    }

    MailScreen #mail-title {
        text-style: bold;
    }

    MailScreen #mail-sync-status {
        color: $text-muted;
        padding-left: 2;
    }

    MailScreen #mail-content {
        width: 100%;
        height: 1fr;
    }

    MailScreen #tag-panel {
        width: 22;
        height: 100%;
    }

    MailScreen #message-panel {
        width: 40;
        height: 100%;
    }

    MailScreen #preview-panel {
        width: 1fr;
        height: 100%;
    }
    """

    BINDINGS = [
        # Mail screen actions
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("ctrl+e", "dismiss", "Close", show=False, priority=True),
        Binding("tab", "cycle_panel", "Next Panel", priority=True),
        Binding("shift+tab", "cycle_panel_back", "Prev Panel", priority=True),
        Binding("left", "cycle_panel_back", show=False, priority=True),
        Binding("right", "cycle_panel", show=False, priority=True),
        Binding("ctrl+n", "compose", "Compose"),
        Binding("ctrl+r", "sync", "Sync"),
        Binding("a", "archive", "Archive"),
        Binding("d", "trash", "Trash"),
        Binding("D", "permanent_delete", "Delete", show=False),
        Binding("u", "toggle_unread", "Unread"),
        Binding("r", "reply", "Reply"),
        Binding("t", "manage_tags", "Tags"),
        Binding("enter", "activate_item", "Open", show=False),
        Binding("up", "cursor_up", show=False),
        Binding("down", "cursor_down", show=False),
        Binding("ctrl+a", "add_account", "Add Account"),
        # Suppress non-email app bindings
        Binding("ctrl+b", "noop", show=False, priority=True),
        Binding("ctrl+d", "noop", show=False, priority=True),
        Binding("ctrl+s", "noop", show=False, priority=True),
        Binding("ctrl+k", "noop", show=False, priority=True),
        Binding("ctrl+j", "noop", show=False, priority=True),
        Binding("ctrl+t", "noop", show=False, priority=True),
        Binding("ctrl+w", "noop", show=False, priority=True),
        Binding("ctrl+tab", "noop", show=False, priority=True),
        Binding("ctrl+shift+tab", "noop", show=False, priority=True),
    ]

    def __init__(
        self,
        account_manager: GmapAccountManager,
        identity_manager: IdentityManager,
        cache: MailCache,
        compose_to: str = "",
        compose_subject: str = "",
        compose_body: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.account_manager = account_manager
        self.identity_manager = identity_manager
        self.cache = cache
        self.compose_to = compose_to
        self.compose_subject = compose_subject
        self.compose_body = compose_body
        self.current_account: GmapAccount | None = None
        self.current_tag: str = "Inbox"
        self.current_msgid: str | None = None
        self._panel_focus_order = ["tag-panel", "message-panel", "preview-panel"]
        self._current_panel_index = 0
        self._pending_sent_retag: bool = False

    def compose(self) -> ComposeResult:
        with Container(id="mail-header"):
            yield Label("Mail", id="mail-title")
            yield Label("", id="mail-sync-status")

        with Horizontal(id="mail-content"):
            yield TagListPanel(id="tag-panel")
            yield MessageListPanel(id="message-panel")
            yield MessagePreviewPanel(id="preview-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the mail screen."""
        accounts = self.account_manager.get_all_accounts()

        if not accounts:
            # No accounts — show add account prompt
            self._update_title("Mail — No accounts configured")
            message_panel = self.query_one("#message-panel", MessageListPanel)
            message_panel.show_placeholder()
            preview_panel = self.query_one("#preview-panel", MessagePreviewPanel)
            preview_panel.show_placeholder()
            self.app.notify("Press Ctrl+A to add a GMAP account")
            return

        # Select first account and sync
        self.current_account = accounts[0]
        self._update_title(
            f"Mail — {self.current_account.mailbox}@{self.current_account.hostname}"
        )
        self.query_one("#tag-panel", TagListPanel).focus()

        # Load cached data first, then sync in background
        self._load_from_cache()
        self._sync_account(self.current_account)

        # Auto-open compose modal if pre-fill address was provided
        if self.compose_to:
            self.call_after_refresh(self._open_compose_for)

    def _open_compose_for(self) -> None:
        """Open compose modal with pre-filled fields from a misfin:// URL."""
        if self.current_account is None:
            return

        from astronomo.widgets.mail.compose_modal import ComposeModal

        self.app.push_screen(
            ComposeModal(
                account=self.current_account,
                identity_manager=self.identity_manager,
                to=self.compose_to,
                subject=self.compose_subject,
                body=self.compose_body,
            ),
            self._on_compose_done,
        )

    def _update_title(self, title: str) -> None:
        """Update the mail screen title."""
        self.query_one("#mail-title", Label).update(title)

    def _update_sync_status(self, status: str) -> None:
        """Update the sync status label."""
        self.query_one("#mail-sync-status", Label).update(status)

    def _load_from_cache(self) -> None:
        """Load tags and messages from local cache."""
        if self.current_account is None:
            return

        account_id = self.current_account.id
        tag_counts = self.cache.get_tag_counts(account_id)

        # Build unread counts for each tag
        unread_counts: dict[str, int] = {}
        for tag in list(tag_counts.keys()) + REQUIRED_TAGS:
            if tag != "Unread":
                unread_counts[tag] = self.cache.get_unread_count(account_id, tag)

        tag_panel = self.query_one("#tag-panel", TagListPanel)
        tag_panel.refresh_list(
            account_label=f"{self.current_account.mailbox}@{self.current_account.hostname}",
            tag_counts=tag_counts,
            unread_counts=unread_counts,
        )

        # Load messages for current tag
        self._load_tag_messages(self.current_tag)

    def _load_tag_messages(self, tag: str) -> None:
        """Load messages for a tag from cache."""
        if self.current_account is None:
            return

        self.current_tag = tag
        messages = self.cache.list_by_tag(self.current_account.id, tag)

        message_panel = self.query_one("#message-panel", MessageListPanel)
        message_panel.show_messages(tag, messages)

        # Clear preview
        preview_panel = self.query_one("#preview-panel", MessagePreviewPanel)
        preview_panel.show_placeholder()
        self.current_msgid = None

    # --- Sync ---

    @work(exclusive=True, group="mail-sync")
    async def _sync_account(self, account: GmapAccount) -> None:
        """Sync messages from the GMAP server."""
        identity = self.identity_manager.get_identity(account.identity_id)
        if identity is None:
            self.app.notify(
                f"Identity not found for {account.name}. Reconfigure the account.",
                severity="error",
            )
            return

        if not identity.cert_path.exists() or not identity.key_path.exists():
            self.app.notify(
                f"Certificate files missing for {account.name}.",
                severity="error",
            )
            return

        self._update_sync_status("Syncing...")

        client = GmapClient(
            hostname=account.hostname,
            port=account.port,
            cert_path=identity.cert_path,
            key_path=identity.key_path,
            timeout=30,
        )

        last_sync = self.cache.get_last_sync(account.id)
        new_count = 0

        try:
            # Fetch message IDs for each tag
            all_new_msgids: set[str] = set()
            tag_msgids: dict[str, list[str]] = {}

            for tag in SYNC_TAGS:
                try:
                    msgids = await client.list_by_tag(tag, since=last_sync)
                    tag_msgids[tag] = msgids
                    all_new_msgids.update(msgids)
                except GmapNotFoundError:
                    tag_msgids[tag] = []
                except GmapTempFailure as e:
                    logger.warning("Temp failure listing tag %s: %s", tag, e)
                    tag_msgids[tag] = []

            # Fetch new messages
            for msgid in all_new_msgids:
                if self.cache.has_message(account.id, msgid):
                    # Update tags for existing messages
                    msg_tags = [tag for tag, ids in tag_msgids.items() if msgid in ids]
                    if msg_tags:
                        self.cache.update_tags(account.id, msgid, add=msg_tags)
                    continue

                try:
                    _msg, raw = await client.get_message(msgid)
                    msg_tags = [tag for tag, ids in tag_msgids.items() if msgid in ids]
                    self.cache.store_message(account.id, msgid, raw, msg_tags)
                    new_count += 1

                    # Detect sent copies: if we just sent a message and
                    # this new message is from ourselves, retag as Sent
                    if self._pending_sent_retag:
                        sender_addr = f"{account.mailbox}@{account.hostname}"
                        if _msg.senders and _msg.senders[0].address == sender_addr:
                            self.cache.update_tags(
                                account.id,
                                msgid,
                                add=["Sent"],
                                remove=["Inbox", "Unread"],
                            )
                            try:
                                await client.add_tag(msgid, "Sent")
                                await client.remove_tag(msgid, "Inbox")
                                await client.remove_tag(msgid, "Unread")
                            except GmapError as e:
                                logger.warning("Failed to retag sent copy: %s", e)
                            self._pending_sent_retag = False
                except GmapTempFailure:
                    logger.warning("Cannot fetch message %s (encrypted?)", msgid)
                except GmapError as e:
                    logger.warning("Failed to fetch message %s: %s", msgid, e)

            # Update sync timestamp
            self.cache.set_last_sync(account.id, datetime.now(UTC))
            self.account_manager.update_account(account.id, last_sync=datetime.now(UTC))

            # Refresh UI
            self._load_from_cache()

            if new_count > 0:
                self.app.notify(f"Synced: {new_count} new message(s)")
            self._update_sync_status(
                f"Last synced: {datetime.now(UTC).strftime('%H:%M UTC')}"
            )

        except GmapAuthError as e:
            self.app.notify(f"Authentication failed: {e}", severity="error")
            self._update_sync_status("Auth error")
        except Exception as e:
            logger.exception("Sync failed for %s", account.name)
            self.app.notify(f"Sync failed: {e}", severity="error")
            self._update_sync_status("Sync failed")

    # --- Message Handlers ---

    def on_tag_list_panel_tag_selected(self, message: TagListPanel.TagSelected) -> None:
        """Handle tag selection from the panel."""
        self._load_tag_messages(message.tag)

    def on_message_list_panel_message_selected(
        self, message: MessageListPanel.MessageSelected
    ) -> None:
        """Handle message selection from the panel."""
        if self.current_account is None:
            return

        self.current_msgid = message.msgid
        cached = self.cache.get_message(self.current_account.id, message.msgid)
        if cached is None:
            return

        # Show preview
        preview_panel = self.query_one("#preview-panel", MessagePreviewPanel)
        preview_panel.show_message(cached)

        # Mark as read (remove Unread tag)
        if "Unread" in cached.tags:
            self._mark_as_read(message.msgid)

    @work(exclusive=True, group="mail-tag-op")
    async def _mark_as_read(self, msgid: str) -> None:
        """Remove Unread tag from a message."""
        if self.current_account is None:
            return

        # Update cache immediately
        self.cache.update_tags(self.current_account.id, msgid, remove=["Unread"])
        self._load_from_cache()

        # Sync to server
        identity = self.identity_manager.get_identity(self.current_account.identity_id)
        if identity is None:
            return

        try:
            client = GmapClient(
                hostname=self.current_account.hostname,
                port=self.current_account.port,
                cert_path=identity.cert_path,
                key_path=identity.key_path,
            )
            await client.remove_tag(msgid, "Unread")
        except GmapError as e:
            logger.warning("Failed to mark as read on server: %s", e)

    # --- Panel Navigation ---

    def _focus_panel(self, panel_id: str) -> None:
        """Focus a panel, auto-focusing first message widget if applicable."""
        if panel_id == "message-panel":
            widgets = list(self.query("MessageWidget"))
            if widgets:
                widgets[0].focus()
                return
        self.query_one(f"#{panel_id}").focus()

    def action_cycle_panel(self) -> None:
        """Cycle focus to the next panel."""
        self._current_panel_index = (self._current_panel_index + 1) % len(
            self._panel_focus_order
        )
        self._focus_panel(self._panel_focus_order[self._current_panel_index])

    def action_cycle_panel_back(self) -> None:
        """Cycle focus to the previous panel."""
        self._current_panel_index = (self._current_panel_index - 1) % len(
            self._panel_focus_order
        )
        self._focus_panel(self._panel_focus_order[self._current_panel_index])

    def action_cursor_up(self) -> None:
        """Move cursor up in the focused panel."""
        tag_panel = self.query_one("#tag-panel", TagListPanel)
        if tag_panel.has_focus:
            tag_panel.move_selection(-1)
        elif self._current_panel_index == 1:
            # Message panel — handled by MessageWidget bindings when focused
            # If panel itself has focus (no message focused), focus last widget
            widgets = list(self.query("MessageWidget"))
            if widgets:
                widgets[-1].focus()

    def action_cursor_down(self) -> None:
        """Move cursor down in the focused panel."""
        tag_panel = self.query_one("#tag-panel", TagListPanel)
        if tag_panel.has_focus:
            tag_panel.move_selection(1)
        elif self._current_panel_index == 1:
            # Message panel — handled by MessageWidget bindings when focused
            # If panel itself has focus (no message focused), focus first widget
            widgets = list(self.query("MessageWidget"))
            if widgets:
                widgets[0].focus()

    def action_activate_item(self) -> None:
        """Activate the selected item in the focused panel."""
        tag_panel = self.query_one("#tag-panel", TagListPanel)
        if tag_panel.has_focus:
            tag_panel.activate_item()

    # --- Mail Actions ---

    def action_sync(self) -> None:
        """Sync the current account."""
        if self.current_account:
            self._sync_account(self.current_account)

    def action_archive(self) -> None:
        """Archive the selected message."""
        if self.current_account and self.current_msgid:
            self._archive_message(self.current_msgid)

    @work(exclusive=True, group="mail-tag-op")
    async def _archive_message(self, msgid: str) -> None:
        """Move message from Inbox to Archive."""
        if self.current_account is None:
            return

        # Update cache
        self.cache.update_tags(
            self.current_account.id,
            msgid,
            add=["Archive"],
            remove=["Inbox"],
        )
        self._load_from_cache()
        self.app.notify("Archived")

        # Sync to server
        identity = self.identity_manager.get_identity(self.current_account.identity_id)
        if identity is None:
            return

        try:
            client = GmapClient(
                hostname=self.current_account.hostname,
                port=self.current_account.port,
                cert_path=identity.cert_path,
                key_path=identity.key_path,
            )
            await client.remove_tag(msgid, "Inbox")
            await client.add_tag(msgid, "Archive")
        except GmapError as e:
            logger.warning("Failed to archive on server: %s", e)

    def action_trash(self) -> None:
        """Move the selected message to Trash."""
        if self.current_account and self.current_msgid:
            self._trash_message(self.current_msgid)

    @work(exclusive=True, group="mail-tag-op")
    async def _trash_message(self, msgid: str) -> None:
        """Tag message as Trash."""
        if self.current_account is None:
            return

        # Update cache — remove Inbox so message disappears from Inbox view
        self.cache.update_tags(
            self.current_account.id,
            msgid,
            add=["Trash"],
            remove=["Inbox"],
        )
        self._load_from_cache()
        self.app.notify("Moved to Trash")

        # Sync to server
        identity = self.identity_manager.get_identity(self.current_account.identity_id)
        if identity is None:
            return

        try:
            client = GmapClient(
                hostname=self.current_account.hostname,
                port=self.current_account.port,
                cert_path=identity.cert_path,
                key_path=identity.key_path,
            )
            await client.add_tag(msgid, "Trash")
            await client.remove_tag(msgid, "Inbox")
        except GmapError as e:
            logger.warning("Failed to trash on server: %s", e)

    def action_permanent_delete(self) -> None:
        """Permanently delete the selected message (must be in Trash)."""
        if not self.current_account or not self.current_msgid:
            return

        if self.current_tag != "Trash":
            self.app.notify("Move to Trash first (press d)", severity="warning")
            return

        from astronomo.widgets.mail.confirm_delete_modal import (
            ConfirmDeleteMailModal,
        )

        self.app.push_screen(
            ConfirmDeleteMailModal(self.current_msgid),
            self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, confirmed: bool | None) -> None:
        """Handle deletion confirmation."""
        if confirmed and self.current_msgid:
            self._delete_message(self.current_msgid)

    @work(exclusive=True, group="mail-tag-op")
    async def _delete_message(self, msgid: str) -> None:
        """Permanently delete a message."""
        if self.current_account is None:
            return

        identity = self.identity_manager.get_identity(self.current_account.identity_id)
        if identity is None:
            return

        try:
            client = GmapClient(
                hostname=self.current_account.hostname,
                port=self.current_account.port,
                cert_path=identity.cert_path,
                key_path=identity.key_path,
            )
            await client.delete_message(msgid)

            # Remove from cache
            self.cache.remove_message(self.current_account.id, msgid)
            self.current_msgid = None
            self._load_from_cache()
            self.app.notify("Deleted permanently")
        except GmapError as e:
            self.app.notify(f"Delete failed: {e}", severity="error")

    def action_toggle_unread(self) -> None:
        """Toggle unread status on the selected message."""
        if self.current_account and self.current_msgid:
            self._toggle_unread(self.current_msgid)

    @work(exclusive=True, group="mail-tag-op")
    async def _toggle_unread(self, msgid: str) -> None:
        """Toggle Unread tag on a message."""
        if self.current_account is None:
            return

        cached = self.cache.get_message(self.current_account.id, msgid)
        if cached is None:
            return

        is_unread = "Unread" in cached.tags
        if is_unread:
            self.cache.update_tags(self.current_account.id, msgid, remove=["Unread"])
        else:
            self.cache.update_tags(self.current_account.id, msgid, add=["Unread"])
        self._load_from_cache()

        # Sync to server
        identity = self.identity_manager.get_identity(self.current_account.identity_id)
        if identity is None:
            return

        try:
            client = GmapClient(
                hostname=self.current_account.hostname,
                port=self.current_account.port,
                cert_path=identity.cert_path,
                key_path=identity.key_path,
            )
            if is_unread:
                await client.remove_tag(msgid, "Unread")
            else:
                await client.add_tag(msgid, "Unread")
        except GmapError as e:
            logger.warning("Failed to toggle unread on server: %s", e)

    def action_compose(self) -> None:
        """Open the compose modal."""
        if self.current_account is None:
            self.app.notify("No account configured", severity="warning")
            return

        from astronomo.widgets.mail.compose_modal import ComposeModal

        self.app.push_screen(
            ComposeModal(
                account=self.current_account,
                identity_manager=self.identity_manager,
            ),
            self._on_compose_done,
        )

    def _on_compose_done(self, sent: bool | None) -> None:
        """Handle compose modal result."""
        if sent:
            self.app.notify("Message sent")
            # Sync to pick up the sent copy; flag it for re-tagging
            # so the copy is tagged Sent (not Inbox/Unread)
            if self.current_account:
                self._pending_sent_retag = True
                self._sync_account(self.current_account)

    def action_reply(self) -> None:
        """Reply to the selected message."""
        if not self.current_account or not self.current_msgid:
            return

        cached = self.cache.get_message(self.current_account.id, self.current_msgid)
        if cached is None:
            return

        from astronomo.widgets.mail.compose_modal import ComposeModal

        self.app.push_screen(
            ComposeModal(
                account=self.current_account,
                identity_manager=self.identity_manager,
                reply_to=cached,
            ),
            self._on_compose_done,
        )

    def action_manage_tags(self) -> None:
        """Manage tags on the selected message."""
        if not self.current_account or not self.current_msgid:
            return

        cached = self.cache.get_message(self.current_account.id, self.current_msgid)
        if cached is None:
            return

        all_tags = self.cache.get_all_tags(self.current_account.id)

        from astronomo.widgets.mail.tag_manage_modal import TagManageModal

        self.app.push_screen(
            TagManageModal(
                current_tags=cached.tags,
                all_tags=all_tags,
            ),
            self._on_tags_changed,
        )

    def _on_tags_changed(self, new_tags: list[str] | None) -> None:
        """Handle tag management result."""
        if new_tags is None or not self.current_account or not self.current_msgid:
            return

        cached = self.cache.get_message(self.current_account.id, self.current_msgid)
        if cached is None:
            return

        old_tags = set(cached.tags)
        new_tags_set = set(new_tags)

        tags_to_add = list(new_tags_set - old_tags)
        tags_to_remove = list(old_tags - new_tags_set)

        if tags_to_add or tags_to_remove:
            self.cache.update_tags(
                self.current_account.id,
                self.current_msgid,
                add=tags_to_add,
                remove=tags_to_remove,
            )
            self._apply_tag_changes_to_server(
                self.current_msgid, tags_to_add, tags_to_remove
            )
            self._load_from_cache()

    @work(exclusive=True, group="mail-tag-op")
    async def _apply_tag_changes_to_server(
        self, msgid: str, add: list[str], remove: list[str]
    ) -> None:
        """Sync tag changes to the server."""
        if self.current_account is None:
            return

        identity = self.identity_manager.get_identity(self.current_account.identity_id)
        if identity is None:
            return

        try:
            client = GmapClient(
                hostname=self.current_account.hostname,
                port=self.current_account.port,
                cert_path=identity.cert_path,
                key_path=identity.key_path,
            )
            for tag in add:
                await client.add_tag(msgid, tag)
            for tag in remove:
                await client.remove_tag(msgid, tag)
        except GmapError as e:
            logger.warning("Failed to sync tags to server: %s", e)

    def action_add_account(self) -> None:
        """Open the add account modal."""
        from astronomo.widgets.mail.add_account_modal import AddAccountModal

        self.app.push_screen(
            AddAccountModal(
                account_manager=self.account_manager,
                identity_manager=self.identity_manager,
            ),
            self._on_account_added,
        )

    def _on_account_added(self, account: GmapAccount | None) -> None:
        """Handle account added from modal."""
        if account:
            self.app.notify(f"Added account: {account.name}")
            self.current_account = account
            self._update_title(f"Mail — {account.mailbox}@{account.hostname}")
            self._sync_account(account)

    def action_noop(self) -> None:
        """No-op action to suppress inherited app bindings."""

    async def action_dismiss(self, result: None = None) -> None:
        """Close the mail screen."""
        self.dismiss()
