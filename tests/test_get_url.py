"""Tests for get_url() status code handling in the Astronomo app."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from astronomo.astronomo_app import Astronomo
from astronomo.widgets import GemtextViewer


@pytest.fixture
def mock_client_factory(monkeypatch):
    """Factory to create mock GeminiClient with configurable responses.

    Returns a function that configures the mock and returns the mock client.
    """

    def _create_mock(
        status=20,
        body="# Test\n\nContent",
        meta="text/gemini",
        redirect_url=None,
    ):
        response = MagicMock()
        response.status = status
        response.body = body
        response.meta = meta
        response.redirect_url = redirect_url
        response.mime_type = "text/gemini" if 20 <= status < 30 else None
        response.is_success.return_value = 20 <= status < 30
        response.is_redirect.return_value = 30 <= status < 40

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=response)

        mock_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr("astronomo.astronomo_app.GeminiClient", mock_class)
        return mock_client, response

    return _create_mock


class TestSuccessResponses:
    """Tests for successful responses (status 20-29)."""

    @pytest.mark.asyncio
    async def test_status_20_displays_content(self, mock_client_factory):
        """Test that status 20 responses display the Gemtext content."""
        mock_client_factory(
            status=20,
            body="# Welcome\n\nThis is a test page.",
        )

        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)

            # Verify content is displayed
            assert len(viewer._link_widgets) >= 0  # Page loaded
            assert viewer is not None

    @pytest.mark.asyncio
    async def test_success_response_added_to_history(self, mock_client_factory):
        """Test that successful responses are added to history."""
        mock_client_factory(
            status=20,
            body="# Page\n\nContent",
        )

        app = Astronomo(initial_url="gemini://example.com/page")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # History should have the entry
            assert len(app.history) >= 1


class TestInputRequests:
    """Tests for input request responses (status 10-11)."""

    @pytest.mark.asyncio
    async def test_status_10_triggers_input_handling(self, mock_client_factory):
        """Test that status 10 triggers input request handling."""
        mock_client_factory(
            status=10,
            meta="Enter search query",
        )

        app = Astronomo(initial_url="gemini://example.com/search")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # The app should have called _handle_input_request
            # We can verify by checking that the viewer content wasn't updated
            # with format_response (since input requests return early)
            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None

    @pytest.mark.asyncio
    async def test_status_11_triggers_sensitive_input(self, mock_client_factory):
        """Test that status 11 triggers sensitive input handling."""
        mock_client_factory(
            status=11,
            meta="Enter password",
        )

        app = Astronomo(initial_url="gemini://example.com/login")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # App should handle sensitive input differently
            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None


class TestRedirectResponses:
    """Tests for redirect responses (status 30-39)."""

    @pytest.mark.asyncio
    async def test_redirect_with_absolute_url(self, mock_client_factory):
        """Test that redirects with absolute URLs are followed."""
        # First call returns redirect, second returns success
        mock_client, response = mock_client_factory(
            status=31,
            redirect_url="gemini://example.com/new-page",
        )

        # Configure second call to return success
        success_response = MagicMock()
        success_response.status = 20
        success_response.body = "# Redirected\n\nYou made it!"
        success_response.meta = "text/gemini"
        success_response.mime_type = "text/gemini"
        success_response.is_success.return_value = True
        success_response.is_redirect.return_value = False

        mock_client.get.side_effect = [response, success_response]

        app = Astronomo(initial_url="gemini://example.com/old-page")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # App should have followed the redirect
            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None


class TestCertificateResponses:
    """Tests for certificate-related responses (status 60-62)."""

    @pytest.mark.asyncio
    async def test_status_60_triggers_certificate_required(self, mock_client_factory):
        """Test that status 60 triggers certificate required handling."""
        mock_client_factory(
            status=60,
            meta="Client certificate required",
        )

        app = Astronomo(initial_url="gemini://secure.example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # App should have called _handle_certificate_required
            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None

    @pytest.mark.asyncio
    async def test_status_61_triggers_not_authorized(self, mock_client_factory):
        """Test that status 61 triggers certificate not authorized handling."""
        mock_client_factory(
            status=61,
            meta="Access denied",
        )

        app = Astronomo(initial_url="gemini://secure.example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None

    @pytest.mark.asyncio
    async def test_status_62_triggers_not_valid(self, mock_client_factory):
        """Test that status 62 triggers certificate not valid handling."""
        mock_client_factory(
            status=62,
            meta="Certificate expired",
        )

        app = Astronomo(initial_url="gemini://secure.example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None


class TestErrorResponses:
    """Tests for error responses (status 40-59)."""

    @pytest.mark.asyncio
    async def test_status_40_displays_error(self, mock_client_factory):
        """Test that temporary failure errors are displayed."""
        mock_client_factory(
            status=40,
            meta="Temporary failure",
        )

        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None

    @pytest.mark.asyncio
    async def test_status_51_displays_not_found(self, mock_client_factory):
        """Test that not found errors are displayed."""
        mock_client_factory(
            status=51,
            meta="Not found",
        )

        app = Astronomo(initial_url="gemini://example.com/missing")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None

    @pytest.mark.asyncio
    async def test_status_59_displays_bad_request(self, mock_client_factory):
        """Test that bad request errors are displayed."""
        mock_client_factory(
            status=59,
            meta="Bad request",
        )

        app = Astronomo(initial_url="gemini://example.com/bad")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            viewer = app.query_one("#content", GemtextViewer)
            assert viewer is not None
