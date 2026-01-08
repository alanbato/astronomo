"""Input modal for Gemini status 10/11 responses.

Provides a modal dialog for collecting user input when a Gemini server
requests it (search queries, passwords, etc.).
"""

from urllib.parse import quote

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea


class InputModal(ModalScreen[str | None]):
    """Modal screen for collecting user input (status 10/11 responses).

    Args:
        prompt: The prompt text from the server's META field
        url: The URL that requested input (for byte limit calculation)
        sensitive: If True, mask input (for status 11 / passwords)
        label: Optional label to show with URL (for Spartan input links)
        max_bytes: Maximum bytes for input (None for Gemini URL limit, 10240 for Spartan)
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
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    InputModal .prompt-text {
        width: 100%;
        padding: 1 0;
        color: $text;
    }

    InputModal .url-text {
        width: 100%;
        padding: 0 0 1 0;
        color: $text-muted;
        text-style: italic;
    }

    InputModal Input {
        width: 100%;
        margin-bottom: 1;
    }

    InputModal TextArea {
        width: 100%;
        height: 3;
        margin-bottom: 1;
    }

    InputModal TextArea.expanded {
        height: 8;
    }

    InputModal TextArea.large {
        height: 15;
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
        label: str | None = None,
        max_bytes: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prompt = prompt
        self.url = url
        self.sensitive = sensitive
        self.label = label
        self.max_bytes = max_bytes
        # Calculate base URL length (without query) for byte counting (Gemini mode)
        self._base_url = url.split("?")[0]
        # Thresholds for expanding the text area
        self._expand_threshold = 100  # Characters to trigger first expansion
        self._large_threshold = 300  # Characters to trigger large expansion

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        title = "Sensitive Input" if self.sensitive else "Input Required"
        container = Container()
        container.border_title = title
        with container:
            # Show label and URL if provided (Spartan input links)
            if self.label:
                yield Label(self.label, classes="prompt-text")
                yield Label(f"URL: {self.url}", classes="url-text")
            else:
                yield Label(self.prompt, classes="prompt-text")

            # Use Input for sensitive data (passwords), TextArea for regular input
            if self.sensitive:
                yield Input(
                    placeholder="Enter your response...",
                    password=True,
                    id="input-field",
                )
            else:
                yield TextArea(
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
        input_field = self.query_one("#input-field")
        input_field.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update byte counter as user types (for Input widget)."""
        if event.input.id == "input-field":
            self._update_counter_and_size(event.value)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update byte counter and handle expansion as user types (for TextArea widget)."""
        if event.text_area.id == "input-field":
            value = event.text_area.text
            self._update_counter_and_size(value)

            # Handle TextArea expansion based on input length
            text_area = event.text_area
            input_length = len(value)

            # Remove all size classes first
            text_area.remove_class("expanded", "large")

            # Apply appropriate size class based on thresholds
            if input_length >= self._large_threshold:
                text_area.add_class("large")
            elif input_length >= self._expand_threshold:
                text_area.add_class("expanded")

    def _update_counter_and_size(self, value: str) -> None:
        """Update byte counter display and styling."""
        byte_counter = self.query_one("#byte-counter", Label)
        remaining = self._calculate_remaining_bytes(value)
        byte_counter.update(self._format_byte_counter(value))

        # Update styling based on remaining bytes
        byte_counter.remove_class("-warning", "-error")
        if remaining < 0:
            byte_counter.add_class("-error")
        elif remaining < 100:
            byte_counter.add_class("-warning")

    def _calculate_remaining_bytes(self, input_value: str) -> int:
        """Calculate remaining bytes for URL or data limit.

        For Gemini (max_bytes=None): URL limit of 1024 bytes
        For Spartan (max_bytes set): Direct data limit
        """
        if self.max_bytes is not None:
            # Spartan mode: count bytes of raw input
            return self.max_bytes - len(input_value.encode("utf-8"))

        # Gemini mode: count bytes of full URL
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
            if self.max_bytes is not None:
                # Spartan mode
                return (
                    f"Input too large by {-remaining} bytes (limit: {self.max_bytes})"
                )
            else:
                # Gemini mode
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
        input_field = self.query_one("#input-field")

        # Get value based on widget type
        if isinstance(input_field, Input):
            value = input_field.value
        elif isinstance(input_field, TextArea):
            value = input_field.text
        else:
            return  # Unsupported widget type

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
