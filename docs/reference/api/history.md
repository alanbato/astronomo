# History API

The history module manages browsing session history.

## Overview

Astronomo maintains an in-memory history of visited pages during a session. Each history entry stores:

- The page URL
- The page content
- Scroll position
- Selected link index
- Response metadata

History is **not persisted** between sessions.

## API Reference

::: astronomo.history
    options:
      show_root_heading: true
      show_source: true
      members:
        - HistoryEntry
        - HistoryManager

## Example Usage

```python
from astronomo.history import HistoryManager, HistoryEntry

# Create a history manager with max 100 entries
history = HistoryManager(max_size=100)

# Add an entry
entry = HistoryEntry(
    url="gemini://example.com/",
    content="# Example Page",
    scroll_position=0,
    link_index=0,
)
history.push(entry)

# Navigate back
if history.can_go_back():
    previous = history.go_back()

# Navigate forward
if history.can_go_forward():
    next_entry = history.go_forward()
```
