"""Tests for the feeds module."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from astronomo.feeds import Feed, FeedFolder, FeedManager, ReadItem


class TestFeed:
    """Tests for the Feed dataclass."""

    def test_create_feed(self) -> None:
        """Test creating a feed with factory method."""
        feed = Feed.create(
            url="gemini://example.com/feed.xml",
            title="Example Feed",
        )

        assert feed.url == "gemini://example.com/feed.xml"
        assert feed.title == "Example Feed"
        assert feed.folder_id is None
        assert feed.last_fetched is None
        assert feed.id  # Should have an auto-generated ID
        assert isinstance(feed.created_at, datetime)

    def test_create_feed_with_folder(self) -> None:
        """Test creating a feed in a folder."""
        feed = Feed.create(
            url="gemini://example.com/feed.xml",
            title="Example",
            folder_id="folder-123",
        )

        assert feed.folder_id == "folder-123"

    def test_feed_to_dict(self) -> None:
        """Test converting feed to dictionary."""
        feed = Feed.create(
            url="gemini://test.com/feed.xml",
            title="Test Feed",
        )
        data = feed.to_dict()

        assert data["url"] == "gemini://test.com/feed.xml"
        assert data["title"] == "Test Feed"
        assert data["id"] == feed.id
        assert "created_at" in data
        assert "folder_id" not in data  # Should not include None values
        assert "last_fetched" not in data  # Should not include None values

    def test_feed_to_dict_with_last_fetched(self) -> None:
        """Test converting feed with last_fetched to dictionary."""
        feed = Feed.create(
            url="gemini://test.com/feed.xml",
            title="Test Feed",
        )
        feed.last_fetched = datetime.now()
        data = feed.to_dict()

        assert "last_fetched" in data
        assert data["last_fetched"] == feed.last_fetched.isoformat()

    def test_feed_from_dict(self) -> None:
        """Test creating feed from dictionary."""
        data = {
            "id": "test-id",
            "url": "gemini://test.com/feed.xml",
            "title": "Test Feed",
            "created_at": "2025-01-01T12:00:00",
        }
        feed = Feed.from_dict(data)

        assert feed.id == "test-id"
        assert feed.url == "gemini://test.com/feed.xml"
        assert feed.title == "Test Feed"
        assert feed.folder_id is None
        assert feed.last_fetched is None

    def test_feed_from_dict_with_last_fetched(self) -> None:
        """Test creating feed from dictionary with last_fetched."""
        data = {
            "id": "test-id",
            "url": "gemini://test.com/feed.xml",
            "title": "Test Feed",
            "created_at": "2025-01-01T12:00:00",
            "last_fetched": "2025-01-02T15:30:00",
        }
        feed = Feed.from_dict(data)

        assert feed.last_fetched == datetime.fromisoformat("2025-01-02T15:30:00")


class TestFeedFolder:
    """Tests for the FeedFolder dataclass."""

    def test_create_folder(self) -> None:
        """Test creating a folder with factory method."""
        folder = FeedFolder.create(name="Tech News")

        assert folder.name == "Tech News"
        assert folder.parent_id is None
        assert folder.id  # Should have an auto-generated ID
        assert isinstance(folder.created_at, datetime)

    def test_folder_to_dict(self) -> None:
        """Test converting folder to dictionary."""
        folder = FeedFolder.create(name="Test Folder")
        data = folder.to_dict()

        assert data["name"] == "Test Folder"
        assert data["id"] == folder.id
        assert "created_at" in data
        assert "parent_id" not in data  # Should not include None values

    def test_folder_from_dict(self) -> None:
        """Test creating folder from dictionary."""
        data = {
            "id": "folder-id",
            "name": "Test Folder",
            "created_at": "2025-01-01T12:00:00",
        }
        folder = FeedFolder.from_dict(data)

        assert folder.id == "folder-id"
        assert folder.name == "Test Folder"
        assert folder.parent_id is None


class TestReadItem:
    """Tests for the ReadItem dataclass."""

    def test_create_read_item(self) -> None:
        """Test creating a read item."""
        item = ReadItem(
            item_id="item-hash-123",
            feed_id="feed-123",
        )

        assert item.item_id == "item-hash-123"
        assert item.feed_id == "feed-123"
        assert isinstance(item.read_at, datetime)

    def test_read_item_to_dict(self) -> None:
        """Test converting read item to dictionary."""
        item = ReadItem(
            item_id="item-hash-123",
            feed_id="feed-123",
        )
        data = item.to_dict()

        assert data["item_id"] == "item-hash-123"
        assert data["feed_id"] == "feed-123"
        assert "read_at" in data

    def test_read_item_from_dict(self) -> None:
        """Test creating read item from dictionary."""
        data = {
            "item_id": "item-hash-123",
            "feed_id": "feed-123",
            "read_at": "2025-01-01T12:00:00",
        }
        item = ReadItem.from_dict(data)

        assert item.item_id == "item-hash-123"
        assert item.feed_id == "feed-123"
        assert item.read_at == datetime.fromisoformat("2025-01-01T12:00:00")


class TestFeedManager:
    """Tests for the FeedManager class."""

    @pytest.fixture
    def temp_config_dir(self) -> Path:
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> FeedManager:
        """Create a FeedManager with temporary storage."""
        return FeedManager(config_dir=temp_config_dir)

    # Initialization tests

    def test_initialize_empty(self, manager: FeedManager) -> None:
        """Test manager initializes with empty lists."""
        assert len(manager.feeds) == 0
        assert len(manager.folders) == 0
        assert len(manager.read_items) == 0

    # Feed CRUD tests

    def test_add_feed(self, manager: FeedManager) -> None:
        """Test adding a feed."""
        feed = manager.add_feed(
            url="gemini://example.com/feed.xml",
            title="Example Feed",
        )

        assert feed.url == "gemini://example.com/feed.xml"
        assert feed.title == "Example Feed"
        assert len(manager.feeds) == 1
        assert manager.feeds[0] == feed

    def test_add_feed_to_folder(self, manager: FeedManager) -> None:
        """Test adding a feed to a folder."""
        folder = manager.add_folder("Tech")
        feed = manager.add_feed(
            url="gemini://example.com/feed.xml",
            title="Example Feed",
            folder_id=folder.id,
        )

        assert feed.folder_id == folder.id

    def test_remove_feed(self, manager: FeedManager) -> None:
        """Test removing a feed."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        result = manager.remove_feed(feed.id)

        assert result is True
        assert len(manager.feeds) == 0

    def test_remove_nonexistent_feed(self, manager: FeedManager) -> None:
        """Test removing a feed that doesn't exist."""
        result = manager.remove_feed("nonexistent-id")
        assert result is False

    def test_remove_feed_removes_read_items(self, manager: FeedManager) -> None:
        """Test that removing a feed also removes its read items."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")

        # Mark some items as read
        manager.mark_as_read(feed.id, "gemini://example.com/item1", None)
        manager.mark_as_read(feed.id, "gemini://example.com/item2", None)

        assert len(manager.read_items) == 2

        # Remove the feed
        manager.remove_feed(feed.id)

        # Read items should be gone
        assert len(manager.read_items) == 0

    def test_update_feed_title(self, manager: FeedManager) -> None:
        """Test updating a feed's title."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Old Title")
        result = manager.update_feed(feed.id, title="New Title")

        assert result is True
        assert feed.title == "New Title"

    def test_update_feed_folder(self, manager: FeedManager) -> None:
        """Test moving a feed to a folder."""
        folder = manager.add_folder("News")
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        result = manager.update_feed(feed.id, folder_id=folder.id)

        assert result is True
        assert feed.folder_id == folder.id

    def test_update_feed_to_root(self, manager: FeedManager) -> None:
        """Test moving a feed from folder to root."""
        folder = manager.add_folder("News")
        feed = manager.add_feed(
            "gemini://example.com/feed.xml", "Example", folder_id=folder.id
        )
        result = manager.update_feed(feed.id, folder_id=None)

        assert result is True
        assert feed.folder_id is None

    def test_update_feed_last_fetched(self, manager: FeedManager) -> None:
        """Test updating a feed's last_fetched timestamp."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        now = datetime.now()
        result = manager.update_feed(feed.id, last_fetched=now)

        assert result is True
        assert feed.last_fetched == now

    def test_get_feed(self, manager: FeedManager) -> None:
        """Test getting a feed by ID."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        found = manager.get_feed(feed.id)

        assert found == feed

    def test_get_nonexistent_feed(self, manager: FeedManager) -> None:
        """Test getting a feed that doesn't exist."""
        found = manager.get_feed("nonexistent")
        assert found is None

    def test_get_feeds_in_folder(self, manager: FeedManager) -> None:
        """Test getting feeds in a specific folder."""
        folder = manager.add_folder("Tech")
        manager.add_feed("gemini://a.com/feed.xml", "A", folder_id=folder.id)
        manager.add_feed("gemini://b.com/feed.xml", "B", folder_id=folder.id)
        manager.add_feed("gemini://c.com/feed.xml", "C")  # Root level

        feeds = manager.get_feeds_in_folder(folder.id)

        assert len(feeds) == 2
        assert all(f.folder_id == folder.id for f in feeds)

    def test_get_root_feeds(self, manager: FeedManager) -> None:
        """Test getting root-level feeds."""
        folder = manager.add_folder("Tech")
        manager.add_feed("gemini://a.com/feed.xml", "A", folder_id=folder.id)
        manager.add_feed("gemini://b.com/feed.xml", "B")  # Root
        manager.add_feed("gemini://c.com/feed.xml", "C")  # Root

        feeds = manager.get_root_feeds()

        assert len(feeds) == 2
        assert all(f.folder_id is None for f in feeds)

    def test_feed_exists(self, manager: FeedManager) -> None:
        """Test checking if a feed exists by URL."""
        manager.add_feed("gemini://example.com/feed.xml", "Example")

        assert manager.feed_exists("gemini://example.com/feed.xml") is True
        assert manager.feed_exists("gemini://other.com/feed.xml") is False

    # Folder CRUD tests

    def test_add_folder(self, manager: FeedManager) -> None:
        """Test adding a folder."""
        folder = manager.add_folder("Tech News")

        assert folder.name == "Tech News"
        assert len(manager.folders) == 1

    def test_remove_folder(self, manager: FeedManager) -> None:
        """Test removing a folder."""
        folder = manager.add_folder("Tech")
        result = manager.remove_folder(folder.id)

        assert result is True
        assert len(manager.folders) == 0

    def test_remove_folder_moves_feeds_to_root(self, manager: FeedManager) -> None:
        """Test that removing a folder moves its feeds to root."""
        folder = manager.add_folder("Tech")
        feed = manager.add_feed(
            "gemini://example.com/feed.xml", "Example", folder_id=folder.id
        )

        manager.remove_folder(folder.id)

        assert feed.folder_id is None
        assert len(manager.feeds) == 1

    def test_rename_folder(self, manager: FeedManager) -> None:
        """Test renaming a folder."""
        folder = manager.add_folder("Old Name")
        result = manager.rename_folder(folder.id, "New Name")

        assert result is True
        assert folder.name == "New Name"

    def test_get_folder(self, manager: FeedManager) -> None:
        """Test getting a folder by ID."""
        folder = manager.add_folder("Tech")
        found = manager.get_folder(folder.id)

        assert found == folder

    def test_get_all_folders(self, manager: FeedManager) -> None:
        """Test getting all folders."""
        manager.add_folder("Tech")
        manager.add_folder("News")
        manager.add_folder("Blogs")

        folders = manager.get_all_folders()

        assert len(folders) == 3

    # Read/unread tracking tests

    def test_generate_item_id(self, manager: FeedManager) -> None:
        """Test generating stable item IDs."""
        feed_id = "feed-123"
        link = "gemini://example.com/item1"
        published = datetime(2025, 1, 15, 10, 0, 0)

        # Same inputs should generate same ID
        id1 = manager.generate_item_id(feed_id, link, published)
        id2 = manager.generate_item_id(feed_id, link, published)

        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) == 16  # Hash truncated to 16 chars

    def test_generate_item_id_different_inputs(self, manager: FeedManager) -> None:
        """Test that different inputs generate different IDs."""
        feed_id = "feed-123"
        link1 = "gemini://example.com/item1"
        link2 = "gemini://example.com/item2"

        id1 = manager.generate_item_id(feed_id, link1, None)
        id2 = manager.generate_item_id(feed_id, link2, None)

        assert id1 != id2

    def test_mark_as_read(self, manager: FeedManager) -> None:
        """Test marking a feed item as read."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        link = "gemini://example.com/item1"

        manager.mark_as_read(feed.id, link, None)

        assert len(manager.read_items) == 1
        assert manager.is_read(feed.id, link, None) is True

    def test_mark_as_read_duplicate(self, manager: FeedManager) -> None:
        """Test that marking the same item as read twice doesn't duplicate."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        link = "gemini://example.com/item1"

        manager.mark_as_read(feed.id, link, None)
        manager.mark_as_read(feed.id, link, None)

        assert len(manager.read_items) == 1

    def test_is_read(self, manager: FeedManager) -> None:
        """Test checking if an item is read."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        link1 = "gemini://example.com/item1"
        link2 = "gemini://example.com/item2"

        manager.mark_as_read(feed.id, link1, None)

        assert manager.is_read(feed.id, link1, None) is True
        assert manager.is_read(feed.id, link2, None) is False

    def test_get_unread_count(self, manager: FeedManager) -> None:
        """Test getting the unread count for a feed."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")

        items = [
            ("gemini://example.com/item1", None),
            ("gemini://example.com/item2", None),
            ("gemini://example.com/item3", None),
        ]

        # Mark one as read
        manager.mark_as_read(feed.id, items[0][0], items[0][1])

        unread = manager.get_unread_count(feed.id, items)

        assert unread == 2

    def test_mark_all_as_read(self, manager: FeedManager) -> None:
        """Test marking all items in a feed as read."""
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")

        items = [
            ("gemini://example.com/item1", None),
            ("gemini://example.com/item2", None),
            ("gemini://example.com/item3", None),
        ]

        manager.mark_all_as_read(feed.id, items)

        assert len(manager.read_items) == 3
        assert all(manager.is_read(feed.id, link, pub) for link, pub in items)

    # Persistence tests

    def test_persistence_save_and_load(self, temp_config_dir: Path) -> None:
        """Test that feeds are persisted to disk."""
        # Create and save
        manager1 = FeedManager(config_dir=temp_config_dir)
        folder = manager1.add_folder("Tech")
        feed = manager1.add_feed(
            "gemini://example.com/feed.xml", "Example", folder_id=folder.id
        )
        manager1.add_feed("gemini://other.com/feed.xml", "Other")
        manager1.mark_as_read(feed.id, "gemini://example.com/item1", None)

        # Load in new manager
        manager2 = FeedManager(config_dir=temp_config_dir)

        assert len(manager2.folders) == 1
        assert len(manager2.feeds) == 2
        assert len(manager2.read_items) == 1
        assert manager2.folders[0].name == "Tech"

    def test_persistence_file_location(self, temp_config_dir: Path) -> None:
        """Test that feeds file is created in correct location."""
        manager = FeedManager(config_dir=temp_config_dir)
        manager.add_feed("gemini://example.com/feed.xml", "Example")

        expected_file = temp_config_dir / "feeds.toml"
        assert expected_file.exists()

    def test_load_nonexistent_file(self, temp_config_dir: Path) -> None:
        """Test loading when file doesn't exist yet."""
        manager = FeedManager(config_dir=temp_config_dir)

        assert len(manager.feeds) == 0
        assert len(manager.folders) == 0
        assert len(manager.read_items) == 0

    def test_creates_config_directory(self) -> None:
        """Test that config directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "config" / "dir"
            manager = FeedManager(config_dir=nested_dir)
            manager.add_feed("gemini://example.com/feed.xml", "Example")

            assert nested_dir.exists()
            assert (nested_dir / "feeds.toml").exists()

    def test_persistence_preserves_last_fetched(self, temp_config_dir: Path) -> None:
        """Test that last_fetched is preserved across saves/loads."""
        # Create and save
        manager1 = FeedManager(config_dir=temp_config_dir)
        feed = manager1.add_feed("gemini://example.com/feed.xml", "Example")
        now = datetime.now()
        manager1.update_feed(feed.id, last_fetched=now)

        # Load in new manager
        manager2 = FeedManager(config_dir=temp_config_dir)

        assert len(manager2.feeds) == 1
        loaded_feed = manager2.feeds[0]
        assert loaded_feed.last_fetched is not None
        # Compare with small tolerance for microsecond differences
        assert abs((loaded_feed.last_fetched - now).total_seconds()) < 1

    # State change tests

    def test_feed_state_changes_persist(self, temp_config_dir: Path) -> None:
        """Test that feed state changes persist correctly."""
        manager = FeedManager(config_dir=temp_config_dir)

        # Add feed in root
        feed = manager.add_feed("gemini://example.com/feed.xml", "Example")
        original_id = feed.id

        # Move to folder
        folder = manager.add_folder("Tech")
        manager.update_feed(feed.id, folder_id=folder.id)

        # Reload
        manager2 = FeedManager(config_dir=temp_config_dir)
        loaded_feed = manager2.get_feed(original_id)

        assert loaded_feed is not None
        assert loaded_feed.folder_id == folder.id

        # Move back to root
        manager2.update_feed(loaded_feed.id, folder_id=None)

        # Reload again
        manager3 = FeedManager(config_dir=temp_config_dir)
        final_feed = manager3.get_feed(original_id)

        assert final_feed is not None
        assert final_feed.folder_id is None

    def test_read_state_persists_across_sessions(self, temp_config_dir: Path) -> None:
        """Test that read state persists across manager instances."""
        # Session 1: Mark items as read
        manager1 = FeedManager(config_dir=temp_config_dir)
        feed = manager1.add_feed("gemini://example.com/feed.xml", "Example")
        manager1.mark_as_read(feed.id, "gemini://example.com/item1", None)
        manager1.mark_as_read(feed.id, "gemini://example.com/item2", None)

        # Session 2: Check read state
        manager2 = FeedManager(config_dir=temp_config_dir)
        loaded_feed = manager2.feeds[0]

        assert manager2.is_read(loaded_feed.id, "gemini://example.com/item1", None)
        assert manager2.is_read(loaded_feed.id, "gemini://example.com/item2", None)
        assert not manager2.is_read(loaded_feed.id, "gemini://example.com/item3", None)

    def test_complex_folder_reorganization(self, manager: FeedManager) -> None:
        """Test complex feed reorganization across folders."""
        # Create structure
        folder1 = manager.add_folder("Tech")
        folder2 = manager.add_folder("News")

        feed1 = manager.add_feed("gemini://a.com/feed.xml", "Feed A")
        feed2 = manager.add_feed(
            "gemini://b.com/feed.xml", "Feed B", folder_id=folder1.id
        )
        feed3 = manager.add_feed(
            "gemini://c.com/feed.xml", "Feed C", folder_id=folder2.id
        )

        # Move feed1 to folder1
        manager.update_feed(feed1.id, folder_id=folder1.id)
        assert len(manager.get_feeds_in_folder(folder1.id)) == 2

        # Move feed2 to folder2
        manager.update_feed(feed2.id, folder_id=folder2.id)
        assert len(manager.get_feeds_in_folder(folder1.id)) == 1
        assert len(manager.get_feeds_in_folder(folder2.id)) == 2

        # Move feed3 to root
        manager.update_feed(feed3.id, folder_id=None)
        assert len(manager.get_root_feeds()) == 1
        assert len(manager.get_feeds_in_folder(folder2.id)) == 1
