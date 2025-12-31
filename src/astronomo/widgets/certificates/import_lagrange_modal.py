"""Import from Lagrange modal for Astronomo."""

from pathlib import Path

from nauyaca.security.certificates import get_certificate_fingerprint_from_path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from astronomo.identities import (
    IdentityManager,
    LagrangeImportResult,
    get_lagrange_idents_path,
)


class ImportLagrangeModal(ModalScreen[LagrangeImportResult | None]):
    """Modal screen for importing identities from Lagrange.

    Shows a preview of identities to import and handles the import workflow.

    Args:
        manager: IdentityManager instance
    """

    CSS_PATH = Path(__file__).parent / "certificates.tcss"

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(self, manager: IdentityManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self._lagrange_path: Path | None = None
        self._discovered: list[tuple[str, Path, Path]] = []
        # Map index to (cert_path, fingerprint, is_duplicate)
        self._importable: dict[int, tuple[Path, str, bool]] = {}

    def compose(self) -> ComposeResult:
        container = Container(id="import-lagrange-container")
        container.border_title = "Import from Lagrange"
        with container:
            # Check for Lagrange directory
            self._lagrange_path = get_lagrange_idents_path()

            if self._lagrange_path is None:
                yield Static(
                    "Lagrange idents directory not found.\n\n"
                    "Make sure Lagrange is installed and has created identities.",
                    classes="warning-text",
                )
                with Horizontal(classes="button-row"):
                    yield Button("Close", variant="default", id="close-btn")
            else:
                # Discover identities
                self._discovered = self.manager.discover_lagrange_identities(
                    self._lagrange_path
                )

                if not self._discovered:
                    yield Static(
                        f"No identities found in:\n{self._lagrange_path}",
                        classes="info-text",
                    )
                    with Horizontal(classes="button-row"):
                        yield Button("Close", variant="default", id="close-btn")
                else:
                    yield Static(
                        f"Found {len(self._discovered)} identity(ies) in Lagrange.",
                        classes="info-text",
                    )
                    yield Static(
                        "Set a name for each identity to import:",
                        classes="field-label",
                    )

                    with VerticalScroll(classes="identity-preview-list"):
                        for idx, (name, cert_path, _key_path) in enumerate(
                            self._discovered
                        ):
                            # Check if already imported (by fingerprint)
                            try:
                                fingerprint = get_certificate_fingerprint_from_path(
                                    cert_path
                                )
                                is_duplicate = (
                                    self.manager.has_identity_with_fingerprint(
                                        fingerprint
                                    )
                                )
                            except Exception:
                                fingerprint = "unknown"
                                is_duplicate = False

                            # Store for import using index as key
                            self._importable[idx] = (
                                cert_path,
                                fingerprint,
                                is_duplicate,
                            )

                            # Truncate fingerprint for display
                            short_fp = (
                                fingerprint[:24] + "..."
                                if len(fingerprint) > 24
                                else fingerprint
                            )

                            with Horizontal(classes="identity-import-row"):
                                if is_duplicate:
                                    yield Static(
                                        f"  {short_fp} (already imported)",
                                        classes="identity-duplicate",
                                    )
                                else:
                                    yield Input(
                                        value=name,
                                        placeholder="Identity name (required)",
                                        id=f"name-{idx}",
                                        classes="identity-name-input",
                                    )
                                    yield Static(
                                        short_fp, classes="identity-fingerprint"
                                    )

                    yield Static(
                        "Note: URL associations cannot be imported from Lagrange.",
                        classes="field-hint",
                    )

                    with Horizontal(classes="button-row"):
                        yield Button("Cancel", variant="default", id="cancel-btn")
                        yield Button("Import", variant="primary", id="import-btn")

    def on_mount(self) -> None:
        """Focus first input on mount."""
        inputs = self.query("Input")
        if inputs:
            inputs.first().focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id in ("close-btn", "cancel-btn"):
            self.dismiss(None)
        elif event.button.id == "import-btn":
            self._perform_import()

    def _get_names_dict(self) -> dict[Path, str]:
        """Collect names from input fields."""
        names: dict[Path, str] = {}
        for idx, (cert_path, _, is_duplicate) in self._importable.items():
            if is_duplicate:
                continue
            try:
                input_widget = self.query_one(f"#name-{idx}", Input)
                name = input_widget.value.strip()
                if name:
                    names[cert_path] = name
            except Exception:
                pass
        return names

    def _validate_names(self) -> bool:
        """Check that all non-duplicate identities have names."""
        for idx, (_, _, is_duplicate) in self._importable.items():
            if is_duplicate:
                continue
            try:
                input_widget = self.query_one(f"#name-{idx}", Input)
                if not input_widget.value.strip():
                    input_widget.focus()
                    return False
            except Exception:
                return False
        return True

    def _perform_import(self) -> None:
        """Perform the import and dismiss with result."""
        if self._lagrange_path is None:
            self.dismiss(None)
            return

        if not self._validate_names():
            self.notify("Please provide a name for each identity", severity="error")
            return

        names = self._get_names_dict()
        result = self.manager.import_from_lagrange(self._lagrange_path, names=names)
        self.dismiss(result)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
