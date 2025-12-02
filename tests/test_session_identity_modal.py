"""Tests for the SessionIdentityModal widget."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App

from astronomo.identities import IdentityManager
from astronomo.widgets.session_identity_modal import (
    IdentityOption,
    SessionIdentityModal,
    SessionIdentityResult,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def identity_manager(temp_config_dir):
    """Create an IdentityManager with temporary storage."""
    return IdentityManager(config_dir=temp_config_dir)


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


class TestSessionIdentityModal:
    """Tests for the SessionIdentityModal widget."""

    @pytest.mark.asyncio
    async def test_modal_shows_anonymous_option(self, identity_manager):
        """Test that modal shows anonymous option."""
        identity = identity_manager.create_identity(
            name="Test Identity", hostname="example.com"
        )
        identity_manager.add_url_prefix(identity.id, "gemini://example.com/")

        matching = identity_manager.get_all_identities_for_url(
            "gemini://example.com/page"
        )
        modal = SessionIdentityModal(
            manager=identity_manager,
            url="gemini://example.com/page",
            matching_identities=matching,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have anonymous option
            anonymous_option = modal.query_one("#option-anonymous", IdentityOption)
            assert anonymous_option is not None
            assert anonymous_option.is_anonymous is True

    @pytest.mark.asyncio
    async def test_modal_shows_matching_identities(self, identity_manager):
        """Test that modal shows all matching identities."""
        identity1 = identity_manager.create_identity(
            name="Identity 1", hostname="example.com"
        )
        identity2 = identity_manager.create_identity(
            name="Identity 2", hostname="example.com"
        )
        identity_manager.add_url_prefix(identity1.id, "gemini://example.com/")
        identity_manager.add_url_prefix(identity2.id, "gemini://example.com/")

        matching = identity_manager.get_all_identities_for_url(
            "gemini://example.com/page"
        )
        modal = SessionIdentityModal(
            manager=identity_manager,
            url="gemini://example.com/page",
            matching_identities=matching,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have 3 options: anonymous + 2 identities
            options = modal.query(IdentityOption)
            assert len(list(options)) == 3

    @pytest.mark.asyncio
    async def test_modal_preselects_first_identity(self, identity_manager):
        """Test that modal pre-selects the first matching identity."""
        identity = identity_manager.create_identity(
            name="Test Identity", hostname="example.com"
        )
        identity_manager.add_url_prefix(identity.id, "gemini://example.com/")

        matching = identity_manager.get_all_identities_for_url(
            "gemini://example.com/page"
        )
        modal = SessionIdentityModal(
            manager=identity_manager,
            url="gemini://example.com/page",
            matching_identities=matching,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # First identity should be selected (not anonymous)
            assert modal._selected_identity is not None
            assert modal._selected_identity.id == identity.id
            assert modal._is_anonymous_selected is False

    @pytest.mark.asyncio
    async def test_modal_cancel_returns_cancelled_result(self, identity_manager):
        """Test that escape returns cancelled result."""
        identity = identity_manager.create_identity(
            name="Test Identity", hostname="example.com"
        )
        identity_manager.add_url_prefix(identity.id, "gemini://example.com/")

        matching = identity_manager.get_all_identities_for_url(
            "gemini://example.com/page"
        )
        modal = SessionIdentityModal(
            manager=identity_manager,
            url="gemini://example.com/page",
            matching_identities=matching,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        assert app._modal_result is not None
        assert app._modal_result.cancelled is True

    @pytest.mark.asyncio
    async def test_modal_enter_uses_selected_identity(self, identity_manager):
        """Test that enter uses the selected identity."""
        identity = identity_manager.create_identity(
            name="Test Identity", hostname="example.com"
        )
        identity_manager.add_url_prefix(identity.id, "gemini://example.com/")

        matching = identity_manager.get_all_identities_for_url(
            "gemini://example.com/page"
        )
        modal = SessionIdentityModal(
            manager=identity_manager,
            url="gemini://example.com/page",
            matching_identities=matching,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

        assert app._modal_result is not None
        assert app._modal_result.cancelled is False
        assert app._modal_result.identity is not None
        assert app._modal_result.identity.id == identity.id


class TestSessionIdentityResult:
    """Tests for the SessionIdentityResult dataclass."""

    def test_identity_result(self, identity_manager, temp_config_dir):
        """Test creating result with identity."""
        identity = identity_manager.create_identity(name="Test", hostname="example.com")
        result = SessionIdentityResult(identity=identity)

        assert result.identity is not None
        assert result.identity.id == identity.id
        assert result.cancelled is False

    def test_anonymous_result(self):
        """Test creating result for anonymous selection."""
        result = SessionIdentityResult(identity=None)

        assert result.identity is None
        assert result.cancelled is False

    def test_cancelled_result(self):
        """Test creating cancelled result."""
        result = SessionIdentityResult(identity=None, cancelled=True)

        assert result.identity is None
        assert result.cancelled is True
