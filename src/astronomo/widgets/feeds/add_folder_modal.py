"""Add Feed Folder modal for Astronomo.

Provides a modal dialog for creating feed folders.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from astronomo.feeds import FeedFolder, FeedManager


class AddFeedFolderModal(ModalScreen[FeedFolder | None]):
    """Modal screen for adding a new feed folder.

    Args:
        manager: FeedManager instance
    """

    DEFAULT_CSS = """
    AddFeedFolderModal {
        align: center middle;
    }

    AddFeedFolderModal > Container {
        width: 50;
        height: auto;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    AddFeedFolderModal Label {
        padding: 1 0 0 0;
    }

    AddFeedFolderModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    AddFeedFolderModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    AddFeedFolderModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "save", "Save", show=False, priority=True),
    ]

    def __init__(self, manager: FeedManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "New Feed Folder"
        with container:
            yield Label("Folder Name:")
            yield Input(
                placeholder="Enter folder name",
                id="name-input",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Create", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Focus the name input on mount."""
        self.query_one("#name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self._save_folder()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self._save_folder()

    def _save_folder(self) -> None:
        """Save the folder and dismiss."""
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            self.app.notify("Folder name is required", severity="error")
            return

        # Create the folder
        folder = self.manager.add_folder(name=name)

        self.dismiss(folder)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save the folder and close the modal."""
        self._save_folder()
