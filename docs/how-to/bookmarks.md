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

## Editing Bookmarks

1. Open the bookmarks sidebar
2. Right-click a bookmark (or use the context menu)
3. Select "Edit"
4. Modify the title or folder
5. Save changes

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
[folders.abc123]
id = "abc123"
name = "Tech Sites"
created_at = "2025-01-15T10:30:00"

[bookmarks.def456]
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
