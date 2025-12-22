"""Browsing settings tab."""

from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from astronomo.config import ConfigManager
from astronomo.widgets.settings.base import SettingDefinition, SettingRow, WidgetType


BROWSING_SETTINGS = [
    SettingDefinition(
        key="browsing.home_page",
        label="Home Page",
        widget_type=WidgetType.INPUT_TEXT,
        description="Default page when launching without a URL (leave empty for none)",
        placeholder="gemini://geminiprotocol.net/",
        default=None,
    ),
    SettingDefinition(
        key="browsing.timeout",
        label="Request Timeout",
        widget_type=WidgetType.INPUT_NUMBER,
        description="Maximum seconds to wait for a server response",
        default=30,
    ),
    SettingDefinition(
        key="browsing.max_redirects",
        label="Max Redirects",
        widget_type=WidgetType.INPUT_NUMBER,
        description="Maximum number of redirects to follow automatically",
        default=5,
    ),
    SettingDefinition(
        key="browsing.identity_prompt",
        label="Identity Prompt",
        widget_type=WidgetType.SELECT,
        description="When to show identity selection for sites with configured identities",
        options=[
            ("Every time", "every_time"),
            ("When ambiguous", "when_ambiguous"),
            ("Remember choice", "remember_choice"),
        ],
        default="when_ambiguous",
    ),
]


class BrowsingSettings(Static):
    """Browsing behavior settings section."""

    DEFAULT_CSS = """
    BrowsingSettings {
        height: 100%;
        width: 100%;
    }
    """

    def __init__(self, config_manager: ConfigManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config_manager = config_manager

    def compose(self) -> ComposeResult:
        with VerticalScroll(can_focus=False):
            for setting in BROWSING_SETTINGS:
                current_value = self._get_value(setting.key)
                yield SettingRow(
                    definition=setting,
                    current_value=current_value,
                    on_change=self._handle_change,
                )

    def _get_value(self, key: str) -> Any:
        """Get current value for a setting key."""
        parts = key.split(".")
        if parts[0] == "browsing":
            return getattr(self.config_manager.config.browsing, parts[1])
        return None

    def _handle_change(self, key: str, value: Any) -> None:
        """Handle setting change - update config and save."""
        parts = key.split(".")
        if parts[0] == "browsing":
            attr = parts[1]
            # Validate and update
            if attr == "home_page":
                # Empty string becomes None
                value = value.strip() if value else None
            elif attr == "timeout":
                if value is None or value <= 0:
                    return  # Invalid, don't save
            elif attr == "max_redirects":
                if value is None or value < 0:
                    return  # Invalid, don't save

            setattr(self.config_manager.config.browsing, attr, value)
            self.config_manager.save()
