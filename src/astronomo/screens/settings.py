"""Settings screen for Astronomo."""

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static, TabbedContent, TabPane

from astronomo.widgets.settings import (
    AppearanceSettings,
    BrowsingSettings,
    CertificatesSettings,
)

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo


class SettingsScreen(ModalScreen[None]):
    """Modal settings dialog with tabbed sections."""

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-dialog {
        width: 80%;
        max-width: 100;
        height: 80%;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
        layout: vertical;
    }

    #settings-title {
        height: auto;
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    #settings-tabs {
        height: 1fr;
    }

    #settings-tabs > ContentSwitcher {
        height: 1fr;
    }

    #settings-tabs TabPane {
        height: 1fr;
        padding: 1;
    }

    AppearanceSettings, BrowsingSettings, CertificatesSettings {
        height: 1fr;
        width: 1fr;
    }

    AppearanceSettings VerticalScroll,
    BrowsingSettings VerticalScroll,
    CertificatesSettings VerticalScroll {
        height: 1fr;
    }

    #settings-hint {
        height: auto;
        text-align: center;
        color: $text-muted;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+comma", "dismiss_settings", "Close", priority=True),
        Binding("escape", "dismiss_settings", "Close", priority=True),
    ]

    def compose(self) -> ComposeResult:
        app: Astronomo = self.app  # type: ignore[assignment]
        with Container(id="settings-dialog"):
            yield Static("Settings", id="settings-title")
            with TabbedContent(id="settings-tabs"):
                with TabPane("Appearance", id="tab-appearance"):
                    yield AppearanceSettings(app.config_manager)
                with TabPane("Browsing", id="tab-browsing"):
                    yield BrowsingSettings(app.config_manager)
                with TabPane("Certificates", id="tab-certificates"):
                    yield CertificatesSettings(app.identities)
            yield Static("Press Escape or Ctrl+, to close", id="settings-hint")

    def action_dismiss_settings(self) -> None:
        """Close the settings modal."""
        self.dismiss()
