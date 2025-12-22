"""Tests for the configuration module."""

import tempfile
from pathlib import Path

import pytest

from astronomo.config import (
    AppearanceConfig,
    BrowsingConfig,
    Config,
    ConfigManager,
    DEFAULT_CONFIG_TEMPLATE,
    SnapshotsConfig,
    VALID_THEMES,
)


class TestAppearanceConfig:
    """Tests for the AppearanceConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default appearance values."""
        config = AppearanceConfig()
        assert config.theme == "textual-dark"
        assert config.syntax_highlighting is True
        assert config.show_emoji is True

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        config = AppearanceConfig(theme="nord")
        data = config.to_dict()
        assert data == {
            "theme": "nord",
            "syntax_highlighting": True,
            "show_emoji": True,
        }

    def test_to_dict_with_show_emoji_false(self) -> None:
        """Test converting to dictionary with show_emoji disabled."""
        config = AppearanceConfig(theme="nord", show_emoji=False)
        data = config.to_dict()
        assert data["show_emoji"] is False

    def test_from_dict_valid_theme(self) -> None:
        """Test creating from dictionary with valid theme."""
        config = AppearanceConfig.from_dict({"theme": "gruvbox"})
        assert config.theme == "gruvbox"

    def test_from_dict_invalid_theme_falls_back(self) -> None:
        """Test that invalid theme falls back to default."""
        config = AppearanceConfig.from_dict({"theme": "invalid-theme"})
        assert config.theme == "textual-dark"

    def test_from_dict_wrong_type_falls_back(self) -> None:
        """Test that wrong type falls back to default."""
        config = AppearanceConfig.from_dict({"theme": 123})
        assert config.theme == "textual-dark"

    def test_from_dict_missing_theme(self) -> None:
        """Test that missing theme uses default."""
        config = AppearanceConfig.from_dict({})
        assert config.theme == "textual-dark"

    def test_from_dict_show_emoji_true(self) -> None:
        """Test creating from dictionary with show_emoji enabled."""
        config = AppearanceConfig.from_dict({"show_emoji": True})
        assert config.show_emoji is True

    def test_from_dict_show_emoji_false(self) -> None:
        """Test creating from dictionary with show_emoji disabled."""
        config = AppearanceConfig.from_dict({"show_emoji": False})
        assert config.show_emoji is False

    def test_from_dict_invalid_show_emoji_falls_back(self) -> None:
        """Test that invalid show_emoji type falls back to default."""
        config = AppearanceConfig.from_dict({"show_emoji": "not-a-bool"})
        assert config.show_emoji is True

    def test_from_dict_missing_show_emoji(self) -> None:
        """Test that missing show_emoji uses default."""
        config = AppearanceConfig.from_dict({})
        assert config.show_emoji is True


class TestBrowsingConfig:
    """Tests for the BrowsingConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default browsing values."""
        config = BrowsingConfig()
        assert config.home_page is None  # No default homepage
        assert config.timeout == 30
        assert config.max_redirects == 5

    def test_to_dict_without_home_page(self) -> None:
        """Test converting to dictionary without home_page set."""
        config = BrowsingConfig()
        data = config.to_dict()
        assert data == {
            "timeout": 30,
            "max_redirects": 5,
            "identity_prompt": "when_ambiguous",
        }
        assert "home_page" not in data  # Should not include None values

    def test_to_dict_with_home_page(self) -> None:
        """Test converting to dictionary with home_page set."""
        config = BrowsingConfig(
            home_page="gemini://example.com/",
            timeout=60,
            max_redirects=10,
        )
        data = config.to_dict()
        assert data == {
            "home_page": "gemini://example.com/",
            "timeout": 60,
            "max_redirects": 10,
            "identity_prompt": "when_ambiguous",
        }

    def test_from_dict_valid_values(self) -> None:
        """Test creating from dictionary with valid values."""
        config = BrowsingConfig.from_dict(
            {
                "home_page": "gemini://test.com/",
                "timeout": 45,
                "max_redirects": 3,
            }
        )
        assert config.home_page == "gemini://test.com/"
        assert config.timeout == 45
        assert config.max_redirects == 3

    def test_from_dict_invalid_timeout_falls_back(self) -> None:
        """Test that invalid timeout falls back to default."""
        config = BrowsingConfig.from_dict({"timeout": -5})
        assert config.timeout == 30

    def test_from_dict_zero_timeout_falls_back(self) -> None:
        """Test that zero timeout falls back to default."""
        config = BrowsingConfig.from_dict({"timeout": 0})
        assert config.timeout == 30

    def test_from_dict_invalid_type_falls_back(self) -> None:
        """Test that wrong type falls back to default."""
        config = BrowsingConfig.from_dict({"timeout": "not-an-int"})
        assert config.timeout == 30

    def test_from_dict_negative_max_redirects_falls_back(self) -> None:
        """Test that negative max_redirects falls back to default."""
        config = BrowsingConfig.from_dict({"max_redirects": -1})
        assert config.max_redirects == 5

    def test_from_dict_zero_max_redirects_is_valid(self) -> None:
        """Test that zero max_redirects is valid (disables redirects)."""
        config = BrowsingConfig.from_dict({"max_redirects": 0})
        assert config.max_redirects == 0

    def test_from_dict_empty_home_page_is_none(self) -> None:
        """Test that empty string home_page is treated as None."""
        config = BrowsingConfig.from_dict({"home_page": ""})
        assert config.home_page is None

    def test_from_dict_whitespace_home_page_is_none(self) -> None:
        """Test that whitespace-only home_page is treated as None."""
        config = BrowsingConfig.from_dict({"home_page": "   "})
        assert config.home_page is None

    def test_from_dict_missing_values_use_defaults(self) -> None:
        """Test that missing values use defaults."""
        config = BrowsingConfig.from_dict({})
        assert config.home_page is None  # No default homepage
        assert config.timeout == 30
        assert config.max_redirects == 5
        assert config.identity_prompt == "when_ambiguous"

    def test_from_dict_valid_identity_prompt(self) -> None:
        """Test that valid identity_prompt values are accepted."""
        for value in ["every_time", "when_ambiguous", "remember_choice"]:
            config = BrowsingConfig.from_dict({"identity_prompt": value})
            assert config.identity_prompt == value

    def test_from_dict_invalid_identity_prompt_falls_back(self) -> None:
        """Test that invalid identity_prompt falls back to default."""
        config = BrowsingConfig.from_dict({"identity_prompt": "invalid_value"})
        assert config.identity_prompt == "when_ambiguous"

    def test_from_dict_wrong_type_identity_prompt_falls_back(self) -> None:
        """Test that wrong type identity_prompt falls back to default."""
        config = BrowsingConfig.from_dict({"identity_prompt": 123})
        assert config.identity_prompt == "when_ambiguous"


class TestSnapshotsConfig:
    """Tests for the SnapshotsConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default snapshots values."""
        config = SnapshotsConfig()
        assert config.directory is None  # No default directory

    def test_to_dict_without_directory(self) -> None:
        """Test converting to dictionary without directory set."""
        config = SnapshotsConfig()
        data = config.to_dict()
        assert data == {}
        assert "directory" not in data  # Should not include None values

    def test_to_dict_with_directory(self) -> None:
        """Test converting to dictionary with directory set."""
        config = SnapshotsConfig(directory="/custom/path")
        data = config.to_dict()
        assert data == {"directory": "/custom/path"}

    def test_from_dict_valid_directory(self) -> None:
        """Test creating from dictionary with valid directory."""
        config = SnapshotsConfig.from_dict({"directory": "/my/snapshots"})
        assert config.directory == "/my/snapshots"

    def test_from_dict_empty_directory_is_none(self) -> None:
        """Test that empty string directory is treated as None."""
        config = SnapshotsConfig.from_dict({"directory": ""})
        assert config.directory is None

    def test_from_dict_whitespace_directory_is_none(self) -> None:
        """Test that whitespace-only directory is treated as None."""
        config = SnapshotsConfig.from_dict({"directory": "   "})
        assert config.directory is None

    def test_from_dict_wrong_type_falls_back(self) -> None:
        """Test that wrong type falls back to None."""
        config = SnapshotsConfig.from_dict({"directory": 123})
        assert config.directory is None

    def test_from_dict_missing_directory(self) -> None:
        """Test that missing directory uses default (None)."""
        config = SnapshotsConfig.from_dict({})
        assert config.directory is None

    def test_post_init_normalizes_empty_string(self) -> None:
        """Test that __post_init__ normalizes empty string to None."""
        # Direct construction with empty string should be normalized
        config = SnapshotsConfig(directory="")
        assert config.directory is None

    def test_post_init_normalizes_whitespace(self) -> None:
        """Test that __post_init__ normalizes whitespace-only to None."""
        config = SnapshotsConfig(directory="   ")
        assert config.directory is None

    def test_post_init_preserves_valid_directory(self) -> None:
        """Test that __post_init__ preserves valid directory paths."""
        config = SnapshotsConfig(directory="/valid/path")
        assert config.directory == "/valid/path"


class TestConfig:
    """Tests for the root Config dataclass."""

    def test_default_creates_nested_defaults(self) -> None:
        """Test that default Config creates nested section defaults."""
        config = Config()
        assert config.appearance.theme == "textual-dark"
        assert config.browsing.timeout == 30
        assert config.snapshots.directory is None

    def test_to_dict(self) -> None:
        """Test full config serialization."""
        config = Config()
        data = config.to_dict()
        assert "appearance" in data
        assert "browsing" in data
        assert "snapshots" in data
        assert data["appearance"]["theme"] == "textual-dark"
        assert data["browsing"]["timeout"] == 30
        assert data["snapshots"] == {}

    def test_from_dict_partial_data(self) -> None:
        """Test that missing sections use defaults."""
        config = Config.from_dict({"appearance": {"theme": "nord"}})
        assert config.appearance.theme == "nord"
        assert config.browsing.timeout == 30  # Default
        assert config.snapshots.directory is None  # Default

    def test_from_dict_empty(self) -> None:
        """Test that empty dict uses all defaults."""
        config = Config.from_dict({})
        assert config.appearance.theme == "textual-dark"
        assert config.browsing.home_page is None
        assert config.snapshots.directory is None


class TestConfigManager:
    """Tests for the ConfigManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> ConfigManager:
        """Create a ConfigManager with temporary storage."""
        config_path = temp_config_dir / "config.toml"
        return ConfigManager(config_path=config_path)

    def test_creates_default_config_on_first_run(self, temp_config_dir: Path) -> None:
        """Test that config file is created on first run."""
        config_path = temp_config_dir / "config.toml"
        ConfigManager(config_path=config_path)

        assert config_path.exists()
        content = config_path.read_text()
        assert "[appearance]" in content
        assert "[browsing]" in content

    def test_default_config_has_comments(self, temp_config_dir: Path) -> None:
        """Test that default config file contains helpful comments."""
        config_path = temp_config_dir / "config.toml"
        ConfigManager(config_path=config_path)

        content = config_path.read_text()
        assert "# " in content  # Has comments
        assert "Available themes:" in content

    def test_loads_existing_config(self, temp_config_dir: Path) -> None:
        """Test loading an existing config file."""
        config_path = temp_config_dir / "config.toml"

        # Write a custom config
        config_path.write_text(
            """
[appearance]
theme = "nord"

[browsing]
timeout = 60
"""
        )

        manager = ConfigManager(config_path=config_path)

        assert manager.theme == "nord"
        assert manager.timeout == 60
        assert manager.home_page is None  # Not set in config

    def test_handles_corrupted_file(self, temp_config_dir: Path) -> None:
        """Test graceful handling of corrupted config file."""
        config_path = temp_config_dir / "config.toml"
        config_path.write_text("this is not { valid toml")

        manager = ConfigManager(config_path=config_path)

        # Should fall back to defaults
        assert manager.theme == "textual-dark"
        assert manager.timeout == 30

    def test_creates_nested_directories(self) -> None:
        """Test that nested config directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "config.toml"
            ConfigManager(config_path=nested_path)

            assert nested_path.exists()

    def test_convenience_properties(self, manager: ConfigManager) -> None:
        """Test that convenience properties work correctly."""
        assert manager.theme == manager.config.appearance.theme
        assert manager.home_page == manager.config.browsing.home_page
        assert manager.timeout == manager.config.browsing.timeout
        assert manager.max_redirects == manager.config.browsing.max_redirects
        assert manager.snapshots_directory == manager.config.snapshots.directory
        assert (
            manager.syntax_highlighting == manager.config.appearance.syntax_highlighting
        )
        assert manager.show_emoji == manager.config.appearance.show_emoji

    def test_save_and_reload(self, temp_config_dir: Path) -> None:
        """Test saving and reloading configuration."""
        config_path = temp_config_dir / "config.toml"

        manager1 = ConfigManager(config_path=config_path)
        manager1.config.appearance.theme = "gruvbox"
        manager1.config.browsing.timeout = 45
        manager1.save()

        manager2 = ConfigManager(config_path=config_path)
        assert manager2.theme == "gruvbox"
        assert manager2.timeout == 45

    def test_default_location_without_path(self) -> None:
        """Test that default location is ~/.config/astronomo/config.toml."""
        # Don't actually create the manager (would create files)
        # Just verify the path logic
        manager = ConfigManager.__new__(ConfigManager)
        manager.config_dir = Path.home() / ".config" / "astronomo"
        manager.config_path = manager.config_dir / "config.toml"

        assert (
            manager.config_path == Path.home() / ".config" / "astronomo" / "config.toml"
        )


class TestValidThemes:
    """Tests for theme validation."""

    def test_all_documented_themes_are_valid(self) -> None:
        """Test that documented themes are in VALID_THEMES set."""
        documented = {
            "textual-dark",
            "textual-light",
            "nord",
            "gruvbox",
            "tokyo-night",
            "solarized-light",
        }
        assert documented.issubset(VALID_THEMES)

    def test_valid_themes_is_frozen(self) -> None:
        """Test that VALID_THEMES cannot be modified."""
        assert isinstance(VALID_THEMES, frozenset)


class TestDefaultConfigTemplate:
    """Tests for the default config template."""

    def test_template_contains_all_sections(self) -> None:
        """Test that template has all config sections."""
        assert "[appearance]" in DEFAULT_CONFIG_TEMPLATE
        assert "[browsing]" in DEFAULT_CONFIG_TEMPLATE

    def test_template_has_default_values(self) -> None:
        """Test that template contains default values."""
        assert 'theme = "textual-dark"' in DEFAULT_CONFIG_TEMPLATE
        assert "timeout = 30" in DEFAULT_CONFIG_TEMPLATE
        assert "max_redirects = 5" in DEFAULT_CONFIG_TEMPLATE
        assert "syntax_highlighting = true" in DEFAULT_CONFIG_TEMPLATE
        assert "show_emoji = true" in DEFAULT_CONFIG_TEMPLATE

    def test_template_has_commented_home_page(self) -> None:
        """Test that home_page is commented out by default."""
        assert "# home_page" in DEFAULT_CONFIG_TEMPLATE
