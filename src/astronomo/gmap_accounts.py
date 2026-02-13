"""GMAP account management for Astronomo.

Provides account configuration storage with TOML persistence,
following the same patterns as FeedManager and BookmarkManager.
"""

import logging
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

logger = logging.getLogger(__name__)

_SENTINEL = object()


@dataclass
class GmapAccount:
    """Represents a GMAP mail account.

    Attributes:
        id: Unique identifier (UUID)
        name: Display name (e.g., "Work Mail")
        hostname: GMAP server hostname
        port: GMAP server port (default 1960)
        mailbox: Mailbox name (from certificate USER_ID)
        identity_id: Reference to IdentityManager identity
        gmap_address: Address for sent mail copies (default: gmap@hostname)
        last_sync: When the account was last synced
        created_at: When the account was added
    """

    id: str
    name: str
    hostname: str
    port: int = 1960
    mailbox: str = ""
    identity_id: str = ""
    gmap_address: str = ""
    last_sync: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        name: str,
        hostname: str,
        port: int = 1960,
        mailbox: str = "",
        identity_id: str = "",
        gmap_address: str = "",
    ) -> Self:
        """Create a new account with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            hostname=hostname,
            port=port,
            mailbox=mailbox,
            identity_id=identity_id,
            gmap_address=gmap_address or f"gmap@{hostname}",
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        data = {
            "id": self.id,
            "name": self.name,
            "hostname": self.hostname,
            "port": self.port,
            "mailbox": self.mailbox,
            "identity_id": self.identity_id,
            "gmap_address": self.gmap_address,
            "created_at": self.created_at.isoformat(),
        }
        if self.last_sync is not None:
            data["last_sync"] = self.last_sync.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary (TOML deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            hostname=data["hostname"],
            port=data.get("port", 1960),
            mailbox=data.get("mailbox", ""),
            identity_id=data.get("identity_id", ""),
            gmap_address=data.get("gmap_address", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_sync=(
                datetime.fromisoformat(data["last_sync"])
                if data.get("last_sync")
                else None
            ),
        )


class GmapAccountManager:
    """Manages GMAP accounts with TOML persistence.

    Provides CRUD operations for mail accounts and persists
    configuration to a TOML file in the user's config directory.

    Args:
        config_dir: Directory for storing accounts file.
                   Defaults to ~/.config/astronomo/
    """

    VERSION = "1.0"

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "astronomo"
        self.accounts_file = self.config_dir / "gmap_accounts.toml"
        self.accounts: list[GmapAccount] = []
        self._load()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load accounts from TOML file."""
        if not self.accounts_file.exists():
            return

        try:
            with open(self.accounts_file, "rb") as f:
                data = tomllib.load(f)

            self.accounts = [GmapAccount.from_dict(a) for a in data.get("accounts", [])]
        except tomllib.TOMLDecodeError as e:
            logger.error("Failed to parse gmap_accounts.toml: %s", e)
            self.accounts = []
        except (KeyError, ValueError, TypeError) as e:
            logger.error("Invalid data in gmap_accounts.toml: %s", e)
            self.accounts = []

    def _save(self) -> None:
        """Save accounts to TOML file."""
        try:
            self._ensure_config_dir()
        except OSError as e:
            logger.error("Cannot create config directory: %s", e)
            raise

        data = {
            "version": self.VERSION,
            "accounts": [a.to_dict() for a in self.accounts],
        }

        try:
            with open(self.accounts_file, "wb") as f:
                tomli_w.dump(data, f)
        except OSError as e:
            logger.error("Cannot save accounts file: %s", e)
            raise

    def add_account(
        self,
        name: str,
        hostname: str,
        port: int = 1960,
        mailbox: str = "",
        identity_id: str = "",
        gmap_address: str = "",
    ) -> GmapAccount:
        """Add a new GMAP account.

        Args:
            name: Display name for the account
            hostname: GMAP server hostname
            port: GMAP server port
            mailbox: Mailbox name
            identity_id: Reference to IdentityManager identity
            gmap_address: Address for sent mail copies

        Returns:
            The created GmapAccount
        """
        account = GmapAccount.create(
            name=name,
            hostname=hostname,
            port=port,
            mailbox=mailbox,
            identity_id=identity_id,
            gmap_address=gmap_address,
        )
        self.accounts.append(account)
        self._save()
        return account

    def remove_account(self, account_id: str) -> bool:
        """Remove an account.

        Args:
            account_id: ID of the account to remove

        Returns:
            True if account was found and removed, False otherwise
        """
        for i, account in enumerate(self.accounts):
            if account.id == account_id:
                del self.accounts[i]
                self._save()
                return True
        return False

    def update_account(
        self,
        account_id: str,
        name: str | None = None,
        hostname: str | None = None,
        port: int | None = None,
        mailbox: str | None = None,
        identity_id: str | None = None,
        gmap_address: str | None = None,
        last_sync: datetime | object = _SENTINEL,
    ) -> bool:
        """Update an account's properties.

        Args:
            account_id: ID of the account to update
            name: New display name (if provided)
            hostname: New hostname (if provided)
            port: New port (if provided)
            mailbox: New mailbox name (if provided)
            identity_id: New identity reference (if provided)
            gmap_address: New GMAP address (if provided)
            last_sync: New last sync timestamp (use _SENTINEL to keep current)

        Returns:
            True if account was found and updated, False otherwise
        """
        for account in self.accounts:
            if account.id == account_id:
                if name is not None:
                    account.name = name
                if hostname is not None:
                    account.hostname = hostname
                if port is not None:
                    account.port = port
                if mailbox is not None:
                    account.mailbox = mailbox
                if identity_id is not None:
                    account.identity_id = identity_id
                if gmap_address is not None:
                    account.gmap_address = gmap_address
                if last_sync is not _SENTINEL:
                    account.last_sync = last_sync  # type: ignore[assignment]
                self._save()
                return True
        return False

    def get_account(self, account_id: str) -> GmapAccount | None:
        """Get an account by ID."""
        for account in self.accounts:
            if account.id == account_id:
                return account
        return None

    def get_all_accounts(self) -> list[GmapAccount]:
        """Get all accounts."""
        return list(self.accounts)
