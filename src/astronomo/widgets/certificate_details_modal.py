"""Certificate details modal for viewing full certificate comparison.

Shows detailed fingerprint and host information for TOFU decisions.
"""

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


@dataclass
class CertificateDetailsResult:
    """Result from the certificate details modal.

    Attributes:
        action: The action taken ("accept" or "reject")
    """

    action: str


class CertificateDetailsModal(ModalScreen[CertificateDetailsResult | None]):
    """Modal showing detailed certificate comparison.

    Displays full fingerprints and host metadata to help users make
    informed decisions about certificate changes.

    Args:
        hostname: The server hostname
        port: The server port
        old_fingerprint: The previously trusted fingerprint
        new_fingerprint: The new certificate fingerprint
        first_seen: When the host was first trusted (ISO format)
        last_seen: When the host was last accessed (ISO format)
    """

    DEFAULT_CSS = """
    CertificateDetailsModal {
        align: center middle;
    }

    CertificateDetailsModal > Container {
        width: 85;
        height: auto;
        max-height: 90%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    CertificateDetailsModal .host-display {
        width: 100%;
        padding: 1 0;
        text-align: center;
        text-style: bold;
    }

    CertificateDetailsModal .section-title {
        width: 100%;
        text-style: bold;
        padding: 1 0 0 0;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    CertificateDetailsModal .fingerprint-block {
        width: 100%;
        padding: 1;
        margin-bottom: 1;
    }

    CertificateDetailsModal .old-block {
        background: $success 10%;
        border: solid $success;
    }

    CertificateDetailsModal .new-block {
        background: $warning 10%;
        border: solid $warning;
    }

    CertificateDetailsModal .fingerprint-header {
        text-style: bold;
        padding-bottom: 1;
    }

    CertificateDetailsModal .fingerprint-full {
        width: 100%;
    }

    CertificateDetailsModal .metadata-row {
        width: 100%;
        height: auto;
        padding: 0 0 0 1;
    }

    CertificateDetailsModal .metadata-label {
        width: 15;
        color: $text-muted;
    }

    CertificateDetailsModal .metadata-value {
        width: 1fr;
    }

    CertificateDetailsModal .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        padding-top: 2;
    }

    CertificateDetailsModal .button-row Button {
        margin: 0 2;
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
        first_seen: str | None = None,
        last_seen: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.hostname = hostname
        self.port = port
        self.old_fingerprint = old_fingerprint
        self.new_fingerprint = new_fingerprint
        self.first_seen = first_seen
        self.last_seen = last_seen

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        container = Container()
        container.border_title = "Certificate Details"
        with container:
            yield Label(
                f"{self.hostname}:{self.port}",
                classes="host-display",
            )

            yield Label("Previously Trusted Certificate", classes="section-title")
            with Vertical(classes="fingerprint-block old-block"):
                yield Label("Fingerprint (SHA-256):", classes="fingerprint-header")
                yield Static(
                    self._format_fingerprint(self.old_fingerprint),
                    classes="fingerprint-full",
                )

            if self.first_seen or self.last_seen:
                with Horizontal(classes="metadata-row"):
                    yield Label("First seen:", classes="metadata-label")
                    yield Label(
                        self._format_date(self.first_seen),
                        classes="metadata-value",
                    )
                with Horizontal(classes="metadata-row"):
                    yield Label("Last seen:", classes="metadata-label")
                    yield Label(
                        self._format_date(self.last_seen),
                        classes="metadata-value",
                    )

            yield Label("New Certificate", classes="section-title")
            with Vertical(classes="fingerprint-block new-block"):
                yield Label("Fingerprint (SHA-256):", classes="fingerprint-header")
                yield Static(
                    self._format_fingerprint(self.new_fingerprint),
                    classes="fingerprint-full",
                )

            with Horizontal(classes="button-row"):
                yield Button("Reject", variant="error", id="reject-btn")
                yield Button("Accept & Trust", variant="success", id="accept-btn")

    def _format_fingerprint(self, fingerprint: str) -> str:
        """Format fingerprint for readable display."""
        # Remove sha256: prefix if present
        if fingerprint.startswith("sha256:"):
            fp = fingerprint[7:]
        else:
            fp = fingerprint

        # Split into groups of 4 for readability
        groups = [fp[i : i + 4] for i in range(0, len(fp), 4)]
        # Join with spaces, 8 groups per line (32 chars)
        lines = []
        for i in range(0, len(groups), 8):
            lines.append(" ".join(groups[i : i + 8]))
        return "\n".join(lines)

    def _format_date(self, date_str: str | None) -> str:
        """Format ISO date for display."""
        if not date_str:
            return "Unknown"
        # Parse ISO format and display nicely
        try:
            # Just show the date and time, strip timezone
            if "T" in date_str:
                date_part, time_part = date_str.split("T")
                time_part = time_part.split("+")[0].split("Z")[0]
                # Truncate to seconds
                if "." in time_part:
                    time_part = time_part.split(".")[0]
                return f"{date_part} {time_part}"
        except (ValueError, IndexError):
            pass
        return date_str

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "reject-btn":
            self.dismiss(CertificateDetailsResult(action="reject"))
        elif event.button.id == "accept-btn":
            self.dismiss(CertificateDetailsResult(action="accept"))

    def action_reject(self) -> None:
        """Reject the certificate (escape key)."""
        self.dismiss(CertificateDetailsResult(action="reject"))
