# Astronomo

**A modern Gemini browser for the terminal**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI](https://img.shields.io/pypi/v/astronomo.svg)](https://pypi.org/project/astronomo/)

---

## What is Astronomo?

[Gemini](gemini://geminiprotocol.net/) is a lightweight internet protocol that sits between Gopher and the web. It prioritizes simplicity, privacy, and user autonomy—no tracking, no ads, no JavaScript. Just clean, focused content served over encrypted connections.

**Astronomo** brings the Gemini experience to your terminal with a modern, polished interface. Built on [Textual](https://textual.textualize.io/)—a powerful Python TUI framework—Astronomo offers features you'd expect from a desktop browser: full mouse support, syntax highlighting, beautiful themes, and responsive async networking.

Whether you're exploring Geminispace for the first time or looking for a better terminal client, Astronomo delivers a seamless browsing experience without leaving your command line.

<img width="1731" height="1017" alt="image" src="https://github.com/user-attachments/assets/88ec1dfe-e6b4-4f34-8720-e17864ce9c50" />

---

## Why Astronomo?

| Feature | Astronomo | Amfora | Bombadillo |
|---------|-----------|--------|------------|
| **UI Framework** | Textual (modern) | ncurses | ncurses |
| **Mouse Support** | Full | Limited | No |
| **Syntax Highlighting** | Yes | Yes | No |
| **Built-in Themes** | 10 | User-contributed | No |
| **Bookmark Folders** | Yes | Flat list | Flat list |
| **Client Certificates** | Yes | Yes | No |
| **TOFU Security** | Yes | Yes | No |
| **Tabs** | Coming soon | Yes | No |
| **Multi-protocol** | Gemini + Gopher + Finger | Proxying | Gopher+Finger |
| **Development** | Active | Maintenance mode | Maintenance mode |
| **Language** | Python | Go | Go |

**Key advantages:**
- **Modern TUI** — Textual provides superior rendering, full mouse support, and async I/O compared to legacy ncurses
- **Active development** — Amfora is in maintenance mode; Astronomo is actively evolving
- **Python extensibility** — Easy to hack, extend, or integrate with your workflow
- **Beautiful out of the box** — 10 popular themes included (Nord, Dracula, Catppuccin, and more)

---

## Features

### Styled Gemtext Rendering
Every Gemtext element is beautifully rendered with distinct visual styling:
- **Headings** — Three levels with different colors and formatting
- **Links** — Colored and underlined with arrow indicators when selected
- **Blockquotes** — Bordered and italicized for clear distinction
- **Lists** — Properly formatted with bullet points
- **Preformatted blocks** — Distinct background with preserved formatting

### Interactive Navigation
Navigate Geminispace effortlessly:
- **Keyboard** — Arrow keys to move between links, Enter to activate
- **Mouse** — Click any link to follow it
- **Visual feedback** — Clear focus indicators show your current selection

### Syntax Highlighting
Code blocks with language hints (` ```python `, ` ```rust `, etc.) are automatically syntax highlighted using Pygments, making technical content easy to read.

### History Navigation
- **Back/Forward** — Navigate your browsing history with Backspace and Shift+Backspace
- **Position memory** — Scroll position and link selection are preserved
- **Fast navigation** — Pages are cached in memory, no re-fetching required

### Bookmarks System
Organize your favorite capsules:
- **Folder organization** — Group bookmarks into collapsible folders
- **Sidebar** — Toggle with Ctrl+B for quick access
- **Quick add** — Bookmark the current page with Ctrl+D
- **Full management** — Edit titles, move between folders, delete
- **Persistence** — Saved as TOML in your config directory

### Client Certificates / Identities
Full support for authenticated Gemini sites:
- **Identity management** — Create, edit, and delete client certificates
- **URL assignment** — Associate identities with specific capsules
- **Settings UI** — Manage everything from an in-app settings panel

### TOFU Certificate Verification
Trust On First Use security via [Nauyaca](https://github.com/alanbato/nauyaca):
- **Automatic trust** — Certificates are stored on first connection
- **Change detection** — Warns if a server's certificate changes unexpectedly
- **Known Hosts management** — View, search, and revoke trusted servers in Settings (Ctrl+,)
- **SQLite storage** — Known hosts persisted at `~/.nauyaca/tofu.db`

### Theming
Choose from 10 built-in themes:
- `textual-dark` (default)
- `textual-light`
- `textual-ansi`
- `nord`
- `gruvbox`
- `tokyo-night`
- `monokai`
- `dracula`
- `catppuccin-mocha`
- `solarized-light`

### Interactive Input
Seamless support for Gemini's input requests:
- **Search queries** — Status 10 prompts for text input
- **Sensitive input** — Status 11 for password-style masked entry
- **Byte counter** — Visual feedback for URL length limits

### Multi-Protocol Support
Browse beyond Gemini with native support for classic protocols:

**Gopher Protocol:**
- **Directory browsing** — Navigate Gopher menus with type indicators ([DIR], [TXT], [SEARCH])
- **Text files** — View Gopher text documents with proper formatting
- **Search support** — Interactive search queries (type 7)
- **Binary downloads** — Download files to `~/Downloads`

**Finger Protocol:**
- **User queries** — Look up user information from Finger servers
- **Flexible URLs** — Supports both `finger://user@host` and `finger://host/user` formats

**Smart URL Detection:**
- `user@host` → automatically uses `finger://`
- `gopher.example.com` → automatically uses `gopher://`
- Everything else → defaults to `gemini://`

### Configuration
- **XDG-compliant** — Config stored at `~/.config/astronomo/`
- **TOML format** — Human-readable with helpful comments
- **Settings screen** — Configure without editing files manually

---

## Installation

### Recommended: Install with uv

```bash
uv tool install astronomo
```

### Alternative: Install with pipx

```bash
pipx install astronomo
```

### From Source (for contributors)

```bash
git clone https://github.com/alanbato/astronomo.git
cd astronomo
uv sync
uv run astronomo
```

---

## Quick Start

```bash
# Launch Astronomo
astronomo

# Open a Gemini capsule
astronomo gemini://geminiprotocol.net/

# Browse a Gopher server
astronomo gopher://gopher.floodgap.com/

# Query a Finger server (smart detection)
astronomo user@example.com

# Use a custom config file
astronomo --config ~/my-config.toml
```

### Capsules to Explore

New to Gemini? Here are some great starting points:

- `gemini://geminiprotocol.net/` — Official Gemini protocol documentation
- `gemini://geminispace.info/` — Search engine for Geminispace
- `gemini://kennedy.gemi.dev/` — Gemini search and discovery
- `gemini://rawtext.club/` — Community and hosting

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Activate selected link |
| `Left` / `Right` | Navigate between links |
| `Backspace` | Go back in history |
| `Shift+Backspace` | Go forward in history |
| `Ctrl+B` | Toggle bookmarks sidebar |
| `Ctrl+D` | Bookmark current page |
| `e` | Edit selected bookmark/folder (in sidebar) |
| `d` | Delete selected bookmark/folder (in sidebar) |
| `Ctrl+Q` | Quit |

---

## Configuration

Astronomo stores configuration at `~/.config/astronomo/config.toml`:

```toml
# Astronomo Configuration

[appearance]
# Available themes: textual-dark, textual-light, textual-ansi, nord,
#                   gruvbox, tokyo-night, monokai, dracula,
#                   catppuccin-mocha, solarized-light
theme = "textual-dark"

# Enable syntax highlighting in code blocks
syntax_highlighting = true

[browsing]
# Default home page (uncomment to set)
# home_page = "gemini://geminiprotocol.net/"

# Request timeout in seconds
timeout = 30

# Maximum redirects to follow
max_redirects = 5
```

Bookmarks are stored separately at `~/.config/astronomo/bookmarks.toml`.

---

## Roadmap

Astronomo is actively developed. Here's what's coming next:

**Phase 2 — Enhanced UX:**
- **Multiple Tabs** — Browse multiple capsules simultaneously
- **Page Search** — Find text within pages (Ctrl+F)
- **Search Engine Integration** — Quick access to Gemini search engines

**Phase 3 — Advanced Features:**
- **Downloads** — Save pages and files to disk
- **Custom Keybindings** — Vi/Emacs-style key configurations

---

## Contributing

Contributions are welcome! Astronomo is built with:

- **[Textual](https://textual.textualize.io/)** — Modern Python TUI framework
- **[Nauyaca](https://github.com/alanbato/nauyaca)** — Gemini protocol library
- **[pytest](https://pytest.org/)** — Testing framework

### Development Setup

```bash
git clone https://github.com/alanbato/astronomo.git
cd astronomo
uv sync --group dev
uv run pre-commit install

# Run the app
uv run astronomo

# Run tests
uv run pytest

# Run with Textual devtools
uv run textual run --dev src/astronomo/astronomo.py
```

---

## Links

**Protocols:**
- [Gemini Protocol](gemini://geminiprotocol.net/) — Learn about the Gemini protocol
- [Gopher Protocol](https://en.wikipedia.org/wiki/Gopher_(protocol)) — The classic menu-driven protocol
- [Finger Protocol](https://en.wikipedia.org/wiki/Finger_(protocol)) — User information lookup protocol

**Development:**
- [Textual Documentation](https://textual.textualize.io/) — The TUI framework powering Astronomo
- [Nauyaca](https://github.com/alanbato/nauyaca) — Gemini protocol library for Python
