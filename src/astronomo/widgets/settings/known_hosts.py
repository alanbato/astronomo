"""Known Hosts settings tab for managing TOFU database.

Displays all trusted server certificates and allows revoking trust.
"""

from typing import Any

from nauyaca.security.tofu import TOFUDatabase
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, Static


class KnownHostItem(Static):
    """Widget displaying a single known host with revoke button."""

    DEFAULT_CSS = """
    KnownHostItem {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
        layout: horizontal;
    }

    KnownHostItem:hover {
        background: $surface-lighten-1;
    }

    KnownHostItem .host-details {
        width: 1fr;
        height: auto;
    }

    KnownHostItem .host-address {
        text-style: bold;
    }

    KnownHostItem .host-fingerprint {
        color: $text-muted;
    }

    KnownHostItem .host-dates {
        color: $text-muted;
    }

    KnownHostItem .action-buttons {
        width: auto;
        height: auto;
        align: right middle;
    }

    KnownHostItem .action-buttons Button {
        min-width: 10;
    }
    """

    class RevokeRequested(Message):
        """Message sent when revoke button is clicked."""

        def __init__(self, hostname: str, port: int) -> None:
            self.hostname = hostname
            self.port = port
            super().__init__()

    def __init__(self, host_info: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.host_info = host_info

    def compose(self) -> ComposeResult:
        hostname = self.host_info["hostname"]
        port = self.host_info["port"]
        fingerprint = self.host_info["fingerprint"]
        first_seen = self.host_info.get("first_seen", "Unknown")
        last_seen = self.host_info.get("last_seen", "Unknown")

        # Left side: host details
        with Vertical(classes="host-details"):
            yield Label(f"{hostname}:{port}", classes="host-address")

            # Fingerprint (truncated for display)
            short_fp = self._truncate_fingerprint(fingerprint)
            yield Label(f"Fingerprint: {short_fp}", classes="host-fingerprint")

            # Dates
            yield Label(
                f"First seen: {self._format_date(first_seen)}", classes="host-dates"
            )
            yield Label(
                f"Last seen: {self._format_date(last_seen)}", classes="host-dates"
            )

        # Right side: revoke button
        with Horizontal(classes="action-buttons"):
            yield Button(
                "Revoke",
                variant="error",
                id=f"revoke-{hostname}-{port}",
            )

    def _truncate_fingerprint(self, fingerprint: str) -> str:
        """Truncate fingerprint for display."""
        if fingerprint.startswith("sha256:"):
            fp = fingerprint[7:]
            if len(fp) > 24:
                return f"sha256:{fp[:12]}...{fp[-12:]}"
        return fingerprint

    def _format_date(self, date_str: str) -> str:
        """Format ISO date for display."""
        if date_str == "Unknown":
            return date_str
        try:
            if "T" in date_str:
                date_part, time_part = date_str.split("T")
                time_part = time_part.split("+")[0].split("Z")[0]
                if "." in time_part:
                    time_part = time_part.split(".")[0]
                return f"{date_part} {time_part}"
        except (ValueError, IndexError):
            pass
        return date_str

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses and emit revoke message."""
        button_id = event.button.id or ""

        if button_id.startswith("revoke-"):
            self.post_message(
                self.RevokeRequested(
                    hostname=self.host_info["hostname"],
                    port=self.host_info["port"],
                )
            )
        event.stop()


class KnownHostsSettings(Static):
    """Known Hosts settings section for managing TOFU database.

    Displays all server certificates that have been trusted via TOFU
    (Trust On First Use) and allows users to revoke trust.
    """

    DEFAULT_CSS = """
    KnownHostsSettings {
        height: 100%;
        width: 100%;
    }

    KnownHostsSettings VerticalScroll {
        height: 1fr;
    }

    KnownHostsSettings .section-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
    }

    KnownHostsSettings .section-title {
        text-style: bold;
    }

    KnownHostsSettings .section-description {
        color: $text-muted;
    }

    KnownHostsSettings .empty-state {
        padding: 2;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tofu_db = TOFUDatabase()

    def compose(self) -> ComposeResult:
        with Vertical(classes="section-header"):
            yield Label("Trusted Server Certificates", classes="section-title")
            yield Label(
                "Servers are automatically trusted on first connection (TOFU). "
                "If a server's certificate changes, you will be prompted to verify it.",
                classes="section-description",
            )

        with VerticalScroll(id="known-hosts-list", can_focus=False):
            yield from self._compose_host_list()

    def _compose_host_list(self) -> ComposeResult:
        """Compose the list of known host items."""
        try:
            hosts = self.tofu_db.list_hosts()
        except Exception as e:
            yield Label(
                f"Error loading known hosts: {e}",
                classes="empty-state",
            )
            return

        if not hosts:
            yield Label(
                "No trusted servers yet. Visit a Gemini server to add it.",
                classes="empty-state",
            )
        else:
            # Sort by last_seen descending (most recently accessed first)
            for host in hosts:
                host_id = f"{host['hostname']}-{host['port']}"
                yield KnownHostItem(host, id=f"known-host-{host_id}")

    async def refresh_list(self) -> None:
        """Refresh the known hosts list after changes."""
        scroll = self.query_one("#known-hosts-list", VerticalScroll)
        await scroll.remove_children()

        try:
            hosts = self.tofu_db.list_hosts()
        except Exception as e:
            await scroll.mount(
                Label(
                    f"Error loading known hosts: {e}",
                    classes="empty-state",
                )
            )
            return

        if not hosts:
            await scroll.mount(
                Label(
                    "No trusted servers yet. Visit a Gemini server to add it.",
                    classes="empty-state",
                )
            )
        else:
            for host in hosts:
                host_id = f"{host['hostname']}-{host['port']}"
                await scroll.mount(KnownHostItem(host, id=f"known-host-{host_id}"))

    def on_known_host_item_revoke_requested(
        self, event: KnownHostItem.RevokeRequested
    ) -> None:
        """Handle revoke button click."""
        try:
            revoked = self.tofu_db.revoke(event.hostname, event.port)

            if revoked:
                self.app.notify(
                    f"Revoked trust for {event.hostname}:{event.port}",
                    severity="information",
                )
            else:
                self.app.notify(
                    f"Host {event.hostname}:{event.port} not found",
                    severity="warning",
                )
        except Exception as e:
            self.app.notify(
                f"Error revoking trust: {e}",
                severity="error",
            )

        # Refresh the list using run_worker for proper async handling
        self.run_worker(self.refresh_list())
