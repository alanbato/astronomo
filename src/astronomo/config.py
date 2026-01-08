"""Configuration management for Astronomo.

This module provides configuration storage with TOML persistence
and sensible defaults.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
    from typing import Self
else:
    import tomli as tomllib
    from typing_extensions import Self

# Available Textual themes (built-in)
VALID_THEMES = frozenset(
    {
        "textual-dark",
        "textual-light",
        "textual-ansi",
        "nord",
        "gruvbox",
        "tokyo-night",
        "monokai",
        "dracula",
        "catppuccin-mocha",
        "solarized-light",
    }
)

# Valid identity prompt behaviors
VALID_IDENTITY_PROMPTS = frozenset(
    {
        "every_time",
        "when_ambiguous",
        "remember_choice",
    }
)

# Default config template with comments (used for first-run creation)
DEFAULT_CONFIG_TEMPLATE = """\
# Astronomo Configuration
# This file is auto-generated on first run.
# Edit to customize your Astronomo experience.

[appearance]
# Theme for the application UI
# Available themes: textual-dark, textual-light, textual-ansi, nord,
#                   gruvbox, tokyo-night, monokai, dracula,
#                   catppuccin-mocha, solarized-light
theme = "textual-dark"

# Enable syntax highlighting in preformatted code blocks
# Uses language hints from alt text (e.g., ```python) or auto-detection
syntax_highlighting = true

# Show emoji characters (off displays text descriptions like [smile])
show_emoji = true

# Maximum width for text content in characters (0 to disable, minimum 40)
# Preformatted blocks and code are always shown at full width
max_content_width = 80

# Show images inline (requires chafapy optional dependency)
show_images = false

# Image rendering quality (low, medium, or high)
image_quality = "medium"

[browsing]
# Default home page when launching without a URL argument
# Uncomment and set to your preferred start page:
# home_page = "gemini://geminiprotocol.net/"

# Request timeout in seconds
timeout = 30

# Maximum number of redirects to follow
max_redirects = 5

# When to show identity selection prompt for sites with configured identities
# Options:
#   every_time     - Always show the identity selection modal
#   when_ambiguous - Only prompt when multiple identities match; auto-select if one
#   remember_choice - Reuse previous choice without prompting (persisted to disk)
identity_prompt = "when_ambiguous"

[snapshots]
# Directory where page snapshots are saved (Ctrl+S)
# Default: ~/.local/share/astronomo/snapshots
# Uncomment to use a custom directory:
# directory = "/path/to/custom/snapshots"
"""


@dataclass
class AppearanceConfig:
    """Appearance settings.

    Attributes:
        theme: Textual theme name (e.g., "textual-dark", "nord", "gruvbox")
        syntax_highlighting: Enable syntax highlighting in preformatted blocks
        show_emoji: Display emoji characters (False shows text descriptions)
        max_content_width: Maximum width for text content (0 to disable, minimum 40)
        show_images: Display images inline (requires chafapy optional dependency)
        image_quality: Image rendering quality ("low", "medium", or "high")
    """

    theme: str = "textual-dark"
    syntax_highlighting: bool = True
    show_emoji: bool = True
    max_content_width: int = 80
    show_images: bool = False
    image_quality: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        return {
            "theme": self.theme,
            "syntax_highlighting": self.syntax_highlighting,
            "show_emoji": self.show_emoji,
            "max_content_width": self.max_content_width,
            "show_images": self.show_images,
            "image_quality": self.image_quality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create from dictionary with validation and fallback to defaults."""
        defaults = cls()
        theme = data.get("theme", defaults.theme)
        # Validate theme - fall back to default if invalid
        if not isinstance(theme, str) or theme not in VALID_THEMES:
            theme = defaults.theme

        syntax_highlighting = data.get(
            "syntax_highlighting", defaults.syntax_highlighting
        )
        if not isinstance(syntax_highlighting, bool):
            syntax_highlighting = defaults.syntax_highlighting

        show_emoji = data.get("show_emoji", defaults.show_emoji)
        if not isinstance(show_emoji, bool):
            show_emoji = defaults.show_emoji

        max_content_width = data.get("max_content_width", defaults.max_content_width)
        if (
            not isinstance(max_content_width, int)
            or max_content_width < 0
            or (max_content_width > 0 and max_content_width < 40)
        ):
            max_content_width = defaults.max_content_width

        show_images = data.get("show_images", defaults.show_images)
        if not isinstance(show_images, bool):
            show_images = defaults.show_images

        image_quality = data.get("image_quality", defaults.image_quality)
        if not isinstance(image_quality, str) or image_quality not in (
            "low",
            "medium",
            "high",
        ):
            image_quality = defaults.image_quality

        return cls(
            theme=theme,
            syntax_highlighting=syntax_highlighting,
            show_emoji=show_emoji,
            max_content_width=max_content_width,
            show_images=show_images,
            image_quality=image_quality,
        )


@dataclass
class BrowsingConfig:
    """Browsing behavior settings.

    Attributes:
        home_page: Default home page URL (None if not set)
        timeout: Request timeout in seconds
        max_redirects: Maximum number of redirects to follow
        identity_prompt: When to show identity selection modal
    """

    home_page: str | None = None
    timeout: int = 30
    max_redirects: int = 5
    identity_prompt: str = "when_ambiguous"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        data: dict[str, Any] = {
            "timeout": self.timeout,
            "max_redirects": self.max_redirects,
            "identity_prompt": self.identity_prompt,
        }
        if self.home_page is not None:
            data["home_page"] = self.home_page
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create from dictionary with validation and fallback to defaults."""
        defaults = cls()

        home_page = data.get("home_page")
        # Empty string or non-string treated as None (not set)
        if not isinstance(home_page, str) or not home_page.strip():
            home_page = None

        timeout = data.get("timeout", defaults.timeout)
        if not isinstance(timeout, int) or timeout <= 0:
            timeout = defaults.timeout

        max_redirects = data.get("max_redirects", defaults.max_redirects)
        if not isinstance(max_redirects, int) or max_redirects < 0:
            max_redirects = defaults.max_redirects

        identity_prompt = data.get("identity_prompt", defaults.identity_prompt)
        if (
            not isinstance(identity_prompt, str)
            or identity_prompt not in VALID_IDENTITY_PROMPTS
        ):
            identity_prompt = defaults.identity_prompt

        return cls(
            home_page=home_page,
            timeout=timeout,
            max_redirects=max_redirects,
            identity_prompt=identity_prompt,
        )


@dataclass
class SnapshotsConfig:
    """Snapshot settings.

    Attributes:
        directory: Directory where page snapshots are saved.
                   Must be a non-empty string or None for default.
                   Empty strings and whitespace-only strings are normalized to None.
                   The default location is ~/.local/share/astronomo/snapshots
    """

    directory: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize directory after construction."""
        if self.directory is not None:
            if not isinstance(self.directory, str) or not self.directory.strip():
                self.directory = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        data: dict[str, Any] = {}
        if self.directory is not None:
            data["directory"] = self.directory
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create from dictionary with validation and fallback to defaults."""
        directory = data.get("directory")
        # Empty string or non-string treated as None (not set)
        if not isinstance(directory, str) or not directory.strip():
            directory = None

        return cls(directory=directory)


@dataclass
class Config:
    """Root configuration container.

    Attributes:
        appearance: Visual appearance settings
        browsing: Browsing behavior settings
        snapshots: Snapshot settings
    """

    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)
    browsing: BrowsingConfig = field(default_factory=BrowsingConfig)
    snapshots: SnapshotsConfig = field(default_factory=SnapshotsConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        return {
            "appearance": self.appearance.to_dict(),
            "browsing": self.browsing.to_dict(),
            "snapshots": self.snapshots.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create from dictionary with fallback to defaults for missing sections."""
        return cls(
            appearance=AppearanceConfig.from_dict(data.get("appearance", {})),
            browsing=BrowsingConfig.from_dict(data.get("browsing", {})),
            snapshots=SnapshotsConfig.from_dict(data.get("snapshots", {})),
        )


class ConfigManager:
    """Manages application configuration with TOML persistence.

    Provides loading and saving of configuration with automatic creation
    of default config file on first run.

    Args:
        config_path: Path to the config file. If None, uses the default
                    location (~/.config/astronomo/config.toml)
    """

    VERSION = "1.0"

    def __init__(self, config_path: Path | None = None):
        if config_path is not None:
            self.config_path = config_path
            self.config_dir = config_path.parent
        else:
            self.config_dir = Path.home() / ".config" / "astronomo"
            self.config_path = self.config_dir / "config.toml"

        self.config: Config = Config()
        self._load()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load configuration from TOML file, creating default if needed."""
        if not self.config_path.exists():
            self._create_default_config()
            return

        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            self.config = Config.from_dict(data)
        except (tomllib.TOMLDecodeError, OSError):
            # If file is corrupted or unreadable, use defaults
            self.config = Config()

    def _create_default_config(self) -> None:
        """Create default config file with comments."""
        self._ensure_config_dir()

        # Write the template directly to preserve comments
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)

        # Load the defaults into memory
        self.config = Config()

    def save(self) -> None:
        """Save current configuration to TOML file.

        Note: This will overwrite the file without comments.
        Use sparingly - prefer the commented template format.
        """
        self._ensure_config_dir()

        data = {
            "version": self.VERSION,
            **self.config.to_dict(),
        }

        with open(self.config_path, "wb") as f:
            tomli_w.dump(data, f)

    # Convenience properties for easy access
    @property
    def theme(self) -> str:
        """Get the configured theme name."""
        return self.config.appearance.theme

    @property
    def home_page(self) -> str | None:
        """Get the configured home page URL, or None if not set."""
        return self.config.browsing.home_page

    @property
    def timeout(self) -> int:
        """Get the configured request timeout."""
        return self.config.browsing.timeout

    @property
    def max_redirects(self) -> int:
        """Get the configured max redirects."""
        return self.config.browsing.max_redirects

    @property
    def syntax_highlighting(self) -> bool:
        """Get whether syntax highlighting is enabled."""
        return self.config.appearance.syntax_highlighting

    @property
    def snapshots_directory(self) -> str | None:
        """Get the configured snapshots directory, or None for default."""
        return self.config.snapshots.directory

    @property
    def show_emoji(self) -> bool:
        """Get whether emoji should be displayed as-is."""
        return self.config.appearance.show_emoji

    @property
    def identity_prompt(self) -> str:
        """Get the configured identity prompt behavior."""
        return self.config.browsing.identity_prompt

    @property
    def max_content_width(self) -> int:
        """Get the configured max content width (0 means disabled)."""
        return self.config.appearance.max_content_width

    @property
    def show_images(self) -> bool:
        """Get whether images should be displayed inline."""
        return self.config.appearance.show_images

    @property
    def image_quality(self) -> str:
        """Get the configured image quality setting."""
        return self.config.appearance.image_quality
