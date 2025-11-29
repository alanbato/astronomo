"""Client certificate identity management for Astronomo.

This module provides identity storage for Gemini client certificates
with TOML persistence and URL prefix matching.
"""

import tomllib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Self

import tomli_w
from nauyaca.security.certificates import (
    generate_self_signed_cert,
    get_certificate_fingerprint_from_path,
    get_certificate_info,
    is_certificate_expired,
    load_certificate,
)


@dataclass
class Identity:
    """Represents a client certificate identity.

    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable name for the identity
        fingerprint: SHA-256 fingerprint of the certificate
        cert_path: Path to the certificate PEM file
        key_path: Path to the private key PEM file
        url_prefixes: List of URL prefixes this identity is used for
        created_at: When the identity was created
        expires_at: Certificate expiration date
    """

    id: str
    name: str
    fingerprint: str
    cert_path: Path
    key_path: Path
    url_prefixes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None

    @classmethod
    def create(
        cls,
        name: str,
        fingerprint: str,
        cert_path: Path,
        key_path: Path,
        expires_at: datetime | None = None,
    ) -> Self:
        """Create a new identity with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            fingerprint=fingerprint,
            cert_path=cert_path,
            key_path=key_path,
            expires_at=expires_at,
        )

    def add_url_prefix(self, prefix: str) -> None:
        """Add a URL prefix this identity should be used for."""
        if prefix not in self.url_prefixes:
            self.url_prefixes.append(prefix)

    def remove_url_prefix(self, prefix: str) -> bool:
        """Remove a URL prefix. Returns True if removed."""
        if prefix in self.url_prefixes:
            self.url_prefixes.remove(prefix)
            return True
        return False

    def matches_url(self, url: str) -> bool:
        """Check if this identity should be used for a given URL."""
        return any(url.startswith(prefix) for prefix in self.url_prefixes)

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        data = {
            "id": self.id,
            "name": self.name,
            "fingerprint": self.fingerprint,
            "cert_path": str(self.cert_path),
            "key_path": str(self.key_path),
            "url_prefixes": self.url_prefixes,
            "created_at": self.created_at.isoformat(),
        }
        if self.expires_at is not None:
            data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary (TOML deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            fingerprint=data["fingerprint"],
            cert_path=Path(data["cert_path"]),
            key_path=Path(data["key_path"]),
            url_prefixes=data.get("url_prefixes", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )


class IdentityManager:
    """Manages client certificate identities with TOML persistence.

    Provides CRUD operations for identities, certificate generation,
    and URL prefix matching.

    Storage locations:
        - Metadata: ~/.config/astronomo/identities.toml
        - Certificates: ~/.config/astronomo/certificates/{id}.pem
        - Keys: ~/.config/astronomo/certificates/{id}.key

    Args:
        config_dir: Directory for storing identity files.
                   Defaults to ~/.config/astronomo/
    """

    VERSION = "1.0"

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "astronomo"
        self.identities_file = self.config_dir / "identities.toml"
        self.certs_dir = self.config_dir / "certificates"
        self.identities: list[Identity] = []
        self._load()

    def _ensure_dirs(self) -> None:
        """Create config and certificates directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.certs_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load identities from TOML file."""
        if not self.identities_file.exists():
            return

        try:
            with open(self.identities_file, "rb") as f:
                data = tomllib.load(f)

            self.identities = [
                Identity.from_dict(i) for i in data.get("identities", [])
            ]
        except (tomllib.TOMLDecodeError, KeyError, ValueError):
            # If file is corrupted, start fresh but don't overwrite
            self.identities = []

    def _save(self) -> None:
        """Save identities to TOML file."""
        self._ensure_dirs()

        data = {
            "version": self.VERSION,
            "identities": [i.to_dict() for i in self.identities],
        }

        with open(self.identities_file, "wb") as f:
            tomli_w.dump(data, f)

    # Identity operations

    def create_identity(
        self,
        name: str,
        hostname: str,
        key_size: int = 2048,
        valid_days: int = 365,
    ) -> Identity:
        """Generate a new identity with self-signed certificate.

        Args:
            name: Human-readable name for the identity
            hostname: Hostname for the certificate (used in CN/SAN)
            key_size: RSA key size in bits (default: 2048)
            valid_days: Certificate validity period in days (default: 365)

        Returns:
            The created Identity
        """
        self._ensure_dirs()

        # Generate certificate using Nauyaca
        cert_pem, key_pem = generate_self_signed_cert(
            hostname=hostname,
            key_size=key_size,
            valid_days=valid_days,
        )

        # Generate ID and file paths
        identity_id = str(uuid.uuid4())
        cert_path = self.certs_dir / f"{identity_id}.pem"
        key_path = self.certs_dir / f"{identity_id}.key"

        # Write certificate and key files
        cert_path.write_bytes(cert_pem)
        key_path.write_bytes(key_pem)

        # Set restrictive permissions on key file
        key_path.chmod(0o600)

        # Get fingerprint and expiration
        fingerprint = get_certificate_fingerprint_from_path(cert_path)
        cert = load_certificate(cert_path)
        cert_info = get_certificate_info(cert)

        # Parse expiration date
        expires_at = None
        if "not_after" in cert_info:
            try:
                expires_at = datetime.fromisoformat(cert_info["not_after"])
            except ValueError:
                pass

        # Create identity object
        identity = Identity(
            id=identity_id,
            name=name,
            fingerprint=fingerprint,
            cert_path=cert_path,
            key_path=key_path,
            expires_at=expires_at,
        )

        self.identities.append(identity)
        self._save()
        return identity

    def remove_identity(self, identity_id: str) -> bool:
        """Remove an identity and its certificate files.

        Args:
            identity_id: ID of the identity to remove

        Returns:
            True if identity was found and removed, False otherwise
        """
        for i, identity in enumerate(self.identities):
            if identity.id == identity_id:
                # Delete certificate files
                if identity.cert_path.exists():
                    identity.cert_path.unlink()
                if identity.key_path.exists():
                    identity.key_path.unlink()
                # Remove from list
                del self.identities[i]
                self._save()
                return True
        return False

    def rename_identity(self, identity_id: str, new_name: str) -> bool:
        """Rename an identity.

        Args:
            identity_id: ID of the identity to rename
            new_name: New name for the identity

        Returns:
            True if identity was found and renamed, False otherwise
        """
        for identity in self.identities:
            if identity.id == identity_id:
                identity.name = new_name
                self._save()
                return True
        return False

    def get_identity(self, identity_id: str) -> Identity | None:
        """Get an identity by ID."""
        for identity in self.identities:
            if identity.id == identity_id:
                return identity
        return None

    def get_all_identities(self) -> list[Identity]:
        """Get all identities."""
        return list(self.identities)

    # URL prefix operations

    def add_url_prefix(self, identity_id: str, url_prefix: str) -> bool:
        """Associate a URL prefix with an identity.

        Args:
            identity_id: ID of the identity
            url_prefix: URL prefix to associate (e.g., "gemini://example.com/")

        Returns:
            True if successful, False if identity not found
        """
        identity = self.get_identity(identity_id)
        if identity:
            identity.add_url_prefix(url_prefix)
            self._save()
            return True
        return False

    def remove_url_prefix(self, identity_id: str, url_prefix: str) -> bool:
        """Remove a URL prefix from an identity.

        Args:
            identity_id: ID of the identity
            url_prefix: URL prefix to remove

        Returns:
            True if successful, False if identity or prefix not found
        """
        identity = self.get_identity(identity_id)
        if identity and identity.remove_url_prefix(url_prefix):
            self._save()
            return True
        return False

    def get_identity_for_url(self, url: str) -> Identity | None:
        """Find the identity that matches a URL based on prefixes.

        Uses longest-prefix matching: if multiple identities match,
        the one with the longest matching prefix is returned.

        Args:
            url: The URL to match against

        Returns:
            The matching Identity, or None if no match
        """
        best_match: Identity | None = None
        best_length = 0

        for identity in self.identities:
            for prefix in identity.url_prefixes:
                if url.startswith(prefix) and len(prefix) > best_length:
                    best_match = identity
                    best_length = len(prefix)

        return best_match

    # Certificate validation

    def is_identity_valid(self, identity_id: str) -> bool:
        """Check if identity's certificate exists and is not expired.

        Args:
            identity_id: ID of the identity to check

        Returns:
            True if certificate exists and is valid, False otherwise
        """
        identity = self.get_identity(identity_id)
        if not identity:
            return False
        if not identity.cert_path.exists():
            return False
        try:
            cert = load_certificate(identity.cert_path)
            return not is_certificate_expired(cert)
        except (FileNotFoundError, ValueError):
            return False

    def regenerate_certificate(
        self,
        identity_id: str,
        hostname: str,
        key_size: int = 2048,
        valid_days: int = 365,
    ) -> bool:
        """Regenerate certificate for existing identity.

        Note: This creates a new key pair and fingerprint. The server
        will see this as a new identity.

        Args:
            identity_id: ID of the identity to regenerate
            hostname: Hostname for the new certificate
            key_size: RSA key size in bits
            valid_days: Certificate validity period in days

        Returns:
            True if successful, False if identity not found
        """
        identity = self.get_identity(identity_id)
        if not identity:
            return False

        # Generate new certificate
        cert_pem, key_pem = generate_self_signed_cert(
            hostname=hostname,
            key_size=key_size,
            valid_days=valid_days,
        )

        # Write new files
        identity.cert_path.write_bytes(cert_pem)
        identity.key_path.write_bytes(key_pem)
        identity.key_path.chmod(0o600)

        # Update fingerprint and expiration
        identity.fingerprint = get_certificate_fingerprint_from_path(identity.cert_path)
        cert = load_certificate(identity.cert_path)
        cert_info = get_certificate_info(cert)

        if "not_after" in cert_info:
            try:
                identity.expires_at = datetime.fromisoformat(cert_info["not_after"])
            except ValueError:
                identity.expires_at = None

        self._save()
        return True
