"""Bookmarks sidebar widget for Astronomo.

Provides a toggleable sidebar with a collapsible folder tree
for managing and navigating bookmarks.
"""

from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder


class FolderWidget(Static):
    """Widget displaying a folder with expand/collapse indicator."""

    DEFAULT_CSS = """
    FolderWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
        color: auto;
    }

    FolderWidget:hover {
        text-style: bold;
    }

    FolderWidget.-selected {
        text-style: bold reverse;
    }
    """

    COLLAPSED_INDICATOR = "▶"
    EXPANDED_INDICATOR = "▼"

    class Clicked(Message):
        """Emitted when the folder is clicked."""

        def __init__(self, folder: Folder) -> None:
            self.folder = folder
            super().__init__()

    def __init__(self, folder: Folder, collapsed: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.folder = folder
        self.collapsed = collapsed

    def on_mount(self) -> None:
        """Apply folder color on mount."""
        if self.folder.color:
            self.styles.background = self.folder.color

    def render(self) -> str:
        indicator = (
            self.COLLAPSED_INDICATOR if self.collapsed else self.EXPANDED_INDICATOR
        )
        return f"{indicator} {self.folder.name}"

    def toggle(self) -> None:
        """Toggle collapsed state."""
        self.collapsed = not self.collapsed
        self.refresh()

    def on_click(self, event: Click) -> None:
        """Handle click to toggle folder."""
        event.stop()
        self.post_message(self.Clicked(self.folder))


class BookmarkWidget(Static):
    """Widget displaying a single bookmark entry."""

    DEFAULT_CSS = """
    BookmarkWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    BookmarkWidget:hover {
        background: $surface;
    }

    BookmarkWidget.-selected {
        background: $accent-muted;
    }

    BookmarkWidget.-indented {
        padding-left: 3;
    }
    """

    class Clicked(Message):
        """Emitted when the bookmark is clicked."""

        def __init__(self, bookmark: Bookmark) -> None:
            self.bookmark = bookmark
            super().__init__()

    def __init__(self, bookmark: Bookmark, indented: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.bookmark = bookmark
        if indented:
            self.add_class("-indented")

    def render(self) -> str:
        return self.bookmark.title

    def on_click(self, event: Click) -> None:
        """Handle click to open bookmark."""
        event.stop()
        self.post_message(self.Clicked(self.bookmark))


class BookmarksSidebar(Container):
    """Sidebar widget for bookmark navigation.

    Features:
    - Collapsible folder tree
    - Keyboard navigation
    - Selection highlighting
    - Message passing for bookmark activation
    """

    DEFAULT_CSS = """
    BookmarksSidebar {
        width: 30;
        height: 100%;
        dock: right;
        border-left: solid $primary;
        display: none;
    }

    BookmarksSidebar.-visible {
        display: block;
    }


    BookmarksSidebar .sidebar-content {
        height: 1fr;
    }

    BookmarksSidebar .empty-message {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("enter", "activate_item", "Open"),
        Binding("space", "toggle_folder", "Toggle"),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("d", "delete_item", "Delete"),
        Binding("e", "edit_item", "Edit"),
        Binding("n", "new_folder", "New Folder"),
    ]

    # Currently selected item index
    selected_index: reactive[int] = reactive(0, init=False)

    BORDER_TITLE = "Bookmarks"

    class BookmarkSelected(Message):
        """Emitted when a bookmark is selected to open."""

        def __init__(self, bookmark: Bookmark) -> None:
            self.bookmark = bookmark
            super().__init__()

    class DeleteRequested(Message):
        """Emitted when delete is requested for an item."""

        def __init__(self, item: Bookmark | Folder) -> None:
            self.item = item
            super().__init__()

    class EditRequested(Message):
        """Emitted when edit is requested for an item."""

        def __init__(self, item: Bookmark | Folder) -> None:
            self.item = item
            super().__init__()

    class NewFolderRequested(Message):
        """Emitted when user wants to create a new folder."""

    def __init__(self, manager: BookmarkManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.can_focus = True
        self._items: list[FolderWidget | BookmarkWidget] = []
        self._collapsed_folders: set[str] = set()  # Track collapsed folder IDs

    def compose(self):
        """Compose the sidebar UI."""
        yield VerticalScroll(classes="sidebar-content")

    def on_mount(self) -> None:
        """Initialize the sidebar content."""
        self.refresh_tree()

    def refresh_tree(self) -> None:
        """Rebuild the bookmark tree display."""
        content = self.query_one(".sidebar-content", VerticalScroll)

        # Clear existing items
        for folder_w in content.query(FolderWidget):
            folder_w.remove()
        for bookmark_w in content.query(BookmarkWidget):
            bookmark_w.remove()
        for empty_w in content.query(".empty-message"):
            empty_w.remove()

        self._items.clear()

        # Check if we have any content
        if not self.manager.bookmarks and not self.manager.folders:
            content.mount(Static("No bookmarks yet", classes="empty-message"))
            return

        # Build the tree: folders first, then root bookmarks
        widgets_to_mount: list[FolderWidget | BookmarkWidget] = []

        # Add folders with their bookmarks
        for folder in self.manager.folders:
            is_collapsed = folder.id in self._collapsed_folders
            folder_widget = FolderWidget(folder, collapsed=is_collapsed)
            self._items.append(folder_widget)
            widgets_to_mount.append(folder_widget)

            # Add bookmarks in this folder (if not collapsed)
            if not is_collapsed:
                for bookmark in self.manager.get_bookmarks_in_folder(folder.id):
                    bookmark_widget = BookmarkWidget(bookmark, indented=True)
                    self._items.append(bookmark_widget)  # type: ignore[arg-type]
                    widgets_to_mount.append(bookmark_widget)

        # Add root-level bookmarks
        for bookmark in self.manager.get_root_bookmarks():
            bookmark_widget = BookmarkWidget(bookmark, indented=False)
            self._items.append(bookmark_widget)  # type: ignore[arg-type]
            widgets_to_mount.append(bookmark_widget)

        # Mount all widgets
        content.mount(*widgets_to_mount)

        # Ensure selection is valid
        if self._items:
            self.selected_index = min(self.selected_index, len(self._items) - 1)
            self._update_selection()
        else:
            self.selected_index = 0

    def _update_selection(self) -> None:
        """Update visual selection state."""
        for i, item in enumerate(self._items):
            if i == self.selected_index:
                item.add_class("-selected")
            else:
                item.remove_class("-selected")

    def _get_selected_item(self) -> FolderWidget | BookmarkWidget | None:
        """Get the currently selected item widget."""
        if 0 <= self.selected_index < len(self._items):
            return self._items[self.selected_index]
        return None

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        """React to selection changes."""
        # Deselect old
        if 0 <= old_index < len(self._items):
            self._items[old_index].remove_class("-selected")

        # Select new
        if 0 <= new_index < len(self._items):
            self._items[new_index].add_class("-selected")
            # Scroll to make visible
            self._items[new_index].scroll_visible()

    def action_cursor_up(self) -> None:
        """Move selection up."""
        if self._items and self.selected_index > 0:
            self.selected_index -= 1

    def action_cursor_down(self) -> None:
        """Move selection down."""
        if self._items and self.selected_index < len(self._items) - 1:
            self.selected_index += 1

    def action_activate_item(self) -> None:
        """Activate the selected item (open bookmark)."""
        item = self._get_selected_item()
        if isinstance(item, BookmarkWidget):
            self.post_message(self.BookmarkSelected(item.bookmark))

    def action_toggle_folder(self) -> None:
        """Toggle folder expand/collapse."""
        item = self._get_selected_item()
        if isinstance(item, FolderWidget):
            folder_id = item.folder.id
            if folder_id in self._collapsed_folders:
                self._collapsed_folders.remove(folder_id)
            else:
                self._collapsed_folders.add(folder_id)
            self.refresh_tree()

    def action_delete_item(self) -> None:
        """Request deletion of selected item."""
        item = self._get_selected_item()
        if isinstance(item, FolderWidget):
            self.post_message(self.DeleteRequested(item.folder))
        elif isinstance(item, BookmarkWidget):
            self.post_message(self.DeleteRequested(item.bookmark))

    def action_edit_item(self) -> None:
        """Request editing of selected item."""
        item = self._get_selected_item()
        if isinstance(item, FolderWidget):
            self.post_message(self.EditRequested(item.folder))
        elif isinstance(item, BookmarkWidget):
            self.post_message(self.EditRequested(item.bookmark))

    def action_new_folder(self) -> None:
        """Request creation of a new folder."""
        self.post_message(self.NewFolderRequested())

    def _select_item_widget(self, widget: FolderWidget | BookmarkWidget) -> None:
        """Update selection to match the given widget."""
        for i, item in enumerate(self._items):
            if item is widget:
                self.selected_index = i
                break

    def on_folder_widget_clicked(self, event: FolderWidget.Clicked) -> None:
        """Handle folder click to toggle and update selection."""
        # Find the widget that posted this message
        widget = event._sender
        if isinstance(widget, FolderWidget):
            self._select_item_widget(widget)
            # Toggle folder
            folder_id = event.folder.id
            if folder_id in self._collapsed_folders:
                self._collapsed_folders.remove(folder_id)
            else:
                self._collapsed_folders.add(folder_id)
            self.refresh_tree()

    def on_bookmark_widget_clicked(self, event: BookmarkWidget.Clicked) -> None:
        """Handle bookmark click to open and update selection."""
        widget = event._sender
        if isinstance(widget, BookmarkWidget):
            self._select_item_widget(widget)
        self.post_message(self.BookmarkSelected(event.bookmark))
