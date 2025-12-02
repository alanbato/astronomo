# Configuration Reference

Astronomo stores its configuration at `~/.config/astronomo/config.toml`.

If the file doesn't exist, Astronomo creates it with default values on first run.

## Configuration File

### Full Example

```toml
[appearance]
theme = "textual-dark"

[browsing]
home_page = "gemini://geminiprotocol.net/"
timeout = 30
max_redirects = 5
```

## Sections

### [appearance]

Visual settings for the browser.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `theme` | string | `"textual-dark"` | Textual theme name |

#### Available Themes

Astronomo supports all built-in Textual themes:

- `textual-dark` - Default dark theme
- `textual-light` - Default light theme
- `textual-ansi` - ANSI colors only (terminal-native)
- `nord` - Nord color scheme
- `gruvbox` - Gruvbox color scheme
- `tokyo-night` - Tokyo Night color scheme
- `monokai` - Monokai color scheme
- `dracula` - Dracula color scheme
- `catppuccin-mocha` - Catppuccin Mocha
- `solarized-light` - Solarized Light

### [browsing]

Behavior settings for browsing.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `home_page` | string | (none) | URL to load on startup if no URL is provided |
| `timeout` | integer | `30` | Request timeout in seconds |
| `max_redirects` | integer | `5` | Maximum number of redirects to follow |

## Data Files

In addition to configuration, Astronomo stores user data in `~/.config/astronomo/`:

| File | Description |
|------|-------------|
| `config.toml` | Configuration settings |
| `bookmarks.toml` | Saved bookmarks and folders |
| `identities/` | Client certificates directory |

## Environment Variables

Astronomo respects the XDG Base Directory specification:

| Variable | Default | Description |
|----------|---------|-------------|
| `XDG_CONFIG_HOME` | `~/.config` | Base directory for configuration files |

## Editing Configuration

You can edit the configuration file directly:

```bash
# Open in your default editor
$EDITOR ~/.config/astronomo/config.toml
```

Changes take effect on the next launch of Astronomo.

Alternatively, use ++ctrl+comma++ to open the in-app settings screen.
