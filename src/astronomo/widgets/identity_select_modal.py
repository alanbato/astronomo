"""Identity select modal for Gemini status 60 responses.

Provides a modal dialog for selecting or creating a client certificate
identity when a Gemini server requests authentication.
"""

from dataclasses import dataclass
from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Static

from astronomo.identities import Identity, IdentityManager


@dataclass
class IdentityResult:
    """Result from the identity select modal.

    Attributes:
        identity: The selected or created identity
        remember: Whether to remember this identity for the URL prefix
    """

    identity: Identity
    remember: bool


class IdentityItem(Static):
    """A selectable identity item in the list."""

    DEFAULT_CSS = """
    IdentityItem {
        width: 100%;
        height: 3;
        padding: 0 1;
        border: solid transparent;
    }

    IdentityItem:hover {
        background: $surface-lighten-1;
    }

    IdentityItem.-selected {
        background: $primary;
        border: solid $primary-lighten-1;
    }

    IdentityItem .identity-name {
        text-style: bold;
    }

    IdentityItem .identity-fingerprint {
        color: $text-muted;
    }
    """

    def __init__(self, identity: Identity, **kwargs) -> None:
        super().__init__(**kwargs)
        self.identity = identity

    def compose(self) -> ComposeResult:
        """Compose the identity item."""
        short_fp = self.identity.fingerprint[:24] + "..."
        yield Label(self.identity.name, classes="identity-name")
        yield Label(short_fp, classes="identity-fingerprint")


class IdentitySelectModal(ModalScreen[IdentityResult | None]):
    """Modal screen for selecting or creating an identity (status 60).

    Args:
        manager: IdentityManager instance
        url: The URL that requested authentication
        message: The server's META message (prompt)
    """

    DEFAULT_CSS = """
    IdentitySelectModal {
        align: center middle;
    }

    IdentitySelectModal > Container {
        width: 70;
        height: auto;
        max-height: 85%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    IdentitySelectModal .url-display {
        width: 100%;
        padding: 0 0 1 0;
        color: $text-muted;
    }

    IdentitySelectModal .prompt-text {
        width: 100%;
        padding: 1 0;
        color: $text;
    }

    IdentitySelectModal .section-label {
        width: 100%;
        padding: 1 0 0 0;
        text-style: bold;
    }

    IdentitySelectModal .identity-list {
        width: 100%;
        height: auto;
        max-height: 12;
        border: solid $primary;
        margin: 1 0;
    }

    IdentitySelectModal .no-identities {
        width: 100%;
        padding: 1;
        color: $text-muted;
        text-align: center;
    }

    IdentitySelectModal .create-new-btn {
        width: 100%;
        margin: 1 0;
    }

    IdentitySelectModal .new-identity-input {
        display: none;
        width: 100%;
        padding: 1 0;
    }

    IdentitySelectModal .new-identity-input.-visible {
        display: block;
    }

    IdentitySelectModal .new-identity-input Input {
        width: 100%;
    }

    IdentitySelectModal Checkbox {
        margin: 1 0;
    }

    IdentitySelectModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    IdentitySelectModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: IdentityManager,
        url: str,
        message: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.url = url
        self.message = message
        self._selected_identity: Identity | None = None
        self._creating_new = False

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Identity Required"
        with container:
            yield Label(self.url, classes="url-display")
            yield Label(self.message, classes="prompt-text")

            yield Label("Select an identity:", classes="section-label")

            identities = self.manager.get_all_identities()
            with VerticalScroll(classes="identity-list"):
                if identities:
                    for identity in identities:
                        yield IdentityItem(identity, id=f"identity-{identity.id}")
                else:
                    yield Label(
                        "No identities yet. Create one below.",
                        classes="no-identities",
                    )

            yield Button(
                "+ Create New Identity",
                variant="default",
                id="create-new-btn",
                classes="create-new-btn",
            )

            with Vertical(classes="new-identity-input", id="new-identity-container"):
                yield Label("Identity name:")
                yield Input(
                    placeholder="My Identity",
                    id="identity-name-input",
                )

            yield Checkbox(
                f"Remember for {self._get_url_prefix()}",
                id="remember-checkbox",
                value=True,
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Use Identity", variant="primary", id="use-btn")

    def _get_url_prefix(self) -> str:
        """Extract URL prefix (scheme://host/) from URL."""
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}/"

    def on_mount(self) -> None:
        """Set up initial state."""
        # Pre-select first identity if available
        identities = self.manager.get_all_identities()
        if identities:
            self._select_identity(identities[0])

    def on_identity_item_click(self, event: IdentityItem) -> None:
        """Handle click on an identity item."""
        # This won't work directly - we need to use Static's click
        pass

    def on_click(self, event) -> None:
        """Handle clicks on identity items."""
        # Find if we clicked on an IdentityItem
        widget = event.widget
        while widget is not None:
            if isinstance(widget, IdentityItem):
                self._select_identity(widget.identity)
                self._creating_new = False
                self.query_one("#new-identity-container").remove_class("-visible")
                break
            widget = getattr(widget, "parent", None)

    def _select_identity(self, identity: Identity) -> None:
        """Select an identity and update UI."""
        self._selected_identity = identity

        # Update visual selection
        for item in self.query(IdentityItem):
            if item.identity.id == identity.id:
                item.add_class("-selected")
            else:
                item.remove_class("-selected")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "use-btn":
            self._use_identity()
        elif event.button.id == "create-new-btn":
            self._show_create_new()

    def _show_create_new(self) -> None:
        """Show the create new identity form."""
        self._creating_new = True
        self._selected_identity = None

        # Deselect all identity items
        for item in self.query(IdentityItem):
            item.remove_class("-selected")

        # Show the input form
        container = self.query_one("#new-identity-container")
        container.add_class("-visible")
        self.query_one("#identity-name-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the name input."""
        if event.input.id == "identity-name-input":
            self._use_identity()

    def _use_identity(self) -> None:
        """Use the selected or created identity and dismiss."""
        identity: Identity | None = None

        if self._creating_new:
            # Create new identity
            name = self.query_one("#identity-name-input", Input).value.strip()
            if not name:
                name = "New Identity"

            # Extract hostname from URL for certificate
            parsed = urlparse(self.url)
            hostname = parsed.netloc

            identity = self.manager.create_identity(
                name=name,
                hostname=hostname,
            )
        else:
            identity = self._selected_identity

        if identity is None:
            # No identity selected or created
            return

        remember = self.query_one("#remember-checkbox", Checkbox).value

        self.dismiss(IdentityResult(identity=identity, remember=remember))

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
