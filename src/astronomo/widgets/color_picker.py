"""Color picker widget for Astronomo.

Provides a color selection component with preset colors and custom hex input.
"""

import re

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widgets import Button, Input, Label, Static

# Preset colors - 6 dark-friendly (muted) and 6 light-friendly (pastel)
PRESET_COLORS: list[tuple[str, str]] = [
    # Dark-friendly (muted)
    ("#4a4a5a", "Slate"),
    ("#5a3d3d", "Maroon"),
    ("#3d5a3d", "Forest"),
    ("#3d4a5a", "Navy"),
    ("#5a4a3d", "Brown"),
    ("#4a3d5a", "Purple"),
    # Light-friendly (pastel)
    ("#b0c4de", "Steel Blue"),
    ("#d4a5a5", "Rose"),
    ("#a5d4a5", "Green"),
    ("#d4d4a5", "Yellow"),
    ("#c4b0de", "Lavender"),
    ("#a5c4d4", "Cyan"),
]

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def is_valid_hex_color(value: str) -> bool:
    """Check if a string is a valid 6-digit hex color.

    Args:
        value: String to validate (should be like "#4a4a5a")

    Returns:
        True if valid hex color, False otherwise
    """
    return bool(HEX_COLOR_PATTERN.match(value))


class ColorSwatch(Button):
    """A clickable color swatch button."""

    DEFAULT_CSS = """
    ColorSwatch {
        width: 5;
        height: 1;
        min-width: 5;
        padding: 0;
        margin: 0;
    }

    ColorSwatch:hover, ColorSwatch.-selected {
        border-top: tall #eeeeee;
        border-bottom: tall #eeeeee;
    }
    """

    def __init__(self, color: str, label: str = "", **kwargs) -> None:
        super().__init__(label=" ", **kwargs)
        self.color = color
        self.styles.background = color


class ColorPicker(Container):
    """Color picker with preset swatches and custom hex input.

    Emits ColorChanged message when user selects a color.

    Args:
        current_color: Currently selected color (hex string or None)
    """

    DEFAULT_CSS = """
    ColorPicker {
        width: 100%;
        height: auto;
        padding: 1 0;
    }

    ColorPicker .color-label {
        padding: 0 0 1 0;
    }

    ColorPicker .color-swatches {
        width: 100%;
        height: auto;
        layout: grid;
        grid-size: 6 2;
        grid-gutter: 1;
        padding-bottom: 1;
    }

    ColorPicker .custom-color-row {
        width: 100%;
        height: auto;
        align: left middle;
    }

    ColorPicker .custom-color-row Label {
        width: auto;
        padding: 0 1 0 0;
    }

    ColorPicker #custom-hex-input {
        width: 12;
    }

    ColorPicker #custom-hex-input.-invalid {
        border: tall $error;
    }

    ColorPicker .preview-swatch {
        width: 5;
        height: 1;
        margin-left: 1;
        border: tall $primary;
    }

    ColorPicker #clear-color-btn {
        margin-left: 1;
    }
    """

    class ColorChanged(Message):
        """Emitted when the selected color changes."""

        def __init__(self, color: str | None) -> None:
            self.color = color
            super().__init__()

    def __init__(self, current_color: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_color = current_color

    def compose(self) -> ComposeResult:
        """Compose the color picker UI."""
        yield Label("Color:", classes="color-label")

        # Preset color swatches in a grid
        with Container(classes="color-swatches"):
            for hex_color, name in PRESET_COLORS:
                swatch = ColorSwatch(hex_color, id=f"swatch-{hex_color[1:]}")
                swatch.tooltip = name
                if hex_color == self._current_color:
                    swatch.add_class("-selected")
                yield swatch

        # Custom hex input row
        with Horizontal(classes="custom-color-row"):
            yield Label("Custom:")
            yield Input(
                value=self._current_color or "",
                placeholder="#000000",
                max_length=7,
                id="custom-hex-input",
            )
            yield Static(classes="preview-swatch", id="color-preview")
            yield Button("Clear", variant="default", id="clear-color-btn")

    def on_mount(self) -> None:
        """Update preview on mount."""
        self._update_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle custom hex input changes."""
        if event.input.id == "custom-hex-input":
            value = event.value.strip()
            input_widget = event.input

            if not value:
                # Empty is valid (means no color)
                input_widget.remove_class("-invalid")
                self._update_preview(None)
            elif is_valid_hex_color(value):
                input_widget.remove_class("-invalid")
                self._select_color(value, update_input=False)
            else:
                input_widget.add_class("-invalid")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses (color swatches and clear button)."""
        if event.button.id == "clear-color-btn":
            self._select_color(None)
        elif isinstance(event.button, ColorSwatch):
            event.stop()
            self._select_color(event.button.color)

    def _select_color(self, color: str | None, update_input: bool = True) -> None:
        """Select a color and emit change message."""
        self._current_color = color

        # Update swatch selection state
        for swatch in self.query(ColorSwatch):
            if color and swatch.color == color:
                swatch.add_class("-selected")
            else:
                swatch.remove_class("-selected")

        # Update input field if needed
        if update_input:
            input_widget = self.query_one("#custom-hex-input", Input)
            input_widget.value = color or ""
            input_widget.remove_class("-invalid")

        self._update_preview()
        self.post_message(self.ColorChanged(color))

    def _update_preview(self, color: str | None = None) -> None:
        """Update the preview swatch."""
        if color is None:
            color = self._current_color

        preview = self.query_one("#color-preview", Static)
        if color and is_valid_hex_color(color):
            preview.styles.background = color
        else:
            preview.styles.background = "transparent"

    @property
    def selected_color(self) -> str | None:
        """Get the currently selected color."""
        return self._current_color
