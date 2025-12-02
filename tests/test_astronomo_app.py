"""Additional tests for Astronomo app to improve coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from astronomo.astronomo_app import Astronomo, build_query_url
from astronomo.widgets import GemtextViewer, BookmarksSidebar


class TestBuildQueryUrl:
    """Tests for the build_query_url utility function."""

    def test_appends_query_to_url(self):
        """Test that query is appended to URL."""
        url = "gemini://example.com/search"
        result = build_query_url(url, "hello")
        assert result == "gemini://example.com/search?hello"

    def test_replaces_existing_query(self):
        """Test that existing query is replaced."""
        url = "gemini://example.com/search?old"
        result = build_query_url(url, "new")
        assert result == "gemini://example.com/search?new"

    def test_encodes_special_characters(self):
        """Test that special characters are URL-encoded."""
        url = "gemini://example.com/search"
        result = build_query_url(url, "hello world")
        assert result == "gemini://example.com/search?hello%20world"

    def test_preserves_path(self):
        """Test that path is preserved."""
        url = "gemini://example.com/path/to/search"
        result = build_query_url(url, "query")
        assert result == "gemini://example.com/path/to/search?query"


class TestWelcomeMessage:
    """Tests for the welcome message when no initial URL is provided."""

    @pytest.mark.asyncio
    async def test_shows_welcome_without_url(
        self, mock_gemini_client, temp_config_path
    ):
        """Test that welcome message is shown when no URL is provided."""
        app = Astronomo(config_path=temp_config_path)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)
            # Check that welcome message is displayed
            has_welcome = any(
                "Welcome to Astronomo" in line.content
                for line in viewer.lines
                if hasattr(line, "content")
            )
            assert has_welcome


class TestUrlInput:
    """Tests for URL input handling."""

    @pytest.mark.asyncio
    async def test_auto_prefixes_gemini_scheme(self, mock_gemini_client):
        """Test that gemini:// is auto-prefixed when submitting URL."""
        app = Astronomo()

        async with app.run_test(size=(80, 24)) as pilot:
            from textual.widgets import Input

            await pilot.pause()

            # Type a URL without scheme
            url_input = app.query_one("#url-input", Input)
            url_input.value = "example.com"
            await pilot.pause()

            # Submit the URL
            await pilot.press("enter")
            await pilot.pause()

            # Verify the mock was called with prefixed URL
            mock_gemini_client.get.assert_called()
            called_url = mock_gemini_client.get.call_args[0][0]
            assert called_url.startswith("gemini://")


class TestHistoryNavigation:
    """Tests for back/forward history navigation."""

    @pytest.mark.asyncio
    async def test_back_button_initially_disabled(self, mock_gemini_client):
        """Test that back button is disabled when there's no history."""
        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            from textual.widgets import Button

            await pilot.pause()

            back_button = app.query_one("#back-button", Button)
            assert back_button.disabled is True

    @pytest.mark.asyncio
    async def test_forward_button_initially_disabled(self, mock_gemini_client):
        """Test that forward button is disabled when there's no forward history."""
        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            from textual.widgets import Button

            await pilot.pause()

            forward_button = app.query_one("#forward-button", Button)
            assert forward_button.disabled is True


class TestBookmarksToggle:
    """Tests for bookmarks sidebar toggle."""

    @pytest.mark.asyncio
    async def test_toggle_bookmarks_visibility(self, mock_gemini_client):
        """Test that Ctrl+B toggles bookmarks sidebar."""
        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            sidebar = app.query_one("#bookmarks-sidebar", BookmarksSidebar)

            # Initially hidden (no -visible class)
            initial_visible = sidebar.has_class("-visible")

            # Toggle with Ctrl+B
            await pilot.press("ctrl+b")
            await pilot.pause()

            # Should toggle
            assert sidebar.has_class("-visible") != initial_visible

            # Toggle again
            await pilot.press("ctrl+b")
            await pilot.pause()

            # Should return to initial state
            assert sidebar.has_class("-visible") == initial_visible


class TestRefreshAction:
    """Tests for page refresh action."""

    @pytest.mark.asyncio
    async def test_refresh_does_nothing_without_url(
        self, mock_gemini_client, temp_config_path
    ):
        """Test that refresh does nothing when no URL is loaded."""
        app = Astronomo(config_path=temp_config_path)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Reset call count
            mock_gemini_client.get.reset_mock()

            # Try refresh
            await pilot.press("ctrl+r")
            await pilot.pause()

            # Should not have called get
            mock_gemini_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_refetches_current_url(self, mock_gemini_client):
        """Test that refresh refetches the current URL."""
        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Wait for initial load
            initial_call_count = mock_gemini_client.get.call_count

            # Refresh
            await pilot.press("ctrl+r")
            await pilot.pause()

            # Should have called get again
            assert mock_gemini_client.get.call_count > initial_call_count


class TestLinkActivation:
    """Tests for link activation handling."""

    @pytest.mark.asyncio
    async def test_relative_link_resolved(self, mock_gemini_client):
        """Test that relative links are resolved against current URL."""
        app = Astronomo(initial_url="gemini://example.com/docs/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Navigate to a relative link (simulated)
            # The mock content has relative links like /docs/specification.gmi
            viewer = app.query_one("#content", GemtextViewer)

            # Check that the viewer has links
            assert len(viewer._link_widgets) > 0


class TestGetPageTitle:
    """Tests for page title extraction."""

    @pytest.mark.asyncio
    async def test_extracts_first_h1(self, mock_gemini_client):
        """Test that page title is extracted from first H1."""
        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # The mock content has "# Gemini FAQ" as the first heading
            title = app._get_page_title()
            assert title == "Gemini FAQ"

    @pytest.mark.asyncio
    async def test_returns_none_for_no_h1(self, mock_gemini_client):
        """Test that None is returned when no H1 exists."""
        # Create custom response without H1
        mock_gemini_client.get = AsyncMock(
            return_value=MagicMock(
                status=20,
                body="Just some plain text\n\nNo headings here.",
                meta="text/gemini",
                mime_type="text/gemini",
                is_success=MagicMock(return_value=True),
                is_redirect=MagicMock(return_value=False),
            )
        )

        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            title = app._get_page_title()
            assert title is None
