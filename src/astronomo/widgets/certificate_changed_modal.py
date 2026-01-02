"""Certificate changed modal for TOFU violations.

Provides a modal dialog when a server's certificate has changed from
what was previously trusted (Trust On First Use violation).
"""

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


@dataclass
class CertificateChangedResult:
    """Result from the certificate changed modal.

    Attributes:
        action: The action taken ("accept", "reject", or "details")
    """

    action: str


class CertificateChangedModal(ModalScreen[CertificateChangedResult | None]):
    """Modal shown when a server's certificate has changed.

    This implements TOFU (Trust On First Use) security by alerting users
    when a previously trusted server presents a different certificate.

    Args:
        hostname: The server hostname
        port: The server port
        old_fingerprint: The previously trusted fingerprint
        new_fingerprint: The new certificate fingerprint
    """

    DEFAULT_CSS = """
    CertificateChangedModal {
        align: center middle;
    }

    CertificateChangedModal > Container {
        width: 75;
        height: auto;
        max-height: 85%;
        border: thick $error;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    CertificateChangedModal .warning-icon {
        width: 100%;
        text-align: center;
        color: $error;
        text-style: bold;
        padding: 1 0;
    }

    CertificateChangedModal .warning-message {
        width: 100%;
        padding: 1;
        background: $error 10%;
        border: solid $error;
        margin: 1 0;
    }

    CertificateChangedModal .host-display {
        width: 100%;
        padding: 0 0 1 0;
        text-align: center;
        text-style: bold;
    }

    CertificateChangedModal .fingerprint-section {
        width: 100%;
        padding: 1 0;
    }

    CertificateChangedModal .fingerprint-label {
        color: $text-muted;
        padding-bottom: 0;
    }

    CertificateChangedModal .fingerprint-value {
        padding: 0 0 1 1;
    }

    CertificateChangedModal .old-fingerprint {
        color: $success;
    }

    CertificateChangedModal .new-fingerprint {
        color: $warning;
    }

    CertificateChangedModal .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        padding-top: 1;
    }

    CertificateChangedModal .button-row Button {
        margin: 0 1;
    }

    CertificateChangedModal .details-row {
        width: 100%;
        height: auto;
        align: center middle;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "reject", "Reject", show=False, priority=True),
    ]

    def __init__(
        self,
        hostname: str,
        port: int,
        old_fingerprint: str,
        new_fingerprint: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.hostname = hostname
        self.port = port
        self.old_fingerprint = old_fingerprint
        self.new_fingerprint = new_fingerprint

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Certificate Changed"
        with container:
            yield Static("WARNING", classes="warning-icon")
            yield Label(
                f"{self.hostname}:{self.port}",
                classes="host-display",
            )
            yield Label(
                "The server's certificate has changed from what was "
                "previously trusted.\n\n"
                "This could indicate:\n"
                "  - A legitimate certificate renewal\n"
                "  - A man-in-the-middle attack\n\n"
                "Verify the new certificate before accepting.",
                classes="warning-message",
            )

            with Vertical(classes="fingerprint-section"):
                yield Label("Previously trusted:", classes="fingerprint-label")
                yield Label(
                    self._truncate_fingerprint(self.old_fingerprint),
                    classes="fingerprint-value old-fingerprint",
                )
                yield Label("New certificate:", classes="fingerprint-label")
                yield Label(
                    self._truncate_fingerprint(self.new_fingerprint),
                    classes="fingerprint-value new-fingerprint",
                )

            with Horizontal(classes="button-row"):
                yield Button("Reject", variant="error", id="reject-btn")
                yield Button("Accept", variant="success", id="accept-btn")

            with Horizontal(classes="details-row"):
                yield Button(
                    "View Details",
                    variant="default",
                    id="details-btn",
                )

    def _truncate_fingerprint(self, fingerprint: str) -> str:
        """Truncate fingerprint for display, keeping prefix and showing key parts."""
        # Format: sha256:abc123...xyz789
        if fingerprint.startswith("sha256:"):
            fp = fingerprint[7:]  # Remove "sha256:" prefix
            if len(fp) > 24:
                return f"sha256:{fp[:12]}...{fp[-12:]}"
        return fingerprint

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "reject-btn":
            self.dismiss(CertificateChangedResult(action="reject"))
        elif event.button.id == "accept-btn":
            self._accept_certificate()
        elif event.button.id == "details-btn":
            self.dismiss(CertificateChangedResult(action="details"))

    def _accept_certificate(self) -> None:
        """Accept the new certificate and update TOFU database."""
        # We need to trust the new certificate
        # Since we don't have the actual certificate object here,
        # we'll signal to the app that it should retry with TOFU disabled
        # and then trust the result
        self.dismiss(CertificateChangedResult(action="accept"))

    def action_reject(self) -> None:
        """Reject the certificate (escape key)."""
        self.dismiss(CertificateChangedResult(action="reject"))
