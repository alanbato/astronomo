# Bookmarks API

The bookmarks module manages bookmarks and folders.

## Overview

Astronomo stores bookmarks in `~/.config/astronomo/bookmarks.toml`. Bookmarks can optionally be organized into folders.

## API Reference

::: astronomo.bookmarks
    options:
      show_root_heading: true
      show_source: true
      members:
        - Bookmark
        - Folder
        - BookmarkManager

## File Format

Bookmarks are stored in TOML format:

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

## Example Usage

```python
from astronomo.bookmarks import BookmarkManager, Bookmark, Folder

# Load bookmarks (creates file if needed)
manager = BookmarkManager()

# Create a folder
folder = manager.create_folder("Tech Sites")

# Add a bookmark to the folder
bookmark = manager.add_bookmark(
    url="gemini://geminiprotocol.net/",
    title="Gemini Protocol",
    folder_id=folder.id,
)

# Get all bookmarks in a folder
bookmarks = manager.get_bookmarks_in_folder(folder.id)

# Save changes (automatic on modification)
manager.save()
```
