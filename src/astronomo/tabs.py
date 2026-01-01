"""Tab management for browser tabs.

This module provides the Tab data structure and TabManager for managing
multiple browser tabs with independent history and state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from astronomo.history import HistoryManager
from astronomo.parser import GemtextLine

if TYPE_CHECKING:
    from astronomo.identities import Identity


@dataclass
class TabState:
    """Represents the current viewer state for a tab.

    Used to save/restore scroll position and link selection when switching tabs.
    """

    scroll_position: float = 0
    link_index: int = 0
    content: list[GemtextLine] = field(default_factory=list)


@dataclass
class Tab:
    """Represents a single browser tab.

    Each tab maintains its own URL, history, scroll position, and session
    identity choices independently from other tabs.

    Attributes:
        id: Unique identifier for the tab
        title: Display title (from page H1 or URL)
        url: Current URL being displayed
        history: Independent navigation history for this tab
        viewer_state: Current scroll position and link selection
        session_identity_choices: Per-tab session identity selections
        created_at: When the tab was created
    """

    id: str
    title: str
    url: str
    history: HistoryManager
    viewer_state: TabState
    session_identity_choices: dict[str, "Identity | None"]
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, url: str = "", title: str = "New Tab") -> "Tab":
        """Create a new tab with default values.

        Args:
            url: Initial URL for the tab
            title: Initial title for the tab

        Returns:
            A new Tab instance with a unique ID
        """
        return cls(
            id=str(uuid4()),
            title=title,
            url=url,
            history=HistoryManager(max_size=100),
            viewer_state=TabState(),
            session_identity_choices={},
        )


class TabManager:
    """Manages multiple browser tabs.

    Provides operations for creating, switching, and closing tabs while
    maintaining tab order and tracking the active tab.

    Args:
        max_tabs: Maximum number of tabs allowed (default: 20)
    """

    def __init__(self, max_tabs: int = 20):
        """Initialize the tab manager."""
        self._tabs: dict[str, Tab] = {}
        self._tab_order: list[str] = []  # Maintains display order
        self._active_index: int = -1
        self._max_tabs = max_tabs

    def create_tab(
        self, url: str = "", title: str = "New Tab", activate: bool = True
    ) -> Tab:
        """Create a new tab.

        Args:
            url: Initial URL for the tab
            title: Initial title for the tab
            activate: Whether to make this the active tab

        Returns:
            The newly created Tab

        Raises:
            RuntimeError: If maximum tab limit is reached
        """
        if len(self._tabs) >= self._max_tabs:
            raise RuntimeError(f"Maximum tab limit ({self._max_tabs}) reached")

        tab = Tab.create(url=url, title=title)
        self._tabs[tab.id] = tab
        self._tab_order.append(tab.id)

        if activate or self._active_index == -1:
            self._active_index = len(self._tab_order) - 1

        return tab

    def close_tab(self, tab_id: str) -> Tab | None:
        """Close a tab and return the next active tab.

        If the closed tab was active, the next tab (or previous if closing
        the last tab) becomes active.

        Args:
            tab_id: ID of the tab to close

        Returns:
            The new active tab, or None if this was the last tab
        """
        if tab_id not in self._tabs:
            return self.current_tab()

        if len(self._tabs) <= 1:
            return None  # Cannot close the last tab

        # Find the tab's position
        tab_index = self._tab_order.index(tab_id)

        # Remove the tab
        del self._tabs[tab_id]
        self._tab_order.remove(tab_id)

        # Determine new active tab
        if tab_index == self._active_index:
            # Closed the active tab - activate the next one (or previous if at end)
            if tab_index >= len(self._tab_order):
                self._active_index = len(self._tab_order) - 1
            # Otherwise keep same index (which is now the next tab)
        elif tab_index < self._active_index:
            # Closed a tab before the active one - adjust index
            self._active_index -= 1

        return self.current_tab()

    def switch_to_tab(self, tab_id: str) -> Tab | None:
        """Switch to a specific tab.

        Args:
            tab_id: ID of the tab to switch to

        Returns:
            The newly active tab, or None if not found
        """
        if tab_id not in self._tabs:
            return None

        self._active_index = self._tab_order.index(tab_id)
        return self.current_tab()

    def switch_to_index(self, index: int) -> Tab | None:
        """Switch to a tab by its index (0-based).

        Args:
            index: The tab index to switch to

        Returns:
            The newly active tab, or None if index is invalid
        """
        if 0 <= index < len(self._tab_order):
            self._active_index = index
            return self.current_tab()
        return None

    def next_tab(self) -> Tab | None:
        """Switch to the next tab (wraps around).

        Returns:
            The newly active tab
        """
        if not self._tab_order:
            return None
        self._active_index = (self._active_index + 1) % len(self._tab_order)
        return self.current_tab()

    def prev_tab(self) -> Tab | None:
        """Switch to the previous tab (wraps around).

        Returns:
            The newly active tab
        """
        if not self._tab_order:
            return None
        self._active_index = (self._active_index - 1) % len(self._tab_order)
        return self.current_tab()

    def current_tab(self) -> Tab | None:
        """Get the currently active tab.

        Returns:
            The active Tab, or None if no tabs exist
        """
        if 0 <= self._active_index < len(self._tab_order):
            return self._tabs.get(self._tab_order[self._active_index])
        return None

    def get_tab(self, tab_id: str) -> Tab | None:
        """Get a tab by its ID.

        Args:
            tab_id: The tab ID to look up

        Returns:
            The Tab, or None if not found
        """
        return self._tabs.get(tab_id)

    def all_tabs(self) -> list[Tab]:
        """Get all tabs in display order.

        Returns:
            List of all tabs in their display order
        """
        return [self._tabs[tab_id] for tab_id in self._tab_order]

    def tab_count(self) -> int:
        """Get the number of open tabs.

        Returns:
            Number of tabs
        """
        return len(self._tabs)

    def can_close_tab(self) -> bool:
        """Check if a tab can be closed (more than one tab exists).

        Returns:
            True if closing a tab is allowed
        """
        return len(self._tabs) > 1

    def can_create_tab(self) -> bool:
        """Check if a new tab can be created.

        Returns:
            True if a new tab can be created
        """
        return len(self._tabs) < self._max_tabs

    def active_index(self) -> int:
        """Get the index of the active tab.

        Returns:
            The 0-based index of the active tab, or -1 if no tabs
        """
        return self._active_index
