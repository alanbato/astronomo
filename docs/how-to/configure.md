# Configuration

This guide explains how to configure Astronomo's behavior and appearance.

## Configuration Methods

### In-App Settings

Press ++ctrl+comma++ to open the Settings screen. Changes are saved automatically.

### Configuration File

Edit `~/.config/astronomo/config.toml` directly:

```bash
$EDITOR ~/.config/astronomo/config.toml
```

Restart Astronomo for changes to take effect.

## Changing the Theme

### Available Themes

| Theme | Description |
|-------|-------------|
| `textual-dark` | Default dark theme |
| `textual-light` | Light theme for bright environments |
| `textual-ansi` | Uses terminal's native colors |
| `nord` | Arctic, cool blue tones |
| `dracula` | Dark theme with purple accents |
| `gruvbox` | Warm, retro color scheme |
| `tokyo-night` | Vibrant dark theme |
| `monokai` | Classic code editor colors |
| `catppuccin-mocha` | Pastel dark theme |
| `solarized-light` | Low-contrast light theme |

### Setting a Theme

```toml
[appearance]
theme = "dracula"
```

## Setting a Home Page

Load a specific page when Astronomo starts:

```toml
[browsing]
home_page = "gemini://geminiprotocol.net/"
```

Without a home page, Astronomo starts with an empty view unless you specify a URL on the command line.

## Adjusting Timeouts

Control how long Astronomo waits for slow servers:

```toml
[browsing]
timeout = 30  # seconds
```

!!! tip
    Increase this value if you frequently access slow servers or have a slow connection.

## Limiting Redirects

Control how many redirects Astronomo follows:

```toml
[browsing]
max_redirects = 5
```

This prevents infinite redirect loops and limits exposure to redirect chains.

## Complete Example

```toml
# Astronomo Configuration
# ~/.config/astronomo/config.toml

[appearance]
theme = "tokyo-night"

[browsing]
home_page = "gemini://geminiprotocol.net/"
timeout = 30
max_redirects = 5
```

## Resetting to Defaults

Delete the config file to reset:

```bash
rm ~/.config/astronomo/config.toml
```

Astronomo recreates it with defaults on next launch.

## Configuration Location

Astronomo follows the XDG Base Directory specification:

- Default: `~/.config/astronomo/config.toml`
- Custom: Set `XDG_CONFIG_HOME` environment variable

```bash
# Use a different config location
XDG_CONFIG_HOME=~/my-config astronomo
```

## Troubleshooting

### Config Not Loading

1. Check file syntax with a TOML validator
2. Ensure file permissions allow reading
3. Check for typos in section names

### Theme Not Changing

1. Verify the theme name is spelled correctly
2. Restart Astronomo after file changes
3. Check that the theme exists in Textual

### Invalid Values

If Astronomo encounters invalid configuration values, it uses defaults and may show a warning. Check the terminal output for error messages.
