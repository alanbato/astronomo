"""Client certificate identity management for Astronomo.

This module provides identity storage for Gemini client certificates
with TOML persistence and URL prefix matching.
"""

import platform
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
from nauyaca.security.certificates import (
    generate_self_signed_cert,
    get_certificate_fingerprint_from_path,
    get_certificate_info,
    is_certificate_expired,
    load_certificate,
)


def pem_file_contains_key(file_path: Path) -> bool:
    """Check if a PEM file contains a private key.

    Args:
        file_path: Path to the PEM file

    Returns:
        True if the file contains a private key section
    """
    try:
        content = file_path.read_text()
        return "-----BEGIN" in content and "PRIVATE KEY-----" in content
    except (OSError, UnicodeDecodeError):
        return False


def pem_file_contains_certificate(file_path: Path) -> bool:
    """Check if a PEM file contains a certificate.

    Args:
        file_path: Path to the PEM file

    Returns:
        True if the file contains a certificate section
    """
    try:
        content = file_path.read_text()
        return "-----BEGIN CERTIFICATE-----" in content
    except (OSError, UnicodeDecodeError):
        return False


def is_combined_pem_file(file_path: Path) -> bool:
    """Check if a PEM file contains both a certificate and private key.

    Args:
        file_path: Path to the PEM file

    Returns:
        True if the file contains both certificate and key
    """
    return pem_file_contains_certificate(file_path) and pem_file_contains_key(file_path)


def extract_key_from_pem(pem_content: str) -> str:
    """Extract the private key section from a combined PEM file.

    Args:
        pem_content: Full content of the PEM file

    Returns:
        The private key section including BEGIN/END markers
    """
    lines = pem_content.split("\n")
    key_lines = []
    in_key = False

    for line in lines:
        if "-----BEGIN" in line and "PRIVATE KEY-----" in line:
            in_key = True
        if in_key:
            key_lines.append(line)
        if in_key and "-----END" in line and "PRIVATE KEY-----" in line:
            break

    return "\n".join(key_lines)


def extract_cert_from_pem(pem_content: str) -> str:
    """Extract the certificate section from a combined PEM file.

    Args:
        pem_content: Full content of the PEM file

    Returns:
        The certificate section including BEGIN/END markers
    """
    lines = pem_content.split("\n")
    cert_lines = []
    in_cert = False

    for line in lines:
        if "-----BEGIN CERTIFICATE-----" in line:
            in_cert = True
        if in_cert:
            cert_lines.append(line)
        if in_cert and "-----END CERTIFICATE-----" in line:
            break

    return "\n".join(cert_lines)


def get_lagrange_idents_path() -> Path | None:
    """Get the Lagrange idents directory path based on the current OS.

    Checks multiple possible locations including Flatpak installations.

    Returns:
        Path to Lagrange idents directory, or None if not found.
    """
    system = platform.system()
    home = Path.home()

    # Define possible paths in order of preference
    paths: list[Path] = []

    if system == "Linux":
        # Standard Linux path
        paths.append(home / ".config" / "lagrange" / "idents")
        # Flatpak installation path
        paths.append(
            home
            / ".var"
            / "app"
            / "fi.skyjake.Lagrange"
            / "config"
            / "lagrange"
            / "idents"
        )
    elif system == "Darwin":  # macOS
        paths.append(
            home / "Library" / "Application Support" / "fi.skyjake.Lagrange" / "idents"
        )
    elif system == "Windows":
        paths.append(home / "AppData" / "Roaming" / "fi.skyjake.Lagrange" / "idents")
    else:
        return None

    # Return the first path that exists
    for path in paths:
        if path.exists() and path.is_dir():
            return path

    return None


@dataclass
class LagrangeImportResult:
    """Result of importing identities from Lagrange.

    Attributes:
        imported: List of successfully imported Identity objects
        skipped_duplicates: List of identity names that were skipped (already exist by fingerprint)
        errors: List of (filename, error_message) tuples for failed imports
    """

    imported: list["Identity"] = field(default_factory=list)
    skipped_duplicates: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


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

    def get_all_identities_for_url(self, url: str) -> list[Identity]:
        """Find all identities that have URL prefixes matching the given URL.

        Unlike get_identity_for_url() which returns only the longest-prefix match,
        this returns ALL identities that could be used for the URL.

        Args:
            url: The URL to match against

        Returns:
            List of matching Identity objects, sorted by longest prefix first
        """
        matches: list[tuple[int, Identity]] = []

        for identity in self.identities:
            for prefix in identity.url_prefixes:
                if url.startswith(prefix):
                    matches.append((len(prefix), identity))
                    break  # Only count each identity once (use longest matching prefix)

        # Sort by prefix length descending (longest match first)
        matches.sort(key=lambda x: x[0], reverse=True)
        return [identity for _, identity in matches]

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

    # Lagrange import operations

    def has_identity_with_fingerprint(self, fingerprint: str) -> bool:
        """Check if an identity with the given fingerprint already exists.

        Args:
            fingerprint: SHA-256 fingerprint to check

        Returns:
            True if an identity with this fingerprint exists
        """
        return any(i.fingerprint == fingerprint for i in self.identities)

    def discover_lagrange_identities(
        self, idents_path: Path
    ) -> list[tuple[str, Path, Path]]:
        """Discover .crt/.key pairs in a Lagrange idents directory.

        Args:
            idents_path: Path to Lagrange idents directory

        Returns:
            List of (name, cert_path, key_path) tuples for valid pairs
        """
        pairs = []
        crt_files = list(idents_path.glob("*.crt"))

        for crt_path in crt_files:
            name = crt_path.stem  # e.g., "myident" from "myident.crt"
            key_path = crt_path.with_suffix(".key")

            if key_path.exists():
                pairs.append((name, crt_path, key_path))

        return pairs

    def import_identity_from_files(
        self,
        name: str,
        source_cert_path: Path,
        source_key_path: Path,
    ) -> Identity:
        """Import an identity from existing certificate and key files.

        Args:
            name: Human-readable name for the identity
            source_cert_path: Path to source certificate PEM file
            source_key_path: Path to source private key PEM file

        Returns:
            The imported Identity

        Raises:
            ValueError: If certificate is invalid or expired
            FileNotFoundError: If source files don't exist
        """
        self._ensure_dirs()

        # Validate and read certificate
        cert = load_certificate(source_cert_path)
        if is_certificate_expired(cert):
            raise ValueError("Certificate is expired")

        # Get fingerprint and expiration
        fingerprint = get_certificate_fingerprint_from_path(source_cert_path)
        cert_info = get_certificate_info(cert)

        # Parse expiration date
        expires_at = None
        if "not_after" in cert_info:
            try:
                expires_at = datetime.fromisoformat(cert_info["not_after"])
            except ValueError:
                pass

        # Generate new ID and destination paths
        identity_id = str(uuid.uuid4())
        dest_cert_path = self.certs_dir / f"{identity_id}.pem"
        dest_key_path = self.certs_dir / f"{identity_id}.key"

        # Copy files
        dest_cert_path.write_bytes(source_cert_path.read_bytes())
        dest_key_path.write_bytes(source_key_path.read_bytes())

        # Set restrictive permissions on key file
        dest_key_path.chmod(0o600)

        # Create identity object
        identity = Identity(
            id=identity_id,
            name=name,
            fingerprint=fingerprint,
            cert_path=dest_cert_path,
            key_path=dest_key_path,
            url_prefixes=[],  # Empty - Lagrange metadata not available
            expires_at=expires_at,
        )

        self.identities.append(identity)
        self._save()
        return identity

    def import_identity_from_custom_files(
        self,
        name: str,
        cert_path: Path,
        key_path: Path | None = None,
    ) -> Identity:
        """Import an identity from custom certificate and key files.

        Supports both separate cert/key files and combined PEM files
        containing both certificate and private key.

        Args:
            name: Human-readable name for the identity
            cert_path: Path to certificate PEM file (may also contain key)
            key_path: Path to private key PEM file. If None, assumes cert_path
                     contains both certificate and key (combined PEM).

        Returns:
            The imported Identity

        Raises:
            ValueError: If certificate is invalid, expired, or files are missing
            FileNotFoundError: If source files don't exist
        """
        self._ensure_dirs()

        # Validate cert file exists
        if not cert_path.exists():
            raise FileNotFoundError(f"Certificate file not found: {cert_path}")

        # Check if using combined PEM or separate files
        if key_path is None:
            # Combined PEM mode - cert_path should contain both cert and key
            if not is_combined_pem_file(cert_path):
                raise ValueError(
                    "Certificate file does not contain both certificate and private key"
                )

            # Read and split the combined PEM
            pem_content = cert_path.read_text()
            cert_pem = extract_cert_from_pem(pem_content)
            key_pem = extract_key_from_pem(pem_content)

            if not cert_pem or not key_pem:
                raise ValueError("Could not extract certificate or key from PEM file")
        else:
            # Separate files mode
            if not key_path.exists():
                raise FileNotFoundError(f"Key file not found: {key_path}")

            if not pem_file_contains_certificate(cert_path):
                raise ValueError(
                    "Certificate file does not contain a valid certificate"
                )

            if not pem_file_contains_key(key_path):
                raise ValueError("Key file does not contain a valid private key")

            cert_pem = cert_path.read_text()
            key_pem = key_path.read_text()

        # Validate and load certificate
        cert = load_certificate(cert_path)
        if is_certificate_expired(cert):
            raise ValueError("Certificate is expired")

        # Get fingerprint and expiration
        fingerprint = get_certificate_fingerprint_from_path(cert_path)

        # Check for duplicate
        if self.has_identity_with_fingerprint(fingerprint):
            raise ValueError("An identity with this certificate already exists")

        cert_info = get_certificate_info(cert)

        # Parse expiration date
        expires_at = None
        if "not_after" in cert_info:
            try:
                expires_at = datetime.fromisoformat(cert_info["not_after"])
            except ValueError:
                pass

        # Generate new ID and destination paths
        identity_id = str(uuid.uuid4())
        dest_cert_path = self.certs_dir / f"{identity_id}.pem"
        dest_key_path = self.certs_dir / f"{identity_id}.key"

        # Write the separated cert and key files
        dest_cert_path.write_text(cert_pem)
        dest_key_path.write_text(key_pem)

        # Set restrictive permissions on key file
        dest_key_path.chmod(0o600)

        # Create identity object
        identity = Identity(
            id=identity_id,
            name=name,
            fingerprint=fingerprint,
            cert_path=dest_cert_path,
            key_path=dest_key_path,
            url_prefixes=[],
            expires_at=expires_at,
        )

        self.identities.append(identity)
        self._save()
        return identity

    def import_from_lagrange(
        self,
        idents_path: Path | None = None,
        names: dict[Path, str] | None = None,
    ) -> LagrangeImportResult:
        """Import identities from Lagrange browser.

        Discovers .crt/.key pairs in the Lagrange idents directory,
        validates certificates, and imports them into Astronomo.

        Args:
            idents_path: Optional explicit path to idents directory.
                        If None, auto-detects based on OS.
            names: Optional dict mapping cert_path to identity name.
                   If provided, uses these names instead of filenames.

        Returns:
            LagrangeImportResult with import statistics

        Raises:
            FileNotFoundError: If Lagrange idents directory not found
        """
        if idents_path is None:
            idents_path = get_lagrange_idents_path()
            if idents_path is None:
                raise FileNotFoundError("Lagrange idents directory not found")

        if not idents_path.exists():
            raise FileNotFoundError(f"Directory not found: {idents_path}")

        pairs = self.discover_lagrange_identities(idents_path)

        result = LagrangeImportResult()

        for default_name, cert_path, key_path in pairs:
            try:
                # Check for duplicate by fingerprint
                fingerprint = get_certificate_fingerprint_from_path(cert_path)
                if self.has_identity_with_fingerprint(fingerprint):
                    # Use fingerprint (truncated) for skipped duplicates
                    result.skipped_duplicates.append(fingerprint[:32] + "...")
                    continue

                # Get name from names dict or fall back to filename
                name = names.get(cert_path, default_name) if names else default_name

                identity = self.import_identity_from_files(name, cert_path, key_path)
                result.imported.append(identity)
            except ValueError as e:
                # Use fingerprint for error reporting
                error_id = fingerprint[:32] + "..." if fingerprint else default_name
                result.errors.append((error_id, str(e)))
            except Exception as e:
                error_id = fingerprint[:32] + "..." if fingerprint else default_name
                result.errors.append((error_id, f"Unexpected error: {e}"))

        return result
