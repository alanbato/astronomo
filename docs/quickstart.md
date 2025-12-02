# Quick Start

This guide will get you browsing Geminispace in under 5 minutes.

## Launching Astronomo

Open your terminal and run:

```bash
astronomo
```

Or navigate directly to a URL:

```bash
astronomo gemini://geminiprotocol.net/
```

## Basic Navigation

### Opening URLs

1. Type or paste a URL in the address bar at the top
2. Press ++enter++ to navigate
3. You can omit `gemini://` - it's added automatically

### Following Links

Links are highlighted in the content area. Navigate them with:

| Key | Action |
|-----|--------|
| ++arrow-left++ / ++arrow-right++ | Move between links |
| ++enter++ | Open selected link |
| Mouse click | Open link directly |

### History Navigation

| Key | Action |
|-----|--------|
| ++backspace++ | Go back |
| ++shift+backspace++ | Go forward |
| Back/Forward buttons | Click the ◀ ▶ buttons |

## Managing Bookmarks

### Adding Bookmarks

Press ++ctrl+d++ to bookmark the current page. A dialog appears where you can:

- Edit the bookmark title
- Choose a folder (or leave in root)

### Viewing Bookmarks

Press ++ctrl+b++ to toggle the bookmarks sidebar. From here you can:

- Click a bookmark to navigate
- Right-click for options (edit, delete)
- Expand/collapse folders

## Other Key Commands

| Key | Action |
|-----|--------|
| ++ctrl+q++ | Quit Astronomo |
| ++ctrl+r++ | Refresh current page |
| ++ctrl+comma++ | Open settings |

## Configuration

Astronomo stores its configuration at `~/.config/astronomo/config.toml`. The default configuration looks like:

```toml
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5
```

See [Configuration Reference](reference/configuration.md) for all options.

## Next Steps

- [Tutorials](tutorials/index.md) - In-depth guides for specific tasks
- [Keybindings Reference](reference/keybindings.md) - Complete list of keyboard shortcuts
- [How-to Guides](how-to/index.md) - Task-oriented guides
