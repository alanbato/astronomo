# RSS/Atom Feeds

This guide explains how to subscribe to, manage, and read RSS/Atom feeds in Astronomo.

## Opening the Feeds Screen

Press ++ctrl+j++ to open the feeds screen. Press ++ctrl+j++ or ++escape++ to close it and return to browsing.

## Subscribing to Feeds

### Adding a New Feed

1. Open the feeds screen (++ctrl+j++)
2. Press ++ctrl+n++ to add a new feed
3. Enter the feed URL (e.g., `gemini://example.com/feed.xml`)
4. Optionally edit the title
5. Optionally select a folder
6. Press ++enter++ to save

### Supported Feed Formats

Astronomo supports:

- **Atom** feeds (recommended)
- **RSS 2.0** feeds
- **RSS 1.0** feeds

Most Gemini capsules that offer feeds use Atom format.

### Finding Feeds

Popular Gemini feed aggregators:

- `gemini://warmedal.se/~antenna/` - Antenna (aggregates many gemlogs)
- `gemini://rawtext.club/~sloum/spacewalk.xml` - Spacewalk
- `gemini://gemini.circumlunar.space/capcom/` - CAPCOM

Many gemlogs also offer their own feeds, typically at `/feed.xml` or `/atom.xml`.

## Reading Feeds

### Navigation

The feeds screen has two panels:

| Panel | Description |
|-------|-------------|
| **Feeds** (left) | Your subscribed feeds organized by folder |
| **Items** (right) | Articles from the selected feed |

### Keyboard Controls

| Key | Action |
|-----|--------|
| ++tab++ | Switch focus between feeds list and items |
| ++arrow-up++ / ++arrow-down++ | Navigate within current panel |
| ++enter++ | Open selected feed or article |
| ++escape++ or ++ctrl+j++ | Close feeds screen |

### Viewing Feed Items

1. Select a feed from the left panel
2. Press ++enter++ to load its items
3. Press ++tab++ to move to the items panel
4. Use ++arrow-up++ / ++arrow-down++ to browse items
5. Press ++enter++ to open an article in the browser

Each feed item shows:

- **Title** - Article headline
- **Time** - Human-readable timestamp (e.g., "2 hours ago", "yesterday")
- **Author** - If provided by the feed
- **Summary** - Brief description if available

### Read/Unread Tracking

- Unread items appear in normal text
- Read items appear dimmed
- Press ++m++ to mark all items in the current feed as read

## Organizing Feeds

### Creating Folders

1. Press ++ctrl+f++ to create a new folder
2. Enter a folder name
3. Press ++enter++ to save

### Moving Feeds to Folders

1. Select a feed
2. Press ++e++ to edit
3. Select a folder from the dropdown
4. Press ++enter++ to save

### Editing Feeds

1. Select a feed
2. Press ++e++ to edit
3. Modify the title or folder
4. Press ++enter++ to save

### Deleting Feeds

1. Select a feed or folder
2. Press ++d++ to delete
3. Confirm deletion

!!! warning
    Deleting a folder moves its feeds to the root level (they are not deleted).

## Refreshing Feeds

| Key | Action |
|-----|--------|
| ++ctrl+r++ | Refresh selected feed |
| ++ctrl+shift+r++ | Refresh all feeds |

## Searching Feeds

Use the search box at the top of the feeds list to filter feeds by name or URL.

## OPML Import/Export

OPML (Outline Processor Markup Language) allows you to transfer feed subscriptions between applications.

### Importing Feeds

1. Press ++ctrl+i++ to import
2. Enter the path to your OPML file
3. Press ++enter++ to import

Feeds are imported with their folder structure preserved.

### Exporting Feeds

1. Press ++ctrl+e++ to export
2. Enter the destination path
3. Press ++enter++ to export

The exported file can be imported into other feed readers.

## Feed Storage

Feeds are stored in `~/.config/astronomo/feeds.toml`:

```toml
[[folders]]
id = "abc123"
name = "News"
created_at = "2025-01-15T10:30:00"

[[feeds]]
id = "def456"
url = "gemini://warmedal.se/~antenna/atom.xml"
title = "Antenna"
folder_id = "abc123"
created_at = "2025-01-15T10:30:00"
last_fetched = "2025-01-15T12:00:00"
```

Read state is stored separately in `~/.config/astronomo/feeds_read.toml`.

## Keyboard Reference

### Feeds Screen

| Key | Action |
|-----|--------|
| ++ctrl+j++ | Close feeds screen |
| ++escape++ | Close feeds screen |
| ++tab++ | Toggle focus between panels |
| ++ctrl+n++ | Add new feed |
| ++ctrl+f++ | Add new folder |
| ++ctrl+r++ | Refresh selected feed |
| ++ctrl+shift+r++ | Refresh all feeds |
| ++ctrl+i++ | Import OPML |
| ++ctrl+e++ | Export OPML |
| ++d++ | Delete selected item |
| ++e++ | Edit selected item |
| ++m++ | Mark all as read |

### Feed Items

| Key | Action |
|-----|--------|
| ++arrow-up++ | Previous item |
| ++arrow-down++ | Next item |
| ++enter++ | Open article |

## Tips

1. **Start with aggregators** - Subscribe to Antenna or CAPCOM to discover new content
2. **Organize early** - Create folders before adding many feeds
3. **Check periodically** - Feeds don't auto-refresh; use ++ctrl+shift+r++ to catch up
4. **Export backups** - Use OPML export to backup your subscriptions
