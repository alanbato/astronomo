"""File picker modal for selecting certificate/key files."""

from collections.abc import Iterable
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DirectoryTree, Input, Label, Static


class CertificateFileTree(DirectoryTree):
    """DirectoryTree filtered to show only certificate-related files."""

    CERTIFICATE_EXTENSIONS = {".pem", ".crt", ".key", ".cert"}

    def __init__(self, path: Path, show_hidden: bool = False, **kwargs) -> None:
        super().__init__(path, **kwargs)
        self.show_hidden = show_hidden

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter to show only directories and certificate files."""
        result = []
        for path in paths:
            # Skip hidden files unless show_hidden is True
            if not self.show_hidden and path.name.startswith("."):
                continue
            # Include directories and certificate files
            if path.is_dir() or path.suffix.lower() in self.CERTIFICATE_EXTENSIONS:
                result.append(path)
        return result


class FilePickerModal(ModalScreen[Path | None]):
    """Modal screen for selecting a certificate or key file.

    Uses a DirectoryTree to browse the filesystem and select files.

    Args:
        title: Title to display in the modal
        start_path: Initial directory to show (defaults to home)
    """

    CSS_PATH = Path(__file__).parent / "certificates.tcss"

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        title: str = "Select File",
        start_path: Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.start_path = start_path or Path.home()
        self._selected_path: Path | None = None
        self._show_hidden = False

    def compose(self) -> ComposeResult:
        container = Container(id="file-picker-container")
        container.border_title = self.title_text
        with container:
            yield Label("Path:", classes="field-label")
            with Horizontal(classes="path-input-row"):
                yield Input(
                    value=str(self.start_path),
                    id="path-input",
                    classes="path-input",
                )
                yield Button("..", variant="default", id="parent-dir-btn")

            yield CertificateFileTree(
                self.start_path,
                show_hidden=self._show_hidden,
                id="file-tree",
            )

            with Horizontal(classes="file-picker-options"):
                yield Checkbox("Show hidden files", id="show-hidden-checkbox")

            yield Static(
                "No file selected",
                id="selected-file-label",
                classes="selected-file",
            )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button(
                    "Select", variant="primary", id="select-btn", disabled=True
                )

    def on_mount(self) -> None:
        """Focus the directory tree on mount."""
        self.query_one("#file-tree", DirectoryTree).focus()

    def on_key(self, event) -> None:
        """Handle Enter key to confirm selection when not in input."""
        if event.key == "enter":
            # If Input is focused, let it handle Enter via on_input_submitted
            path_input = self.query_one("#path-input", Input)
            if path_input.has_focus:
                return
            # Otherwise, if a file is selected, dismiss with it
            if self._selected_path is not None:
                event.prevent_default()
                event.stop()
                self.dismiss(self._selected_path)

    async def _replace_tree(self, new_path: Path) -> None:
        """Replace the directory tree with a new one rooted at new_path."""
        old_tree = self.query_one("#file-tree", CertificateFileTree)

        # Create new tree with updated path
        new_tree = CertificateFileTree(
            new_path,
            show_hidden=self._show_hidden,
            id="file-tree",
        )

        # Replace the old tree by mounting the new one in the same position
        await old_tree.remove()
        container = self.query_one("#file-picker-container", Container)
        # Mount after the path-input-row Horizontal container
        path_input_row = self.query_one(".path-input-row", Horizontal)
        await container.mount(new_tree, after=path_input_row)

        # Update the path input
        path_input = self.query_one("#path-input", Input)
        path_input.value = str(new_path)

        # Clear selection since tree was replaced
        self._selected_path = None
        selected_label = self.query_one("#selected-file-label", Static)
        selected_label.update("No file selected")
        select_btn = self.query_one("#select-btn", Button)
        select_btn.disabled = True

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle show hidden files checkbox toggle."""
        if event.checkbox.id == "show-hidden-checkbox":
            self._show_hidden = event.value

            # Get current tree and its path
            old_tree = self.query_one("#file-tree", CertificateFileTree)
            current_path = Path(old_tree.path)

            await self._replace_tree(current_path)

    def _select_file(self, path: Path) -> None:
        """Select a file (update UI state without dismissing)."""
        self._selected_path = path

        # Update path input
        path_input = self.query_one("#path-input", Input)
        path_input.value = str(path)

        # Update selected label
        selected_label = self.query_one("#selected-file-label", Static)
        selected_label.update(f"Selected: {path.name}")

        # Enable select button
        select_btn = self.query_one("#select-btn", Button)
        select_btn.disabled = False

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle path input submission."""
        if event.input.id == "path-input":
            path_str = event.value.strip()
            if not path_str:
                return

            path = Path(path_str).expanduser()

            if not path.exists():
                self.notify(f"Path does not exist: {path}", severity="error")
                return

            if path.is_file():
                # Check if it's a valid certificate file
                if path.suffix.lower() in CertificateFileTree.CERTIFICATE_EXTENSIONS:
                    # Select the file (don't dismiss - user can press Enter again or click Select)
                    self._select_file(path)
                else:
                    self.notify(
                        f"Not a certificate file: {path.name}",
                        severity="warning",
                    )
            elif path.is_dir():
                # Navigate to the directory
                await self._replace_tree(path)

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection in the tree."""
        self._select_file(event.path)

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle directory selection - update the path input."""
        path_input = self.query_one("#path-input", Input)
        path_input.value = str(event.path)

        # Clear file selection when navigating
        self._selected_path = None
        selected_label = self.query_one("#selected-file-label", Static)
        selected_label.update("No file selected")

        select_btn = self.query_one("#select-btn", Button)
        select_btn.disabled = True

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "select-btn":
            self.dismiss(self._selected_path)
        elif event.button.id == "parent-dir-btn":
            # Navigate to parent directory
            tree = self.query_one("#file-tree", CertificateFileTree)
            current_path = Path(tree.path)
            parent_path = current_path.parent
            if parent_path != current_path:  # Not at root
                await self._replace_tree(parent_path)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select the current file and close the modal."""
        if self._selected_path is not None:
            self.dismiss(self._selected_path)
