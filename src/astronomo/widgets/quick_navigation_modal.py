"""Quick navigation modal with fuzzy search.

Provides a keyboard-driven fuzzy finder for quickly jumping to
bookmarks and history entries.
"""

from dataclasses import dataclass
from typing import Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListView, ListItem

from astronomo.bookmarks import BookmarkManager
from astronomo.history import HistoryManager

# Type alias for navigation item sources
NavigationSource = Literal["bookmark", "history"]


@dataclass
class NavigationItem:
    """Represents a single searchable navigation item.

    Attributes:
        url: The URL to navigate to
        title: Display title
        source: Where this item came from ("bookmark" or "history")
        timestamp: Optional timestamp for sorting recent items
    """

    url: str
    title: str
    source: NavigationSource
    timestamp: str = ""


class NavigationListItem(ListItem):
    """ListItem subclass that stores a URL for navigation.

    Attributes:
        url: The URL to navigate to when this item is selected
    """

    def __init__(self, *args, url: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.url = url


class QuickNavigationModal(ModalScreen[str | None]):
    """Modal screen for quick navigation with fuzzy search.

    Args:
        bookmark_manager: BookmarkManager instance
        history_manager: HistoryManager instance
    """

    DEFAULT_CSS = """
    QuickNavigationModal {
        align: center middle;
    }

    QuickNavigationModal > Container {
        width: 80;
        height: 70%;
        max-height: 40;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 0;
    }

    QuickNavigationModal #search-input {
        width: 100%;
        height: 3;
        border: tall $primary;
        margin: 0 1;
    }

    QuickNavigationModal ListView {
        width: 100%;
        height: 1fr;
        margin: 0 1;
    }

    QuickNavigationModal ListItem {
        padding: 0 1;
        height: auto;
    }

    QuickNavigationModal .result-item {
        height: auto;
        padding: 0;
    }

    QuickNavigationModal .result-title {
        text-style: bold;
        color: $text;
    }

    QuickNavigationModal .result-url {
        color: $text-muted;
    }

    QuickNavigationModal .result-source {
        color: $accent;
        text-style: italic;
    }

    QuickNavigationModal .no-results {
        width: 100%;
        height: auto;
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("ctrl+k", "cancel", "Close", show=False, priority=True),
        Binding("enter", "select", "Select", show=False, priority=True),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
    ]

    def __init__(
        self,
        bookmark_manager: BookmarkManager,
        history_manager: HistoryManager,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.bookmark_manager = bookmark_manager
        self.history_manager = history_manager
        self._all_items: list[NavigationItem] = []
        self._filtered_items: list[NavigationItem] = []

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Quick Navigation (Ctrl+K)"
        with container:
            yield Input(
                placeholder="Type to search bookmarks and history...",
                id="search-input",
            )
            yield ListView(id="results-list")

    def on_mount(self) -> None:
        """Initialize the navigation items and focus the search input."""
        self._load_all_items()
        self._update_results("")
        self.query_one("#search-input", Input).focus()

    def _load_all_items(self) -> None:
        """Load all bookmarks and history entries into the searchable list."""
        self._all_items = []

        # Load bookmarks with error handling for corrupted data
        for bookmark in self.bookmark_manager.bookmarks:
            try:
                self._all_items.append(
                    NavigationItem(
                        url=bookmark.url,
                        title=bookmark.title,
                        source="bookmark",
                        timestamp=bookmark.created_at.isoformat(),
                    )
                )
            except (AttributeError, TypeError):
                # Skip corrupted bookmark entries
                continue

        # Build set of bookmark URLs for O(1) duplicate detection
        bookmark_urls = {item.url for item in self._all_items}

        # Load history entries (skip URLs already in bookmarks)
        for entry in self.history_manager.get_all_entries():
            if entry.url in bookmark_urls:
                continue
            try:
                self._all_items.append(
                    NavigationItem(
                        url=entry.url,
                        title=entry.url,  # History doesn't have titles
                        source="history",
                        timestamp=entry.timestamp.isoformat(),
                    )
                )
            except (AttributeError, TypeError):
                # Skip corrupted history entries
                continue

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update search results as user types."""
        if event.input.id == "search-input":
            self._update_results(event.value)

    def _update_results(self, query: str) -> None:
        """Filter and display results based on search query.

        Args:
            query: The search string from the user
        """
        if not query.strip():
            # Show all items sorted by timestamp (most recent first)
            self._filtered_items = sorted(
                self._all_items,
                key=lambda x: x.timestamp,
                reverse=True,
            )[:20]  # Limit to 20 most recent
        else:
            # Perform fuzzy search and sort by score
            scored_items = []
            for item in self._all_items:
                score = self._fuzzy_score(query.lower(), item)
                if score > 0:
                    scored_items.append((score, item))

            # Sort by score (highest first)
            scored_items.sort(key=lambda x: x[0], reverse=True)
            self._filtered_items = [item for score, item in scored_items[:20]]

        # Update the ListView
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()

        if not self._filtered_items:
            # Show "no results" message
            results_list.append(
                ListItem(Label("No results found", classes="no-results"))
            )
        else:
            for item in self._filtered_items:
                results_list.append(self._create_list_item(item))

            # Auto-select first item
            if len(results_list) > 0:
                results_list.index = 0

    def _fuzzy_score(self, query: str, item: NavigationItem) -> int:
        """Calculate fuzzy match score for an item.

        Args:
            query: Lowercase search query
            item: NavigationItem to score

        Returns:
            Score (higher is better, 0 means no match)
        """
        title_lower = item.title.lower()
        url_lower = item.url.lower()

        # Check for exact substring match in title (highest score)
        if query in title_lower:
            # Bonus for match at start
            if title_lower.startswith(query):
                return 1000
            return 500

        # Check for exact substring match in URL
        if query in url_lower:
            return 300

        # Check for acronym match (e.g., "gp" matches "Gemini Protocol")
        if self._matches_acronym(query, title_lower):
            return 200

        # Check for word boundary matches
        title_words = title_lower.split()
        url_words = url_lower.replace("://", " ").replace("/", " ").split()

        for word in title_words:
            if word.startswith(query):
                return 100

        for word in url_words:
            if word.startswith(query):
                return 50

        return 0

    def _matches_acronym(self, query: str, text: str) -> bool:
        """Check if query matches the acronym of text.

        Args:
            query: Search query
            text: Text to check

        Returns:
            True if query matches first letters of words in text
        """
        words = text.split()
        if len(query) > len(words):
            return False

        acronym = "".join(word[0] for word in words if word)
        return acronym.startswith(query)

    def _create_list_item(self, item: NavigationItem) -> NavigationListItem:
        """Create a NavigationListItem widget for a navigation item.

        Args:
            item: NavigationItem to display

        Returns:
            Configured NavigationListItem widget with URL stored
        """
        container = Vertical(
            Label(item.title, classes="result-title"),
            Label(item.url, classes="result-url"),
            Label(f"[{item.source}]", classes="result-source"),
            classes="result-item",
        )
        return NavigationListItem(container, url=item.url)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection from the list."""
        if isinstance(event.item, NavigationListItem):
            self.dismiss(event.item.url)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select the current item and close the modal."""
        results_list = self.query_one("#results-list", ListView)
        item = results_list.highlighted_child
        if isinstance(item, NavigationListItem):
            self.dismiss(item.url)
        else:
            # No valid item selected (e.g., "No results" message) - dismiss gracefully
            self.dismiss(None)

    def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        results_list = self.query_one("#results-list", ListView)
        results_list.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        results_list = self.query_one("#results-list", ListView)
        results_list.action_cursor_up()
