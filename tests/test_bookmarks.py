"""Tests for the bookmarks module."""

import tempfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder


class TestBookmark:
    """Tests for the Bookmark dataclass."""

    def test_create_bookmark(self) -> None:
        """Test creating a bookmark with factory method."""
        bookmark = Bookmark.create(
            url="gemini://example.com/",
            title="Example Site",
        )

        assert bookmark.url == "gemini://example.com/"
        assert bookmark.title == "Example Site"
        assert bookmark.folder_id is None
        assert bookmark.id  # Should have an auto-generated ID
        assert isinstance(bookmark.created_at, datetime)

    def test_create_bookmark_with_folder(self) -> None:
        """Test creating a bookmark in a folder."""
        bookmark = Bookmark.create(
            url="gemini://example.com/",
            title="Example",
            folder_id="folder-123",
        )

        assert bookmark.folder_id == "folder-123"

    def test_bookmark_to_dict(self) -> None:
        """Test converting bookmark to dictionary."""
        bookmark = Bookmark.create(
            url="gemini://test.com/",
            title="Test",
        )
        data = bookmark.to_dict()

        assert data["url"] == "gemini://test.com/"
        assert data["title"] == "Test"
        assert data["id"] == bookmark.id
        assert "created_at" in data
        assert "folder_id" not in data  # Should not include None values

    def test_bookmark_from_dict(self) -> None:
        """Test creating bookmark from dictionary."""
        data = {
            "id": "test-id",
            "url": "gemini://test.com/",
            "title": "Test",
            "created_at": "2025-01-01T12:00:00",
        }
        bookmark = Bookmark.from_dict(data)

        assert bookmark.id == "test-id"
        assert bookmark.url == "gemini://test.com/"
        assert bookmark.title == "Test"
        assert bookmark.folder_id is None


class TestFolder:
    """Tests for the Folder dataclass."""

    def test_create_folder(self) -> None:
        """Test creating a folder with factory method."""
        folder = Folder.create(name="Favorites")

        assert folder.name == "Favorites"
        assert folder.parent_id is None
        assert folder.id  # Should have an auto-generated ID
        assert isinstance(folder.created_at, datetime)

    def test_folder_to_dict(self) -> None:
        """Test converting folder to dictionary."""
        folder = Folder.create(name="Test Folder")
        data = folder.to_dict()

        assert data["name"] == "Test Folder"
        assert data["id"] == folder.id
        assert "created_at" in data
        assert "parent_id" not in data  # Should not include None values
        assert "color" not in data  # Should not include None values

    def test_folder_to_dict_with_color(self) -> None:
        """Test converting folder with color to dictionary."""
        folder = Folder.create(name="Colored Folder")
        folder.color = "#4a4a5a"
        data = folder.to_dict()

        assert data["color"] == "#4a4a5a"

    def test_folder_from_dict(self) -> None:
        """Test creating folder from dictionary."""
        data = {
            "id": "folder-id",
            "name": "Test Folder",
            "created_at": "2025-01-01T12:00:00",
        }
        folder = Folder.from_dict(data)

        assert folder.id == "folder-id"
        assert folder.name == "Test Folder"
        assert folder.parent_id is None
        assert folder.color is None

    def test_folder_from_dict_with_color(self) -> None:
        """Test creating folder with color from dictionary."""
        data = {
            "id": "folder-id",
            "name": "Colored Folder",
            "color": "#b0c4de",
            "created_at": "2025-01-01T12:00:00",
        }
        folder = Folder.from_dict(data)

        assert folder.color == "#b0c4de"

    def test_folder_without_color_backward_compatible(self) -> None:
        """Test that folders without color field load correctly (backward compatibility)."""
        data = {
            "id": "old-folder",
            "name": "Old Folder",
            "created_at": "2024-01-01T12:00:00",
        }
        folder = Folder.from_dict(data)

        assert folder.id == "old-folder"
        assert folder.name == "Old Folder"
        assert folder.color is None


class TestBookmarkManager:
    """Tests for the BookmarkManager class."""

    @pytest.fixture
    def temp_config_dir(self) -> Iterator[Path]:
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> BookmarkManager:
        """Create a BookmarkManager with temporary storage."""
        return BookmarkManager(config_dir=temp_config_dir)

    def test_initialize_empty(self, manager: BookmarkManager) -> None:
        """Test manager initializes with empty lists."""
        assert len(manager.bookmarks) == 0
        assert len(manager.folders) == 0

    def test_add_bookmark(self, manager: BookmarkManager) -> None:
        """Test adding a bookmark."""
        bookmark = manager.add_bookmark(
            url="gemini://example.com/",
            title="Example",
        )

        assert bookmark.url == "gemini://example.com/"
        assert bookmark.title == "Example"
        assert len(manager.bookmarks) == 1
        assert manager.bookmarks[0] == bookmark

    def test_add_bookmark_to_folder(self, manager: BookmarkManager) -> None:
        """Test adding a bookmark to a folder."""
        folder = manager.add_folder("Favorites")
        bookmark = manager.add_bookmark(
            url="gemini://example.com/",
            title="Example",
            folder_id=folder.id,
        )

        assert bookmark.folder_id == folder.id

    def test_remove_bookmark(self, manager: BookmarkManager) -> None:
        """Test removing a bookmark."""
        bookmark = manager.add_bookmark("gemini://example.com/", "Example")
        result = manager.remove_bookmark(bookmark.id)

        assert result is True
        assert len(manager.bookmarks) == 0

    def test_remove_nonexistent_bookmark(self, manager: BookmarkManager) -> None:
        """Test removing a bookmark that doesn't exist."""
        result = manager.remove_bookmark("nonexistent-id")
        assert result is False

    def test_update_bookmark_title(self, manager: BookmarkManager) -> None:
        """Test updating a bookmark's title."""
        bookmark = manager.add_bookmark("gemini://example.com/", "Old Title")
        result = manager.update_bookmark(bookmark.id, title="New Title")

        assert result is True
        assert bookmark.title == "New Title"

    def test_update_bookmark_folder(self, manager: BookmarkManager) -> None:
        """Test moving a bookmark to a folder."""
        folder = manager.add_folder("New Folder")
        bookmark = manager.add_bookmark("gemini://example.com/", "Example")
        result = manager.update_bookmark(bookmark.id, folder_id=folder.id)

        assert result is True
        assert bookmark.folder_id == folder.id

    def test_update_bookmark_to_root(self, manager: BookmarkManager) -> None:
        """Test moving a bookmark from folder to root."""
        folder = manager.add_folder("Folder")
        bookmark = manager.add_bookmark(
            "gemini://example.com/", "Example", folder_id=folder.id
        )
        result = manager.update_bookmark(bookmark.id, folder_id=None)

        assert result is True
        assert bookmark.folder_id is None

    def test_get_bookmark(self, manager: BookmarkManager) -> None:
        """Test getting a bookmark by ID."""
        bookmark = manager.add_bookmark("gemini://example.com/", "Example")
        found = manager.get_bookmark(bookmark.id)

        assert found == bookmark

    def test_get_nonexistent_bookmark(self, manager: BookmarkManager) -> None:
        """Test getting a bookmark that doesn't exist."""
        found = manager.get_bookmark("nonexistent")
        assert found is None

    def test_get_bookmarks_in_folder(self, manager: BookmarkManager) -> None:
        """Test getting bookmarks in a specific folder."""
        folder = manager.add_folder("Test")
        manager.add_bookmark("gemini://a.com/", "A", folder_id=folder.id)
        manager.add_bookmark("gemini://b.com/", "B", folder_id=folder.id)
        manager.add_bookmark("gemini://c.com/", "C")  # Root level

        bookmarks = manager.get_bookmarks_in_folder(folder.id)

        assert len(bookmarks) == 2
        assert all(b.folder_id == folder.id for b in bookmarks)

    def test_get_root_bookmarks(self, manager: BookmarkManager) -> None:
        """Test getting root-level bookmarks."""
        folder = manager.add_folder("Test")
        manager.add_bookmark("gemini://a.com/", "A", folder_id=folder.id)
        manager.add_bookmark("gemini://b.com/", "B")  # Root
        manager.add_bookmark("gemini://c.com/", "C")  # Root

        bookmarks = manager.get_root_bookmarks()

        assert len(bookmarks) == 2
        assert all(b.folder_id is None for b in bookmarks)

    def test_bookmark_exists(self, manager: BookmarkManager) -> None:
        """Test checking if a bookmark exists by URL."""
        manager.add_bookmark("gemini://example.com/", "Example")

        assert manager.bookmark_exists("gemini://example.com/") is True
        assert manager.bookmark_exists("gemini://other.com/") is False

    def test_add_folder(self, manager: BookmarkManager) -> None:
        """Test adding a folder."""
        folder = manager.add_folder("Favorites")

        assert folder.name == "Favorites"
        assert len(manager.folders) == 1

    def test_remove_folder(self, manager: BookmarkManager) -> None:
        """Test removing a folder."""
        folder = manager.add_folder("Test")
        result = manager.remove_folder(folder.id)

        assert result is True
        assert len(manager.folders) == 0

    def test_remove_folder_moves_bookmarks_to_root(
        self, manager: BookmarkManager
    ) -> None:
        """Test that removing a folder moves its bookmarks to root."""
        folder = manager.add_folder("Test")
        bookmark = manager.add_bookmark(
            "gemini://example.com/", "Example", folder_id=folder.id
        )

        manager.remove_folder(folder.id)

        assert bookmark.folder_id is None
        assert len(manager.bookmarks) == 1

    def test_rename_folder(self, manager: BookmarkManager) -> None:
        """Test renaming a folder."""
        folder = manager.add_folder("Old Name")
        result = manager.rename_folder(folder.id, "New Name")

        assert result is True
        assert folder.name == "New Name"

    def test_update_folder_color(self, manager: BookmarkManager) -> None:
        """Test setting a folder's color."""
        folder = manager.add_folder("Test")
        result = manager.update_folder_color(folder.id, "#4a4a5a")

        assert result is True
        assert folder.color == "#4a4a5a"

    def test_update_folder_color_to_none(self, manager: BookmarkManager) -> None:
        """Test clearing a folder's color."""
        folder = manager.add_folder("Test")
        manager.update_folder_color(folder.id, "#4a4a5a")
        result = manager.update_folder_color(folder.id, None)

        assert result is True
        assert folder.color is None

    def test_update_folder_color_not_found(self, manager: BookmarkManager) -> None:
        """Test updating color for non-existent folder."""
        result = manager.update_folder_color("fake-id", "#4a4a5a")
        assert result is False

    def test_folder_color_persistence(self, temp_config_dir: Path) -> None:
        """Test that folder color is persisted to disk."""
        manager1 = BookmarkManager(config_dir=temp_config_dir)
        folder = manager1.add_folder("Colored Folder")
        manager1.update_folder_color(folder.id, "#b0c4de")

        # Load in new manager
        manager2 = BookmarkManager(config_dir=temp_config_dir)
        loaded_folder = manager2.get_folder(folder.id)

        assert loaded_folder is not None
        assert loaded_folder.color == "#b0c4de"

    def test_get_folder(self, manager: BookmarkManager) -> None:
        """Test getting a folder by ID."""
        folder = manager.add_folder("Test")
        found = manager.get_folder(folder.id)

        assert found == folder

    def test_get_all_folders(self, manager: BookmarkManager) -> None:
        """Test getting all folders."""
        manager.add_folder("A")
        manager.add_folder("B")
        manager.add_folder("C")

        folders = manager.get_all_folders()

        assert len(folders) == 3

    def test_persistence_save_and_load(self, temp_config_dir: Path) -> None:
        """Test that bookmarks are persisted to disk."""
        # Create and save
        manager1 = BookmarkManager(config_dir=temp_config_dir)
        folder = manager1.add_folder("Test Folder")
        manager1.add_bookmark("gemini://example.com/", "Example", folder_id=folder.id)
        manager1.add_bookmark("gemini://other.com/", "Other")

        # Load in new manager
        manager2 = BookmarkManager(config_dir=temp_config_dir)

        assert len(manager2.folders) == 1
        assert len(manager2.bookmarks) == 2
        assert manager2.folders[0].name == "Test Folder"

    def test_persistence_file_location(self, temp_config_dir: Path) -> None:
        """Test that bookmarks file is created in correct location."""
        manager = BookmarkManager(config_dir=temp_config_dir)
        manager.add_bookmark("gemini://example.com/", "Example")

        expected_file = temp_config_dir / "bookmarks.toml"
        assert expected_file.exists()

    def test_load_nonexistent_file(self, temp_config_dir: Path) -> None:
        """Test loading when file doesn't exist yet."""
        manager = BookmarkManager(config_dir=temp_config_dir)

        assert len(manager.bookmarks) == 0
        assert len(manager.folders) == 0

    def test_creates_config_directory(self) -> None:
        """Test that config directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "config" / "dir"
            manager = BookmarkManager(config_dir=nested_dir)
            manager.add_bookmark("gemini://example.com/", "Example")

            assert nested_dir.exists()
            assert (nested_dir / "bookmarks.toml").exists()
