"""Tab bar widget for displaying and managing browser tabs."""

from textual.containers import Container, Horizontal, HorizontalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static

from astronomo.tabs import Tab


class TabButton(Horizontal):
    """A single tab button with title and close button.

    Displays the tab title and provides click-to-select and close functionality.
    """

    DEFAULT_CSS = """
    TabButton {
        width: auto;
        height: 1;
        min-width: 8;
        max-width: 25;
        padding: 0 1;
        background: $surface;
        border-right: solid $primary-darken-2;
        color: $text;
    }

    TabButton:hover {
        background: $surface-lighten-1;
    }

    TabButton.-active {
        background: $accent-muted;
    }

    TabButton.-active:hover {
        background: $accent-muted;
    }

    TabButton .tab-title {
        width: 1fr;
        height: 1;
        content-align: left middle;
        text-overflow: ellipsis;
        overflow: hidden;
    }

    TabButton .tab-close {
        width: 3;
        min-width: 3;
        height: 1;
        padding: 0;
        border: none;
        background: transparent;
        content-align: center middle;
    }

    TabButton .tab-close:hover {
        color: $error;
        background: $error-muted;
    }
    """

    class Clicked(Message):
        """Message sent when tab is clicked (not close button)."""

        def __init__(self, tab_id: str) -> None:
            self.tab_id = tab_id
            super().__init__()

    class CloseClicked(Message):
        """Message sent when close button is clicked."""

        def __init__(self, tab_id: str) -> None:
            self.tab_id = tab_id
            super().__init__()

    active: reactive[bool] = reactive(False)

    def __init__(self, tab_id: str, title: str, active: bool = False) -> None:
        super().__init__()
        self.tab_id = tab_id
        self._title = title
        self.active = active

    def compose(self):
        yield Static(self._title, classes="tab-title")
        yield Button("\u00d7", classes="tab-close")  # × symbol

    def watch_active(self, active: bool) -> None:
        """Update styling when active state changes."""
        if active:
            self.add_class("-active")
        else:
            self.remove_class("-active")

    def update_title(self, title: str) -> None:
        """Update the displayed title."""
        self._title = title
        title_widget = self.query_one(".tab-title", Static)
        title_widget.update(title)

    def on_click(self, event) -> None:
        """Handle click on tab (but not close button)."""
        # Check if click was on close button
        if event.widget.has_class("tab-close"):
            return
        self.post_message(self.Clicked(self.tab_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button press."""
        if event.button.has_class("tab-close"):
            event.stop()
            self.post_message(self.CloseClicked(self.tab_id))


class TabBar(Container):
    """Horizontal bar containing all tab buttons and new tab button.

    Displays tabs in order with the ability to select, close, and create tabs.
    Supports horizontal scrolling when many tabs are open.
    """

    DEFAULT_CSS = """
    TabBar {
        dock: top;
        height: 1;
        width: 100%;
        background: $surface-darken-1;
    }

    TabBar > HorizontalScroll {
        width: 100%;
        height: 1;
        scrollbar-size: 0 0;
    }

    TabBar #new-tab-button {
        width: 4;
        min-width: 4;
        height: 1;
        padding: 0;
        border: none;
        background: $surface;
        color: $text-accent;
        content-align: center middle;
    }

    TabBar #new-tab-button:hover {
        background: $surface-lighten-1;
        color: $accent;
    }
    """

    class TabSelected(Message):
        """Message sent when a tab is selected."""

        def __init__(self, tab_id: str) -> None:
            self.tab_id = tab_id
            super().__init__()

    class TabCloseRequested(Message):
        """Message sent when a tab close is requested."""

        def __init__(self, tab_id: str) -> None:
            self.tab_id = tab_id
            super().__init__()

    class NewTabRequested(Message):
        """Message sent when new tab button is clicked."""

    def compose(self):
        with HorizontalScroll(id="tabs-scroll"):
            yield Button("+", id="new-tab-button")

    def update_tabs(self, tabs: list[Tab], active_tab_id: str) -> None:
        """Update the tab bar with the current tab list.

        Args:
            tabs: List of tabs in display order
            active_tab_id: ID of the currently active tab
        """
        scroll = self.query_one("#tabs-scroll", HorizontalScroll)
        new_tab_button = self.query_one("#new-tab-button", Button)

        # Remove all existing tab buttons
        for button in list(scroll.query(TabButton)):
            button.remove()

        # Add new tab buttons before the new-tab-button
        for tab in tabs:
            is_active = tab.id == active_tab_id
            button = TabButton(tab.id, tab.title, active=is_active)
            scroll.mount(button, before=new_tab_button)

    def set_active_tab(self, tab_id: str) -> None:
        """Set which tab is visually active.

        Args:
            tab_id: ID of the tab to mark as active
        """
        scroll = self.query_one("#tabs-scroll", HorizontalScroll)
        for button in scroll.query(TabButton):
            button.active = button.tab_id == tab_id

    def update_tab_title(self, tab_id: str, title: str) -> None:
        """Update a specific tab's title.

        Args:
            tab_id: ID of the tab to update
            title: New title to display
        """
        scroll = self.query_one("#tabs-scroll", HorizontalScroll)
        for button in scroll.query(TabButton):
            if button.tab_id == tab_id:
                button.update_title(title)
                break

    def on_tab_button_clicked(self, message: TabButton.Clicked) -> None:
        """Handle tab selection."""
        self.post_message(self.TabSelected(message.tab_id))

    def on_tab_button_close_clicked(self, message: TabButton.CloseClicked) -> None:
        """Handle tab close request."""
        self.post_message(self.TabCloseRequested(message.tab_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle new tab button press."""
        if event.button.id == "new-tab-button":
            event.stop()
            self.post_message(self.NewTabRequested())
