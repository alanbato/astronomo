# Customizing Astronomo

This tutorial shows you how to personalize Astronomo with configuration, themes, and organized bookmarks.

**Time:** 15 minutes

## Prerequisites

- Completed [Your First Session](first-session.md) tutorial
- Basic familiarity with TOML format (we'll explain as we go)

## Step 1: Open Settings

Press ++ctrl+comma++ to open the Settings screen.

Here you can adjust common settings through a graphical interface. Changes are saved automatically.

## Step 2: Change the Theme

Astronomo supports multiple color themes.

### Via Settings Screen

1. In Settings, find the Theme option
2. Select a theme from the list
3. The change applies immediately

### Via Configuration File

You can also edit the config file directly:

```bash
# Open with your editor
$EDITOR ~/.config/astronomo/config.toml
```

Change the theme setting:

```toml
[appearance]
theme = "nord"  # Try: dracula, gruvbox, tokyo-night, monokai
```

Save and restart Astronomo.

### Available Themes

| Theme | Description |
|-------|-------------|
| `textual-dark` | Default dark theme |
| `textual-light` | Light theme |
| `nord` | Cool blue-gray tones |
| `dracula` | Purple and pink accents |
| `gruvbox` | Warm retro colors |
| `tokyo-night` | Vibrant dark theme |
| `monokai` | Classic editor colors |
| `catppuccin-mocha` | Pastel dark theme |
| `solarized-light` | Easy on the eyes |

## Step 3: Set a Home Page

Configure a page to load on startup:

```toml
[browsing]
home_page = "gemini://geminiprotocol.net/"
```

Now when you run `astronomo` without arguments, it loads your home page.

## Step 4: Organize Bookmarks into Folders

Let's organize your bookmarks with folders.

### Create a Folder

1. Press ++ctrl+b++ to open bookmarks sidebar
2. Look for the "New Folder" option
3. Enter a name like "Tech" or "News"

### Move Bookmarks to Folders

When adding a new bookmark (++ctrl+d++):

1. Enter the bookmark title
2. Select a folder from the dropdown
3. Save the bookmark

### Example Organization

```
Bookmarks
├── Tech
│   ├── Gemini Protocol Docs
│   └── Solderpunk's Gemlog
├── News
│   ├── Antenna
│   └── CAPCOM
└── Personal
    └── My Gemlog
```

## Step 5: Adjust Browsing Behavior

Fine-tune how Astronomo handles requests:

```toml
[browsing]
timeout = 30        # Seconds to wait for slow servers
max_redirects = 5   # How many redirects to follow
```

!!! tip
    If you're on a slow connection, increase the timeout:
    ```toml
    timeout = 60
    ```

## Step 6: Understand the Config File

Here's a complete example configuration:

```toml
# Astronomo Configuration
# Location: ~/.config/astronomo/config.toml

[appearance]
# Visual theme (see docs for full list)
theme = "tokyo-night"

[browsing]
# Page to load on startup (optional)
home_page = "gemini://geminiprotocol.net/"

# Request timeout in seconds
timeout = 30

# Maximum redirects to follow
max_redirects = 5
```

## Step 7: Backup Your Data

Your Astronomo data lives in `~/.config/astronomo/`:

```
~/.config/astronomo/
├── config.toml      # Your settings
├── bookmarks.toml   # Your bookmarks
└── identities/      # Client certificates
```

To backup:

```bash
cp -r ~/.config/astronomo ~/astronomo-backup
```

To restore on another machine:

```bash
cp -r ~/astronomo-backup ~/.config/astronomo
```

## What You Learned

You now know how to:

- [x] Change themes
- [x] Set a home page
- [x] Organize bookmarks into folders
- [x] Adjust timeout and redirect settings
- [x] Edit the configuration file
- [x] Backup your data

## Next Steps

- [Configuration Reference](../reference/configuration.md) - All configuration options
- [Certificates Guide](../how-to/certificates.md) - Set up client certificates
- [Architecture](../explanation/architecture.md) - Understand how Astronomo works
