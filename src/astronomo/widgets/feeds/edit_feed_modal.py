"""Edit Feed modal for Astronomo.

Provides a modal dialog for editing feed subscriptions.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from astronomo.feeds import Feed, FeedManager


class EditFeedModal(ModalScreen[bool]):
    """Modal screen for editing a feed subscription.

    Args:
        manager: FeedManager instance
        feed: The Feed to edit
    """

    DEFAULT_CSS = """
    EditFeedModal {
        align: center middle;
    }

    EditFeedModal > Container {
        width: 60;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    EditFeedModal Label {
        padding: 1 0 0 0;
    }

    EditFeedModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    EditFeedModal Select {
        width: 100%;
        margin-bottom: 1;
    }

    EditFeedModal .url-label {
        color: $text-muted;
        margin-bottom: 1;
    }

    EditFeedModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    EditFeedModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "save", "Save", show=False, priority=True),
    ]

    def __init__(self, manager: FeedManager, feed: Feed, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.feed = feed

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Edit Feed"
        with container:
            yield Label("Feed URL:")
            yield Label(self.feed.url, classes="url-label")

            yield Label("Title:")
            yield Input(
                value=self.feed.title,
                placeholder="Feed title",
                id="title-input",
            )

            yield Label("Folder:")
            yield Select(
                self._get_folder_options(),
                value=self.feed.folder_id or Select.BLANK,
                id="folder-select",
                allow_blank=True,
                prompt="(No folder)",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def _get_folder_options(self) -> list[tuple[str, str]]:
        """Get folder options for the select widget."""
        options = []

        # Add existing folders
        for folder in self.manager.get_all_folders():
            options.append((folder.name, folder.id))

        return options

    def on_mount(self) -> None:
        """Focus the title input on mount."""
        self.query_one("#title-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "save-btn":
            self._save_feed()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self._save_feed()

    def _save_feed(self) -> None:
        """Save the feed changes and dismiss."""
        title = self.query_one("#title-input", Input).value.strip()
        if not title:
            title = self.feed.url  # Fallback to URL if title is empty

        folder_select = self.query_one("#folder-select", Select)
        folder_id: str | None = None

        if folder_select.value != Select.BLANK:
            folder_id = str(folder_select.value)

        # Update the feed
        self.manager.update_feed(
            feed_id=self.feed.id,
            title=title,
            folder_id=folder_id,
        )

        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)

    def action_save(self) -> None:
        """Save the feed changes and close the modal."""
        self._save_feed()
