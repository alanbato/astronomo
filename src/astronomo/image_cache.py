"""Image cache manager with LRU eviction.

Caches downloaded images to avoid re-downloading on history navigation.
Uses filesystem-based storage with SHA256 URL hashing for cache keys.
"""

import hashlib
import time
from pathlib import Path


class ImageCache:
    """Simple LRU cache for images with size limits.

    Storage: ~/.cache/astronomo/images/
    Naming: SHA256(url)[:16] as filename
    LRU: Tracked via access log (dict in memory)
    Eviction: When cache exceeds max_size_mb or max_slots

    Args:
        cache_dir: Directory for cache storage (default: ~/.cache/astronomo/images)
        max_size_mb: Maximum cache size in megabytes (default: 100)
        max_slots: Maximum number of cached images (default: 10)
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        max_size_mb: int = 100,
        max_slots: int = 10,
    ):
        """Initialize image cache manager."""
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "astronomo" / "images"
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_slots = max_slots

        # Access log: cache_key -> timestamp (ephemeral, rebuilt on restart)
        self._access_log: dict[str, float] = {}

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Rebuild access log from existing files
        self._rebuild_access_log()

    def _rebuild_access_log(self) -> None:
        """Rebuild access log from filesystem (mtime of cached files)."""
        for filepath in self.cache_dir.glob("*"):
            if filepath.is_file():
                cache_key = filepath.name
                # Use file modification time as last access time
                self._access_log[cache_key] = filepath.stat().st_mtime

    def get_cache_key(self, url: str) -> str:
        """Generate cache key from URL using SHA256 hash.

        Args:
            url: The URL to hash

        Returns:
            First 16 characters of SHA256 hash (collision-resistant)
        """
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def get(self, url: str) -> bytes | None:
        """Retrieve image from cache.

        Args:
            url: The original image URL

        Returns:
            Image data as bytes, or None if not cached
        """
        cache_key = self.get_cache_key(url)
        filepath = self.cache_dir / cache_key

        if not filepath.exists():
            return None

        # Update access time
        self._access_log[cache_key] = time.time()
        filepath.touch()  # Update mtime for consistency

        try:
            return filepath.read_bytes()
        except (OSError, IOError):
            # Corrupted cache file, delete it
            filepath.unlink(missing_ok=True)
            self._access_log.pop(cache_key, None)
            return None

    def put(self, url: str, data: bytes) -> None:
        """Store image in cache with LRU eviction.

        Args:
            url: The original image URL
            data: Image data as bytes
        """
        cache_key = self.get_cache_key(url)
        filepath = self.cache_dir / cache_key

        # Evict if needed before adding new item
        self._evict_if_needed(len(data))

        # Write to cache
        try:
            filepath.write_bytes(data)
            self._access_log[cache_key] = time.time()
        except (OSError, IOError):
            # Failed to write, silently ignore
            pass

    def _evict_if_needed(self, incoming_size: int) -> None:
        """Evict least recently used items if cache is full.

        Args:
            incoming_size: Size of incoming item in bytes
        """
        # Get current cache files
        cache_files = [f for f in self.cache_dir.glob("*") if f.is_file()]

        # Check slot count limit
        while len(cache_files) >= self.max_slots:
            self._evict_oldest(cache_files)
            cache_files = [f for f in self.cache_dir.glob("*") if f.is_file()]

        # Check size limit
        current_size = sum(f.stat().st_size for f in cache_files)
        while current_size + incoming_size > self.max_size_bytes and cache_files:
            evicted_size = self._evict_oldest(cache_files)
            current_size -= evicted_size
            cache_files = [f for f in self.cache_dir.glob("*") if f.is_file()]

    def _evict_oldest(self, cache_files: list[Path]) -> int:
        """Evict the least recently used cache file.

        Args:
            cache_files: List of current cache file paths

        Returns:
            Size of evicted file in bytes
        """
        if not cache_files:
            return 0

        # Find oldest by access time
        oldest = min(
            cache_files, key=lambda f: self._access_log.get(f.name, 0), default=None
        )

        if oldest is None:
            return 0

        try:
            size = oldest.stat().st_size
            oldest.unlink()
            self._access_log.pop(oldest.name, None)
            return size
        except (OSError, IOError):
            return 0

    def clear(self) -> None:
        """Clear entire cache."""
        for filepath in self.cache_dir.glob("*"):
            if filepath.is_file():
                filepath.unlink(missing_ok=True)
        self._access_log.clear()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with 'count' and 'size_bytes' keys
        """
        cache_files = [f for f in self.cache_dir.glob("*") if f.is_file()]
        return {
            "count": len(cache_files),
            "size_bytes": sum(f.stat().st_size for f in cache_files),
        }
