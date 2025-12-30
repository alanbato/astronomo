"""History management for browsing navigation.

This module provides history tracking for the Gemini browser, enabling
back/forward navigation with cached content to avoid re-fetching pages.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from astronomo.parser import GemtextLine


@dataclass
class HistoryEntry:
    """Represents a single entry in the browsing history.

    Attributes:
        url: The URL of the page
        content: Parsed Gemtext content as list of GemtextLine objects
        scroll_position: Vertical scroll position in the viewer
        link_index: Currently selected link index
        timestamp: When the page was visited
        status: Gemini response status code
        meta: Response metadata string
        mime_type: Content MIME type
    """

    url: str
    content: list[GemtextLine]
    scroll_position: float = 0
    link_index: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    status: int = 20
    meta: str = ""
    mime_type: str = "text/gemini"


class HistoryManager:
    """Manages browsing history with back/forward navigation.

    Implements standard browser history behavior:
    - Each navigation creates a new entry
    - Navigating back/forward moves through the history stack
    - New navigation from a non-head position clears forward history
    - Maximum size enforced with LRU eviction (oldest entries removed first)

    Args:
        max_size: Maximum number of history entries to keep (default: 100)
    """

    def __init__(self, max_size: int = 100):
        """Initialize history manager with specified maximum size."""
        self._history: deque[HistoryEntry] = deque(maxlen=max_size)
        self._current_index: int = -1  # -1 means no history

    def push(self, entry: HistoryEntry) -> None:
        """Add new entry to history, clearing forward history if not at head.

        When adding a new entry while not at the head of history (i.e., after
        navigating back), all forward history entries are removed. This matches
        standard browser behavior.

        Args:
            entry: The HistoryEntry to add
        """
        # If we're not at the head of history, remove everything after current position
        if self._current_index >= 0 and self._current_index < len(self._history) - 1:
            # Clear forward history
            while len(self._history) > self._current_index + 1:
                self._history.pop()

        # Add new entry
        self._history.append(entry)
        self._current_index = len(self._history) - 1

    def can_go_back(self) -> bool:
        """Check if back navigation is possible.

        Returns:
            True if there are entries before the current position
        """
        return self._current_index > 0

    def can_go_forward(self) -> bool:
        """Check if forward navigation is possible.

        Returns:
            True if there are entries after the current position
        """
        return self._current_index >= 0 and self._current_index < len(self._history) - 1

    def go_back(self) -> Optional[HistoryEntry]:
        """Navigate back and return the entry.

        Returns:
            The previous HistoryEntry, or None if already at the start
        """
        if not self.can_go_back():
            return None
        self._current_index -= 1
        return self._history[self._current_index]

    def go_forward(self) -> Optional[HistoryEntry]:
        """Navigate forward and return the entry.

        Returns:
            The next HistoryEntry, or None if already at the end
        """
        if not self.can_go_forward():
            return None
        self._current_index += 1
        return self._history[self._current_index]

    def current(self) -> Optional[HistoryEntry]:
        """Get current history entry.

        Returns:
            The current HistoryEntry, or None if history is empty
        """
        if self._current_index >= 0 and self._current_index < len(self._history):
            return self._history[self._current_index]
        return None

    def clear(self) -> None:
        """Clear all history."""
        self._history.clear()
        self._current_index = -1

    def __len__(self) -> int:
        """Return the number of entries in history."""
        return len(self._history)

    def get_all_entries(self) -> list[HistoryEntry]:
        """Return all history entries as a list.

        Returns:
            List of all HistoryEntry objects, oldest first
        """
        return list(self._history)
