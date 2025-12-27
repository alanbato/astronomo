"""Tests for modal widgets (bookmark, edit, etc.)."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Input, ListView, Select

from astronomo.bookmarks import BookmarkManager
from astronomo.history import HistoryEntry, HistoryManager
from astronomo.parser import GemtextLine, LineType
from astronomo.widgets.add_bookmark_modal import AddBookmarkModal, NEW_FOLDER_SENTINEL
from astronomo.widgets.edit_item_modal import EditItemModal
from astronomo.widgets.quick_navigation_modal import QuickNavigationModal
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
            name_input.focus()
            await pilot.pause()

            # Use Enter key to save (more robust than clicking button)
            await pilot.press("enter")
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

    @pytest.mark.asyncio
    async def test_edit_folder_shows_color_picker(self, bookmark_manager):
        """Test that color picker is shown when editing a folder."""
        from astronomo.widgets.color_picker import ColorPicker

        folder = bookmark_manager.add_folder("Test Folder")
        modal = EditItemModal(bookmark_manager, folder)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Color picker should be present
            color_pickers = modal.query(ColorPicker)
            assert len(color_pickers) == 1

    @pytest.mark.asyncio
    async def test_edit_bookmark_no_color_picker(self, bookmark_manager):
        """Test that color picker is NOT shown when editing a bookmark."""
        from astronomo.widgets.color_picker import ColorPicker

        bookmark = bookmark_manager.add_bookmark(
            "gemini://example.com/", "Test Bookmark"
        )
        modal = EditItemModal(bookmark_manager, bookmark)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Color picker should NOT be present
            color_pickers = modal.query(ColorPicker)
            assert len(color_pickers) == 0


class TestQuickNavigationModal:
    """Tests for the QuickNavigationModal widget."""

    @pytest.fixture
    def history_manager(self):
        """Create a HistoryManager for testing."""
        return HistoryManager(max_size=100)

    @pytest.fixture
    def populated_managers(self, bookmark_manager, history_manager):
        """Create managers with some test data."""
        # Add bookmarks
        bookmark_manager.add_bookmark("gemini://example.com/", "Example Site")
        bookmark_manager.add_bookmark("gemini://gemini.circumlunar.space/", "Project Gemini")
        bookmark_manager.add_bookmark("gemini://test.org/page", "Test Page")

        # Add history entries
        history_manager.push(
            HistoryEntry(
                url="gemini://history1.com/",
                content=[GemtextLine(LineType.TEXT, "Test")],
            )
        )
        history_manager.push(
            HistoryEntry(
                url="gemini://history2.com/",
                content=[GemtextLine(LineType.TEXT, "Test")],
            )
        )

        return bookmark_manager, history_manager

    @pytest.mark.asyncio
    async def test_modal_shows_bookmarks_and_history(
        self, bookmark_manager, history_manager, populated_managers
    ):
        """Test that modal displays both bookmarks and history entries."""
        bm, hm = populated_managers
        modal = QuickNavigationModal(bm, hm)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have 3 bookmarks + 2 history = 5 items total
            assert len(modal._all_items) == 5

    @pytest.mark.asyncio
    async def test_search_filters_results(
        self, bookmark_manager, history_manager, populated_managers
    ):
        """Test that typing in search input filters the results."""
        bm, hm = populated_managers
        modal = QuickNavigationModal(bm, hm)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            search_input = modal.query_one("#search-input", Input)
            search_input.value = "gemini"
            await pilot.pause()

            # Should filter to only items matching "gemini"
            assert len(modal._filtered_items) > 0
            assert all("gemini" in item.title.lower() or "gemini" in item.url.lower()
                      for item in modal._filtered_items)

    @pytest.mark.asyncio
    async def test_escape_cancels(
        self, bookmark_manager, history_manager, populated_managers
    ):
        """Test that escape key cancels the modal."""
        bm, hm = populated_managers
        modal = QuickNavigationModal(bm, hm)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        # Modal should be dismissed with None
        assert app._modal_result is None

    @pytest.mark.asyncio
    async def test_enter_selects_item(
        self, bookmark_manager, history_manager, populated_managers
    ):
        """Test that enter key selects the highlighted item."""
        bm, hm = populated_managers
        modal = QuickNavigationModal(bm, hm)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Enter should select the first (highlighted) item
            await pilot.press("enter")
            await pilot.pause()

        # Should return a URL
        assert app._modal_result is not None
        assert app._modal_result.startswith("gemini://")

    @pytest.mark.asyncio
    async def test_fuzzy_scoring_prioritizes_title_matches(self, bookmark_manager, history_manager):
        """Test that fuzzy scoring prioritizes matches in titles."""
        bookmark_manager.add_bookmark("gemini://example.com/", "Example Site")
        bookmark_manager.add_bookmark("gemini://test.com/example", "Test Site")

        modal = QuickNavigationModal(bookmark_manager, history_manager)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Search for "example"
            item1 = modal._all_items[0]
            item2 = modal._all_items[1]

            score1 = modal._fuzzy_score("example", item1)
            score2 = modal._fuzzy_score("example", item2)

            # Title match should score higher than URL match
            assert score1 > score2

    @pytest.mark.asyncio
    async def test_empty_search_shows_recent_items(
        self, bookmark_manager, history_manager, populated_managers
    ):
        """Test that empty search shows most recent items."""
        bm, hm = populated_managers
        modal = QuickNavigationModal(bm, hm)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()

            # With no search query, should show items sorted by timestamp
            results_list = modal.query_one("#results-list", ListView)
            assert len(results_list.children) > 0
            assert len(modal._filtered_items) <= 20  # Limited to 20


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
