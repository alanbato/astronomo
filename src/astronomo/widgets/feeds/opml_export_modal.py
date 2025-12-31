"""OPML Export modal for Astronomo.

Provides a modal dialog for exporting feeds to an OPML file.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class OpmlExportModal(ModalScreen[Path | None]):
    """Modal screen for exporting feeds to OPML.

    Returns the path where OPML file should be saved, or None if cancelled.
    """

    DEFAULT_CSS = """
    OpmlExportModal {
        align: center middle;
    }

    OpmlExportModal > Container {
        width: 70;
        height: auto;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    OpmlExportModal Label {
        padding: 1 0 0 0;
    }

    OpmlExportModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    OpmlExportModal .hint {
        color: $text-muted;
        padding: 0 0 1 0;
    }

    OpmlExportModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    OpmlExportModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "export_file", "Export", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Export Feeds to OPML"
        with container:
            yield Label("Output File Path:")
            yield Input(
                value=str(Path.home() / "astronomo-feeds.opml"),
                placeholder="/path/to/feeds.opml",
                id="path-input",
            )
            yield Label(
                "Enter the path where the OPML file should be saved.",
                classes="hint",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Export", variant="primary", id="export-btn")

    def on_mount(self) -> None:
        """Focus the path input on mount."""
        input_widget = self.query_one("#path-input", Input)
        input_widget.focus()
        # Select all text for easy editing
        input_widget.action_select_all()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "export-btn":
            self._export_file()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self._export_file()

    def _export_file(self) -> None:
        """Export to the OPML file."""
        path_str = self.query_one("#path-input", Input).value.strip()
        if not path_str:
            self.app.notify("File path is required", severity="error")
            return

        # Expand ~ to home directory
        path = Path(path_str).expanduser()

        # Check if parent directory exists
        if not path.parent.exists():
            self.app.notify(f"Directory not found: {path.parent}", severity="error")
            return

        # Warn if file already exists (but still allow overwrite)
        if path.exists():
            self.app.notify("File will be overwritten", timeout=2)

        self.dismiss(path)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_export_file(self) -> None:
        """Export the file and close the modal."""
        self._export_file()
