# API Reference

This section documents Astronomo's Python API for developers who want to extend or integrate with the browser.

## Modules

| Module | Description |
|--------|-------------|
| [Parser](parser.md) | Gemtext parsing utilities |
| [History](history.md) | Session history management |
| [Bookmarks](bookmarks.md) | Bookmark and folder management |
| [Config](config.md) | Configuration management |
| [Identities](identities.md) | Client certificate management |

## Usage

Astronomo's modules can be imported and used independently:

```python
from astronomo.parser import parse_gemtext, LineType
from astronomo.history import HistoryManager, HistoryEntry
from astronomo.bookmarks import BookmarkManager, Bookmark, Folder
from astronomo.config import ConfigManager
from astronomo.identities import IdentityManager, Identity
```

## Design Principles

- **Dataclasses for data**: All data structures use Python dataclasses
- **TOML for persistence**: Configuration and bookmarks are stored in TOML format
- **XDG compliance**: User data follows the XDG Base Directory specification
- **Type hints**: Full type annotations for IDE support
