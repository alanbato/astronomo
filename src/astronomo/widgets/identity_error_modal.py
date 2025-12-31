"""Identity error modal for Gemini status 61/62 responses.

Provides a modal dialog for handling certificate errors:
- Status 61: Certificate not authorized
- Status 62: Certificate not valid (expired, malformed)
"""

from dataclasses import dataclass
from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from astronomo.identities import Identity, IdentityManager


@dataclass
class IdentityErrorResult:
    """Result from the identity error modal.

    Attributes:
        action: The action to take ("switch", "regenerate", or "cancel")
        identity: The identity to use (for "switch" action)
    """

    action: str
    identity: Identity | None = None


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


class IdentityErrorModal(ModalScreen[IdentityErrorResult | None]):
    """Modal screen for handling certificate errors (status 61/62).

    Args:
        manager: IdentityManager instance
        url: The URL that returned the error
        message: The server's META message
        error_type: Either "not_authorized" (61) or "not_valid" (62)
        current_identity: The identity that was used (if any)
    """

    DEFAULT_CSS = """
    IdentityErrorModal {
        align: center middle;
    }

    IdentityErrorModal > Container {
        width: 70;
        height: auto;
        max-height: 85%;
        border: thick $error;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    IdentityErrorModal .url-display {
        width: 100%;
        padding: 0 0 1 0;
        color: $text-muted;
    }

    IdentityErrorModal .error-message {
        width: 100%;
        padding: 1;
        background: $error 10%;
        border: solid $error;
        margin: 1 0;
    }

    IdentityErrorModal .current-identity {
        width: 100%;
        padding: 1 0;
    }

    IdentityErrorModal .current-identity-label {
        color: $text-muted;
    }

    IdentityErrorModal .current-identity-name {
        text-style: bold;
    }

    IdentityErrorModal .section-label {
        width: 100%;
        padding: 1 0 0 0;
        text-style: bold;
    }

    IdentityErrorModal .identity-list {
        width: 100%;
        height: auto;
        max-height: 10;
        border: solid $primary;
        margin: 1 0;
    }

    IdentityErrorModal .no-identities {
        width: 100%;
        padding: 1;
        color: $text-muted;
        text-align: center;
    }

    IdentityErrorModal .action-buttons {
        width: 100%;
        padding: 1 0;
    }

    IdentityErrorModal .action-buttons Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    IdentityErrorModal .new-identity-input {
        display: none;
        width: 100%;
        padding: 1 0;
    }

    IdentityErrorModal .new-identity-input.-visible {
        display: block;
    }

    IdentityErrorModal .new-identity-input Input {
        width: 100%;
    }

    IdentityErrorModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    IdentityErrorModal .button-row Button {
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
        error_type: str,
        current_identity: Identity | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.url = url
        self.message = message
        self.error_type = error_type  # "not_authorized" or "not_valid"
        self.current_identity = current_identity
        self._selected_identity: Identity | None = None
        self._creating_new = False

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        if self.error_type == "not_authorized":
            title = "Certificate Not Authorized"
        else:  # not_valid
            title = "Certificate Not Valid"
        container = Container()
        container.border_title = title
        with container:
            yield Label(self.url, classes="url-display")
            yield Label(self.message, classes="error-message")

            # Show current identity info if available
            if self.current_identity:
                with Vertical(classes="current-identity"):
                    yield Label("Current identity:", classes="current-identity-label")
                    yield Label(
                        self.current_identity.name, classes="current-identity-name"
                    )

                # Show regenerate option for invalid certificates
                if self.error_type == "not_valid":
                    with Vertical(classes="action-buttons"):
                        yield Button(
                            "Regenerate Certificate",
                            variant="warning",
                            id="regenerate-btn",
                        )

            yield Label("Switch to different identity:", classes="section-label")

            # Show other identities (excluding current)
            other_identities = [
                i
                for i in self.manager.get_all_identities()
                if self.current_identity is None or i.id != self.current_identity.id
            ]

            with VerticalScroll(classes="identity-list"):
                if other_identities:
                    for identity in other_identities:
                        yield IdentityItem(identity, id=f"identity-{identity.id}")
                else:
                    yield Label(
                        "No other identities available.",
                        classes="no-identities",
                    )

            with Vertical(classes="action-buttons"):
                yield Button(
                    "+ Create New Identity",
                    variant="default",
                    id="create-new-btn",
                )

            with Vertical(classes="new-identity-input", id="new-identity-container"):
                yield Label("Identity name:")
                yield Input(
                    placeholder="My Identity",
                    id="identity-name-input",
                )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button(
                    "Use Selected", variant="primary", id="use-btn", disabled=True
                )

    def on_mount(self) -> None:
        """Set up initial state."""
        # Pre-select first other identity if available
        other_identities = [
            i
            for i in self.manager.get_all_identities()
            if self.current_identity is None or i.id != self.current_identity.id
        ]
        if other_identities:
            self._select_identity(other_identities[0])

    def on_click(self, event) -> None:
        """Handle clicks on identity items."""
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

        # Enable the use button
        self.query_one("#use-btn", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "use-btn":
            self._use_identity()
        elif event.button.id == "create-new-btn":
            self._show_create_new()
        elif event.button.id == "regenerate-btn":
            self._regenerate_certificate()

    def _show_create_new(self) -> None:
        """Show the create new identity form."""
        self._creating_new = True
        self._selected_identity = None

        # Deselect all identity items
        for item in self.query(IdentityItem):
            item.remove_class("-selected")

        # Show the input form and enable button
        container = self.query_one("#new-identity-container")
        container.add_class("-visible")
        self.query_one("#identity-name-input", Input).focus()
        self.query_one("#use-btn", Button).disabled = False

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
            return

        self.dismiss(IdentityErrorResult(action="switch", identity=identity))

    def _regenerate_certificate(self) -> None:
        """Regenerate the current identity's certificate."""
        if self.current_identity is None:
            return

        # Extract hostname from URL
        parsed = urlparse(self.url)
        hostname = parsed.netloc

        self.manager.regenerate_certificate(self.current_identity.id, hostname)

        self.dismiss(
            IdentityErrorResult(action="regenerate", identity=self.current_identity)
        )

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
