"""Appearance settings tab."""

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from astronomo.config import VALID_THEMES, ConfigManager
from astronomo.widgets.settings.base import SettingDefinition, SettingRow, WidgetType

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo


APPEARANCE_SETTINGS = [
    SettingDefinition(
        key="appearance.theme",
        label="Theme",
        widget_type=WidgetType.SELECT,
        description="Color scheme for the application interface",
        options=[(theme, theme) for theme in sorted(VALID_THEMES)],
        default="textual-dark",
    ),
    SettingDefinition(
        key="appearance.syntax_highlighting",
        label="Syntax Highlighting",
        widget_type=WidgetType.SWITCH,
        description="Enable syntax highlighting in preformatted code blocks",
        default=True,
    ),
]


class AppearanceSettings(Static):
    """Appearance settings section."""

    DEFAULT_CSS = """
    AppearanceSettings {
        height: 100%;
        width: 100%;
    }
    """

    def __init__(self, config_manager: ConfigManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config_manager = config_manager

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            for setting in APPEARANCE_SETTINGS:
                current_value = self._get_value(setting.key)
                yield SettingRow(
                    definition=setting,
                    current_value=current_value,
                    on_change=self._handle_change,
                )

    def _get_value(self, key: str) -> Any:
        """Get current value for a setting key."""
        parts = key.split(".")
        if parts[0] == "appearance":
            return getattr(self.config_manager.config.appearance, parts[1])
        return None

    def _handle_change(self, key: str, value: Any) -> None:
        """Handle setting change - update config and save."""
        parts = key.split(".")
        if parts[0] == "appearance":
            if parts[1] == "theme":
                self.config_manager.config.appearance.theme = value
                self.config_manager.save()
                # Apply theme immediately
                app: Astronomo = self.app  # type: ignore[assignment]
                app.theme = value
            elif parts[1] == "syntax_highlighting":
                self.config_manager.config.appearance.syntax_highlighting = value
                self.config_manager.save()
