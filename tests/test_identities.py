"""Tests for the identities module."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from astronomo.identities import Identity, IdentityManager


class TestIdentity:
    """Tests for the Identity dataclass."""

    def test_create_generates_uuid(self) -> None:
        """Test that create() generates a unique ID."""
        identity = Identity.create(
            name="Test Identity",
            fingerprint="sha256:abc123",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )
        assert identity.id is not None
        assert len(identity.id) == 36  # UUID format

    def test_create_sets_fields(self) -> None:
        """Test that create() sets all provided fields."""
        cert_path = Path("/tmp/cert.pem")
        key_path = Path("/tmp/key.pem")
        expires = datetime(2026, 1, 15, 10, 30, 0)

        identity = Identity.create(
            name="My Identity",
            fingerprint="sha256:fedcba",
            cert_path=cert_path,
            key_path=key_path,
            expires_at=expires,
        )

        assert identity.name == "My Identity"
        assert identity.fingerprint == "sha256:fedcba"
        assert identity.cert_path == cert_path
        assert identity.key_path == key_path
        assert identity.expires_at == expires
        assert identity.url_prefixes == []

    def test_add_url_prefix(self) -> None:
        """Test adding a URL prefix."""
        identity = Identity.create(
            name="Test",
            fingerprint="sha256:abc",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )

        identity.add_url_prefix("gemini://example.com/")
        assert "gemini://example.com/" in identity.url_prefixes

    def test_add_url_prefix_no_duplicates(self) -> None:
        """Test that duplicate prefixes are not added."""
        identity = Identity.create(
            name="Test",
            fingerprint="sha256:abc",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )

        identity.add_url_prefix("gemini://example.com/")
        identity.add_url_prefix("gemini://example.com/")
        assert len(identity.url_prefixes) == 1

    def test_remove_url_prefix(self) -> None:
        """Test removing a URL prefix."""
        identity = Identity.create(
            name="Test",
            fingerprint="sha256:abc",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )
        identity.add_url_prefix("gemini://example.com/")

        result = identity.remove_url_prefix("gemini://example.com/")
        assert result is True
        assert "gemini://example.com/" not in identity.url_prefixes

    def test_remove_url_prefix_not_found(self) -> None:
        """Test removing a prefix that doesn't exist."""
        identity = Identity.create(
            name="Test",
            fingerprint="sha256:abc",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )

        result = identity.remove_url_prefix("gemini://notfound.com/")
        assert result is False

    def test_matches_url_exact_prefix(self) -> None:
        """Test URL matching with exact prefix."""
        identity = Identity.create(
            name="Test",
            fingerprint="sha256:abc",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )
        identity.add_url_prefix("gemini://example.com/app/")

        assert identity.matches_url("gemini://example.com/app/") is True
        assert identity.matches_url("gemini://example.com/app/page") is True
        assert identity.matches_url("gemini://example.com/other/") is False

    def test_matches_url_multiple_prefixes(self) -> None:
        """Test URL matching with multiple prefixes."""
        identity = Identity.create(
            name="Test",
            fingerprint="sha256:abc",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
        )
        identity.add_url_prefix("gemini://site1.com/")
        identity.add_url_prefix("gemini://site2.com/")

        assert identity.matches_url("gemini://site1.com/page") is True
        assert identity.matches_url("gemini://site2.com/page") is True
        assert identity.matches_url("gemini://site3.com/page") is False

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        identity = Identity(
            id="test-uuid",
            name="My Identity",
            fingerprint="sha256:abc123",
            cert_path=Path("/home/user/.config/astronomo/certificates/test.pem"),
            key_path=Path("/home/user/.config/astronomo/certificates/test.key"),
            url_prefixes=["gemini://example.com/"],
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            expires_at=datetime(2026, 1, 15, 10, 30, 0),
        )

        data = identity.to_dict()

        assert data["id"] == "test-uuid"
        assert data["name"] == "My Identity"
        assert data["fingerprint"] == "sha256:abc123"
        assert "/certificates/test.pem" in data["cert_path"]
        assert "/certificates/test.key" in data["key_path"]
        assert data["url_prefixes"] == ["gemini://example.com/"]
        assert data["created_at"] == "2025-01-15T10:30:00"
        assert data["expires_at"] == "2026-01-15T10:30:00"

    def test_to_dict_without_expires_at(self) -> None:
        """Test that expires_at is omitted when None."""
        identity = Identity(
            id="test-uuid",
            name="My Identity",
            fingerprint="sha256:abc123",
            cert_path=Path("/tmp/cert.pem"),
            key_path=Path("/tmp/key.pem"),
            url_prefixes=[],
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            expires_at=None,
        )

        data = identity.to_dict()
        assert "expires_at" not in data

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "test-uuid",
            "name": "My Identity",
            "fingerprint": "sha256:abc123",
            "cert_path": "/home/user/cert.pem",
            "key_path": "/home/user/key.pem",
            "url_prefixes": ["gemini://example.com/"],
            "created_at": "2025-01-15T10:30:00",
            "expires_at": "2026-01-15T10:30:00",
        }

        identity = Identity.from_dict(data)

        assert identity.id == "test-uuid"
        assert identity.name == "My Identity"
        assert identity.fingerprint == "sha256:abc123"
        assert identity.cert_path == Path("/home/user/cert.pem")
        assert identity.key_path == Path("/home/user/key.pem")
        assert identity.url_prefixes == ["gemini://example.com/"]
        assert identity.created_at == datetime(2025, 1, 15, 10, 30, 0)
        assert identity.expires_at == datetime(2026, 1, 15, 10, 30, 0)

    def test_from_dict_without_optional_fields(self) -> None:
        """Test deserialization with missing optional fields."""
        data = {
            "id": "test-uuid",
            "name": "My Identity",
            "fingerprint": "sha256:abc123",
            "cert_path": "/tmp/cert.pem",
            "key_path": "/tmp/key.pem",
            "created_at": "2025-01-15T10:30:00",
        }

        identity = Identity.from_dict(data)

        assert identity.url_prefixes == []
        assert identity.expires_at is None


class TestIdentityManager:
    """Tests for the IdentityManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> IdentityManager:
        """Create an IdentityManager with temporary storage."""
        return IdentityManager(config_dir=temp_config_dir)

    def test_creates_directories(self, temp_config_dir: Path) -> None:
        """Test that directories are created on first use."""
        manager = IdentityManager(config_dir=temp_config_dir)
        manager._ensure_dirs()

        assert (temp_config_dir / "certificates").exists()

    def test_empty_on_first_run(self, manager: IdentityManager) -> None:
        """Test that manager starts with no identities."""
        assert manager.get_all_identities() == []

    def test_create_identity(self, manager: IdentityManager) -> None:
        """Test creating a new identity with certificate."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )

        assert identity.name == "Test Identity"
        assert identity.fingerprint.startswith("sha256:")
        assert identity.cert_path.exists()
        assert identity.key_path.exists()
        assert identity in manager.get_all_identities()

    def test_create_identity_with_custom_validity(
        self, manager: IdentityManager
    ) -> None:
        """Test creating identity with custom validity period."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
            valid_days=730,  # 2 years
        )

        # Certificate should have an expiration date
        assert identity.expires_at is not None

    def test_key_file_permissions(self, manager: IdentityManager) -> None:
        """Test that private key has restrictive permissions."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )

        # Check that key file has 0600 permissions
        mode = identity.key_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_remove_identity(self, manager: IdentityManager) -> None:
        """Test removing an identity."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        cert_path = identity.cert_path
        key_path = identity.key_path

        result = manager.remove_identity(identity.id)

        assert result is True
        assert manager.get_identity(identity.id) is None
        assert not cert_path.exists()
        assert not key_path.exists()

    def test_remove_identity_not_found(self, manager: IdentityManager) -> None:
        """Test removing a non-existent identity."""
        result = manager.remove_identity("nonexistent-id")
        assert result is False

    def test_rename_identity(self, manager: IdentityManager) -> None:
        """Test renaming an identity."""
        identity = manager.create_identity(
            name="Original Name",
            hostname="example.com",
        )

        result = manager.rename_identity(identity.id, "New Name")

        assert result is True
        assert manager.get_identity(identity.id).name == "New Name"

    def test_rename_identity_not_found(self, manager: IdentityManager) -> None:
        """Test renaming a non-existent identity."""
        result = manager.rename_identity("nonexistent-id", "New Name")
        assert result is False

    def test_get_identity(self, manager: IdentityManager) -> None:
        """Test getting an identity by ID."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )

        found = manager.get_identity(identity.id)
        assert found is not None
        assert found.id == identity.id
        assert found.name == identity.name

    def test_get_identity_not_found(self, manager: IdentityManager) -> None:
        """Test getting a non-existent identity."""
        found = manager.get_identity("nonexistent-id")
        assert found is None

    def test_add_url_prefix(self, manager: IdentityManager) -> None:
        """Test adding a URL prefix to an identity."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )

        result = manager.add_url_prefix(identity.id, "gemini://example.com/")

        assert result is True
        assert "gemini://example.com/" in identity.url_prefixes

    def test_add_url_prefix_not_found(self, manager: IdentityManager) -> None:
        """Test adding a prefix to a non-existent identity."""
        result = manager.add_url_prefix("nonexistent-id", "gemini://example.com/")
        assert result is False

    def test_remove_url_prefix(self, manager: IdentityManager) -> None:
        """Test removing a URL prefix from an identity."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        manager.add_url_prefix(identity.id, "gemini://example.com/")

        result = manager.remove_url_prefix(identity.id, "gemini://example.com/")

        assert result is True
        assert "gemini://example.com/" not in identity.url_prefixes

    def test_get_identity_for_url_exact_match(self, manager: IdentityManager) -> None:
        """Test finding identity for URL with exact prefix."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        manager.add_url_prefix(identity.id, "gemini://example.com/app/")

        found = manager.get_identity_for_url("gemini://example.com/app/page")

        assert found is not None
        assert found.id == identity.id

    def test_get_identity_for_url_no_match(self, manager: IdentityManager) -> None:
        """Test that non-matching URL returns None."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        manager.add_url_prefix(identity.id, "gemini://example.com/app/")

        found = manager.get_identity_for_url("gemini://other.com/page")

        assert found is None

    def test_get_identity_for_url_longest_prefix(
        self, manager: IdentityManager
    ) -> None:
        """Test that longest matching prefix wins."""
        identity1 = manager.create_identity(
            name="Site-wide",
            hostname="example.com",
        )
        identity2 = manager.create_identity(
            name="App-specific",
            hostname="example.com",
        )

        manager.add_url_prefix(identity1.id, "gemini://example.com/")
        manager.add_url_prefix(identity2.id, "gemini://example.com/app/")

        # Specific path should match app-specific identity
        found = manager.get_identity_for_url("gemini://example.com/app/page")
        assert found.id == identity2.id

        # Root path should match site-wide identity
        found = manager.get_identity_for_url("gemini://example.com/other/page")
        assert found.id == identity1.id

    def test_is_identity_valid(self, manager: IdentityManager) -> None:
        """Test checking if an identity is valid."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
            valid_days=365,
        )

        assert manager.is_identity_valid(identity.id) is True

    def test_is_identity_valid_not_found(self, manager: IdentityManager) -> None:
        """Test that non-existent identity is not valid."""
        assert manager.is_identity_valid("nonexistent-id") is False

    def test_is_identity_valid_missing_cert(self, manager: IdentityManager) -> None:
        """Test that identity with missing cert file is not valid."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        # Delete the cert file
        identity.cert_path.unlink()

        assert manager.is_identity_valid(identity.id) is False

    def test_persistence(self, temp_config_dir: Path) -> None:
        """Test that identities persist across manager instances."""
        # Create identity with first manager
        manager1 = IdentityManager(config_dir=temp_config_dir)
        identity = manager1.create_identity(
            name="Persistent Identity",
            hostname="example.com",
        )
        manager1.add_url_prefix(identity.id, "gemini://example.com/")

        # Load with second manager
        manager2 = IdentityManager(config_dir=temp_config_dir)

        assert len(manager2.get_all_identities()) == 1
        loaded = manager2.get_identity(identity.id)
        assert loaded is not None
        assert loaded.name == "Persistent Identity"
        assert "gemini://example.com/" in loaded.url_prefixes

    def test_handles_corrupted_file(self, temp_config_dir: Path) -> None:
        """Test graceful handling of corrupted identities file."""
        identities_file = temp_config_dir / "identities.toml"
        identities_file.write_text("this is not { valid toml")

        manager = IdentityManager(config_dir=temp_config_dir)

        # Should fall back to empty list
        assert manager.get_all_identities() == []

    def test_regenerate_certificate(self, manager: IdentityManager) -> None:
        """Test regenerating a certificate for an existing identity."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        old_fingerprint = identity.fingerprint

        result = manager.regenerate_certificate(identity.id, "example.com")

        assert result is True
        # Fingerprint should change with new key
        assert identity.fingerprint != old_fingerprint
        assert identity.cert_path.exists()
        assert identity.key_path.exists()

    def test_regenerate_certificate_not_found(self, manager: IdentityManager) -> None:
        """Test regenerating certificate for non-existent identity."""
        result = manager.regenerate_certificate("nonexistent-id", "example.com")
        assert result is False
