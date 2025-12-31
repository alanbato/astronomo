"""Feed management for Astronomo.

This module provides RSS/Atom feed subscription management with folder organization,
read/unread tracking, and TOML persistence.
"""

import hashlib
import logging
import tomllib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Self

import tomli_w

logger = logging.getLogger(__name__)


@dataclass
class Feed:
    """Represents a subscribed feed.

    Attributes:
        id: Unique identifier (UUID)
        url: The Gemini URL of the feed
        title: Display title for the feed
        folder_id: ID of containing folder, or None for root level
        created_at: When the feed was subscribed
        last_fetched: When the feed was last successfully fetched
    """

    id: str
    url: str
    title: str
    folder_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    last_fetched: datetime | None = None

    @classmethod
    def create(cls, url: str, title: str, folder_id: str | None = None) -> Self:
        """Create a new feed with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            url=url,
            title=title,
            folder_id=folder_id,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        data = {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
        }
        if self.folder_id is not None:
            data["folder_id"] = self.folder_id
        if self.last_fetched is not None:
            data["last_fetched"] = self.last_fetched.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary (TOML deserialization)."""
        return cls(
            id=data["id"],
            url=data["url"],
            title=data["title"],
            folder_id=data.get("folder_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_fetched=datetime.fromisoformat(data["last_fetched"])
            if data.get("last_fetched")
            else None,
        )


@dataclass
class FeedFolder:
    """Represents a feed folder.

    Attributes:
        id: Unique identifier (UUID)
        name: Display name of the folder
        parent_id: ID of parent folder for nesting (future use)
        created_at: When the folder was created
    """

    id: str
    name: str
    parent_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, name: str, parent_id: str | None = None) -> Self:
        """Create a new folder with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }
        if self.parent_id is not None:
            data["parent_id"] = self.parent_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary (TOML deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            parent_id=data.get("parent_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class ReadItem:
    """Represents a read feed item.

    Attributes:
        item_id: Unique identifier for the feed item (hash)
        feed_id: ID of the feed this item belongs to
        read_at: When the item was marked as read
    """

    item_id: str
    feed_id: str
    read_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        return {
            "item_id": self.item_id,
            "feed_id": self.feed_id,
            "read_at": self.read_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary (TOML deserialization)."""
        return cls(
            item_id=data["item_id"],
            feed_id=data["feed_id"],
            read_at=datetime.fromisoformat(data["read_at"]),
        )


class FeedManager:
    """Manages feeds, folders, and read status with TOML persistence.

    Provides CRUD operations for feeds and folders, tracks read/unread status,
    and persists everything to a TOML file in the user's config directory.

    Args:
        config_dir: Directory for storing feeds file.
                   Defaults to ~/.config/astronomo/
    """

    VERSION = "1.0"

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "astronomo"
        self.feeds_file = self.config_dir / "feeds.toml"
        self.feeds: list[Feed] = []
        self.folders: list[FeedFolder] = []
        self.read_items: list[ReadItem] = []
        self._load()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load feeds from TOML file."""
        if not self.feeds_file.exists():
            return

        try:
            with open(self.feeds_file, "rb") as f:
                data = tomllib.load(f)

            self.folders = [FeedFolder.from_dict(f) for f in data.get("folders", [])]
            self.feeds = [Feed.from_dict(f) for f in data.get("feeds", [])]
            self.read_items = [
                ReadItem.from_dict(r) for r in data.get("read_items", [])
            ]
        except tomllib.TOMLDecodeError as e:
            # TOML syntax is invalid
            logger.error("Failed to parse feeds.toml: %s", e)
            self.feeds = []
            self.folders = []
            self.read_items = []
        except (KeyError, ValueError, TypeError) as e:
            # Data structure is invalid
            logger.error("Invalid data in feeds.toml: %s", e)
            self.feeds = []
            self.folders = []
            self.read_items = []

    def _save(self) -> None:
        """Save feeds to TOML file.

        Raises:
            OSError: If the file cannot be written (disk full, permissions, etc.)
        """
        try:
            self._ensure_config_dir()
        except OSError as e:
            logger.error("Cannot create config directory: %s", e)
            raise

        data = {
            "version": self.VERSION,
            "folders": [f.to_dict() for f in self.folders],
            "feeds": [f.to_dict() for f in self.feeds],
            "read_items": [r.to_dict() for r in self.read_items],
        }

        try:
            with open(self.feeds_file, "wb") as f:
                tomli_w.dump(data, f)
        except OSError as e:
            logger.error("Cannot save feeds file: %s", e)
            raise

    # Feed operations

    def add_feed(self, url: str, title: str, folder_id: str | None = None) -> Feed:
        """Add a new feed subscription.

        Args:
            url: The Gemini URL of the feed
            title: Display title for the feed
            folder_id: Optional folder ID to place the feed in

        Returns:
            The created Feed
        """
        feed = Feed.create(url=url, title=title, folder_id=folder_id)
        self.feeds.append(feed)
        self._save()
        return feed

    def remove_feed(self, feed_id: str) -> bool:
        """Remove a feed subscription.

        Also removes all read status entries for this feed.

        Args:
            feed_id: ID of the feed to remove

        Returns:
            True if feed was found and removed, False otherwise
        """
        # Remove read items for this feed
        self.read_items = [r for r in self.read_items if r.feed_id != feed_id]

        # Remove the feed
        for i, feed in enumerate(self.feeds):
            if feed.id == feed_id:
                del self.feeds[i]
                self._save()
                return True
        return False

    def update_feed(
        self,
        feed_id: str,
        title: str | None = None,
        folder_id: str | None = ...,  # type: ignore[assignment]
        last_fetched: datetime | None = None,
    ) -> bool:
        """Update a feed's properties.

        Args:
            feed_id: ID of the feed to update
            title: New title (if provided)
            folder_id: New folder ID, None for root, or ... to keep current
            last_fetched: Update last fetched timestamp

        Returns:
            True if feed was found and updated, False otherwise
        """
        for feed in self.feeds:
            if feed.id == feed_id:
                if title is not None:
                    feed.title = title
                if folder_id is not ...:
                    feed.folder_id = folder_id
                if last_fetched is not None:
                    feed.last_fetched = last_fetched
                self._save()
                return True
        return False

    def get_feed(self, feed_id: str) -> Feed | None:
        """Get a feed by ID."""
        for feed in self.feeds:
            if feed.id == feed_id:
                return feed
        return None

    def get_feeds_in_folder(self, folder_id: str | None) -> list[Feed]:
        """Get all feeds in a specific folder.

        Args:
            folder_id: Folder ID, or None for root-level feeds

        Returns:
            List of feeds in the specified folder
        """
        return [f for f in self.feeds if f.folder_id == folder_id]

    def get_root_feeds(self) -> list[Feed]:
        """Get all feeds not in any folder."""
        return self.get_feeds_in_folder(None)

    def feed_exists(self, url: str) -> bool:
        """Check if a feed for the given URL already exists."""
        return any(f.url == url for f in self.feeds)

    # Folder operations

    def add_folder(self, name: str) -> FeedFolder:
        """Add a new folder.

        Args:
            name: Display name for the folder

        Returns:
            The created FeedFolder
        """
        folder = FeedFolder.create(name=name)
        self.folders.append(folder)
        self._save()
        return folder

    def remove_folder(self, folder_id: str) -> bool:
        """Remove a folder, moving its feeds to root.

        Args:
            folder_id: ID of the folder to remove

        Returns:
            True if folder was found and removed, False otherwise
        """
        # Move feeds to root level
        for feed in self.feeds:
            if feed.folder_id == folder_id:
                feed.folder_id = None

        # Remove the folder
        for i, folder in enumerate(self.folders):
            if folder.id == folder_id:
                del self.folders[i]
                self._save()
                return True
        return False

    def rename_folder(self, folder_id: str, name: str) -> bool:
        """Rename a folder.

        Args:
            folder_id: ID of the folder to rename
            name: New name for the folder

        Returns:
            True if folder was found and renamed, False otherwise
        """
        for folder in self.folders:
            if folder.id == folder_id:
                folder.name = name
                self._save()
                return True
        return False

    def get_folder(self, folder_id: str) -> FeedFolder | None:
        """Get a folder by ID."""
        for folder in self.folders:
            if folder.id == folder_id:
                return folder
        return None

    def get_all_folders(self) -> list[FeedFolder]:
        """Get all folders."""
        return list(self.folders)

    # Read/unread tracking

    @staticmethod
    def generate_item_id(
        feed_id: str, link: str, published: datetime | None = None
    ) -> str:
        """Generate a unique ID for a feed item.

        Uses a hash of feed_id + link + published date to create a stable ID.

        Args:
            feed_id: ID of the feed
            link: URL of the feed item
            published: Publication date of the item

        Returns:
            A unique item ID (hash)
        """
        pub_str = published.isoformat() if published else ""
        content = f"{feed_id}|{link}|{pub_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def mark_as_read(
        self, feed_id: str, link: str, published: datetime | None = None
    ) -> None:
        """Mark a feed item as read.

        Args:
            feed_id: ID of the feed
            link: URL of the feed item
            published: Publication date of the item
        """
        item_id = self.generate_item_id(feed_id, link, published)

        # Check if already marked as read
        if any(r.item_id == item_id for r in self.read_items):
            return

        read_item = ReadItem(item_id=item_id, feed_id=feed_id)
        self.read_items.append(read_item)
        self._save()

    def is_read(
        self, feed_id: str, link: str, published: datetime | None = None
    ) -> bool:
        """Check if a feed item is marked as read.

        Args:
            feed_id: ID of the feed
            link: URL of the feed item
            published: Publication date of the item

        Returns:
            True if the item is marked as read, False otherwise
        """
        item_id = self.generate_item_id(feed_id, link, published)
        return any(r.item_id == item_id for r in self.read_items)

    def get_unread_count(
        self, feed_id: str, items: list[tuple[str, datetime | None]]
    ) -> int:
        """Get the number of unread items in a feed.

        Args:
            feed_id: ID of the feed
            items: List of (link, published) tuples for feed items

        Returns:
            Number of unread items
        """
        unread = 0
        for link, published in items:
            if not self.is_read(feed_id, link, published):
                unread += 1
        return unread

    def mark_all_as_read(
        self, feed_id: str, items: list[tuple[str, datetime | None]]
    ) -> None:
        """Mark all items in a feed as read.

        Args:
            feed_id: ID of the feed
            items: List of (link, published) tuples for feed items
        """
        for link, published in items:
            self.mark_as_read(feed_id, link, published)
