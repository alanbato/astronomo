"""Tests for modal widgets (bookmark, edit, etc.)."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Input, Select

from astronomo.bookmarks import BookmarkManager
from astronomo.widgets.add_bookmark_modal import AddBookmarkModal, NEW_FOLDER_SENTINEL
from astronomo.widgets.edit_item_modal import EditItemModal
from astronomo.widgets.save_snapshot_modal import SaveSnapshotModal


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def bookmark_manager(temp_config_dir):
    """Create a BookmarkManager with temporary storage."""
    return BookmarkManager(config_dir=temp_config_dir)


class ModalTestApp(App):
    """Minimal app for testing modal screens."""

    def __init__(self, modal_screen):
        super().__init__()
        self._modal_screen = modal_screen
        self._modal_result = None

    def on_mount(self):
        self.push_screen(self._modal_screen, callback=self._on_modal_dismiss)

    def _on_modal_dismiss(self, result):
        self._modal_result = result


class TestAddBookmarkModal:
    """Tests for the AddBookmarkModal widget."""

    @pytest.mark.asyncio
    async def test_modal_shows_url_as_default_title(self, bookmark_manager):
        """Test that modal pre-fills title with URL when no suggested title."""
        url = "gemini://example.com/page"
        modal = AddBookmarkModal(bookmark_manager, url)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            title_input = modal.query_one("#title-input", Input)
            assert title_input.value == url

    @pytest.mark.asyncio
    async def test_modal_shows_suggested_title(self, bookmark_manager):
        """Test that modal pre-fills with suggested title when provided."""
        url = "gemini://example.com/page"
        suggested = "Example Page Title"
        modal = AddBookmarkModal(bookmark_manager, url, suggested_title=suggested)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            title_input = modal.query_one("#title-input", Input)
            assert title_input.value == suggested

    @pytest.mark.asyncio
    async def test_modal_creates_bookmark_on_save(self, bookmark_manager):
        """Test that clicking save creates a bookmark."""
        url = "gemini://example.com/"
        modal = AddBookmarkModal(bookmark_manager, url, suggested_title="Test Bookmark")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Press enter to save (triggers binding or input submission)
            await pilot.press("enter")
            await pilot.pause()

        # Bookmark should be created
        assert len(bookmark_manager.bookmarks) == 1
        assert bookmark_manager.bookmarks[0].title == "Test Bookmark"
        assert bookmark_manager.bookmarks[0].url == url

    @pytest.mark.asyncio
    async def test_modal_cancel_does_not_create_bookmark(self, bookmark_manager):
        """Test that cancel button dismisses without creating bookmark."""
        url = "gemini://example.com/"
        modal = AddBookmarkModal(bookmark_manager, url)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#cancel-btn")
            await pilot.pause()

        # No bookmark should be created
        assert len(bookmark_manager.bookmarks) == 0

    @pytest.mark.asyncio
    async def test_modal_shows_folder_options(self, bookmark_manager):
        """Test that folder select shows existing folders."""
        # Create some folders
        folder1 = bookmark_manager.add_folder("Work")
        folder2 = bookmark_manager.add_folder("Personal")

        modal = AddBookmarkModal(bookmark_manager, "gemini://test.com/")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have the folders plus "New Folder" option
            options = modal._get_folder_options()
            assert len(options) == 3  # 2 folders + New Folder
            assert ("Work", folder1.id) in options
            assert ("Personal", folder2.id) in options
            assert ("+ New Folder", NEW_FOLDER_SENTINEL) in options

    @pytest.mark.asyncio
    async def test_modal_creates_bookmark_in_folder(self, bookmark_manager):
        """Test creating a bookmark in a specific folder."""
        folder = bookmark_manager.add_folder("Test Folder")
        url = "gemini://example.com/"
        modal = AddBookmarkModal(bookmark_manager, url, suggested_title="Test")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Select the folder
            folder_select = modal.query_one("#folder-select", Select)
            folder_select.value = folder.id
            await pilot.pause()

            # Save via enter key
            await pilot.press("enter")
            await pilot.pause()

        # Bookmark should be in the folder
        assert len(bookmark_manager.bookmarks) == 1
        assert bookmark_manager.bookmarks[0].folder_id == folder.id

    @pytest.mark.asyncio
    async def test_escape_key_cancels_modal(self, bookmark_manager):
        """Test that escape key dismisses the modal."""
        modal = AddBookmarkModal(bookmark_manager, "gemini://test.com/")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        assert len(bookmark_manager.bookmarks) == 0


class TestEditItemModal:
    """Tests for the EditItemModal widget."""

    @pytest.mark.asyncio
    async def test_edit_bookmark_shows_current_title(self, bookmark_manager):
        """Test that edit modal shows current bookmark title."""
        bookmark = bookmark_manager.add_bookmark(
            "gemini://example.com/", "Original Title"
        )
        modal = EditItemModal(bookmark_manager, bookmark)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            assert name_input.value == "Original Title"

    @pytest.mark.asyncio
    async def test_edit_folder_shows_current_name(self, bookmark_manager):
        """Test that edit modal shows current folder name."""
        folder = bookmark_manager.add_folder("Original Folder")
        modal = EditItemModal(bookmark_manager, folder)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            assert name_input.value == "Original Folder"

    @pytest.mark.asyncio
    async def test_edit_bookmark_updates_title(self, bookmark_manager):
        """Test that saving updates the bookmark title."""
        bookmark = bookmark_manager.add_bookmark(
            "gemini://example.com/", "Original Title"
        )
        modal = EditItemModal(bookmark_manager, bookmark)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            name_input.value = "New Title"
            await pilot.pause()

            await pilot.click("#save-btn")
            await pilot.pause()

        # Title should be updated
        assert bookmark.title == "New Title"

    @pytest.mark.asyncio
    async def test_edit_folder_updates_name(self, bookmark_manager):
        """Test that saving updates the folder name."""
        folder = bookmark_manager.add_folder("Original Name")
        modal = EditItemModal(bookmark_manager, folder)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            name_input.value = "New Folder Name"
            await pilot.pause()

            await pilot.click("#save-btn")
            await pilot.pause()

        # Name should be updated
        assert folder.name == "New Folder Name"

    @pytest.mark.asyncio
    async def test_edit_cancel_does_not_update(self, bookmark_manager):
        """Test that cancel does not update the item."""
        bookmark = bookmark_manager.add_bookmark(
            "gemini://example.com/", "Original Title"
        )
        modal = EditItemModal(bookmark_manager, bookmark)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            name_input.value = "Should Not Save"
            await pilot.pause()

            await pilot.click("#cancel-btn")
            await pilot.pause()

        # Title should remain unchanged
        assert bookmark.title == "Original Title"

    @pytest.mark.asyncio
    async def test_edit_empty_name_does_not_save(self, bookmark_manager):
        """Test that empty name is not saved."""
        bookmark = bookmark_manager.add_bookmark(
            "gemini://example.com/", "Original Title"
        )
        modal = EditItemModal(bookmark_manager, bookmark)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            name_input.value = ""
            await pilot.pause()

            await pilot.click("#save-btn")
            await pilot.pause()

        # Title should remain unchanged
        assert bookmark.title == "Original Title"

    @pytest.mark.asyncio
    async def test_enter_key_saves(self, bookmark_manager):
        """Test that enter key saves changes."""
        bookmark = bookmark_manager.add_bookmark(
            "gemini://example.com/", "Original Title"
        )
        modal = EditItemModal(bookmark_manager, bookmark)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            name_input = modal.query_one("#name-input", Input)
            name_input.value = "Updated via Enter"
            await pilot.pause()

            # Submit via enter on the input
            await pilot.press("enter")
            await pilot.pause()

        assert bookmark.title == "Updated via Enter"


class TestSaveSnapshotModal:
    """Tests for the SaveSnapshotModal widget."""

    @pytest.mark.asyncio
    async def test_modal_displays_url(self, temp_config_dir):
        """Test that modal displays the URL being saved."""
        url = "gemini://example.com/page"
        save_path = temp_config_dir / "test.gmi"
        modal = SaveSnapshotModal(url, save_path)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Check that the modal stores the URL
            assert modal.url == url

    @pytest.mark.asyncio
    async def test_modal_displays_save_path(self, temp_config_dir):
        """Test that modal displays the save path."""
        url = "gemini://example.com/page"
        save_path = temp_config_dir / "test.gmi"
        modal = SaveSnapshotModal(url, save_path)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Check that the modal stores the save path
            assert modal.save_path == save_path

    @pytest.mark.asyncio
    async def test_save_button_confirms(self, temp_config_dir):
        """Test that clicking save button returns True."""
        url = "gemini://example.com/page"
        save_path = temp_config_dir / "test.gmi"
        modal = SaveSnapshotModal(url, save_path)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            save_btn = modal.query_one("#save-btn")
            await pilot.click(save_btn)
            await pilot.pause()

        assert app._modal_result is True

    @pytest.mark.asyncio
    async def test_cancel_button_cancels(self, temp_config_dir):
        """Test that clicking cancel button returns False."""
        url = "gemini://example.com/page"
        save_path = temp_config_dir / "test.gmi"
        modal = SaveSnapshotModal(url, save_path)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            cancel_btn = modal.query_one("#cancel-btn")
            await pilot.click(cancel_btn)
            await pilot.pause()

        assert app._modal_result is False

    @pytest.mark.asyncio
    async def test_escape_key_cancels(self, temp_config_dir):
        """Test that escape key cancels the modal."""
        url = "gemini://example.com/page"
        save_path = temp_config_dir / "test.gmi"
        modal = SaveSnapshotModal(url, save_path)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        assert app._modal_result is False

    @pytest.mark.asyncio
    async def test_enter_key_confirms(self, temp_config_dir):
        """Test that enter key confirms the save."""
        url = "gemini://example.com/page"
        save_path = temp_config_dir / "test.gmi"
        modal = SaveSnapshotModal(url, save_path)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

        assert app._modal_result is True
