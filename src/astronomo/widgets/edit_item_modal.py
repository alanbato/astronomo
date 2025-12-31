"""Edit Item modal for Astronomo.

Provides a modal dialog for editing bookmark titles and folder names.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from astronomo.bookmarks import Bookmark, BookmarkManager, Folder
from astronomo.widgets.color_picker import ColorPicker


class EditItemModal(ModalScreen[bool]):
    """Modal screen for editing a bookmark or folder.

    Args:
        manager: BookmarkManager instance
        item: The Bookmark or Folder to edit
    """

    DEFAULT_CSS = """
    EditItemModal {
        align: center middle;
    }

    EditItemModal > Container {
        width: 55;
        height: auto;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    EditItemModal Label {
        padding: 1 0 0 0;
    }

    EditItemModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    EditItemModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    EditItemModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "save", "Save", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: BookmarkManager,
        item: Bookmark | Folder,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.item = item
        self._is_bookmark = isinstance(item, Bookmark)
        # Track selected color for folders
        self._selected_color: str | None = (
            None if self._is_bookmark else item.color  # type: ignore[union-attr]
        )

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        title = "Edit Bookmark" if self._is_bookmark else "Edit Folder"
        label = "Title:" if self._is_bookmark else "Name:"
        current_value = (
            self.item.title if self._is_bookmark else self.item.name  # type: ignore
        )
        container = Container()
        container.border_title = title
        with container:
            yield Label(label)
            yield Input(
                value=current_value,
                placeholder="Enter new name",
                id="name-input",
            )

            # Show color picker for folders only
            if not self._is_bookmark:
                yield ColorPicker(
                    current_color=self._selected_color,
                    id="color-picker",
                )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        input_widget = self.query_one("#name-input", Input)
        input_widget.focus()
        # Select all text for easy replacement
        input_widget.action_select_all()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "save-btn":
            self._save_changes()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        # Only save if it's the name input (not the color picker's hex input)
        if event.input.id == "name-input":
            self._save_changes()

    def on_color_picker_color_changed(self, event: ColorPicker.ColorChanged) -> None:
        """Handle color selection changes."""
        self._selected_color = event.color

    def _save_changes(self) -> None:
        """Save the changes and dismiss."""
        new_name = self.query_one("#name-input", Input).value.strip()
        if not new_name:
            # Don't allow empty names
            self.dismiss(False)
            return

        if self._is_bookmark:
            self.manager.update_bookmark(self.item.id, title=new_name)
        else:
            self.manager.rename_folder(self.item.id, new_name)
            self.manager.update_folder_color(self.item.id, self._selected_color)

        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)

    def action_save(self) -> None:
        """Save changes and close the modal."""
        self._save_changes()
