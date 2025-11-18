"""Tests for history management."""

from datetime import datetime


from astronomo.history import HistoryEntry, HistoryManager
from astronomo.parser import GemtextLine, LineType


def create_test_entry(url: str, content_text: str = "Test content") -> HistoryEntry:
    """Helper to create a test history entry."""
    content = [
        GemtextLine(line_type=LineType.TEXT, content=content_text, raw=content_text)
    ]
    return HistoryEntry(
        url=url,
        content=content,
        scroll_position=0,
        link_index=0,
    )


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_create_entry_with_defaults(self):
        """Test creating entry with default values."""
        content = [GemtextLine(line_type=LineType.TEXT, content="Test", raw="Test")]
        entry = HistoryEntry(url="gemini://example.com", content=content)

        assert entry.url == "gemini://example.com"
        assert entry.content == content
        assert entry.scroll_position == 0
        assert entry.link_index == 0
        assert entry.status == 20
        assert entry.meta == ""
        assert entry.mime_type == "text/gemini"
        assert isinstance(entry.timestamp, datetime)

    def test_create_entry_with_custom_values(self):
        """Test creating entry with custom values."""
        content = [GemtextLine(line_type=LineType.TEXT, content="Test", raw="Test")]
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        entry = HistoryEntry(
            url="gemini://example.com/page",
            content=content,
            scroll_position=100,
            link_index=5,
            timestamp=timestamp,
            status=20,
            meta="text/gemini",
            mime_type="text/gemini",
        )

        assert entry.url == "gemini://example.com/page"
        assert entry.scroll_position == 100
        assert entry.link_index == 5
        assert entry.timestamp == timestamp
        assert entry.status == 20


class TestHistoryManager:
    """Tests for HistoryManager class."""

    def test_initialize_empty(self):
        """Test history manager initializes empty."""
        manager = HistoryManager()
        assert len(manager) == 0
        assert not manager.can_go_back()
        assert not manager.can_go_forward()
        assert manager.current() is None

    def test_push_single_entry(self):
        """Test pushing a single entry."""
        manager = HistoryManager()
        entry = create_test_entry("gemini://example.com")

        manager.push(entry)

        assert len(manager) == 1
        assert not manager.can_go_back()
        assert not manager.can_go_forward()
        assert manager.current() == entry

    def test_push_multiple_entries(self):
        """Test pushing multiple entries."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com/1")
        entry2 = create_test_entry("gemini://example.com/2")
        entry3 = create_test_entry("gemini://example.com/3")

        manager.push(entry1)
        manager.push(entry2)
        manager.push(entry3)

        assert len(manager) == 3
        assert manager.can_go_back()
        assert not manager.can_go_forward()
        assert manager.current() == entry3

    def test_go_back(self):
        """Test back navigation."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com/1")
        entry2 = create_test_entry("gemini://example.com/2")
        entry3 = create_test_entry("gemini://example.com/3")

        manager.push(entry1)
        manager.push(entry2)
        manager.push(entry3)

        # Go back once
        prev = manager.go_back()
        assert prev == entry2
        assert manager.current() == entry2
        assert manager.can_go_back()
        assert manager.can_go_forward()

        # Go back again
        prev = manager.go_back()
        assert prev == entry1
        assert manager.current() == entry1
        assert not manager.can_go_back()
        assert manager.can_go_forward()

    def test_go_back_at_start(self):
        """Test back navigation at start returns None."""
        manager = HistoryManager()
        entry = create_test_entry("gemini://example.com")
        manager.push(entry)

        result = manager.go_back()
        assert result is None
        assert manager.current() == entry

    def test_go_forward(self):
        """Test forward navigation."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com/1")
        entry2 = create_test_entry("gemini://example.com/2")
        entry3 = create_test_entry("gemini://example.com/3")

        manager.push(entry1)
        manager.push(entry2)
        manager.push(entry3)

        # Go back twice
        manager.go_back()
        manager.go_back()

        # Go forward once
        next_entry = manager.go_forward()
        assert next_entry == entry2
        assert manager.current() == entry2
        assert manager.can_go_back()
        assert manager.can_go_forward()

        # Go forward again
        next_entry = manager.go_forward()
        assert next_entry == entry3
        assert manager.current() == entry3
        assert manager.can_go_back()
        assert not manager.can_go_forward()

    def test_go_forward_at_end(self):
        """Test forward navigation at end returns None."""
        manager = HistoryManager()
        entry = create_test_entry("gemini://example.com")
        manager.push(entry)

        result = manager.go_forward()
        assert result is None
        assert manager.current() == entry

    def test_clear_forward_history_on_new_navigation(self):
        """Test that forward history is cleared when navigating to new page."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com/1")
        entry2 = create_test_entry("gemini://example.com/2")
        entry3 = create_test_entry("gemini://example.com/3")
        entry4 = create_test_entry("gemini://example.com/4")

        # Create history: 1 -> 2 -> 3
        manager.push(entry1)
        manager.push(entry2)
        manager.push(entry3)

        # Go back to entry1
        manager.go_back()  # to entry2
        manager.go_back()  # to entry1

        # Navigate to new page (entry4)
        manager.push(entry4)

        # Forward history should be cleared
        assert len(manager) == 2  # Only entry1 and entry4
        assert manager.current() == entry4
        assert manager.can_go_back()
        assert not manager.can_go_forward()

        # Verify entry2 and entry3 are gone
        prev = manager.go_back()
        assert prev == entry1

    def test_max_size_enforcement(self):
        """Test that history enforces maximum size with LRU eviction."""
        max_size = 5
        manager = HistoryManager(max_size=max_size)

        # Add more entries than max_size
        entries = [create_test_entry(f"gemini://example.com/{i}") for i in range(10)]
        for entry in entries:
            manager.push(entry)

        # Should only have max_size entries
        assert len(manager) == max_size

        # Should have the last 5 entries
        assert manager.current() == entries[9]
        manager.go_back()
        assert manager.current() == entries[8]
        manager.go_back()
        assert manager.current() == entries[7]
        manager.go_back()
        assert manager.current() == entries[6]
        manager.go_back()
        assert manager.current() == entries[5]
        assert not manager.can_go_back()  # Can't go further back

    def test_clear(self):
        """Test clearing history."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com/1")
        entry2 = create_test_entry("gemini://example.com/2")

        manager.push(entry1)
        manager.push(entry2)
        assert len(manager) == 2

        manager.clear()

        assert len(manager) == 0
        assert not manager.can_go_back()
        assert not manager.can_go_forward()
        assert manager.current() is None

    def test_duplicate_urls_allowed(self):
        """Test that visiting the same URL multiple times creates separate entries."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com", "First visit")
        entry2 = create_test_entry("gemini://other.com", "Different page")
        entry3 = create_test_entry("gemini://example.com", "Second visit")

        manager.push(entry1)
        manager.push(entry2)
        manager.push(entry3)

        # All three entries should exist
        assert len(manager) == 3
        assert manager.current() == entry3

        # Going back should show both visits to example.com
        manager.go_back()
        assert manager.current() == entry2
        manager.go_back()
        assert manager.current() == entry1

    def test_boundary_checks_empty_history(self):
        """Test boundary checks with empty history."""
        manager = HistoryManager()

        assert not manager.can_go_back()
        assert not manager.can_go_forward()
        assert manager.go_back() is None
        assert manager.go_forward() is None

    def test_state_preservation_in_entry(self):
        """Test that history entries preserve UI state."""
        content = [
            GemtextLine(line_type=LineType.HEADING_1, content="Title", raw="# Title"),
            GemtextLine(line_type=LineType.TEXT, content="Some text", raw="Some text"),
        ]
        entry = HistoryEntry(
            url="gemini://example.com",
            content=content,
            scroll_position=150,
            link_index=3,
        )

        # Verify state is preserved
        assert entry.scroll_position == 150
        assert entry.link_index == 3
        assert len(entry.content) == 2

    def test_back_forward_cycle(self):
        """Test multiple back and forward cycles."""
        manager = HistoryManager()
        entry1 = create_test_entry("gemini://example.com/1")
        entry2 = create_test_entry("gemini://example.com/2")
        entry3 = create_test_entry("gemini://example.com/3")

        manager.push(entry1)
        manager.push(entry2)
        manager.push(entry3)

        # Cycle: back, back, forward, back, forward, forward
        assert manager.current() == entry3
        manager.go_back()
        assert manager.current() == entry2
        manager.go_back()
        assert manager.current() == entry1
        manager.go_forward()
        assert manager.current() == entry2
        manager.go_back()
        assert manager.current() == entry1
        manager.go_forward()
        assert manager.current() == entry2
        manager.go_forward()
        assert manager.current() == entry3
