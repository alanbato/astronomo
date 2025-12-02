# Astronomo

**A Gemini browser for the terminal.**

Astronomo is a modern terminal-based browser for the [Gemini protocol](https://geminiprotocol.net/), built with Python using [Textual](https://textual.textualize.io/) for the TUI and [Nauyaca](https://nauyaca.readthedocs.io/) for Gemini protocol support.

---

## Features

<div class="grid cards" markdown>

-   :material-keyboard:{ .lg .middle } **Keyboard-First Navigation**

    ---

    Navigate links with arrow keys, browse history with backspace, and access all features without leaving the keyboard.

-   :material-bookmark:{ .lg .middle } **Bookmarks with Folders**

    ---

    Organize your favorite capsules with a hierarchical bookmark system, stored locally in TOML format.

-   :material-palette:{ .lg .middle } **Themeable Interface**

    ---

    Choose from built-in Textual themes or customize the appearance to your liking.

-   :material-history:{ .lg .middle } **Session History**

    ---

    Navigate back and forward through your browsing session with scroll position preservation.

-   :material-certificate:{ .lg .middle } **Certificate Management**

    ---

    Create and manage client certificates for authenticated Gemini sites.

-   :material-code-tags:{ .lg .middle } **Syntax Highlighting**

    ---

    Code blocks in preformatted text are automatically syntax-highlighted.

</div>

---

## Quick Example

```bash
# Install with uv (recommended)
uv tool install astronomo

# Or with pip
pip install astronomo

# Launch and browse
astronomo gemini://geminiprotocol.net/
```

---

## Getting Started

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **[Installation](installation.md)**

    ---

    Get Astronomo installed on your system

-   :material-rocket-launch:{ .lg .middle } **[Quick Start](quickstart.md)**

    ---

    Start browsing Geminispace in 5 minutes

-   :material-school:{ .lg .middle } **[Tutorials](tutorials/index.md)**

    ---

    Step-by-step guides for common tasks

-   :material-book-open-variant:{ .lg .middle } **[Reference](reference/index.md)**

    ---

    Detailed documentation of all features

</div>

---

## Project Status

Astronomo is currently in **v0.1.0** (early development). Phase 1 features are complete:

| Feature | Status |
|---------|--------|
| Interactive link navigation | :white_check_mark: |
| Styled Gemtext rendering | :white_check_mark: |
| History (back/forward) | :white_check_mark: |
| Bookmarks with folders | :white_check_mark: |
| Configuration file | :white_check_mark: |
| Input prompts (search, passwords) | :white_check_mark: |
| Client certificates | :white_check_mark: |

See the [Changelog](changelog.md) for version history.

---

## Links

- [GitHub Repository](https://github.com/alanbato/astronomo)
- [Nauyaca Documentation](https://nauyaca.readthedocs.io/) (Gemini protocol library)
- [Gemini Protocol Specification](https://geminiprotocol.net/docs/specification.gmi)
