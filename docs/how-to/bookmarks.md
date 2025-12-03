# Bookmarks

This guide explains how to manage bookmarks and folders in Astronomo.

## Adding Bookmarks

### Quick Add

1. Navigate to a page you want to save
2. Press ++ctrl+d++
3. Edit the title if desired
4. Optionally select a folder
5. Press ++enter++ to save

### From the Sidebar

1. Press ++ctrl+b++ to open the bookmarks sidebar
2. Use the "Add Bookmark" option if available

## Viewing Bookmarks

Press ++ctrl+b++ to toggle the bookmarks sidebar.

The sidebar shows:

- All your bookmarks organized by folder
- Root-level bookmarks (not in any folder)
- Folders that can be expanded/collapsed

## Organizing with Folders

### Creating Folders

1. Open the bookmarks sidebar (++ctrl+b++)
2. Look for the "New Folder" option
3. Enter a folder name
4. The folder appears in your bookmark list

### Adding Bookmarks to Folders

When creating a new bookmark (++ctrl+d++):

1. Fill in the bookmark details
2. Select a folder from the dropdown
3. Save the bookmark

### Suggested Organization

Consider organizing by topic:

```
├── News & Aggregators
│   ├── Antenna
│   ├── CAPCOM
│   └── Gemini Observatory
├── Technical
│   ├── Gemini Protocol Docs
│   └── FAQ
├── Gemlogs
│   ├── Solderpunk
│   └── Other Gemlogs
└── Personal
    └── My Gemlog
```

## Customizing Folder Colors

You can set a custom background color for folders to help visually distinguish them.

### Setting a Folder Color

1. Open the bookmarks sidebar (++ctrl+b++)
2. Select the folder you want to customize
3. Press ++e++ to edit the folder
4. In the color picker, choose from:
    - **Preset colors**: 12 theme-friendly colors (6 muted, 6 pastel)
    - **Custom hex**: Enter any 6-digit hex color (e.g., `#4a4a5a`)
5. Press ++enter++ or click "Save"

### Removing a Folder Color

1. Edit the folder (++e++)
2. Click the "Clear" button in the color picker
3. Save changes

The text color automatically adjusts for readability on any background color.

### Available Preset Colors

| Muted (dark themes) | Pastel (light themes) |
|---------------------|----------------------|
| Slate (#4a4a5a)     | Steel Blue (#b0c4de) |
| Maroon (#5a3d3d)    | Rose (#d4a5a5)       |
| Forest (#3d5a3d)    | Green (#a5d4a5)      |
| Navy (#3d4a5a)      | Yellow (#d4d4a5)     |
| Brown (#5a4a3d)     | Lavender (#c4b0de)   |
| Purple (#4a3d5a)    | Cyan (#a5c4d4)       |

## Editing Bookmarks

1. Open the bookmarks sidebar
2. Select a bookmark
3. Press ++e++ to edit
4. Modify the title
5. Press ++enter++ to save

## Deleting Bookmarks

1. Open the bookmarks sidebar
2. Right-click a bookmark
3. Select "Delete"
4. Confirm deletion

## Deleting Folders

!!! warning
    Deleting a folder does not delete bookmarks inside it. They become root-level bookmarks.

1. Open the bookmarks sidebar
2. Right-click a folder
3. Select "Delete"
4. Confirm deletion

## Bookmark Storage

Bookmarks are stored in `~/.config/astronomo/bookmarks.toml`:

```toml
[[folders]]
id = "abc123"
name = "Tech Sites"
color = "#3d4a5a"  # Optional: hex color for folder background
created_at = "2025-01-15T10:30:00"

[[bookmarks]]
id = "def456"
url = "gemini://geminiprotocol.net/"
title = "Gemini Protocol"
folder_id = "abc123"
created_at = "2025-01-15T10:30:00"
```

You can edit this file directly if needed.

## Backup and Restore

### Backup

```bash
cp ~/.config/astronomo/bookmarks.toml ~/bookmarks-backup.toml
```

### Restore

```bash
cp ~/bookmarks-backup.toml ~/.config/astronomo/bookmarks.toml
```

## Tips

1. **Use descriptive titles** - Future you will thank present you
2. **Create folders early** - Easier to organize as you go
3. **Regular cleanup** - Remove bookmarks for dead capsules
4. **Backup periodically** - Especially before system changes
