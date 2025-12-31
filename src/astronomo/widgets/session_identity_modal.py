"""Session identity selection modal.

Provides a modal dialog for selecting an identity before making a request
to a URL where one or more identities are available. The selection is
remembered for the duration of the session.
"""

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from astronomo.identities import Identity, IdentityManager


@dataclass
class SessionIdentityResult:
    """Result from the session identity selection modal.

    Attributes:
        identity: The selected identity, or None for anonymous browsing
        cancelled: True if the user cancelled the navigation
    """

    identity: Identity | None
    cancelled: bool = False


class IdentityOption(Static):
    """A selectable identity option in the list."""

    DEFAULT_CSS = """
    IdentityOption {
        width: 100%;
        height: 3;
        padding: 0 1;
        border: solid transparent;
    }

    IdentityOption:hover {
        background: $surface-lighten-1;
    }

    IdentityOption.-selected {
        background: $primary;
        border: solid $primary-lighten-1;
    }

    IdentityOption .option-name {
        text-style: bold;
    }

    IdentityOption .option-detail {
        color: $text-muted;
    }

    IdentityOption.-anonymous .option-name {
        color: $text-muted;
    }
    """

    def __init__(
        self, identity: Identity | None, is_anonymous: bool = False, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.identity = identity
        self.is_anonymous = is_anonymous
        if is_anonymous:
            self.add_class("-anonymous")

    def compose(self) -> ComposeResult:
        """Compose the identity option."""
        if self.is_anonymous:
            yield Label("Continue without identity", classes="option-name")
            yield Label("Browse anonymously", classes="option-detail")
        else:
            assert self.identity is not None
            short_fp = self.identity.fingerprint[:24] + "..."
            yield Label(self.identity.name, classes="option-name")
            yield Label(short_fp, classes="option-detail")


class SessionIdentityModal(ModalScreen[SessionIdentityResult]):
    """Modal screen for selecting identity before making a request.

    Shows available identities for the URL and allows:
    - Selecting an existing identity
    - Continuing without an identity (anonymous)
    - Cancelling the navigation

    Args:
        manager: IdentityManager instance
        url: The URL being navigated to
        matching_identities: Pre-filtered list of identities that match the URL
    """

    DEFAULT_CSS = """
    SessionIdentityModal {
        align: center middle;
    }

    SessionIdentityModal > Container {
        width: 70;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    SessionIdentityModal .url-display {
        width: 100%;
        padding: 0 0 1 0;
        color: $text-muted;
    }

    SessionIdentityModal .info-text {
        width: 100%;
        padding: 1 0;
        color: $text;
    }

    SessionIdentityModal .identity-list {
        width: 100%;
        height: auto;
        max-height: 15;
        border: solid $primary;
        margin: 1 0;
    }

    SessionIdentityModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    SessionIdentityModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "use_selected", "Use Selected", show=False, priority=True),
    ]

    def __init__(
        self,
        manager: IdentityManager,
        url: str,
        matching_identities: list[Identity],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.url = url
        self.matching_identities = matching_identities
        self._selected_identity: Identity | None = None
        self._is_anonymous_selected = False

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Select Identity"
        with container:
            yield Label(self._truncate_url(self.url), classes="url-display")
            yield Label(
                "One or more identities are available for this site.",
                classes="info-text",
            )

            with VerticalScroll(classes="identity-list"):
                # Anonymous option first
                yield IdentityOption(
                    identity=None, is_anonymous=True, id="option-anonymous"
                )

                # Then all matching identities
                for identity in self.matching_identities:
                    yield IdentityOption(identity, id=f"option-{identity.id}")

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Use Selected", variant="primary", id="use-btn")

    def _truncate_url(self, url: str, max_length: int = 60) -> str:
        """Truncate URL for display if too long."""
        if len(url) <= max_length:
            return url
        return url[: max_length - 3] + "..."

    def on_mount(self) -> None:
        """Set up initial state - pre-select first identity."""
        if self.matching_identities:
            self._select_identity(self.matching_identities[0])
        else:
            self._select_anonymous()

    def on_click(self, event) -> None:
        """Handle clicks on identity options."""
        widget = event.widget
        while widget is not None:
            if isinstance(widget, IdentityOption):
                if widget.is_anonymous:
                    self._select_anonymous()
                else:
                    self._select_identity(widget.identity)
                break
            widget = getattr(widget, "parent", None)

    def _select_identity(self, identity: Identity | None) -> None:
        """Select an identity and update UI."""
        self._selected_identity = identity
        self._is_anonymous_selected = False
        self._update_selection_ui()

    def _select_anonymous(self) -> None:
        """Select anonymous browsing."""
        self._selected_identity = None
        self._is_anonymous_selected = True
        self._update_selection_ui()

    def _update_selection_ui(self) -> None:
        """Update visual selection state."""
        for option in self.query(IdentityOption):
            if option.is_anonymous:
                if self._is_anonymous_selected:
                    option.add_class("-selected")
                else:
                    option.remove_class("-selected")
            elif option.identity is not None:
                if (
                    self._selected_identity is not None
                    and option.identity.id == self._selected_identity.id
                ):
                    option.add_class("-selected")
                else:
                    option.remove_class("-selected")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "use-btn":
            self.action_use_selected()

    def action_use_selected(self) -> None:
        """Use the selected identity and dismiss."""
        if self._is_anonymous_selected:
            self.dismiss(SessionIdentityResult(identity=None, cancelled=False))
        elif self._selected_identity is not None:
            self.dismiss(
                SessionIdentityResult(identity=self._selected_identity, cancelled=False)
            )
        # If nothing is selected (shouldn't happen), do nothing

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(SessionIdentityResult(identity=None, cancelled=True))
