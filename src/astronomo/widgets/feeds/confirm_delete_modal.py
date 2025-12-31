"""Confirm Delete modal for feeds in Astronomo.

Provides a confirmation dialog before deleting feeds or folders.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from astronomo.feeds import Feed, FeedFolder, FeedManager


class ConfirmDeleteFeedModal(ModalScreen[bool]):
    """Modal screen for confirming feed or folder deletion.

    Args:
        manager: FeedManager instance
        item: The feed or folder to delete
    """

    DEFAULT_CSS = """
    ConfirmDeleteFeedModal {
        align: center middle;
    }

    ConfirmDeleteFeedModal > Container {
        width: 55;
        height: auto;
        border: thick $error;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDeleteFeedModal .item-name {
        text-style: bold;
        padding: 1 0;
        text-align: center;
    }

    ConfirmDeleteFeedModal .warning-text {
        color: $text-muted;
        padding: 1 0;
    }

    ConfirmDeleteFeedModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    ConfirmDeleteFeedModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: FeedManager,
        item: Feed | FeedFolder,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.item = item

    def compose(self) -> ComposeResult:
        item = self.item
        title = "Delete Feed" if isinstance(item, Feed) else "Delete Folder"
        container = Container()
        container.border_title = title
        with container:
            if isinstance(item, Feed):
                yield Static("Are you sure you want to delete this feed?")
                yield Label(f'"{item.title}"', classes="item-name")
                yield Static(
                    "This will remove the subscription and all read status "
                    "for this feed.",
                    classes="warning-text",
                )
            else:
                yield Static("Are you sure you want to delete this folder?")
                yield Label(f'"{item.name}"', classes="item-name")
                # Check if folder has feeds
                feeds_in_folder = self.manager.get_feeds_in_folder(item.id)
                if feeds_in_folder:
                    yield Static(
                        f"This folder contains {len(feeds_in_folder)} feed(s). "
                        "They will be moved to the root level.",
                        classes="warning-text",
                    )
                else:
                    yield Static(
                        "This folder is empty.",
                        classes="warning-text",
                    )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Delete", variant="error", id="delete-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "delete-btn":
            self._delete_item()

    def _delete_item(self) -> None:
        """Delete the item and dismiss."""
        if isinstance(self.item, Feed):
            self.manager.remove_feed(self.item.id)
        else:
            self.manager.remove_folder(self.item.id)
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(False)
