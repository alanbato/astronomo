# Config API

The config module manages application configuration.

## Overview

Configuration is stored in `~/.config/astronomo/config.toml`. The module provides typed access to settings with validation and defaults.

## API Reference

::: astronomo.config
    options:
      show_root_heading: true
      show_source: true
      members:
        - AppearanceConfig
        - BrowsingConfig
        - Config
        - ConfigManager

## Configuration File

The default configuration:

```toml
[appearance]
theme = "textual-dark"

[browsing]
# home_page = "gemini://geminiprotocol.net/"  # Optional
timeout = 30
max_redirects = 5
```

## Example Usage

```python
from astronomo.config import ConfigManager

# Load configuration (creates default if needed)
config = ConfigManager()

# Access settings
print(config.theme)  # "textual-dark"
print(config.timeout)  # 30
print(config.max_redirects)  # 5

# Use a custom config path
from pathlib import Path
config = ConfigManager(config_path=Path("~/.my-astronomo-config.toml"))
```

## Available Themes

Astronomo uses Textual's built-in themes:

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
