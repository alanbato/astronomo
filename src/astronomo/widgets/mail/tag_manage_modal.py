"""Tag management modal for GMAP mail."""

import re

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label

# Valid custom tag pattern
TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class TagManageModal(ModalScreen[list[str] | None]):
    """Modal for managing tags on a message.

    Returns the new list of tags, or None if cancelled.
    """

    DEFAULT_CSS = """
    TagManageModal {
        align: center middle;
    }

    TagManageModal > Container {
        width: 50;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    TagManageModal VerticalScroll {
        height: auto;
        max-height: 15;
        margin-bottom: 1;
    }

    TagManageModal #tag-grid {
        layout: grid;
        grid-size: 2;
        grid-gutter: 0 1;
        height: auto;
        width: 100%;
    }

    TagManageModal .add-tag-row {
        width: 100%;
        height: auto;
        padding-top: 1;
    }

    TagManageModal .add-tag-row Input {
        width: 1fr;
    }

    TagManageModal .add-tag-row Button {
        width: auto;
        margin-left: 1;
    }

    TagManageModal .button-row {
        align: center middle;
        padding-top: 1;
    }

    TagManageModal .hint {
        color: $text-muted;
        padding-top: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        current_tags: list[str],
        all_tags: list[str],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._current_tags = set(current_tags)
        # Combine all known tags, keeping unique
        self._all_tags = sorted(set(all_tags) | self._current_tags)

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Manage Tags"
        with container:
            yield Label("Select tags for this message:")

            with VerticalScroll():
                with Container(id="tag-grid"):
                    for tag in self._all_tags:
                        checked = tag in self._current_tags
                        yield Checkbox(tag, value=checked, id=f"tag-{tag}")

            # Add new tag
            with Horizontal(classes="add-tag-row"):
                yield Input(
                    placeholder="New tag name",
                    id="new-tag-input",
                )
                yield Button("Add", id="add-tag-btn")
            yield Label(
                "Letters, digits, underscores, hyphens only",
                classes="hint",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self._save_tags()
        elif event.button.id == "add-tag-btn":
            self._add_new_tag()

    def _add_new_tag(self) -> None:
        """Add a new custom tag."""
        tag_input = self.query_one("#new-tag-input", Input)
        tag_name = tag_input.value.strip()

        if not tag_name:
            return

        if not TAG_PATTERN.match(tag_name):
            self.app.notify(
                "Tag must contain only letters, digits, underscores, hyphens",
                severity="error",
            )
            return

        # Check if already exists
        existing_ids = {f"tag-{t}" for t in self._all_tags}
        if f"tag-{tag_name}" in existing_ids:
            self.app.notify("Tag already exists", severity="warning")
            return

        # Add checkbox for the new tag
        self._all_tags.append(tag_name)
        grid = self.query_one("#tag-grid")
        grid.mount(Checkbox(tag_name, value=True, id=f"tag-{tag_name}"))
        tag_input.value = ""

    def _save_tags(self) -> None:
        """Collect selected tags and dismiss."""
        tags = []
        for tag in self._all_tags:
            try:
                checkbox = self.query_one(f"#tag-{tag}", Checkbox)
                if checkbox.value:
                    tags.append(tag)
            except Exception:
                continue
        self.dismiss(tags)

    def action_cancel(self) -> None:
        self.dismiss(None)
