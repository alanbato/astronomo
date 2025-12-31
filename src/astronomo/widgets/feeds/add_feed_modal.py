"""Add Feed modal for Astronomo.

Provides a modal dialog for adding feed subscriptions with title,
URL, and folder selection.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from astronomo.feeds import Feed, FeedManager

# Special value for "create new folder" option
NEW_FOLDER_SENTINEL = "__NEW_FOLDER__"


class AddFeedModal(ModalScreen[Feed | None]):
    """Modal screen for adding a new feed subscription.

    Args:
        manager: FeedManager instance
        url: Optional pre-filled URL
        suggested_title: Optional pre-filled title
    """

    DEFAULT_CSS = """
    AddFeedModal {
        align: center middle;
    }

    AddFeedModal > Container {
        width: 60;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    AddFeedModal Label {
        padding: 1 0 0 0;
    }

    AddFeedModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    AddFeedModal Select {
        width: 100%;
        margin-bottom: 1;
    }

    AddFeedModal .new-folder-input {
        display: none;
    }

    AddFeedModal .new-folder-input.-visible {
        display: block;
    }

    AddFeedModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    AddFeedModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "save", "Save", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: FeedManager,
        url: str | None = None,
        suggested_title: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.url = url or ""
        self.suggested_title = suggested_title or ""
        self._creating_new_folder = False

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Add Feed"
        with container:
            yield Label("Feed URL:")
            yield Input(
                value=self.url,
                placeholder="gemini://example.com/feed.xml",
                id="url-input",
            )

            yield Label("Title:")
            yield Input(
                value=self.suggested_title,
                placeholder="Feed title",
                id="title-input",
            )

            yield Label("Folder:")
            yield Select(
                self._get_folder_options(),
                value=Select.BLANK,
                id="folder-select",
                allow_blank=True,
                prompt="(No folder)",
            )

            with Vertical(classes="new-folder-input", id="new-folder-container"):
                yield Label("New folder name:")
                yield Input(
                    placeholder="Enter folder name",
                    id="new-folder-input",
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

        # Add "New Folder" option at the end
        options.append(("+ New Folder", NEW_FOLDER_SENTINEL))

        return options

    def on_mount(self) -> None:
        """Focus the URL input on mount."""
        if not self.url:
            self.query_one("#url-input", Input).focus()
        else:
            self.query_one("#title-input", Input).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle folder selection changes."""
        new_folder_container = self.query_one("#new-folder-container")

        if event.value == NEW_FOLDER_SENTINEL:
            self._creating_new_folder = True
            new_folder_container.add_class("-visible")
            self.query_one("#new-folder-input", Input).focus()
        else:
            self._creating_new_folder = False
            new_folder_container.remove_class("-visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self._save_feed()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in inputs."""
        if event.input.id in ("url-input", "title-input", "new-folder-input"):
            self._save_feed()

    def _save_feed(self) -> None:
        """Save the feed and dismiss."""
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            self.app.notify("URL is required", severity="error")
            return

        # Validate that it's a Gemini URL
        if not url.startswith("gemini://"):
            self.app.notify("Only Gemini URLs are supported", severity="error")
            return

        # Check if feed already exists
        if self.manager.feed_exists(url):
            self.app.notify("This feed is already subscribed", severity="warning")
            return

        title = self.query_one("#title-input", Input).value.strip()
        if not title:
            title = url  # Fallback to URL if title is empty

        folder_select = self.query_one("#folder-select", Select)
        folder_id: str | None = None

        if self._creating_new_folder:
            # Create new folder first
            new_folder_name = self.query_one("#new-folder-input", Input).value.strip()
            if new_folder_name:
                new_folder = self.manager.add_folder(new_folder_name)
                folder_id = new_folder.id
        elif (
            folder_select.value != Select.BLANK
            and folder_select.value != NEW_FOLDER_SENTINEL
        ):
            folder_id = str(folder_select.value)

        # Create the feed
        feed = self.manager.add_feed(
            url=url,
            title=title,
            folder_id=folder_id,
        )

        self.dismiss(feed)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save the feed and close the modal."""
        self._save_feed()
