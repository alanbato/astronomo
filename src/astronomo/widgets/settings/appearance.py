"""Appearance settings tab."""

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from astronomo.config import VALID_THEMES, ConfigManager
from astronomo.widgets.settings.base import SettingDefinition, SettingRow, WidgetType

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo

from astronomo.widgets.gemtext_viewer import GemtextViewer


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
    SettingDefinition(
        key="appearance.show_emoji",
        label="Show Emoji",
        widget_type=WidgetType.SWITCH,
        description="Display emoji characters (off shows text descriptions)",
        default=True,
    ),
    SettingDefinition(
        key="appearance.max_content_width",
        label="Max Content Width",
        widget_type=WidgetType.INPUT_NUMBER,
        description="Maximum width for text in characters (0 to disable, min 40)",
        default=80,
        placeholder="80",
    ),
    SettingDefinition(
        key="appearance.show_images",
        label="Show Images",
        widget_type=WidgetType.SWITCH,
        description="Display images inline (requires chafa.py)",
        default=False,
    ),
    SettingDefinition(
        key="appearance.image_quality",
        label="Image Quality",
        widget_type=WidgetType.SELECT,
        description="Quality level for rendered images",
        options=[("Low", "low"), ("Medium", "medium"), ("High", "high")],
        default="medium",
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
        with VerticalScroll(can_focus=False):
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
            app: Astronomo = self.app  # type: ignore[assignment]
            if parts[1] == "theme":
                self.config_manager.config.appearance.theme = value
                self.config_manager.save()
                # Apply theme immediately
                app.theme = value
            elif parts[1] == "syntax_highlighting":
                self.config_manager.config.appearance.syntax_highlighting = value
                self.config_manager.save()
            elif parts[1] == "show_emoji":
                self.config_manager.config.appearance.show_emoji = value
                self.config_manager.save()
                # Re-render content to apply the change (no network request)
                try:
                    viewer = app.query_one("GemtextViewer", expect_type=GemtextViewer)
                    viewer.rerender_content()
                except Exception:
                    pass  # Viewer not available (e.g., in tests)
            elif parts[1] == "max_content_width":
                # Validate: must be 0 (disabled) or >= 40
                if value < 0:
                    value = 0
                elif value > 0 and value < 40:
                    value = 40
                self.config_manager.config.appearance.max_content_width = value
                self.config_manager.save()
                # Apply width constraint immediately
                try:
                    viewer = app.query_one("GemtextViewer", expect_type=GemtextViewer)
                    viewer.apply_width_constraint()
                except Exception:
                    pass  # Viewer not available (e.g., in tests)
            elif parts[1] == "show_images":
                self.config_manager.config.appearance.show_images = value
                self.config_manager.save()
            elif parts[1] == "image_quality":
                self.config_manager.config.appearance.image_quality = value
                self.config_manager.save()
