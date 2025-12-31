"""Import custom certificate modal for Astronomo."""

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Static

from astronomo.identities import Identity, IdentityManager

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo


class ImportCustomModal(ModalScreen[Identity | None]):
    """Modal screen for importing custom certificate/key files.

    Supports both separate cert/key files and combined PEM files.

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
        self._cert_path: Path | None = None
        self._key_path: Path | None = None

    def compose(self) -> ComposeResult:
        container = Container(id="import-custom-container")
        container.border_title = "Import Certificate"
        with container:
            yield Label("Identity Name:", classes="field-label")
            yield Input(placeholder="My Certificate", id="name-input")

            yield Label("Certificate File:", classes="field-label")
            with Horizontal(classes="path-input-row"):
                yield Input(
                    placeholder="/path/to/certificate.pem",
                    id="cert-path-input",
                    classes="path-input",
                )
                yield Button("Browse", variant="default", id="browse-cert-btn")

            yield Checkbox(
                "Certificate and key are in the same file",
                id="combined-pem-checkbox",
                value=False,
            )

            with Vertical(id="key-section"):
                yield Label("Private Key File:", classes="field-label")
                with Horizontal(classes="path-input-row"):
                    yield Input(
                        placeholder="/path/to/private.key",
                        id="key-path-input",
                        classes="path-input",
                    )
                    yield Button("Browse", variant="default", id="browse-key-btn")

            yield Static("", id="error-display", classes="error-text")

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Import", variant="primary", id="import-btn")

    def on_mount(self) -> None:
        """Focus the name input on mount."""
        self.query_one("#name-input", Input).focus()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle combined PEM checkbox toggle."""
        key_section = self.query_one("#key-section", Vertical)
        if event.value:
            key_section.add_class("hidden")
        else:
            key_section.remove_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "import-btn":
            self._perform_import()
        elif event.button.id == "browse-cert-btn":
            self._browse_for_cert()
        elif event.button.id == "browse-key-btn":
            self._browse_for_key()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in inputs."""
        if event.input.id == "name-input":
            self.query_one("#cert-path-input", Input).focus()
        elif event.input.id == "cert-path-input":
            checkbox = self.query_one("#combined-pem-checkbox", Checkbox)
            if checkbox.value:
                self._perform_import()
            else:
                self.query_one("#key-path-input", Input).focus()
        elif event.input.id == "key-path-input":
            self._perform_import()

    def _get_start_path_from_value(self, value: str) -> Path | None:
        """Get a start path from a field value, returning parent dir if file."""
        if not value:
            return None
        path = Path(value).expanduser()
        if path.exists():
            return path.parent if path.is_file() else path
        return None

    def _browse_for_cert(self) -> None:
        """Open file picker for certificate file."""
        from astronomo.widgets.certificates.file_picker_modal import FilePickerModal

        # Check if there's an existing value to use as starting directory
        cert_value = self.query_one("#cert-path-input", Input).value.strip()
        start_path = self._get_start_path_from_value(cert_value)

        # If no cert path, try using the key path as a fallback
        if start_path is None:
            key_value = self.query_one("#key-path-input", Input).value.strip()
            start_path = self._get_start_path_from_value(key_value)

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            FilePickerModal(title="Select Certificate File", start_path=start_path),
            callback=self._on_cert_selected,
        )

    def _on_cert_selected(self, path: Path | None) -> None:
        """Handle certificate file selection."""
        if path is not None:
            self._cert_path = path
            cert_input = self.query_one("#cert-path-input", Input)
            cert_input.value = str(path)

    def _browse_for_key(self) -> None:
        """Open file picker for key file."""
        from astronomo.widgets.certificates.file_picker_modal import FilePickerModal

        # Check if there's an existing value to use as starting directory
        key_value = self.query_one("#key-path-input", Input).value.strip()
        start_path = self._get_start_path_from_value(key_value)

        # If no key path, try using the cert path as a fallback
        if start_path is None:
            cert_value = self.query_one("#cert-path-input", Input).value.strip()
            start_path = self._get_start_path_from_value(cert_value)

        app: Astronomo = self.app  # type: ignore[assignment]
        app.push_screen(
            FilePickerModal(title="Select Private Key File", start_path=start_path),
            callback=self._on_key_selected,
        )

    def _on_key_selected(self, path: Path | None) -> None:
        """Handle key file selection."""
        if path is not None:
            self._key_path = path
            key_input = self.query_one("#key-path-input", Input)
            key_input.value = str(path)

    def _clear_error(self) -> None:
        """Clear any displayed error."""
        error_display = self.query_one("#error-display", Static)
        error_display.update("")

    def _show_error(self, message: str) -> None:
        """Display an error message."""
        error_display = self.query_one("#error-display", Static)
        error_display.update(message)

    def _validate_inputs(self) -> tuple[str, Path, Path | None] | None:
        """Validate inputs and return (name, cert_path, key_path) or None on error."""
        self._clear_error()

        # Get name
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            name = "Imported Certificate"

        # Get cert path
        cert_path_str = self.query_one("#cert-path-input", Input).value.strip()
        if not cert_path_str:
            self._show_error("Please specify a certificate file path")
            self.query_one("#cert-path-input", Input).focus()
            return None

        cert_path = Path(cert_path_str).expanduser()
        if not cert_path.exists():
            self._show_error(f"Certificate file not found: {cert_path}")
            self.query_one("#cert-path-input", Input).focus()
            return None

        # Check if combined PEM
        combined = self.query_one("#combined-pem-checkbox", Checkbox).value

        if combined:
            # Combined mode - no key path needed
            return (name, cert_path, None)
        else:
            # Separate files mode - need key path
            key_path_str = self.query_one("#key-path-input", Input).value.strip()
            if not key_path_str:
                self._show_error("Please specify a private key file path")
                self.query_one("#key-path-input", Input).focus()
                return None

            key_path = Path(key_path_str).expanduser()
            if not key_path.exists():
                self._show_error(f"Key file not found: {key_path}")
                self.query_one("#key-path-input", Input).focus()
                return None

            return (name, cert_path, key_path)

    def _perform_import(self) -> None:
        """Perform the import and dismiss with result."""
        validated = self._validate_inputs()
        if validated is None:
            return

        name, cert_path, key_path = validated

        try:
            identity = self.manager.import_identity_from_custom_files(
                name=name,
                cert_path=cert_path,
                key_path=key_path,
            )
            self.notify(f"Imported identity: {identity.name}", severity="information")
            self.dismiss(identity)
        except FileNotFoundError as e:
            self._show_error(str(e))
        except ValueError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"Import failed: {e}")

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
