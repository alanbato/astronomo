"""Bookmarks management for Astronomo.

This module provides bookmark storage with folder organization
and TOML persistence.
"""

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
    from typing import Self
else:
    import tomli as tomllib
    from typing_extensions import Self


@dataclass
class Bookmark:
    """Represents a single bookmark.

    Attributes:
        id: Unique identifier (UUID)
        url: The Gemini URL
        title: Display title for the bookmark
        folder_id: ID of containing folder, or None for root level
        created_at: When the bookmark was created
    """

    id: str
    url: str
    title: str
    folder_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, url: str, title: str, folder_id: str | None = None) -> Self:
        """Create a new bookmark with auto-generated ID."""
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
        )


@dataclass
class Folder:
    """Represents a bookmark folder.

    Attributes:
        id: Unique identifier (UUID)
        name: Display name of the folder
        parent_id: ID of parent folder for nesting (future use)
        color: Background color as hex string (e.g., "#4a4a5a") or None for default
        created_at: When the folder was created
    """

    id: str
    name: str
    parent_id: str | None = None
    color: str | None = None
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
        if self.color is not None:
            data["color"] = self.color
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary (TOML deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            parent_id=data.get("parent_id"),
            color=data.get("color"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class BookmarkManager:
    """Manages bookmarks and folders with TOML persistence.

    Provides CRUD operations for bookmarks and folders, with automatic
    persistence to a TOML file in the user's config directory.

    Args:
        config_dir: Directory for storing bookmarks file.
                   Defaults to ~/.config/astronomo/
    """

    VERSION = "1.0"

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "astronomo"
        self.bookmarks_file = self.config_dir / "bookmarks.toml"
        self.bookmarks: list[Bookmark] = []
        self.folders: list[Folder] = []
        self._load()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load bookmarks from TOML file."""
        if not self.bookmarks_file.exists():
            return

        try:
            with open(self.bookmarks_file, "rb") as f:
                data = tomllib.load(f)

            self.folders = [Folder.from_dict(f) for f in data.get("folders", [])]
            self.bookmarks = [Bookmark.from_dict(b) for b in data.get("bookmarks", [])]
        except (tomllib.TOMLDecodeError, KeyError, ValueError):
            # If file is corrupted, start fresh but don't overwrite
            self.bookmarks = []
            self.folders = []

    def _save(self) -> None:
        """Save bookmarks to TOML file."""
        self._ensure_config_dir()

        data = {
            "version": self.VERSION,
            "folders": [f.to_dict() for f in self.folders],
            "bookmarks": [b.to_dict() for b in self.bookmarks],
        }

        with open(self.bookmarks_file, "wb") as f:
            tomli_w.dump(data, f)

    # Bookmark operations

    def add_bookmark(
        self, url: str, title: str, folder_id: str | None = None
    ) -> Bookmark:
        """Add a new bookmark.

        Args:
            url: The Gemini URL to bookmark
            title: Display title for the bookmark
            folder_id: Optional folder ID to place the bookmark in

        Returns:
            The created Bookmark
        """
        bookmark = Bookmark.create(url=url, title=title, folder_id=folder_id)
        self.bookmarks.append(bookmark)
        self._save()
        return bookmark

    def remove_bookmark(self, bookmark_id: str) -> bool:
        """Remove a bookmark by ID.

        Args:
            bookmark_id: ID of the bookmark to remove

        Returns:
            True if bookmark was found and removed, False otherwise
        """
        for i, bookmark in enumerate(self.bookmarks):
            if bookmark.id == bookmark_id:
                del self.bookmarks[i]
                self._save()
                return True
        return False

    def update_bookmark(
        self,
        bookmark_id: str,
        title: str | None = None,
        folder_id: str | None = ...,  # type: ignore[assignment]
    ) -> bool:
        """Update a bookmark's properties.

        Args:
            bookmark_id: ID of the bookmark to update
            title: New title (if provided)
            folder_id: New folder ID, None for root, or ... to keep current

        Returns:
            True if bookmark was found and updated, False otherwise
        """
        for bookmark in self.bookmarks:
            if bookmark.id == bookmark_id:
                if title is not None:
                    bookmark.title = title
                if folder_id is not ...:
                    bookmark.folder_id = folder_id
                self._save()
                return True
        return False

    def get_bookmark(self, bookmark_id: str) -> Bookmark | None:
        """Get a bookmark by ID."""
        for bookmark in self.bookmarks:
            if bookmark.id == bookmark_id:
                return bookmark
        return None

    def get_bookmarks_in_folder(self, folder_id: str | None) -> list[Bookmark]:
        """Get all bookmarks in a specific folder.

        Args:
            folder_id: Folder ID, or None for root-level bookmarks

        Returns:
            List of bookmarks in the specified folder
        """
        return [b for b in self.bookmarks if b.folder_id == folder_id]

    def get_root_bookmarks(self) -> list[Bookmark]:
        """Get all bookmarks not in any folder."""
        return self.get_bookmarks_in_folder(None)

    def bookmark_exists(self, url: str) -> bool:
        """Check if a bookmark for the given URL already exists."""
        return any(b.url == url for b in self.bookmarks)

    # Folder operations

    def add_folder(self, name: str) -> Folder:
        """Add a new folder.

        Args:
            name: Display name for the folder

        Returns:
            The created Folder
        """
        folder = Folder.create(name=name)
        self.folders.append(folder)
        self._save()
        return folder

    def remove_folder(self, folder_id: str) -> bool:
        """Remove a folder, moving its bookmarks to root.

        Args:
            folder_id: ID of the folder to remove

        Returns:
            True if folder was found and removed, False otherwise
        """
        # Move bookmarks to root level
        for bookmark in self.bookmarks:
            if bookmark.folder_id == folder_id:
                bookmark.folder_id = None

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

    def update_folder_color(self, folder_id: str, color: str | None) -> bool:
        """Update a folder's background color.

        Args:
            folder_id: ID of the folder to update
            color: Hex color string (e.g., "#4a4a5a") or None for default

        Returns:
            True if folder was found and updated, False otherwise
        """
        for folder in self.folders:
            if folder.id == folder_id:
                folder.color = color
                self._save()
                return True
        return False

    def get_folder(self, folder_id: str) -> Folder | None:
        """Get a folder by ID."""
        for folder in self.folders:
            if folder.id == folder_id:
                return folder
        return None

    def get_all_folders(self) -> list[Folder]:
        """Get all folders."""
        return list(self.folders)
