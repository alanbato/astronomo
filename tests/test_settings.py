"""Tests for the settings screen and settings panels."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult

from astronomo.config import ConfigManager
from astronomo.identities import IdentityManager
from astronomo.widgets.settings import AppearanceSettings, BrowsingSettings
from astronomo.widgets.settings.certificates import CertificatesSettings


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a ConfigManager with temporary storage."""
    config_path = temp_config_dir / "config.toml"
    return ConfigManager(config_path=config_path)


@pytest.fixture
def identity_manager(temp_config_dir):
    """Create an IdentityManager with temporary storage."""
    return IdentityManager(config_dir=temp_config_dir)


class WidgetTestApp(App):
    """Minimal app for testing widgets."""

    def __init__(self, widget):
        super().__init__()
        self._test_widget = widget

    def compose(self) -> ComposeResult:
        yield self._test_widget


class TestAppearanceSettings:
    """Tests for the AppearanceSettings widget."""

    @pytest.mark.asyncio
    async def test_appearance_settings_compose(self, config_manager):
        """Test that appearance settings compose without error."""
        widget = AppearanceSettings(config_manager)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have theme setting row
            assert widget.query("SettingRow")

    @pytest.mark.asyncio
    async def test_get_value_returns_theme(self, config_manager):
        """Test that _get_value returns the current theme."""
        widget = AppearanceSettings(config_manager)

        value = widget._get_value("appearance.theme")
        assert value == "textual-dark"  # Default theme

    @pytest.mark.asyncio
    async def test_get_value_returns_syntax_highlighting(self, config_manager):
        """Test that _get_value returns syntax highlighting setting."""
        widget = AppearanceSettings(config_manager)

        value = widget._get_value("appearance.syntax_highlighting")
        assert value is True  # Default is enabled


class TestBrowsingSettings:
    """Tests for the BrowsingSettings widget."""

    @pytest.mark.asyncio
    async def test_browsing_settings_compose(self, config_manager):
        """Test that browsing settings compose without error."""
        widget = BrowsingSettings(config_manager)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have setting rows
            assert widget.query("SettingRow")

    @pytest.mark.asyncio
    async def test_get_value_returns_timeout(self, config_manager):
        """Test that _get_value returns the current timeout."""
        widget = BrowsingSettings(config_manager)

        value = widget._get_value("browsing.timeout")
        assert value == 30  # Default timeout

    @pytest.mark.asyncio
    async def test_get_value_returns_max_redirects(self, config_manager):
        """Test that _get_value returns max redirects."""
        widget = BrowsingSettings(config_manager)

        value = widget._get_value("browsing.max_redirects")
        assert value == 5  # Default

    @pytest.mark.asyncio
    async def test_get_value_returns_home_page(self, config_manager):
        """Test that _get_value returns home page."""
        widget = BrowsingSettings(config_manager)

        value = widget._get_value("browsing.home_page")
        assert value is None  # No default home page

    @pytest.mark.asyncio
    async def test_handle_change_updates_timeout(self, config_manager):
        """Test that changing timeout updates config."""
        widget = BrowsingSettings(config_manager)

        widget._handle_change("browsing.timeout", 60)

        assert config_manager.timeout == 60

    @pytest.mark.asyncio
    async def test_handle_change_rejects_invalid_timeout(self, config_manager):
        """Test that invalid timeout is not saved."""
        widget = BrowsingSettings(config_manager)

        widget._handle_change("browsing.timeout", -5)

        # Should remain at default
        assert config_manager.timeout == 30

    @pytest.mark.asyncio
    async def test_handle_change_updates_max_redirects(self, config_manager):
        """Test that changing max_redirects updates config."""
        widget = BrowsingSettings(config_manager)

        widget._handle_change("browsing.max_redirects", 10)

        assert config_manager.max_redirects == 10

    @pytest.mark.asyncio
    async def test_handle_change_updates_home_page(self, config_manager):
        """Test that changing home page updates config."""
        widget = BrowsingSettings(config_manager)

        widget._handle_change("browsing.home_page", "gemini://example.com/")

        assert config_manager.home_page == "gemini://example.com/"

    @pytest.mark.asyncio
    async def test_handle_change_whitespace_home_page_becomes_empty(
        self, config_manager
    ):
        """Test that whitespace home page becomes empty string."""
        widget = BrowsingSettings(config_manager)

        widget._handle_change("browsing.home_page", "  ")

        # Whitespace is stripped to empty string
        assert config_manager.home_page == ""


class TestCertificatesSettings:
    """Tests for the CertificatesSettings widget."""

    @pytest.mark.asyncio
    async def test_certificates_settings_compose(self, identity_manager):
        """Test that certificates settings compose without error."""
        widget = CertificatesSettings(identity_manager)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            from textual.widgets import Button

            await pilot.pause()
            # Should have create button
            create_btn = widget.query_one("#create-identity-btn", Button)
            assert create_btn is not None

    @pytest.mark.asyncio
    async def test_empty_state_message(self, identity_manager):
        """Test that empty state shows appropriate message."""
        widget = CertificatesSettings(identity_manager)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should show empty state message
            empty_labels = widget.query(".empty-state")
            assert len(empty_labels) == 1

    @pytest.mark.asyncio
    async def test_shows_identity_list_items(self, identity_manager):
        """Test that identity items are displayed."""
        # Create some identities
        identity_manager.create_identity("Test Identity 1", "example.com")
        identity_manager.create_identity("Test Identity 2", "other.com")

        widget = CertificatesSettings(identity_manager)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            from astronomo.widgets.settings.certificates import IdentityListItem

            await pilot.pause()
            # Should have identity list items
            items = widget.query(IdentityListItem)
            assert len(items) == 2

    @pytest.mark.asyncio
    async def test_compose_identity_list_returns_items(self, identity_manager):
        """Test that _compose_identity_list yields identity items."""
        identity_manager.create_identity("Test", "test.com")

        widget = CertificatesSettings(identity_manager)

        items = list(widget._compose_identity_list())
        # Should have one IdentityListItem
        from astronomo.widgets.settings.certificates import IdentityListItem

        assert len(items) == 1
        assert isinstance(items[0], IdentityListItem)


class TestIdentityListItem:
    """Tests for the IdentityListItem widget."""

    @pytest.mark.asyncio
    async def test_displays_identity_name(self, identity_manager):
        """Test that identity name is displayed."""
        identity = identity_manager.create_identity("My Test Identity", "test.com")

        from astronomo.widgets.settings.certificates import IdentityListItem

        widget = IdentityListItem(identity)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Should have the identity name
            name_labels = list(widget.query(".identity-name"))
            assert len(name_labels) == 1
            # Access the label's rendered text
            label_text = str(name_labels[0].render())
            assert "My Test Identity" in label_text

    @pytest.mark.asyncio
    async def test_displays_fingerprint(self, identity_manager):
        """Test that fingerprint is displayed (truncated)."""
        identity = identity_manager.create_identity("Test", "test.com")

        from astronomo.widgets.settings.certificates import IdentityListItem

        widget = IdentityListItem(identity)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            await pilot.pause()
            info_labels = list(widget.query(".identity-info"))
            # One of them should contain "Fingerprint"
            has_fingerprint = any(
                "Fingerprint" in str(label.render()) for label in info_labels
            )
            assert has_fingerprint

    @pytest.mark.asyncio
    async def test_has_action_buttons(self, identity_manager):
        """Test that edit, URLs, and delete buttons exist."""
        identity = identity_manager.create_identity("Test", "test.com")

        from astronomo.widgets.settings.certificates import IdentityListItem

        widget = IdentityListItem(identity)
        app = WidgetTestApp(widget)

        async with app.run_test() as pilot:
            from textual.widgets import Button

            await pilot.pause()
            buttons = widget.query(Button)
            button_ids = [b.id for b in buttons]

            assert any("edit-" in bid for bid in button_ids if bid)
            assert any("urls-" in bid for bid in button_ids if bid)
            assert any("delete-" in bid for bid in button_ids if bid)

    @pytest.mark.asyncio
    async def test_format_expiration_unknown(self, identity_manager):
        """Test expiration formatting when expires_at is None."""
        identity = identity_manager.create_identity("Test", "test.com")
        identity.expires_at = None  # Force None for test

        from astronomo.widgets.settings.certificates import IdentityListItem

        widget = IdentityListItem(identity)

        text, css_class = widget._format_expiration()
        assert "Unknown" in text
        assert css_class == "identity-info"
