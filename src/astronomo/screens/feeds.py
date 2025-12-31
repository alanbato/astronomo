"""Feeds screen for Astronomo.

Provides a full-screen interface for managing and viewing RSS/Atom feeds
with folder organization, read/unread tracking, and feed item viewing.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import humanize

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Input, Label, Static

from astronomo.feed_fetcher import FeedData, FeedItem, fetch_feed
from astronomo.feeds import Feed, FeedFolder, FeedManager
from astronomo.opml import export_opml, import_opml
from astronomo.widgets.feeds import (
    AddFeedFolderModal,
    AddFeedModal,
    ConfirmDeleteFeedModal,
    EditFeedFolderModal,
    EditFeedModal,
    OpmlExportModal,
    OpmlImportModal,
)

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo

logger = logging.getLogger(__name__)


def format_relative_time(dt: datetime | None) -> str:
    """Format a datetime as a human-readable relative time string."""
    if dt is None:
        return ""
    # Handle future dates (e.g., feeds that use noon UTC for today's posts)
    now = datetime.now(dt.tzinfo)
    if dt > now:
        return "today"
    return humanize.naturaltime(dt)


class FeedFolderWidget(Static):
    """Widget displaying a feed folder with expand/collapse indicator."""

    DEFAULT_CSS = """
    FeedFolderWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    FeedFolderWidget:hover {
        background: $surface;
    }

    FeedFolderWidget.-selected {
        background: $accent-muted;
    }
    """

    COLLAPSED_INDICATOR = "▶"
    EXPANDED_INDICATOR = "▼"

    def __init__(self, folder: FeedFolder, collapsed: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.folder = folder
        self.collapsed = collapsed

    def render(self) -> str:
        indicator = (
            self.COLLAPSED_INDICATOR if self.collapsed else self.EXPANDED_INDICATOR
        )
        return f"{indicator} {self.folder.name}"

    def toggle(self) -> None:
        """Toggle collapsed state."""
        self.collapsed = not self.collapsed
        self.refresh()


class FeedWidget(Static):
    """Widget displaying a feed with unread count badge."""

    DEFAULT_CSS = """
    FeedWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    FeedWidget:hover {
        background: $surface;
    }

    FeedWidget.-selected {
        background: $accent-muted;
    }

    FeedWidget.-indented {
        padding-left: 3;
    }
    """

    def __init__(
        self,
        feed: Feed,
        indented: bool = False,
        unread_count: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.feed = feed
        self.unread_count = unread_count
        if indented:
            self.add_class("-indented")

    def render(self) -> str:
        badge = f" ({self.unread_count})" if self.unread_count > 0 else ""
        return f"{self.feed.title}{badge}"


class FeedItemWidget(Static, can_focus=True):
    """Widget displaying a single feed item."""

    DEFAULT_CSS = """
    FeedItemWidget {
        width: 100%;
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
    }

    FeedItemWidget:hover {
        background: $surface;
    }

    FeedItemWidget:focus {
        border: solid $accent;
        background: $surface;
    }

    FeedItemWidget.-read {
        color: $text-muted;
    }

    FeedItemWidget .item-title {
        text-style: bold;
    }

    FeedItemWidget .item-meta {
        color: $text-muted;
        padding-top: 0;
    }

    FeedItemWidget .item-summary {
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("up", "focus_previous_item", "Previous", show=False),
        Binding("down", "focus_next_item", "Next", show=False),
        Binding("enter", "select_item", "Open", show=False),
    ]

    def __init__(
        self,
        item: FeedItem,
        is_read: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.item = item
        self.is_read = is_read
        if is_read:
            self.add_class("-read")
        # Set border title to human-readable time
        self.border_title = format_relative_time(item.published)

    def action_focus_previous_item(self) -> None:
        """Focus the previous item, or feed list if at first item."""
        items = list(self.screen.query("FeedItemWidget"))
        if items and items[0] is self:
            # At first item, go back to feed list
            self.screen.query_one("#feed-list", FeedListPanel).focus()
        else:
            self.screen.focus_previous()

    def action_focus_next_item(self) -> None:
        """Focus the next item."""
        self.screen.focus_next()

    def action_select_item(self) -> None:
        """Select/activate this item."""
        # Trigger click behavior
        items_panel = self.screen.query_one("#feed-items", FeedItemsPanel)
        if items_panel.current_feed is not None:
            items_panel.post_message(
                FeedItemsPanel.ItemSelected(self.item, items_panel.current_feed.id)
            )

    def compose(self) -> ComposeResult:
        """Compose the item widget."""
        yield Label(self.item.title, classes="item-title")

        # Show author if available
        if self.item.author:
            yield Label(f"by {self.item.author}", classes="item-meta")

        if self.item.summary:
            # Truncate long summaries
            summary = self.item.summary[:200]
            if len(self.item.summary) > 200:
                summary += "..."
            yield Label(summary, classes="item-summary")


class FeedListPanel(VerticalScroll, can_focus=True):
    """Left panel showing feeds organized in folders."""

    BORDER_TITLE = "Feeds"

    DEFAULT_CSS = """
    FeedListPanel {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    FeedListPanel:focus {
        border: solid $accent;
    }

    FeedListPanel .empty-message {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    selected_index: reactive[int] = reactive(0, init=False)

    class FeedSelected(Message):
        """Emitted when a feed is selected."""

        def __init__(self, feed: Feed) -> None:
            self.feed = feed
            super().__init__()

    class DeleteRequested(Message):
        """Emitted when delete is requested."""

        def __init__(self, item: Feed | FeedFolder) -> None:
            self.item = item
            super().__init__()

    class EditRequested(Message):
        """Emitted when edit is requested."""

        def __init__(self, item: Feed | FeedFolder) -> None:
            self.item = item
            super().__init__()

    def __init__(self, manager: FeedManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self._collapsed_folders: set[str] = set()
        self._items: list[Feed | FeedFolder] = []
        self._unread_counts: dict[str, int] = {}
        self._search_query: str = ""

    def on_mount(self) -> None:
        """Refresh the feed list on mount."""
        self.refresh_list()

    def refresh_list(
        self,
        unread_counts: dict[str, int] | None = None,
        search_query: str = "",
    ) -> None:
        """Refresh the feed list display.

        Args:
            unread_counts: Optional dict mapping feed_id to unread count
            search_query: Optional search query to filter feeds
        """
        if unread_counts:
            self._unread_counts = unread_counts

        if search_query is not None:
            self._search_query = search_query.lower()

        # Clear existing content
        self.remove_children()

        # Build the list
        self._items = []

        # Get folders and root feeds
        folders = self.manager.get_all_folders()
        root_feeds = self.manager.get_root_feeds()

        if not folders and not root_feeds:
            self.mount(Label("No feeds yet", classes="empty-message"))
            return

        # Helper to check if feed matches search
        def matches_search(feed: Feed) -> bool:
            if not self._search_query:
                return True
            return (
                self._search_query in feed.title.lower()
                or self._search_query in feed.url.lower()
            )

        # Add root-level feeds
        for feed in root_feeds:
            if matches_search(feed):
                self._items.append(feed)
                unread = self._unread_counts.get(feed.id, 0)
                self.mount(FeedWidget(feed, unread_count=unread))

        # Add folders and their feeds
        for folder in folders:
            feeds_in_folder = self.manager.get_feeds_in_folder(folder.id)
            # Filter feeds in this folder
            matching_feeds = [f for f in feeds_in_folder if matches_search(f)]

            # Only show folder if it has matching feeds or no search is active
            if not self._search_query or matching_feeds:
                self._items.append(folder)
                collapsed = folder.id in self._collapsed_folders
                self.mount(FeedFolderWidget(folder, collapsed))

                # Add feeds in this folder if not collapsed
                if not collapsed:
                    for feed in matching_feeds:
                        self._items.append(feed)
                        unread = self._unread_counts.get(feed.id, 0)
                        self.mount(FeedWidget(feed, indented=True, unread_count=unread))

        # Show message if search returned no results
        if self._search_query and not self._items:
            self.mount(Label("No matching feeds", classes="empty-message"))

        self._update_selection()

    def _update_selection(self) -> None:
        """Update the visual selection."""
        # Remove selection from all items
        for widget in self.query("FeedWidget, FeedFolderWidget"):
            widget.remove_class("-selected")

        # Add selection to current item
        if 0 <= self.selected_index < len(self._items):
            widgets = list(self.query("FeedWidget, FeedFolderWidget"))
            if widgets and 0 <= self.selected_index < len(widgets):
                widgets[self.selected_index].add_class("-selected")

    def get_selected_item(self) -> Feed | FeedFolder | None:
        """Get the currently selected item."""
        if 0 <= self.selected_index < len(self._items):
            return self._items[self.selected_index]
        return None

    def move_selection(self, delta: int) -> None:
        """Move the selection by delta positions."""
        if not self._items:
            return

        self.selected_index = max(
            0, min(len(self._items) - 1, self.selected_index + delta)
        )
        self._update_selection()

    def toggle_folder(self) -> None:
        """Toggle the selected folder's collapsed state."""
        item = self.get_selected_item()
        if isinstance(item, FeedFolder):
            if item.id in self._collapsed_folders:
                self._collapsed_folders.remove(item.id)
            else:
                self._collapsed_folders.add(item.id)
            self.refresh_list()

    def activate_item(self) -> None:
        """Activate the selected item."""
        item = self.get_selected_item()
        if isinstance(item, Feed):
            self.post_message(self.FeedSelected(item))
        elif isinstance(item, FeedFolder):
            self.toggle_folder()

    def delete_item(self) -> None:
        """Request deletion of the selected item."""
        item = self.get_selected_item()
        if item:
            self.post_message(self.DeleteRequested(item))

    def edit_item(self) -> None:
        """Request editing of the selected item."""
        item = self.get_selected_item()
        if item:
            self.post_message(self.EditRequested(item))


class FeedItemsPanel(VerticalScroll):
    """Right panel showing items from the selected feed."""

    BORDER_TITLE = "Items"

    DEFAULT_CSS = """
    FeedItemsPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
    }

    FeedItemsPanel:focus-within {
        border: solid $accent;
    }

    FeedItemsPanel .feed-info {
        padding: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    FeedItemsPanel .feed-description {
        color: $text-muted;
        padding-top: 0;
    }

    FeedItemsPanel .loading-message {
        padding: 1;
        text-align: center;
        color: $text-muted;
    }

    FeedItemsPanel .error-message {
        padding: 1;
        color: $error;
    }

    FeedItemsPanel .empty-message {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    class ItemSelected(Message):
        """Emitted when a feed item is clicked."""

        def __init__(self, item: FeedItem, feed_id: str) -> None:
            self.item = item
            self.feed_id = feed_id
            super().__init__()

    def __init__(self, manager: FeedManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.current_feed: Feed | None = None
        self.current_feed_data: FeedData | None = None

    def show_placeholder(self) -> None:
        """Show placeholder when no feed is selected."""
        self.remove_children()
        self.mount(Label("Select a feed to view its items", classes="empty-message"))

    def show_loading(self, feed: Feed) -> None:
        """Show loading state while fetching feed."""
        self.remove_children()
        self.current_feed = feed
        self.mount(Label(f"Loading {feed.title}...", classes="loading-message"))

    def show_error(self, error: str) -> None:
        """Show error message."""
        self.remove_children()
        self.mount(Label(f"Error: {error}", classes="error-message"))

    def show_feed_items(self, feed: Feed, feed_data: FeedData) -> None:
        """Display feed items.

        Args:
            feed: The Feed object
            feed_data: Fetched and parsed feed data
        """
        self.remove_children()
        self.current_feed = feed
        self.current_feed_data = feed_data

        # Feed title and info
        self.mount(Label(feed_data.title or feed.title, classes="panel-title"))

        if feed_data.description:
            info_container = Container(classes="feed-info")
            self.mount(info_container)
            info_container.mount(
                Label(feed_data.description, classes="feed-description")
            )

        # Feed items
        if not feed_data.items:
            self.mount(Label("No items in this feed", classes="empty-message"))
            return

        for item in feed_data.items:
            is_read = self.manager.is_read(feed.id, item.link, item.published)
            item_widget = FeedItemWidget(item, is_read)
            self.mount(item_widget)

    def on_click(self, event) -> None:
        """Handle clicks on feed items."""
        # Find if we clicked on a FeedItemWidget
        widget = event.widget
        while widget and not isinstance(widget, FeedItemWidget):
            widget = widget.parent

        if isinstance(widget, FeedItemWidget) and self.current_feed:
            self.post_message(self.ItemSelected(widget.item, self.current_feed.id))


class FeedsScreen(Screen):
    """Full-screen interface for feed management and viewing."""

    DEFAULT_CSS = """
    FeedsScreen {
        background: $background;
    }

    FeedsScreen #feeds-header {
        height: auto;
        width: 100%;
        padding: 1;
        background: $surface;
    }

    FeedsScreen #feeds-title {
        text-style: bold;
    }

    FeedsScreen #feeds-content {
        width: 100%;
        height: 1fr;
    }

    FeedsScreen #feed-list-column {
        width: 30;
        height: 100%;
    }

    FeedsScreen #search-input {
        width: 100%;
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("ctrl+j", "dismiss", "Close", show=False, priority=True),
        Binding("tab", "toggle_panel_focus", "Switch Panel", priority=True),
        Binding("ctrl+n", "add_feed", "New Feed"),
        Binding("ctrl+f", "add_folder", "New Folder"),
        Binding("ctrl+r", "refresh_feed", "Refresh"),
        Binding("ctrl+shift+r", "refresh_all", "Refresh All"),
        Binding("ctrl+i", "import_opml", "Import"),
        Binding("ctrl+e", "export_opml", "Export", priority=True),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "activate_item", "Open", show=False),
        Binding("space", "toggle_folder", "Toggle", show=False),
        Binding("d", "delete_item", "Delete"),
        Binding("e", "edit_item", "Edit"),
        Binding("m", "mark_all_read", "Mark Read"),
    ]

    def __init__(self, manager: FeedManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager

    def compose(self) -> ComposeResult:
        """Compose the feeds screen UI."""
        with Container(id="feeds-header"):
            yield Label("Feed Reader", id="feeds-title")

        with Horizontal(id="feeds-content"):
            with Vertical(id="feed-list-column"):
                search_input = Input(placeholder="Type to filter...", id="search-input")
                search_input.border_title = "Search"
                yield search_input
                yield FeedListPanel(self.manager, id="feed-list")
            yield FeedItemsPanel(self.manager, id="feed-items")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the feeds screen."""
        items_panel = self.query_one("#feed-items", FeedItemsPanel)
        items_panel.show_placeholder()
        # Set initial focus to feed list for keyboard navigation
        self.query_one("#feed-list", FeedListPanel).focus()

    def action_toggle_panel_focus(self) -> None:
        """Toggle focus between feed list and first feed item."""
        feed_list = self.query_one("#feed-list", FeedListPanel)

        if feed_list.has_focus:
            # Focus first feed item if available
            items = list(self.query("FeedItemWidget"))
            if items:
                items[0].focus()
        else:
            feed_list.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            search_query = event.value
            feed_list = self.query_one("#feed-list", FeedListPanel)
            feed_list.refresh_list(search_query=search_query)

    def on_feed_list_panel_feed_selected(
        self, message: FeedListPanel.FeedSelected
    ) -> None:
        """Handle feed selection from the list panel."""
        self._load_feed(message.feed)

    @work(exclusive=True)
    async def _load_feed(self, feed: Feed) -> None:
        """Load and display a feed's items.

        Args:
            feed: The Feed to load
        """
        app: Astronomo = self.app  # type: ignore[assignment]
        items_panel = self.query_one("#feed-items", FeedItemsPanel)

        # Show loading state
        items_panel.show_loading(feed)

        # Fetch the feed
        feed_data = await fetch_feed(
            url=feed.url,
            timeout=app.config_manager.timeout,
            max_redirects=app.config_manager.max_redirects,
        )

        # Update last_fetched timestamp
        if not feed_data.error:
            from datetime import datetime

            self.manager.update_feed(feed.id, last_fetched=datetime.now())

        # Display results
        if feed_data.error:
            items_panel.show_error(feed_data.error)
        else:
            items_panel.show_feed_items(feed, feed_data)

            # Update unread counts
            self._refresh_unread_counts()

    def _refresh_unread_counts(self) -> None:
        """Refresh unread counts for all feeds."""
        # This is a simplified version - in a full implementation,
        # we'd need to fetch all feeds to get accurate counts
        feed_list = self.query_one("#feed-list", FeedListPanel)
        feed_list.refresh_list()

    def on_feed_items_panel_item_selected(
        self, message: FeedItemsPanel.ItemSelected
    ) -> None:
        """Handle feed item selection."""
        app: Astronomo = self.app  # type: ignore[assignment]

        # Mark as read
        self.manager.mark_as_read(
            message.feed_id, message.item.link, message.item.published
        )

        # Refresh the items panel to update read status
        feed = self.manager.get_feed(message.feed_id)
        items_panel = self.query_one("#feed-items", FeedItemsPanel)
        if feed and items_panel.current_feed_data:
            items_panel.show_feed_items(feed, items_panel.current_feed_data)

        # Open the link in the main browser if it's a Gemini URL
        if message.item.link.startswith("gemini://"):
            self.dismiss()
            app.get_url(message.item.link)

    # Actions

    async def action_dismiss(self, result: None = None) -> None:
        """Close the feeds screen."""
        self.dismiss()

    def action_add_feed(self) -> None:
        """Add a new feed."""
        self.app.push_screen(AddFeedModal(self.manager), self._on_feed_added)

    def _on_feed_added(self, feed: Feed | None) -> None:
        """Handle feed added from modal."""
        if feed:
            self.app.notify(f"Added feed: {feed.title}")
            feed_list = self.query_one("#feed-list", FeedListPanel)
            feed_list.refresh_list()

    def action_add_folder(self) -> None:
        """Add a new folder."""
        self.app.push_screen(AddFeedFolderModal(self.manager), self._on_folder_added)

    def _on_folder_added(self, folder: FeedFolder | None) -> None:
        """Handle folder added from modal."""
        if folder:
            self.app.notify(f"Added folder: {folder.name}")
            feed_list = self.query_one("#feed-list", FeedListPanel)
            feed_list.refresh_list()

    def action_refresh_feed(self) -> None:
        """Refresh the currently selected feed."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        item = feed_list.get_selected_item()
        if isinstance(item, Feed):
            self._load_feed(item)

    def action_refresh_all(self) -> None:
        """Refresh all feeds (placeholder)."""
        # TODO: Implement refresh all feeds
        self.app.notify("Refresh all not yet implemented")

    def action_import_opml(self) -> None:
        """Import feeds from OPML."""
        self.app.push_screen(OpmlImportModal(), self._on_opml_import)

    def _on_opml_import(self, path) -> None:
        """Handle OPML import."""
        if path:
            try:
                feeds_added, feeds_skipped = import_opml(self.manager, path)
                msg = f"Import complete: {feeds_added} added"
                if feeds_skipped > 0:
                    msg += f", {feeds_skipped} skipped"
                self.app.notify(msg, timeout=3)

                # Refresh the feed list
                feed_list = self.query_one("#feed-list", FeedListPanel)
                feed_list.refresh_list()
            except Exception as e:
                logger.exception("OPML import failed for %s", path)
                self.app.notify(f"Import failed: {e}", severity="error", timeout=5)

    def action_export_opml(self) -> None:
        """Export feeds to OPML."""
        self.app.push_screen(OpmlExportModal(), self._on_opml_export)

    def _on_opml_export(self, path) -> None:
        """Handle OPML export."""
        if path:
            try:
                export_opml(self.manager, path)
                self.app.notify(f"Feeds exported to {path}", timeout=3)
            except Exception as e:
                logger.exception("OPML export failed for %s", path)
                self.app.notify(f"Export failed: {e}", severity="error", timeout=5)

    def action_cursor_up(self) -> None:
        """Move cursor up in feed list."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        feed_list.move_selection(-1)

    def action_cursor_down(self) -> None:
        """Move cursor down in feed list."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        feed_list.move_selection(1)

    def action_activate_item(self) -> None:
        """Activate the selected item."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        feed_list.activate_item()

    def action_toggle_folder(self) -> None:
        """Toggle folder collapsed state."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        feed_list.toggle_folder()

    def action_delete_item(self) -> None:
        """Delete the selected item after confirmation."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        item = feed_list.get_selected_item()

        if item is None:
            return

        self.app.push_screen(
            ConfirmDeleteFeedModal(self.manager, item),
            self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, deleted: bool | None) -> None:
        """Handle deletion confirmation result."""
        if deleted:
            feed_list = self.query_one("#feed-list", FeedListPanel)
            feed_list.refresh_list()
            items_panel = self.query_one("#feed-items", FeedItemsPanel)
            items_panel.show_placeholder()
            self.app.notify("Item deleted")

    def action_edit_item(self) -> None:
        """Edit the selected item."""
        feed_list = self.query_one("#feed-list", FeedListPanel)
        item = feed_list.get_selected_item()

        if isinstance(item, Feed):
            self.app.push_screen(
                EditFeedModal(self.manager, item),
                self._on_feed_edited,
            )
        elif isinstance(item, FeedFolder):
            self.app.push_screen(
                EditFeedFolderModal(self.manager, item),
                self._on_folder_edited,
            )

    def _on_feed_edited(self, updated: bool | None) -> None:
        """Handle feed edited from modal."""
        if updated:
            self.app.notify("Feed updated")
            feed_list = self.query_one("#feed-list", FeedListPanel)
            feed_list.refresh_list()

    def _on_folder_edited(self, updated: bool | None) -> None:
        """Handle folder edited from modal."""
        if updated:
            self.app.notify("Folder updated")
            feed_list = self.query_one("#feed-list", FeedListPanel)
            feed_list.refresh_list()

    def action_mark_all_read(self) -> None:
        """Mark all items in the current feed as read."""
        items_panel = self.query_one("#feed-items", FeedItemsPanel)
        if items_panel.current_feed and items_panel.current_feed_data:
            feed = items_panel.current_feed
            feed_data = items_panel.current_feed_data

            if feed_data.items:
                items = [(item.link, item.published) for item in feed_data.items]
                self.manager.mark_all_as_read(feed.id, items)

                # Refresh display
                items_panel.show_feed_items(feed, feed_data)
                self._refresh_unread_counts()

                self.app.notify(f"Marked all items in {feed.title} as read")
