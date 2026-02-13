"""SQLite message cache for GMAP mail.

Provides local storage for messages and tags, enabling fast queries
and offline access. Cache location follows XDG spec (~/.cache/astronomo/).
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    last_sync TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    account_id TEXT NOT NULL,
    msgid TEXT NOT NULL,
    raw_bytes BLOB NOT NULL,
    sender TEXT,
    subject TEXT,
    timestamp TEXT,
    body_preview TEXT DEFAULT '',
    cached_at TEXT NOT NULL,
    PRIMARY KEY (account_id, msgid)
);

CREATE TABLE IF NOT EXISTS message_tags (
    account_id TEXT NOT NULL,
    msgid TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (account_id, msgid, tag)
);

CREATE INDEX IF NOT EXISTS idx_messages_timestamp
    ON messages(account_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_tags_lookup
    ON message_tags(account_id, tag);

CREATE INDEX IF NOT EXISTS idx_tags_msgid
    ON message_tags(account_id, msgid);
"""


@dataclass
class CachedMessage:
    """A message stored in the local cache.

    Attributes:
        msgid: Server-assigned message ID
        raw_bytes: Raw gemmail message bytes
        sender: Sender address string
        subject: Message subject (from first heading)
        timestamp: Message timestamp
        tags: List of tags on this message
        cached_at: When the message was cached locally
    """

    msgid: str
    raw_bytes: bytes
    sender: str
    subject: str | None
    timestamp: datetime | None
    body_preview: str = ""
    tags: list[str] = field(default_factory=list)
    cached_at: datetime = field(default_factory=datetime.now)

    def parse(self):
        """Parse raw bytes into a GemmailMessage."""
        from titlani.content.gemmail import GemmailMessage

        return GemmailMessage.from_bytes(self.raw_bytes)


class MailCache:
    """SQLite cache for GMAP messages.

    Args:
        cache_dir: Directory for the cache database.
                  Defaults to ~/.cache/astronomo/
    """

    def __init__(self, cache_dir: Path | None = None):
        cache_dir = cache_dir or Path.home() / ".cache" / "astronomo"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "mail_cache.db"
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_schema(self) -> None:
        """Create database tables and indexes if they don't exist."""
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)

        # Check/set schema version
        cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
        else:
            current = row["version"]
            if current < 2:
                conn.execute(
                    "ALTER TABLE messages ADD COLUMN body_preview TEXT DEFAULT ''"
                )
                conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def store_message(
        self,
        account_id: str,
        msgid: str,
        raw: bytes,
        tags: list[str],
    ) -> None:
        """Store a message in the cache.

        Args:
            account_id: Account ID
            msgid: Server message ID
            raw: Raw gemmail bytes
            tags: List of tags for this message
        """
        conn = self._get_conn()

        from titlani.content.gemmail import GemmailMessage

        # Parse message metadata for indexed fields
        sender = ""
        subject = None
        timestamp = None
        body_preview = ""
        try:
            msg = GemmailMessage.from_bytes(raw)
            if msg.senders:
                sender = str(msg.senders[0])
            subject = msg.subject
            if msg.timestamps:
                timestamp = msg.timestamps[0].isoformat()
            # Extract body preview: first non-heading, non-link, non-empty line
            if msg.body:
                for line in msg.body.splitlines():
                    stripped = line.strip()
                    if (
                        stripped
                        and not stripped.startswith("#")
                        and not stripped.startswith("=>")
                    ):
                        body_preview = stripped[:100]
                        break
        except Exception:
            logger.warning("Failed to parse message %s for indexing", msgid)

        now = datetime.now().isoformat()

        conn.execute(
            """INSERT OR REPLACE INTO messages
               (account_id, msgid, raw_bytes, sender, subject, timestamp,
                body_preview, cached_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (account_id, msgid, raw, sender, subject, timestamp, body_preview, now),
        )

        # Replace tags
        conn.execute(
            "DELETE FROM message_tags WHERE account_id = ? AND msgid = ?",
            (account_id, msgid),
        )
        for tag in tags:
            conn.execute(
                """INSERT OR IGNORE INTO message_tags
                   (account_id, msgid, tag) VALUES (?, ?, ?)""",
                (account_id, msgid, tag),
            )

        conn.commit()

    def get_message(self, account_id: str, msgid: str) -> CachedMessage | None:
        """Get a message from the cache.

        Args:
            account_id: Account ID
            msgid: Message ID

        Returns:
            CachedMessage or None if not found
        """
        conn = self._get_conn()

        cursor = conn.execute(
            """SELECT msgid, raw_bytes, sender, subject, timestamp,
                      body_preview, cached_at
               FROM messages
               WHERE account_id = ? AND msgid = ?""",
            (account_id, msgid),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        # Get tags
        tag_cursor = conn.execute(
            "SELECT tag FROM message_tags WHERE account_id = ? AND msgid = ?",
            (account_id, msgid),
        )
        tags = [r["tag"] for r in tag_cursor.fetchall()]

        return CachedMessage(
            msgid=row["msgid"],
            raw_bytes=row["raw_bytes"],
            sender=row["sender"] or "",
            subject=row["subject"],
            timestamp=(
                datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None
            ),
            body_preview=row["body_preview"] or "",
            tags=tags,
            cached_at=datetime.fromisoformat(row["cached_at"]),
        )

    def list_by_tag(
        self,
        account_id: str,
        tag: str,
        limit: int = 200,
    ) -> list[CachedMessage]:
        """List messages with a specific tag, sorted newest first.

        Args:
            account_id: Account ID
            tag: Tag to filter by
            limit: Maximum number of messages to return

        Returns:
            List of CachedMessage objects
        """
        conn = self._get_conn()

        # Exclude Trash-tagged messages from non-Trash views (GMAP spec:
        # Trash hides messages from all other tag views)
        if tag == "Trash":
            cursor = conn.execute(
                """SELECT m.msgid, m.raw_bytes, m.sender, m.subject,
                          m.timestamp, m.body_preview, m.cached_at
                   FROM messages m
                   JOIN message_tags t ON m.account_id = t.account_id
                                       AND m.msgid = t.msgid
                   WHERE m.account_id = ? AND t.tag = ?
                   ORDER BY m.timestamp DESC
                   LIMIT ?""",
                (account_id, tag, limit),
            )
        else:
            cursor = conn.execute(
                """SELECT m.msgid, m.raw_bytes, m.sender, m.subject,
                          m.timestamp, m.body_preview, m.cached_at
                   FROM messages m
                   JOIN message_tags t ON m.account_id = t.account_id
                                       AND m.msgid = t.msgid
                   WHERE m.account_id = ? AND t.tag = ?
                     AND NOT EXISTS (
                       SELECT 1 FROM message_tags trash
                       WHERE trash.account_id = m.account_id
                         AND trash.msgid = m.msgid
                         AND trash.tag = 'Trash'
                     )
                   ORDER BY m.timestamp DESC
                   LIMIT ?""",
                (account_id, tag, limit),
            )
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            # Get all tags for each message
            tag_cursor = conn.execute(
                "SELECT tag FROM message_tags WHERE account_id = ? AND msgid = ?",
                (account_id, row["msgid"]),
            )
            tags = [r["tag"] for r in tag_cursor.fetchall()]

            messages.append(
                CachedMessage(
                    msgid=row["msgid"],
                    raw_bytes=row["raw_bytes"],
                    sender=row["sender"] or "",
                    subject=row["subject"],
                    timestamp=(
                        datetime.fromisoformat(row["timestamp"])
                        if row["timestamp"]
                        else None
                    ),
                    body_preview=row["body_preview"] or "",
                    tags=tags,
                    cached_at=datetime.fromisoformat(row["cached_at"]),
                )
            )

        return messages

    def update_tags(
        self,
        account_id: str,
        msgid: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> None:
        """Update tags on a message.

        Args:
            account_id: Account ID
            msgid: Message ID
            add: Tags to add
            remove: Tags to remove
        """
        conn = self._get_conn()

        if remove:
            for tag in remove:
                conn.execute(
                    """DELETE FROM message_tags
                       WHERE account_id = ? AND msgid = ? AND tag = ?""",
                    (account_id, msgid, tag),
                )

        if add:
            for tag in add:
                conn.execute(
                    """INSERT OR IGNORE INTO message_tags
                       (account_id, msgid, tag) VALUES (?, ?, ?)""",
                    (account_id, msgid, tag),
                )

        conn.commit()

    def remove_message(self, account_id: str, msgid: str) -> None:
        """Remove a message from the cache.

        Args:
            account_id: Account ID
            msgid: Message ID
        """
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM message_tags WHERE account_id = ? AND msgid = ?",
            (account_id, msgid),
        )
        conn.execute(
            "DELETE FROM messages WHERE account_id = ? AND msgid = ?",
            (account_id, msgid),
        )
        conn.commit()

    def get_last_sync(self, account_id: str) -> datetime | None:
        """Get the last sync timestamp for an account.

        Args:
            account_id: Account ID

        Returns:
            Last sync datetime or None
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT last_sync FROM accounts WHERE account_id = ?",
            (account_id,),
        )
        row = cursor.fetchone()
        if row is None or row["last_sync"] is None:
            return None
        return datetime.fromisoformat(row["last_sync"])

    def set_last_sync(self, account_id: str, ts: datetime) -> None:
        """Set the last sync timestamp for an account.

        Args:
            account_id: Account ID
            ts: Sync timestamp
        """
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO accounts (account_id, hostname, last_sync)
               VALUES (?, '', ?)""",
            (account_id, ts.isoformat()),
        )
        conn.commit()

    def get_all_tags(self, account_id: str) -> list[str]:
        """Get all unique tags for an account, ordered by message count.

        Args:
            account_id: Account ID

        Returns:
            List of tag names
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT tag, COUNT(*) as cnt
               FROM message_tags
               WHERE account_id = ?
               GROUP BY tag
               ORDER BY cnt DESC""",
            (account_id,),
        )
        return [row["tag"] for row in cursor.fetchall()]

    def get_tag_counts(self, account_id: str) -> dict[str, int]:
        """Get message counts per tag.

        Args:
            account_id: Account ID

        Returns:
            Dict mapping tag name to message count
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT tag, COUNT(*) as cnt
               FROM message_tags
               WHERE account_id = ?
               GROUP BY tag""",
            (account_id,),
        )
        return {row["tag"]: row["cnt"] for row in cursor.fetchall()}

    def get_unread_count(self, account_id: str, tag: str) -> int:
        """Get the number of unread messages in a tag.

        Args:
            account_id: Account ID
            tag: Tag to count unread for

        Returns:
            Number of messages that have both the given tag and "Unread" tag
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT COUNT(DISTINCT t1.msgid) as cnt
               FROM message_tags t1
               JOIN message_tags t2 ON t1.account_id = t2.account_id
                                    AND t1.msgid = t2.msgid
               WHERE t1.account_id = ? AND t1.tag = ? AND t2.tag = 'Unread'""",
            (account_id, tag),
        )
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def has_message(self, account_id: str, msgid: str) -> bool:
        """Check if a message exists in the cache.

        Args:
            account_id: Account ID
            msgid: Message ID

        Returns:
            True if the message exists
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT 1 FROM messages WHERE account_id = ? AND msgid = ?",
            (account_id, msgid),
        )
        return cursor.fetchone() is not None
