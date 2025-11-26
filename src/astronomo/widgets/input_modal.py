"""Input modal for Gemini status 10/11 responses.

Provides a modal dialog for collecting user input when a Gemini server
requests it (search queries, passwords, etc.).
"""

from urllib.parse import quote

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class InputModal(ModalScreen[str | None]):
    """Modal screen for collecting user input (status 10/11 responses).

    Args:
        prompt: The prompt text from the server's META field
        url: The URL that requested input (for byte limit calculation)
        sensitive: If True, mask input (for status 11 / passwords)
    """

    DEFAULT_CSS = """
    InputModal {
        align: center middle;
    }

    InputModal > Container {
        width: 70;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    InputModal .modal-title {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        padding-bottom: 1;
    }

    InputModal .prompt-text {
        width: 100%;
        padding: 1 0;
        color: $text;
    }

    InputModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    InputModal .byte-counter {
        width: 100%;
        text-align: right;
        color: $text-muted;
        padding-bottom: 1;
    }

    InputModal .byte-counter.-warning {
        color: $warning;
    }

    InputModal .byte-counter.-error {
        color: $error;
    }

    InputModal .button-row {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    InputModal .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("enter", "submit", "Submit", show=False, priority=True),
    ]

    def __init__(
        self,
        prompt: str,
        url: str,
        sensitive: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prompt = prompt
        self.url = url
        self.sensitive = sensitive
        # Calculate base URL length (without query) for byte counting
        self._base_url = url.split("?")[0]

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        title = "Sensitive Input" if self.sensitive else "Input Required"

        with Container():
            yield Label(title, classes="modal-title")
            yield Label(self.prompt, classes="prompt-text")
            yield Input(
                placeholder="Enter your response...",
                password=self.sensitive,
                id="input-field",
            )
            yield Label(
                self._format_byte_counter(""), id="byte-counter", classes="byte-counter"
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Submit", variant="primary", id="submit-btn")

    def on_mount(self) -> None:
        """Focus the input field on mount."""
        self.query_one("#input-field", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update byte counter as user types."""
        if event.input.id == "input-field":
            byte_counter = self.query_one("#byte-counter", Label)
            remaining = self._calculate_remaining_bytes(event.value)
            byte_counter.update(self._format_byte_counter(event.value))

            # Update styling based on remaining bytes
            byte_counter.remove_class("-warning", "-error")
            if remaining < 0:
                byte_counter.add_class("-error")
            elif remaining < 100:
                byte_counter.add_class("-warning")

    def _calculate_remaining_bytes(self, input_value: str) -> int:
        """Calculate remaining bytes for URL limit.

        The Gemini spec limits URLs to 1024 bytes.
        """
        if not input_value:
            # Just the base URL + "?" if there's input
            return 1024 - len(self._base_url.encode("utf-8")) - 1

        encoded_query = quote(input_value)
        full_url = f"{self._base_url}?{encoded_query}"
        return 1024 - len(full_url.encode("utf-8"))

    def _format_byte_counter(self, input_value: str) -> str:
        """Format the byte counter display."""
        remaining = self._calculate_remaining_bytes(input_value)
        if remaining < 0:
            return f"URL too long by {-remaining} bytes"
        return f"{remaining} bytes remaining"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "submit-btn":
            self._submit_input()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field."""
        if event.input.id == "input-field":
            self._submit_input()

    def _submit_input(self) -> None:
        """Submit the input and dismiss the modal."""
        input_field = self.query_one("#input-field", Input)
        value = input_field.value

        # Check if URL would be too long
        if self._calculate_remaining_bytes(value) < 0:
            # Don't submit if over limit
            return

        self.dismiss(value)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_submit(self) -> None:
        """Submit the input and close the modal."""
        self._submit_input()
