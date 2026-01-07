# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Astronomo is a multi-protocol browser for the terminal, supporting Gemini, Gopher, and Finger protocols. Built on Textual (a TUI framework) with Nauyaca (Gemini), Mototli (Gopher), and Mapilli (Finger) as protocol libraries. The project is in active development.

## Technology Stack

- **Language**: Python 3.10+
- **Package Manager**: uv
- **UI Framework**: Textual (TUI framework with syntax highlighting support)
- **Gemini Protocol**: Nauyaca
- **Gopher Protocol**: Mototli
- **Finger Protocol**: Mapilli
- **Testing**: pytest
- **Linting/Formatting**: Ruff
- **Type Checking**: ty
- **Development Tools**: textual-dev, pre-commit

## Development Commands

### Environment Setup
```bash
# Install dependencies (uv handles virtual environment automatically)
uv sync

# Install development dependencies
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install
```

### Running the Application
```bash
# Run the application
uv run astronomo

# Run the Textual app directly (for development)
uv run python src/astronomo/astronomo_app.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_file.py

# Run a specific test
uv run pytest tests/test_file.py::test_function_name
```

### Linting and Formatting
```bash
# Run ruff linter with auto-fix
uv run ruff check --fix

# Run ruff formatter
uv run ruff format

# Run type checking
uv run ty check src/

# Run all pre-commit hooks manually
uv run pre-commit run --all-files
```

### Textual Development Tools
```bash
# Run Textual dev console for debugging
uv run textual console

# Run with Textual devtools enabled
uv run textual run --dev src/astronomo/astronomo_app.py
```

## Architecture

The project uses a simple structure with the main application code in `src/astronomo/`:

### Core Files
- `__init__.py`: Entry point with `main()` function
- `astronomo_app.py`: Main Textual App class implementation
- `parser.py`: Gemtext parser (headings, links, lists, blockquotes, preformatted text)
- `history.py`: `HistoryManager` and `HistoryEntry` for back/forward navigation
- `bookmarks.py`: `BookmarkManager`, `Bookmark`, and `Folder` dataclasses with TOML persistence
- `config.py`: `ConfigManager` with nested dataclasses (`Config`, `AppearanceConfig`, `BrowsingConfig`, `SnapshotsConfig`)
- `identities.py`: `IdentityManager` for client certificate management
- `response_handler.py`: Gemini response processing and status code handling
- `syntax.py`: Syntax highlighting for preformatted code blocks via Pygments

### Formatters (`src/astronomo/formatters/`)
- `__init__.py`: Exports formatter functions
- `gopher.py`: Gopher menu/content formatting (`format_gopher_menu`, `parse_gopher_url`, `fetch_gopher`)
- `finger.py`: Finger response formatting (`fetch_finger`)

### Screens (`src/astronomo/screens/`)
- `settings.py`: Settings screen with tabs for appearance, browsing, and certificates

### Widgets (`src/astronomo/widgets/`)
- `gemtext_viewer.py`: Main content viewer with specialized widgets for each Gemtext element type:
  - `GemtextHeadingWidget`, `GemtextLinkWidget`, `GemtextBlockquoteWidget`
  - `GemtextListItemWidget`, `GemtextPreformattedWidget`, `GemtextTextWidget`
- `navigation.py`: Address bar and navigation controls
- `bookmarks_sidebar.py`: Toggleable sidebar (Ctrl+B) with collapsible folder tree
- `add_bookmark_modal.py`: Modal for adding bookmarks (Ctrl+D)
- `edit_item_modal.py`: Modal for editing bookmark/folder titles
- `input_modal.py`: Modal for status 10/11 input requests (search, passwords) with byte counter
- `session_identity_modal.py`: Modal for session-based identity selection before requests
- `identity_select_modal.py`: Modal for identity selection on status 60 (certificate required)
- `identity_error_modal.py`: Modal for handling status 61/62 certificate errors
- `save_snapshot_modal.py`: Modal for confirming page snapshot saves (Ctrl+S)
- `certificate_changed_modal.py`: Modal for TOFU violations (server certificate changed)
- `certificate_details_modal.py`: Full certificate fingerprint comparison modal

### Settings Widgets (`src/astronomo/widgets/settings/`)
- `base.py`: Base class for settings panels
- `appearance.py`: Theme selection panel
- `browsing.py`: Browsing preferences panel
- `certificates.py`: Identity/certificate management panel
- `known_hosts.py`: TOFU known hosts management (view/revoke trusted servers) with search filtering and pagination (10 items per page)

### Certificate Widgets (`src/astronomo/widgets/certificates/`)
- `create_modal.py`: Modal for creating new identities
- `edit_modal.py`: Modal for editing identity details
- `manage_urls_modal.py`: Modal for managing URL associations
- `confirm_delete_modal.py`: Confirmation modal for identity deletion
- `import_lagrange_modal.py`: Modal for importing identities from Lagrange browser

The application is built on Textual's App framework, which provides the TUI infrastructure. The Nauyaca library handles Gemini protocol communication.

## Configuration System

### User Config (`~/.config/astronomo/config.toml`)
```toml
[appearance]
theme = "textual-dark"  # Textual built-in themes
syntax_highlighting = true  # Enable syntax highlighting in code blocks

[browsing]
# home_page = "gemini://geminiprotocol.net/"  # Optional
timeout = 30
max_redirects = 5

[snapshots]
# Directory where page snapshots are saved (Ctrl+S)
# Default: ~/.local/share/astronomo/snapshots
# directory = "/path/to/custom/snapshots"
```

**Adding new config values:**
1. Add field to appropriate dataclass in `config.py` (`AppearanceConfig`, `BrowsingConfig`, or create new)
2. Add default value and validation logic
3. Update the default config template with comments
4. Document in this file

**Planned config sections** (not yet implemented):
- `[keybindings]`: Custom keyboard shortcuts
- `[downloads]`: Download directory, ask location preference
- `[privacy]`: Save history toggle, max history size

## Multi-Protocol Architecture

Astronomo supports four protocols: Gemini, Gopher, Finger, and Nex.

### URL Routing

The `_normalize_url` method in `astronomo_app.py` handles smart URL detection:

1. URLs with explicit scheme (e.g., `gemini://`, `gopher://`, `finger://`, `nex://`) are used as-is
2. `user@host` patterns are detected as Finger URLs
3. Hostnames starting with `gopher.` or port `:70` are detected as Gopher
4. Hostnames starting with `nex.` or port `:1900` are detected as Nex
5. All other URLs default to Gemini

### Protocol Dispatch

The `get_url` method routes requests to protocol-specific handlers:
- `_fetch_gemini()` - Gemini protocol via Nauyaca
- `_fetch_gopher()` - Gopher protocol via Mototli
- `_fetch_finger()` - Finger protocol via Mapilli
- `_fetch_nex()` - Nex protocol (inline TCP client)

### Unified Display

All protocols convert their responses to Gemtext format, allowing the same `GemtextViewer` widget to render content uniformly:

- **Gopher**: Menus become Gemtext links with type indicators (`[DIR]`, `[TXT]`, `[SEARCH]`)
- **Finger**: Responses wrapped in preformatted blocks with a heading
- **Gemini**: Native Gemtext parsing
- **Nex**: Directory listings are already Gemtext-compatible, parsed directly

### Gopher-Specific Features

- **Search support**: Type 7 items trigger `InputModal` for query input
- **Binary downloads**: Types 9, g, I save files to `~/Downloads`
- **External links**: HTTP links (type h) open in system browser

### Nex Protocol Details

- **Simple TCP protocol**: Port 1900, plain text (no TLS)
- **Gemtext-compatible**: Directory listings use `=> url label` syntax
- **Inline implementation**: No external library needed, direct asyncio TCP client
- **Auto-detection**: `nex.*` hostnames and `:1900` port automatically detected

### Bookmarks (`~/.config/astronomo/bookmarks.toml`)
```toml
[folders.folder-uuid]
id = "folder-uuid"
name = "My Folder"
created_at = "2025-01-15T10:30:00"

[bookmarks.bookmark-uuid]
id = "bookmark-uuid"
url = "gemini://example.com/"
title = "Example Site"
folder_id = "folder-uuid"  # Optional
created_at = "2025-01-15T10:30:00"
```

## Current Development Status

**Completed Features:**
- ✅ Interactive links with keyboard/mouse navigation
- ✅ Styled Gemtext rendering with CSS
- ✅ History navigation (back/forward with scroll position preservation)
- ✅ Bookmarks system with folder organization
- ✅ Configuration file with settings UI (Ctrl+,)
- ✅ Interactive Input Support (status 10/11 responses)
- ✅ Client certificates/identity management with URL associations
- ✅ Session-based identity selection
- ✅ Syntax highlighting for code blocks (via Pygments)
- ✅ Theme support (10 built-in themes)
- ✅ Import identities from Lagrange browser
- ✅ Page snapshots (save pages as .gmi files with Ctrl+S)
- ✅ Multi-protocol support (Gemini, Gopher, Finger, Nex)
- ✅ Smart URL detection for protocol auto-selection
- ✅ Gopher search and binary downloads
- ✅ TOFU management UI (certificate change warnings, Known Hosts settings tab)

**Planned Features:**
- Multiple tabs with independent history and state
- Page search (Ctrl+F)
- Downloads support
- Custom keybindings

## Key Patterns and Best Practices

### Widget Development
- All Gemtext element widgets extend a base `GemtextLineWidget` class (extends `Static`)
- Use Textual's CSS system for styling, not Rich directly
- Modal screens should use `priority=True` on bindings to prevent key event bubbling

### Modal Screen Patterns
Modal screens follow a consistent structure:

**Class Structure:**
```python
class MyModal(ModalScreen[ResultType | None]):
    """Modal description."""

    DEFAULT_CSS = """..."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        container = Container()
        container.border_title = "Modal Title"
        with container:
            yield ...  # Modal content

    def action_cancel(self) -> None:
        self.dismiss(None)
```

**CSS Patterns for Modals:**
```css
MyModal {
    align: center middle;
}

MyModal > Container {
    width: 70-85;           /* Fixed width in cells */
    height: auto;
    max-height: 85%;
    border: thick $primary;  /* Use $error for warnings */
    border-title-align: center;
    background: $surface;
    padding: 1 2;
}
```

**Semantic Border Colors:**
- `$primary` - Standard informational modals
- `$error` - Warning/danger modals (certificate changes, deletions)
- `$success` - Success confirmations

**Common Widget Classes:**
- `.section-title` - Bold headers with `border-bottom: solid $primary`
- `.warning-message` - `background: $error 10%; border: solid $error`
- `.empty-state` - Centered muted text for empty lists
- `.button-row` - `align: center middle; padding-top: 1`

### Settings Tab Patterns
Settings tabs extend `Static` and follow this structure:

```python
class MySettings(Static):
    DEFAULT_CSS = """
    MySettings {
        height: 100%;
        width: 100%;
    }

    MySettings VerticalScroll {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(classes="section-header"):
            yield Label("Section Title", classes="section-title")
            yield Label("Description...", classes="section-description")

        with VerticalScroll(id="item-list", can_focus=False):
            yield from self._compose_list()
```

**Adding to Settings Screen:**
1. Create widget in `src/astronomo/widgets/settings/`
2. Export from `widgets/settings/__init__.py`
3. Import in `screens/settings.py`
4. Add CSS selector to existing comma-separated list
5. Add `TabPane` in `compose()`

### List Item Widget Patterns
For scrollable lists of items with actions:

```python
class MyListItem(Static):
    DEFAULT_CSS = """
    MyListItem {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
        layout: horizontal;
    }

    MyListItem:hover {
        background: $surface-lighten-1;
    }

    MyListItem .item-details {
        width: 1fr;
        height: auto;
    }

    MyListItem .action-buttons {
        width: auto;
        height: auto;
        align: right middle;
    }
    """

    class ActionRequested(Message):
        def __init__(self, item_id: str) -> None:
            self.item_id = item_id
            super().__init__()
```

### CSS Limitations
Textual CSS does not support all standard CSS properties:
- **No `font-family`** - Textual uses the terminal's monospace font
- **No `font-size`** - Font size is controlled by terminal settings
- Use `text-style: bold/italic/underline` instead of `font-weight`/`font-style`
- Colors use Textual variables: `$primary`, `$error`, `$warning`, `$success`, `$surface`, `$text-muted`

### Keyboard Shortcuts
- Document all keybindings in footer/help
- Global: Ctrl+Q (quit), Ctrl+R (refresh), Ctrl+B (bookmarks), Ctrl+D (add bookmark), Ctrl+S (save snapshot), Ctrl+, (settings)
- Navigation: Backspace (back), Shift+Backspace (forward)
- Links: Left/Right arrows for link navigation, Enter to activate
- Scrolling: Up/Down arrows, Page Up/Down, Home/End
- Sidebar: e (edit), d (delete) when bookmark/folder selected

### Data Persistence
- Use TOML format for all user data (config, bookmarks, future known_hosts)
- Use `tomllib` (Python 3.11+ built-in) for reading, `tomli-w` for writing
- Follow XDG Base Directory spec (`~/.config/astronomo/`)
- Handle missing/corrupted files gracefully with defaults

### History Management
- `HistoryEntry` stores URL, content, scroll position, link index, and response metadata
- Uses `deque` with `maxlen=100` for automatic LRU eviction
- In-memory only (not persisted to disk)

### Identity Management
Client certificates for Gemini authentication are managed by `IdentityManager` (`identities.py`):

**Storage:**
- Metadata: `~/.config/astronomo/identities.toml`
- Certificates: `~/.config/astronomo/certificates/{id}.pem`
- Private keys: `~/.config/astronomo/certificates/{id}.key` (with 0600 permissions)

**Identity Selection Flow:**
1. **Session-based selection**: When navigating to a URL with matching identity prefixes, `SessionIdentityModal` prompts the user to select an identity or browse anonymously
2. **Session memory**: Choices are stored in `_session_identity_choices` dict (keyed by URL prefix, persists until app quits)
3. **Status 60 handling**: If server requests certificate, `IdentitySelectModal` allows selection with optional "remember" for persistent association
4. **Status 61/62 handling**: `IdentityErrorModal` allows switching identity or regenerating certificates

**Key Methods:**
- `get_identity_for_url(url)`: Returns single best-match identity (longest prefix)
- `get_all_identities_for_url(url)`: Returns all matching identities (for selection modal)
- `create_identity(name, hostname)`: Generates self-signed certificate via Nauyaca
- `is_identity_valid(id)`: Checks certificate exists and is not expired
- `import_from_lagrange(idents_path, names)`: Imports certificates from Lagrange browser

**Lagrange Import:**
- Discovers `.crt`/`.key` pairs from Lagrange's idents directory
- Supports standard and Flatpak installations:
  - Linux: `~/.config/lagrange/idents/` or `~/.var/app/fi.skyjake.Lagrange/config/lagrange/idents/`
  - macOS: `~/Library/Application Support/fi.skyjake.Lagrange/idents/`
  - Windows: `%APPDATA%/fi.skyjake.Lagrange/idents/`
- User can set custom names for each identity before import
- Duplicates are detected by fingerprint and skipped
- URL associations cannot be imported (Lagrange uses proprietary binary format)

**URL Prefix Matching:**
- Identities can have multiple URL prefixes (e.g., `gemini://example.com/app/`)
- Longest-prefix matching determines which identity to use
- Session choices use host-level prefixes (`gemini://host/`)

### URL Handling
- Smart URL detection: `user@host` → Finger, `gopher.*` or `:70` → Gopher, `nex.*` or `:1900` → Nex, default → Gemini
- Use `urljoin` for resolving relative URLs (works for all protocols)
- URL-encode query strings with `urllib.parse.quote()`
- Cross-protocol links work seamlessly (Gemini can link to Gopher, Nex, etc.)

## Pre-commit Hooks

The project uses pre-commit hooks that run automatically on commit:
- Ruff linting (with auto-fix)
- Ruff formatting
- ty type checking (non-blocking)
- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML validation
- Large file checks
- Merge conflict detection
- Line ending normalization (LF)

When fixing linting issues during commits, use `git add -u .` to stage only modified files, avoiding unintended additions.
- Use the testing documentation for Textual apps on https://textual.textualize.io/guide/testing/
- Whenever you implement new functionality or fix a bug, add a list item to docs/changelog.md
