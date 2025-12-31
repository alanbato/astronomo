"""Save Snapshot confirmation modal for Astronomo.

Provides a modal dialog for confirming the save of a Gemini page snapshot.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class SaveSnapshotModal(ModalScreen[bool]):
    """Modal screen for confirming a page snapshot save.

    Args:
        url: URL of the page to save
        save_path: Full path where the file will be saved
    """

    DEFAULT_CSS = """
    SaveSnapshotModal {
        align: center middle;
    }

    SaveSnapshotModal > Container {
        width: 70;
        height: auto;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    SaveSnapshotModal .info-label {
        color: $text-muted;
        padding-top: 1;
    }

    SaveSnapshotModal .info-value {
        padding-bottom: 1;
        text-style: bold;
    }

    SaveSnapshotModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    SaveSnapshotModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "save", "Save", show=False, priority=True),
    ]

    def __init__(
        self,
        url: str,
        save_path: Path,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.save_path = save_path

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Save Page Snapshot"
        with container:
            yield Label("URL:", classes="info-label")
            yield Static(self.url, classes="info-value")

            yield Label("Save to:", classes="info-label")
            yield Static(str(self.save_path), classes="info-value")

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Focus the save button on mount."""
        self.query_one("#save-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "save-btn":
            self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)

    def action_save(self) -> None:
        """Confirm save and close the modal."""
        self.dismiss(True)
