"""Known Hosts settings tab for managing TOFU database.

Displays all trusted server certificates and allows revoking trust.
"""

from typing import Any

from nauyaca.security.tofu import TOFUDatabase
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label, Static


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
        # Replace periods with underscores for valid Textual widget ID
        safe_hostname = hostname.replace(".", "_")
        with Horizontal(classes="action-buttons"):
            yield Button(
                "Revoke",
                variant="error",
                id=f"revoke-{safe_hostname}-{port}",
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

    KnownHostsSettings #search-input {
        width: 100%;
        margin-bottom: 1;
    }

    KnownHostsSettings .pagination-container {
        width: 100%;
        height: auto;
        padding: 0;
        align: center middle;
        layout: horizontal;
    }

    KnownHostsSettings .pagination-container Button {
        min-width: 6;
    }

    KnownHostsSettings .pagination-info {
        padding: 0 1;
        color: $text-muted;
    }
    """

    ITEMS_PER_PAGE = 10

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tofu_db = TOFUDatabase()
        self._search_query: str = ""
        self._current_page: int = 0
        self._all_hosts: list[dict[str, Any]] = []
        self._filtered_hosts: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="section-header"):
            yield Label("Trusted Server Certificates", classes="section-title")
            yield Label(
                "Servers are automatically trusted on first connection (TOFU). "
                "If a server's certificate changes, you will be prompted to verify it.",
                classes="section-description",
            )

        # Search input
        search_input = Input(placeholder="Filter by hostname...", id="search-input")
        search_input.border_title = "Search"
        yield search_input

        with VerticalScroll(id="known-hosts-list", can_focus=False):
            yield from self._compose_host_list()

        # Pagination controls
        with Horizontal(classes="pagination-container"):
            yield Button("Prev", id="prev-page", disabled=True)
            yield Label("Page 1 of 1", id="pagination-info", classes="pagination-info")
            yield Button("Next", id="next-page", disabled=True)

    def on_mount(self) -> None:
        """Update pagination UI after initial mount."""
        self._update_pagination_ui()

    def _filter_hosts(self, hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter hosts by search query (hostname only, case-insensitive)."""
        if not self._search_query:
            return hosts
        query_lower = self._search_query.lower()
        return [h for h in hosts if query_lower in h["hostname"].lower()]

    def _paginate_hosts(self, hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return the current page of hosts."""
        start_idx = self._current_page * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        return hosts[start_idx:end_idx]

    def _get_total_pages(self) -> int:
        """Calculate total number of pages."""
        if not self._filtered_hosts:
            return 1
        return (
            len(self._filtered_hosts) + self.ITEMS_PER_PAGE - 1
        ) // self.ITEMS_PER_PAGE

    def _update_pagination_ui(self) -> None:
        """Update pagination button states and info label."""
        total_pages = self._get_total_pages()

        # Update buttons
        prev_btn = self.query_one("#prev-page", Button)
        next_btn = self.query_one("#next-page", Button)

        prev_btn.disabled = self._current_page == 0
        next_btn.disabled = self._current_page >= total_pages - 1

        # Update info label
        info_label = self.query_one("#pagination-info", Label)
        if self._filtered_hosts:
            current_display = self._current_page + 1
            info_label.update(f"Page {current_display} of {total_pages}")
        else:
            info_label.update("Page 1 of 1")

    def _load_and_prepare_hosts(self) -> tuple[list[dict[str, Any]], str | None]:
        """Load hosts from database and prepare filtered/paginated list.

        Returns:
            Tuple of (paginated_hosts, error_message).
            If error_message is not None, paginated_hosts will be empty.
        """
        try:
            self._all_hosts = self.tofu_db.list_hosts()
            self._filtered_hosts = self._filter_hosts(self._all_hosts)

            # Ensure current page is valid after filtering
            total_pages = self._get_total_pages()
            if self._current_page >= total_pages:
                self._current_page = max(0, total_pages - 1)

            return self._paginate_hosts(self._filtered_hosts), None
        except Exception as e:
            return [], f"Error loading known hosts: {e}"

    def _get_empty_state_message(self) -> str:
        """Get the appropriate empty state message."""
        if self._search_query:
            return "No hosts match your search."
        return "No trusted servers yet. Visit a Gemini server to add it."

    def _create_host_widget(self, host: dict[str, Any], index: int) -> KnownHostItem:
        """Create a KnownHostItem widget for the given host."""
        # Replace periods with underscores for valid Textual widget ID
        # Include index to ensure uniqueness in case of duplicate entries
        safe_hostname = host["hostname"].replace(".", "_")
        host_id = f"{safe_hostname}-{host['port']}-{index}"
        return KnownHostItem(host, id=f"known-host-{host_id}")

    def _compose_host_list(self) -> ComposeResult:
        """Compose the list of known host items."""
        paginated_hosts, error = self._load_and_prepare_hosts()

        if error:
            yield Label(error, classes="empty-state")
            return

        if not self._filtered_hosts:
            yield Label(self._get_empty_state_message(), classes="empty-state")
        else:
            for idx, host in enumerate(paginated_hosts):
                yield self._create_host_widget(host, idx)

    async def refresh_list(self, reset_page: bool = True) -> None:
        """Refresh the known hosts list after changes.

        Args:
            reset_page: If True, reset to page 0.
        """
        if reset_page:
            self._current_page = 0

        scroll = self.query_one("#known-hosts-list", VerticalScroll)
        await scroll.remove_children()

        paginated_hosts, error = self._load_and_prepare_hosts()

        if error:
            await scroll.mount(Label(error, classes="empty-state"))
            self._update_pagination_ui()
            return

        if not self._filtered_hosts:
            await scroll.mount(
                Label(self._get_empty_state_message(), classes="empty-state")
            )
        else:
            for idx, host in enumerate(paginated_hosts):
                await scroll.mount(self._create_host_widget(host, idx))

        self._update_pagination_ui()

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

        # Refresh the list, preserving current page
        self.run_worker(self.refresh_list(reset_page=False))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._search_query = event.value
            self.run_worker(self.refresh_list(reset_page=True))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle pagination button presses."""
        button_id = event.button.id or ""

        if button_id == "prev-page" and self._current_page > 0:
            self._current_page -= 1
            self.run_worker(self.refresh_list(reset_page=False))
            event.stop()
        elif button_id == "next-page":
            total_pages = self._get_total_pages()
            if self._current_page < total_pages - 1:
                self._current_page += 1
                self.run_worker(self.refresh_list(reset_page=False))
            event.stop()
