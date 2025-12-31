"""Manage URLs modal for Astronomo."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from astronomo.identities import Identity, IdentityManager


class UrlItem(Static):
    """A single URL prefix item with remove button."""

    DEFAULT_CSS = """
    UrlItem {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    UrlItem:hover {
        background: $surface-lighten-1;
    }

    UrlItem Horizontal {
        height: auto;
        align: left middle;
    }

    UrlItem .url-text {
        width: 1fr;
    }

    UrlItem .remove-btn {
        min-width: 3;
        height: 1;
        border: none;
    }
    """

    def __init__(self, url: str, identity_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.identity_id = identity_id

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.url, classes="url-text")
            yield Button(
                "x",
                variant="error",
                id="remove-url",
                classes="remove-btn",
            )


class ManageUrlsModal(ModalScreen[None]):
    """Modal screen for managing URL prefix associations.

    Args:
        manager: IdentityManager instance
        identity: The identity to manage URLs for
    """

    CSS_PATH = Path(__file__).parent / "certificates.tcss"

    BINDINGS = [
        Binding("escape", "close", "Close", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: IdentityManager,
        identity: Identity,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.identity = identity

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "URL Associations"
        with container:
            yield Label(f"Identity: {self.identity.name}", classes="identity-name")

            yield Label("URLs using this identity:", classes="section-label")

            with VerticalScroll(classes="url-list", id="url-list"):
                yield from self._compose_url_list()

            with Container(classes="add-section"):
                yield Label("Add new URL prefix:", classes="section-label")
                with Horizontal(classes="add-row"):
                    yield Input(
                        placeholder="gemini://example.com/",
                        id="url-input",
                    )
                    yield Button("Add", variant="primary", id="add-btn")

            with Horizontal(classes="button-row"):
                yield Button("Done", variant="default", id="done-btn")

    def _compose_url_list(self) -> ComposeResult:
        """Compose the list of URL items."""
        if not self.identity.url_prefixes:
            yield Label(
                "No URL associations yet.",
                classes="no-urls",
            )
        else:
            for url in self.identity.url_prefixes:
                yield UrlItem(url, self.identity.id)

    def _refresh_url_list(self) -> None:
        """Refresh the URL list after changes."""
        # Reload identity to get updated url_prefixes
        updated_identity = self.manager.get_identity(self.identity.id)
        if updated_identity:
            self.identity = updated_identity

        scroll = self.query_one("#url-list", VerticalScroll)
        scroll.remove_children()

        if not self.identity.url_prefixes:
            scroll.mount(
                Label(
                    "No URL associations yet.",
                    classes="no-urls",
                )
            )
        else:
            for url in self.identity.url_prefixes:
                scroll.mount(UrlItem(url, self.identity.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "done-btn":
            self.dismiss(None)
        elif event.button.id == "add-btn":
            self._add_url()
        elif event.button.id == "remove-url":
            # Find the UrlItem parent and remove that URL
            widget = event.button
            while widget is not None:
                if isinstance(widget, UrlItem):
                    self._remove_url(widget.url)
                    break
                widget = widget.parent  # type: ignore

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in URL input."""
        if event.input.id == "url-input":
            self._add_url()

    def _add_url(self) -> None:
        """Add a new URL prefix."""
        url_input = self.query_one("#url-input", Input)
        url = url_input.value.strip()

        if not url:
            return

        # Ensure it starts with gemini://
        if not url.startswith("gemini://"):
            url = f"gemini://{url}"

        # Ensure it ends with /
        if not url.endswith("/"):
            url = f"{url}/"

        self.manager.add_url_prefix(self.identity.id, url)
        url_input.value = ""
        self._refresh_url_list()

    def _remove_url(self, url: str) -> None:
        """Remove a URL prefix."""
        self.manager.remove_url_prefix(self.identity.id, url)
        self._refresh_url_list()

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)
