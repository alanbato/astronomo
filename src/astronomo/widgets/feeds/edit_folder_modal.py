"""Edit Feed Folder modal for Astronomo.

Provides a modal dialog for editing feed folders.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from astronomo.feeds import FeedFolder, FeedManager


class EditFeedFolderModal(ModalScreen[bool]):
    """Modal screen for editing a feed folder.

    Args:
        manager: FeedManager instance
        folder: The FeedFolder to edit
    """

    DEFAULT_CSS = """
    EditFeedFolderModal {
        align: center middle;
    }

    EditFeedFolderModal > Container {
        width: 50;
        height: auto;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    EditFeedFolderModal Label {
        padding: 1 0 0 0;
    }

    EditFeedFolderModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    EditFeedFolderModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    EditFeedFolderModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "save", "Save", show=False, priority=True),
    ]

    def __init__(self, manager: FeedManager, folder: FeedFolder, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.folder = folder

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Edit Feed Folder"
        with container:
            yield Label("Folder Name:")
            yield Input(
                value=self.folder.name,
                placeholder="Enter folder name",
                id="name-input",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Focus the name input on mount."""
        self.query_one("#name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "save-btn":
            self._save_folder()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self._save_folder()

    def _save_folder(self) -> None:
        """Save the folder changes and dismiss."""
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            self.app.notify("Folder name is required", severity="error")
            return

        # Update the folder
        self.manager.rename_folder(folder_id=self.folder.id, name=name)

        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)

    def action_save(self) -> None:
        """Save the folder changes and close the modal."""
        self._save_folder()
