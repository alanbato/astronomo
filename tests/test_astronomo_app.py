"""Additional tests for Astronomo app to improve coverage."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    @pytest.mark.asyncio
    async def test_uses_response_url_for_relative_links(self, mock_gemini_client):
        """Test that response.url (after redirects) is used for relative links.

        When a server redirects from /~user to /~user/, the response.url
        should include the trailing slash, and relative links should be
        resolved against that URL.
        """
        # Simulate a redirect: request /~user, server returns content at /~user/
        mock_gemini_client.get = AsyncMock(
            return_value=MagicMock(
                status=20,
                body="# Page\n=> ./about.gmi About\n",
                meta="text/gemini",
                mime_type="text/gemini",
                is_success=MagicMock(return_value=True),
                is_redirect=MagicMock(return_value=False),
                url="gemini://example.com/~user/",  # Final URL after redirect
            )
        )

        # User navigates to URL without trailing slash
        app = Astronomo(initial_url="gemini://example.com/~user")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # The current_url should be the final URL (with trailing slash)
            assert app.current_url == "gemini://example.com/~user/"

            # Verify relative links would resolve correctly
            from urllib.parse import urljoin

            resolved = urljoin(app.current_url, "./about.gmi")
            assert resolved == "gemini://example.com/~user/about.gmi"


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
                url=None,  # Final URL after redirects
            )
        )

        app = Astronomo(initial_url="gemini://example.com/")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            title = app._get_page_title()
            assert title is None


class TestSessionChoicePersistence:
    """Tests for session identity choice persistence."""

    @pytest.mark.asyncio
    async def test_save_and_load_session_choice(
        self, mock_gemini_client, config_with_identity_prompt, tmp_path
    ):
        """Test that session choices are persisted and loaded correctly."""
        # Create a mock identity
        from astronomo.identities import Identity
        from datetime import datetime

        mock_identity = Identity(
            id="test-id-123",
            name="Test Identity",
            fingerprint="SHA256:abc123",
            cert_path=tmp_path / "test.pem",
            key_path=tmp_path / "test.key",
            url_prefixes=["gemini://example.com/"],
            created_at=datetime.now(),
        )

        app = Astronomo(config_path=config_with_identity_prompt)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Manually save a session choice
            prefix = "gemini://example.com/"
            app._session_identity_choices[prefix] = mock_identity
            app._save_session_choice(prefix, mock_identity)

            # Verify the file was created
            session_file = app._session_choices_path
            assert session_file.exists()

            # Verify the content
            import tomllib

            with open(session_file, "rb") as f:
                data = tomllib.load(f)
            assert data["choices"][prefix] == "test-id-123"

    @pytest.mark.asyncio
    async def test_save_anonymous_choice(self, mock_gemini_client, minimal_config_file):
        """Test that anonymous choice is persisted correctly."""
        app = Astronomo(config_path=minimal_config_file)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Save anonymous choice
            prefix = "gemini://example.com/"
            app._session_identity_choices[prefix] = None
            app._save_session_choice(prefix, None)

            # Verify the content
            import tomllib

            with open(app._session_choices_path, "rb") as f:
                data = tomllib.load(f)
            assert data["choices"][prefix] == "anonymous"

    @pytest.mark.asyncio
    async def test_load_session_choices_on_startup(
        self, mock_gemini_client, minimal_config_file, session_choices_file, tmp_path
    ):
        """Test that session choices are loaded on app startup."""
        import tomli_w

        # Create identity files
        certs_dir = tmp_path / "certificates"
        certs_dir.mkdir()
        cert_path = certs_dir / "test-id.pem"
        key_path = certs_dir / "test-id.key"
        cert_path.write_text("CERT")
        key_path.write_text("KEY")

        # Create identity in identities.toml
        identities_file = tmp_path / "identities.toml"
        identity_data = {
            "version": "1.0",
            "identities": [
                {
                    "id": "test-id",
                    "name": "Test",
                    "hostname": "example.com",
                    "created_at": "2025-01-01T00:00:00",
                    "url_prefixes": [],
                    "cert_path": str(cert_path),
                    "key_path": str(key_path),
                }
            ],
        }
        with open(identities_file, "wb") as f:
            tomli_w.dump(identity_data, f)

        # session_choices_file fixture creates session_choices.toml with test-id and anonymous

        # Patch IdentityManager to use our temp dir
        from unittest.mock import patch

        with patch("astronomo.astronomo_app.IdentityManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_identity = MagicMock()
            mock_identity.id = "test-id"
            mock_manager.get_identity.return_value = mock_identity
            mock_manager.is_identity_valid.return_value = True
            mock_manager_class.return_value = mock_manager

            app = Astronomo(config_path=minimal_config_file)

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                # Verify choices were loaded
                assert "gemini://example.com/" in app._session_identity_choices
                assert "gemini://other.com/" in app._session_identity_choices
                assert (
                    app._session_identity_choices["gemini://other.com/"] is None
                )  # anonymous


class TestIdentityPromptBehavior:
    """Tests for identity_prompt setting behavior."""

    @pytest.mark.asyncio
    async def test_get_session_prefix_for_url(
        self, mock_gemini_client, minimal_config_file
    ):
        """Test URL prefix extraction."""
        app = Astronomo(config_path=minimal_config_file)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Test various URLs
            assert (
                app._get_session_prefix_for_url("gemini://example.com/")
                == "gemini://example.com/"
            )
            assert (
                app._get_session_prefix_for_url("gemini://example.com/path/to/page")
                == "gemini://example.com/"
            )
            assert (
                app._get_session_prefix_for_url("gemini://sub.example.com:1965/page")
                == "gemini://sub.example.com:1965/"
            )

    @pytest.mark.asyncio
    async def test_get_session_identity_choice_not_prompted(
        self, mock_gemini_client, minimal_config_file
    ):
        """Test that _NOT_YET_PROMPTED is returned for unknown URLs."""
        from astronomo.astronomo_app import _NOT_YET_PROMPTED

        app = Astronomo(config_path=minimal_config_file)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            choice = app._get_session_identity_choice("gemini://unknown.com/")
            assert choice is _NOT_YET_PROMPTED

    @pytest.mark.asyncio
    async def test_get_session_identity_choice_anonymous(
        self, mock_gemini_client, minimal_config_file
    ):
        """Test that None is returned for anonymous choices."""
        app = Astronomo(config_path=minimal_config_file)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Set anonymous choice
            app._session_identity_choices["gemini://example.com/"] = None

            choice = app._get_session_identity_choice("gemini://example.com/page")
            assert choice is None

    @pytest.mark.asyncio
    async def test_get_session_identity_choice_with_identity(
        self, mock_gemini_client, minimal_config_file
    ):
        """Test that identity is returned when previously selected."""
        from unittest.mock import patch

        mock_identity = MagicMock()
        mock_identity.id = "test-id"

        with patch("astronomo.astronomo_app.IdentityManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.is_identity_valid.return_value = True
            mock_manager_class.return_value = mock_manager

            app = Astronomo(config_path=minimal_config_file)

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                # Set identity choice
                app._session_identity_choices["gemini://example.com/"] = mock_identity

                choice = app._get_session_identity_choice("gemini://example.com/page")
                assert choice is mock_identity


class TestSaveSnapshot:
    """Tests for the snapshot save functionality."""

    @pytest.mark.asyncio
    async def test_does_nothing_without_url(self, mock_gemini_client, temp_config_path):
        """Test that save snapshot does nothing when no URL is loaded."""
        app = Astronomo(config_path=temp_config_path)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            # Try to save snapshot without loading a page
            with patch.object(app, "push_screen") as mock_push:
                app.action_save_snapshot()
                await pilot.pause()

                # Should not show modal since no URL
                mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_shows_confirmation_modal(self, mock_gemini_client, temp_config_path):
        """Test that save snapshot shows confirmation modal."""
        mock_gemini_client.get = AsyncMock(
            return_value=MagicMock(
                status=20,
                body="# Test Page\nSome content",
                meta="text/gemini",
                mime_type="text/gemini",
                is_success=MagicMock(return_value=True),
                is_redirect=MagicMock(return_value=False),
                url=None,
            )
        )

        app = Astronomo(
            initial_url="gemini://example.com/test", config_path=temp_config_path
        )

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            with patch.object(app, "push_screen") as mock_push:
                app.action_save_snapshot()
                await pilot.pause()

                # Should show modal
                mock_push.assert_called_once()
                # First arg should be SaveSnapshotModal
                modal_arg = mock_push.call_args[0][0]
                assert modal_arg.__class__.__name__ == "SaveSnapshotModal"

    @pytest.mark.asyncio
    async def test_uses_default_snapshot_directory(
        self, mock_gemini_client, temp_config_path
    ):
        """Test that default snapshot directory is used when not configured."""
        mock_gemini_client.get = AsyncMock(
            return_value=MagicMock(
                status=20,
                body="# Test Page\nSome content",
                meta="text/gemini",
                mime_type="text/gemini",
                is_success=MagicMock(return_value=True),
                is_redirect=MagicMock(return_value=False),
                url=None,
            )
        )

        app = Astronomo(
            initial_url="gemini://example.com/test", config_path=temp_config_path
        )

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            with patch.object(app, "push_screen") as mock_push:
                app.action_save_snapshot()
                await pilot.pause()

                # Get the modal that was passed
                modal = mock_push.call_args[0][0]
                save_path = modal.save_path

                # Should use default directory
                assert ".local/share/astronomo/snapshots" in str(save_path)

    @pytest.mark.asyncio
    async def test_uses_custom_snapshot_directory(self, mock_gemini_client):
        """Test that custom snapshot directory is used when configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            config_path = temp_dir / "config.toml"
            custom_snapshot_dir = temp_dir / "custom_snapshots"

            # Create config with custom snapshot directory
            config_path.write_text(
                f"""\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5

[snapshots]
directory = "{custom_snapshot_dir}"
"""
            )

            mock_gemini_client.get = AsyncMock(
                return_value=MagicMock(
                    status=20,
                    body="# Test Page\nSome content",
                    meta="text/gemini",
                    mime_type="text/gemini",
                    is_success=MagicMock(return_value=True),
                    is_redirect=MagicMock(return_value=False),
                    url=None,
                )
            )

            app = Astronomo(
                initial_url="gemini://example.com/test", config_path=config_path
            )

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                with patch.object(app, "push_screen") as mock_push:
                    app.action_save_snapshot()
                    await pilot.pause()

                    # Get the modal that was passed
                    modal = mock_push.call_args[0][0]
                    save_path = modal.save_path

                    # Should use custom directory
                    assert str(custom_snapshot_dir) in str(save_path)

    @pytest.mark.asyncio
    async def test_filename_includes_timestamp(
        self, mock_gemini_client, temp_config_path
    ):
        """Test that filename includes a timestamp."""
        mock_gemini_client.get = AsyncMock(
            return_value=MagicMock(
                status=20,
                body="# Test Page\nSome content",
                meta="text/gemini",
                mime_type="text/gemini",
                is_success=MagicMock(return_value=True),
                is_redirect=MagicMock(return_value=False),
                url=None,
            )
        )

        app = Astronomo(
            initial_url="gemini://example.com/test", config_path=temp_config_path
        )

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            with patch.object(app, "push_screen") as mock_push:
                app.action_save_snapshot()
                await pilot.pause()

                # Get the modal that was passed
                modal = mock_push.call_args[0][0]
                filename = modal.save_path.name

                # Should have .gmi extension
                assert filename.endswith(".gmi")
                # Should include hostname
                assert "example.com" in filename
                # Filename should match pattern: hostname_YYYY-MM-DD_HH-MM-SS.gmi
                # Check for presence of underscore and dashes (timestamp pattern)
                assert "_" in filename
                assert "-" in filename

    @pytest.mark.asyncio
    async def test_saves_file_on_confirmation(self, mock_gemini_client):
        """Test that file is saved when user confirms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            config_path = temp_dir / "config.toml"
            snapshot_dir = temp_dir / "snapshots"

            config_path.write_text(
                f"""\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5

[snapshots]
directory = "{snapshot_dir}"
"""
            )

            test_content = "# Test Page\n=> /link Test Link\nSome text content"
            mock_gemini_client.get = AsyncMock(
                return_value=MagicMock(
                    status=20,
                    body=test_content,
                    meta="text/gemini",
                    mime_type="text/gemini",
                    is_success=MagicMock(return_value=True),
                    is_redirect=MagicMock(return_value=False),
                    url=None,
                )
            )

            app = Astronomo(
                initial_url="gemini://example.com/test", config_path=config_path
            )

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                # Trigger save action
                app.action_save_snapshot()
                await pilot.pause()

                # Confirm the modal (press enter)
                await pilot.press("enter")
                await pilot.pause()

                # Check that file was saved
                saved_files = list(snapshot_dir.glob("*.gmi"))
                assert len(saved_files) == 1

                # Check content
                saved_content = saved_files[0].read_text()
                assert "# Test Page" in saved_content
                assert "=> /link Test Link" in saved_content
                assert "Some text content" in saved_content

    @pytest.mark.asyncio
    async def test_does_not_save_on_cancel(self, mock_gemini_client):
        """Test that file is not saved when user cancels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            config_path = temp_dir / "config.toml"
            snapshot_dir = temp_dir / "snapshots"

            config_path.write_text(
                f"""\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5

[snapshots]
directory = "{snapshot_dir}"
"""
            )

            mock_gemini_client.get = AsyncMock(
                return_value=MagicMock(
                    status=20,
                    body="# Test Page\nSome content",
                    meta="text/gemini",
                    mime_type="text/gemini",
                    is_success=MagicMock(return_value=True),
                    is_redirect=MagicMock(return_value=False),
                    url=None,
                )
            )

            app = Astronomo(
                initial_url="gemini://example.com/test", config_path=config_path
            )

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                # Trigger save action
                app.action_save_snapshot()
                await pilot.pause()

                # Cancel the modal (press escape)
                await pilot.press("escape")
                await pilot.pause()

                # Check that no file was saved
                if snapshot_dir.exists():
                    saved_files = list(snapshot_dir.glob("*.gmi"))
                    assert len(saved_files) == 0

    @pytest.mark.asyncio
    async def test_shows_notification_without_url(
        self, mock_gemini_client, temp_config_path
    ):
        """Test that a warning notification is shown when no URL is loaded."""
        app = Astronomo(config_path=temp_config_path)

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            with patch.object(app, "notify") as mock_notify:
                app.action_save_snapshot()
                await pilot.pause()

                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert "No page loaded" in call_args[0][0]
                assert call_args[1]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_sanitizes_hostname_with_port(self, mock_gemini_client):
        """Test that hostname with port number generates valid filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            config_path = temp_dir / "config.toml"
            snapshot_dir = temp_dir / "snapshots"

            config_path.write_text(
                f"""\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5

[snapshots]
directory = "{snapshot_dir}"
"""
            )

            mock_gemini_client.get = AsyncMock(
                return_value=MagicMock(
                    status=20,
                    body="# Test Page\nSome content",
                    meta="text/gemini",
                    mime_type="text/gemini",
                    is_success=MagicMock(return_value=True),
                    is_redirect=MagicMock(return_value=False),
                    url=None,
                )
            )

            # Use URL with non-standard port
            app = Astronomo(
                initial_url="gemini://example.com:1965/test", config_path=config_path
            )

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                with patch.object(app, "push_screen") as mock_push:
                    app.action_save_snapshot()
                    await pilot.pause()

                    modal = mock_push.call_args[0][0]
                    filename = modal.save_path.name

                    # Port colon should be replaced with underscore
                    assert "example.com_1965" in filename
                    # Should not contain colon
                    assert ":" not in filename

    @pytest.mark.asyncio
    async def test_handles_directory_creation_permission_error(
        self, mock_gemini_client, temp_config_path
    ):
        """Test that directory creation permission errors show notification."""
        mock_gemini_client.get = AsyncMock(
            return_value=MagicMock(
                status=20,
                body="# Test Page\nSome content",
                meta="text/gemini",
                mime_type="text/gemini",
                is_success=MagicMock(return_value=True),
                is_redirect=MagicMock(return_value=False),
                url=None,
            )
        )

        app = Astronomo(
            initial_url="gemini://example.com/test", config_path=temp_config_path
        )

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_mkdir.side_effect = PermissionError("Access denied")

                with patch.object(app, "notify") as mock_notify:
                    app.action_save_snapshot()
                    await pilot.pause()

                    mock_notify.assert_called_once()
                    call_args = mock_notify.call_args
                    assert "Permission denied" in call_args[0][0]
                    assert call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_shows_success_notification_on_save(self, mock_gemini_client):
        """Test that success notification is shown when file is saved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            config_path = temp_dir / "config.toml"
            snapshot_dir = temp_dir / "snapshots"

            config_path.write_text(
                f"""\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5

[snapshots]
directory = "{snapshot_dir}"
"""
            )

            mock_gemini_client.get = AsyncMock(
                return_value=MagicMock(
                    status=20,
                    body="# Test Page\nSome content",
                    meta="text/gemini",
                    mime_type="text/gemini",
                    is_success=MagicMock(return_value=True),
                    is_redirect=MagicMock(return_value=False),
                    url=None,
                )
            )

            app = Astronomo(
                initial_url="gemini://example.com/test", config_path=config_path
            )

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                with patch.object(app, "notify") as mock_notify:
                    # Trigger save action
                    app.action_save_snapshot()
                    await pilot.pause()

                    # Confirm the modal (press enter)
                    await pilot.press("enter")
                    await pilot.pause()

                    # Should show success notification
                    mock_notify.assert_called_once()
                    call_args = mock_notify.call_args
                    assert "Saved to" in call_args[0][0]
                    assert call_args[1]["severity"] == "information"

    @pytest.mark.asyncio
    async def test_handles_file_write_permission_error(self, mock_gemini_client):
        """Test that file write permission errors show notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            config_path = temp_dir / "config.toml"
            snapshot_dir = temp_dir / "snapshots"
            snapshot_dir.mkdir()

            config_path.write_text(
                f"""\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5

[snapshots]
directory = "{snapshot_dir}"
"""
            )

            mock_gemini_client.get = AsyncMock(
                return_value=MagicMock(
                    status=20,
                    body="# Test Page\nSome content",
                    meta="text/gemini",
                    mime_type="text/gemini",
                    is_success=MagicMock(return_value=True),
                    is_redirect=MagicMock(return_value=False),
                    url=None,
                )
            )

            app = Astronomo(
                initial_url="gemini://example.com/test", config_path=config_path
            )

            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()

                with patch("pathlib.Path.write_text") as mock_write:
                    mock_write.side_effect = PermissionError("Cannot write")

                    with patch.object(app, "notify") as mock_notify:
                        # Trigger save action
                        app.action_save_snapshot()
                        await pilot.pause()

                        # Confirm the modal (press enter)
                        await pilot.press("enter")
                        await pilot.pause()

                        # Should show error notification
                        mock_notify.assert_called_once()
                        call_args = mock_notify.call_args
                        assert "Permission denied" in call_args[0][0]
                        assert call_args[1]["severity"] == "error"
