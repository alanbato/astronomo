"""OPML Import modal for Astronomo.

Provides a modal dialog for importing feeds from an OPML file.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class OpmlImportModal(ModalScreen[Path | None]):
    """Modal screen for importing feeds from OPML.

    Returns the path to the OPML file to import, or None if cancelled.
    """

    DEFAULT_CSS = """
    OpmlImportModal {
        align: center middle;
    }

    OpmlImportModal > Container {
        width: 70;
        height: auto;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    OpmlImportModal Label {
        padding: 1 0 0 0;
    }

    OpmlImportModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    OpmlImportModal .hint {
        color: $text-muted;
        padding: 0 0 1 0;
    }

    OpmlImportModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    OpmlImportModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "import_file", "Import", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Import Feeds from OPML"
        with container:
            yield Label("OPML File Path:")
            yield Input(
                placeholder="/path/to/feeds.opml",
                id="path-input",
            )
            yield Label(
                "Enter the path to an OPML file. Only Gemini feeds will be imported.",
                classes="hint",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Import", variant="primary", id="import-btn")

    def on_mount(self) -> None:
        """Focus the path input on mount."""
        self.query_one("#path-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "import-btn":
            self._import_file()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self._import_file()

    def _import_file(self) -> None:
        """Import the OPML file."""
        path_str = self.query_one("#path-input", Input).value.strip()
        if not path_str:
            self.app.notify("File path is required", severity="error")
            return

        # Expand ~ to home directory
        path = Path(path_str).expanduser()

        # Check if file exists
        if not path.exists():
            self.app.notify(f"File not found: {path}", severity="error")
            return

        if not path.is_file():
            self.app.notify(f"Not a file: {path}", severity="error")
            return

        self.dismiss(path)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_import_file(self) -> None:
        """Import the file and close the modal."""
        self._import_file()
