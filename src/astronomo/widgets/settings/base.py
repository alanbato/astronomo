"""Base classes for settings widgets."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Select, Static, Switch


class WidgetType(Enum):
    """Types of setting widgets."""

    SELECT = auto()
    INPUT_TEXT = auto()
    INPUT_NUMBER = auto()
    SWITCH = auto()


@dataclass
class SettingDefinition:
    """Definition for a configurable setting.

    Attributes:
        key: Dot-notation path to the setting (e.g., "appearance.theme")
        label: Display label for the setting
        widget_type: Type of widget to render
        description: Help text shown below the widget
        options: For SELECT type, list of (label, value) tuples
        default: Default value for the setting
        placeholder: Placeholder text for input widgets
    """

    key: str
    label: str
    widget_type: WidgetType
    description: str
    options: list[tuple[str, Any]] | None = None
    default: Any = None
    placeholder: str = ""


class SettingRow(Static):
    """A single setting row with label, widget, and description."""

    DEFAULT_CSS = """
    SettingRow {
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
    }

    SettingRow .setting-content {
        height: auto;
    }

    SettingRow .setting-row-inner {
        height: auto;
        align: left middle;
    }

    SettingRow .setting-label {
        width: 20;
        padding: 1 2 1 0;
    }

    SettingRow .setting-widget {
        width: 1fr;
        max-width: 40;
    }

    SettingRow .setting-switch {
        width: 0.5fr;
        max-width: 20;
    }


    SettingRow .setting-description {
        color: $text-muted;
        text-style: italic;
        padding: 0 0 0 0;
    }
    """

    def __init__(
        self,
        definition: SettingDefinition,
        current_value: Any,
        on_change: Callable[[str, Any], None],
        **kwargs: Any,
    ) -> None:
        """Initialize a setting row.

        Args:
            definition: The setting definition
            current_value: The current value of the setting
            on_change: Callback when value changes (key, new_value)
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.definition = definition
        self.current_value = current_value
        self.on_change = on_change

    def compose(self) -> ComposeResult:
        with Vertical(classes="setting-content"):
            with Horizontal(classes="setting-row-inner"):
                yield Label(self.definition.label, classes="setting-label")
                yield self._create_widget()
            yield Label(self.definition.description, classes="setting-description")

    def _create_widget(self) -> Static | Input | Select[Any] | Switch:
        """Create the appropriate widget for this setting type."""
        widget_id = f"setting-{self.definition.key.replace('.', '-')}"

        match self.definition.widget_type:
            case WidgetType.SELECT:
                return Select(
                    options=self.definition.options or [],
                    value=self.current_value,
                    id=widget_id,
                    classes="setting-widget",
                    allow_blank=False,
                )
            case WidgetType.INPUT_TEXT:
                return Input(
                    value=self.current_value or "",
                    placeholder=self.definition.placeholder,
                    id=widget_id,
                    classes="setting-widget",
                )
            case WidgetType.INPUT_NUMBER:
                return Input(
                    value=str(self.current_value) if self.current_value else "",
                    placeholder=self.definition.placeholder,
                    type="integer",
                    id=widget_id,
                    classes="setting-widget",
                )
            case WidgetType.SWITCH:
                return Switch(
                    value=bool(self.current_value),
                    id=widget_id,
                    classes="setting-widget setting-switch",
                )
            case _:
                # This should never happen if all WidgetType cases are handled
                raise ValueError(f"Unknown widget type: {self.definition.widget_type}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        widget_id = f"setting-{self.definition.key.replace('.', '-')}"
        if event.select.id == widget_id:
            self.on_change(self.definition.key, event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input widget changes."""
        widget_id = f"setting-{self.definition.key.replace('.', '-')}"
        if event.input.id == widget_id:
            value: Any = event.value
            if self.definition.widget_type == WidgetType.INPUT_NUMBER:
                try:
                    value = int(value) if value else self.definition.default
                except ValueError:
                    return  # Invalid number, don't save
            self.on_change(self.definition.key, value)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch widget changes."""
        widget_id = f"setting-{self.definition.key.replace('.', '-')}"
        if event.switch.id == widget_id:
            self.on_change(self.definition.key, event.value)
