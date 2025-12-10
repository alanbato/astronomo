"""Tests for the identities module."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from nauyaca.security.certificates import generate_self_signed_cert

from astronomo.identities import (
    Identity,
    IdentityManager,
    LagrangeImportResult,
    extract_cert_from_pem,
    extract_key_from_pem,
    get_lagrange_idents_path,
    is_combined_pem_file,
    pem_file_contains_certificate,
    pem_file_contains_key,
)


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

    def test_get_all_identities_for_url_single_match(
        self, manager: IdentityManager
    ) -> None:
        """Test getting all identities for URL with single match."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        manager.add_url_prefix(identity.id, "gemini://example.com/")

        matches = manager.get_all_identities_for_url("gemini://example.com/page")

        assert len(matches) == 1
        assert matches[0].id == identity.id

    def test_get_all_identities_for_url_multiple_matches(
        self, manager: IdentityManager
    ) -> None:
        """Test getting all identities for URL with multiple matches."""
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

        # URL under /app/ should match both identities
        matches = manager.get_all_identities_for_url("gemini://example.com/app/page")

        assert len(matches) == 2
        # Longest prefix first
        assert matches[0].id == identity2.id
        assert matches[1].id == identity1.id

    def test_get_all_identities_for_url_no_matches(
        self, manager: IdentityManager
    ) -> None:
        """Test getting all identities for URL with no matches."""
        identity = manager.create_identity(
            name="Test Identity",
            hostname="example.com",
        )
        manager.add_url_prefix(identity.id, "gemini://example.com/")

        matches = manager.get_all_identities_for_url("gemini://other.com/page")

        assert matches == []

    def test_get_all_identities_for_url_sorted_by_prefix_length(
        self, manager: IdentityManager
    ) -> None:
        """Test that results are sorted by prefix length (longest first)."""
        identity1 = manager.create_identity(name="Short", hostname="example.com")
        identity2 = manager.create_identity(name="Medium", hostname="example.com")
        identity3 = manager.create_identity(name="Long", hostname="example.com")

        # Add prefixes in random order
        manager.add_url_prefix(identity2.id, "gemini://example.com/path/")
        manager.add_url_prefix(identity1.id, "gemini://example.com/")
        manager.add_url_prefix(identity3.id, "gemini://example.com/path/to/deep/")

        matches = manager.get_all_identities_for_url(
            "gemini://example.com/path/to/deep/page"
        )

        assert len(matches) == 3
        assert matches[0].name == "Long"
        assert matches[1].name == "Medium"
        assert matches[2].name == "Short"

    def test_get_all_identities_for_url_counts_each_identity_once(
        self, manager: IdentityManager
    ) -> None:
        """Test that each identity is only counted once even with multiple matching prefixes."""
        identity = manager.create_identity(
            name="Multi-prefix",
            hostname="example.com",
        )
        manager.add_url_prefix(identity.id, "gemini://example.com/")
        manager.add_url_prefix(identity.id, "gemini://example.com/app/")

        matches = manager.get_all_identities_for_url("gemini://example.com/app/page")

        # Identity should appear only once
        assert len(matches) == 1
        assert matches[0].id == identity.id


class TestGetLagrangePath:
    """Tests for Lagrange path detection."""

    def test_returns_path_or_none(self) -> None:
        """Test that function returns Path or None."""
        result = get_lagrange_idents_path()
        assert result is None or isinstance(result, Path)


class TestLagrangeImportResult:
    """Tests for LagrangeImportResult dataclass."""

    def test_default_values(self) -> None:
        """Test that dataclass has empty defaults."""
        result = LagrangeImportResult()
        assert result.imported == []
        assert result.skipped_duplicates == []
        assert result.errors == []


class TestDiscoverLagrangeIdentities:
    """Tests for discovering Lagrange identity files."""

    @pytest.fixture
    def temp_lagrange_dir(self):
        """Create a temporary Lagrange-like idents directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> IdentityManager:
        """Create IdentityManager with temp storage."""
        return IdentityManager(config_dir=temp_config_dir)

    def test_empty_directory(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test discovery in empty directory."""
        pairs = manager.discover_lagrange_identities(temp_lagrange_dir)
        assert pairs == []

    def test_discovers_valid_pairs(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test discovering valid .crt/.key pairs."""
        # Create a valid certificate pair
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test.example.com",
            valid_days=365,
        )

        (temp_lagrange_dir / "myident.crt").write_bytes(cert_pem)
        (temp_lagrange_dir / "myident.key").write_bytes(key_pem)

        pairs = manager.discover_lagrange_identities(temp_lagrange_dir)

        assert len(pairs) == 1
        name, cert_path, key_path = pairs[0]
        assert name == "myident"
        assert cert_path.suffix == ".crt"
        assert key_path.suffix == ".key"

    def test_ignores_orphaned_crt(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test that .crt without matching .key is ignored."""
        cert_pem, _ = generate_self_signed_cert(hostname="test", valid_days=365)
        (temp_lagrange_dir / "orphan.crt").write_bytes(cert_pem)

        pairs = manager.discover_lagrange_identities(temp_lagrange_dir)
        assert pairs == []

    def test_discovers_multiple_pairs(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test discovering multiple identity pairs."""
        for name in ["ident1", "ident2", "ident3"]:
            cert_pem, key_pem = generate_self_signed_cert(
                hostname=f"{name}.example.com",
                valid_days=365,
            )
            (temp_lagrange_dir / f"{name}.crt").write_bytes(cert_pem)
            (temp_lagrange_dir / f"{name}.key").write_bytes(key_pem)

        pairs = manager.discover_lagrange_identities(temp_lagrange_dir)

        assert len(pairs) == 3
        names = {name for name, _, _ in pairs}
        assert names == {"ident1", "ident2", "ident3"}


class TestImportFromLagrange:
    """Tests for the full import workflow."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_lagrange_dir(self):
        """Create a temporary Lagrange-like idents directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> IdentityManager:
        """Create IdentityManager with temp storage."""
        return IdentityManager(config_dir=temp_config_dir)

    def test_import_single_identity(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test importing a single identity."""
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test.example.com",
            valid_days=365,
        )
        (temp_lagrange_dir / "testident.crt").write_bytes(cert_pem)
        (temp_lagrange_dir / "testident.key").write_bytes(key_pem)

        result = manager.import_from_lagrange(temp_lagrange_dir)

        assert len(result.imported) == 1
        assert result.imported[0].name == "testident"
        assert result.skipped_duplicates == []
        assert result.errors == []

    def test_skip_duplicate_fingerprint(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test that identities with same fingerprint are skipped."""
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test.example.com",
            valid_days=365,
        )
        (temp_lagrange_dir / "ident1.crt").write_bytes(cert_pem)
        (temp_lagrange_dir / "ident1.key").write_bytes(key_pem)

        # First import
        result1 = manager.import_from_lagrange(temp_lagrange_dir)
        assert len(result1.imported) == 1

        # Second import with same files
        result2 = manager.import_from_lagrange(temp_lagrange_dir)
        assert len(result2.imported) == 0
        assert len(result2.skipped_duplicates) == 1
        # Skipped duplicates now show truncated fingerprint, not name
        assert result2.skipped_duplicates[0].startswith("sha256:")

    def test_import_sets_permissions(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test that imported key files have 0600 permissions."""
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test",
            valid_days=365,
        )
        (temp_lagrange_dir / "secureident.crt").write_bytes(cert_pem)
        (temp_lagrange_dir / "secureident.key").write_bytes(key_pem)

        result = manager.import_from_lagrange(temp_lagrange_dir)

        assert len(result.imported) == 1
        mode = result.imported[0].key_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_directory_not_found(self, manager: IdentityManager) -> None:
        """Test FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError):
            manager.import_from_lagrange(Path("/nonexistent/path"))

    def test_url_prefixes_empty(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test that imported identities have empty URL prefixes."""
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test",
            valid_days=365,
        )
        (temp_lagrange_dir / "ident.crt").write_bytes(cert_pem)
        (temp_lagrange_dir / "ident.key").write_bytes(key_pem)

        result = manager.import_from_lagrange(temp_lagrange_dir)

        assert result.imported[0].url_prefixes == []

    def test_import_multiple_identities(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test importing multiple identities at once."""
        for name in ["alice", "bob", "charlie"]:
            cert_pem, key_pem = generate_self_signed_cert(
                hostname=f"{name}.example.com",
                valid_days=365,
            )
            (temp_lagrange_dir / f"{name}.crt").write_bytes(cert_pem)
            (temp_lagrange_dir / f"{name}.key").write_bytes(key_pem)

        result = manager.import_from_lagrange(temp_lagrange_dir)

        assert len(result.imported) == 3
        names = {i.name for i in result.imported}
        assert names == {"alice", "bob", "charlie"}

    def test_imported_identity_persists(
        self, temp_config_dir: Path, temp_lagrange_dir: Path
    ) -> None:
        """Test that imported identities persist across manager instances."""
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test",
            valid_days=365,
        )
        (temp_lagrange_dir / "persistent.crt").write_bytes(cert_pem)
        (temp_lagrange_dir / "persistent.key").write_bytes(key_pem)

        # Import with first manager
        manager1 = IdentityManager(config_dir=temp_config_dir)
        result = manager1.import_from_lagrange(temp_lagrange_dir)
        imported_id = result.imported[0].id

        # Load with second manager
        manager2 = IdentityManager(config_dir=temp_config_dir)
        loaded = manager2.get_identity(imported_id)

        assert loaded is not None
        assert loaded.name == "persistent"

    def test_has_identity_with_fingerprint(self, manager: IdentityManager) -> None:
        """Test checking for existing fingerprint."""
        identity = manager.create_identity(name="Test", hostname="example.com")

        assert manager.has_identity_with_fingerprint(identity.fingerprint) is True
        assert manager.has_identity_with_fingerprint("nonexistent") is False

    def test_import_with_custom_names(
        self, manager: IdentityManager, temp_lagrange_dir: Path
    ) -> None:
        """Test importing with custom names provided."""
        cert_pem, key_pem = generate_self_signed_cert(
            hostname="test.example.com",
            valid_days=365,
        )
        cert_path = temp_lagrange_dir / "original_name.crt"
        cert_path.write_bytes(cert_pem)
        (temp_lagrange_dir / "original_name.key").write_bytes(key_pem)

        # Import with custom name
        custom_names = {cert_path: "My Custom Identity Name"}
        result = manager.import_from_lagrange(temp_lagrange_dir, names=custom_names)

        assert len(result.imported) == 1
        assert result.imported[0].name == "My Custom Identity Name"


class TestPemHelperFunctions:
    """Tests for PEM file helper functions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cert_and_key(self):
        """Generate a certificate and key pair."""
        return generate_self_signed_cert(hostname="test.example.com", valid_days=365)

    def test_pem_file_contains_certificate_true(
        self, temp_dir: Path, cert_and_key: tuple
    ) -> None:
        """Test detecting certificate in PEM file."""
        cert_pem, _ = cert_and_key
        cert_path = temp_dir / "cert.pem"
        cert_path.write_bytes(cert_pem)

        assert pem_file_contains_certificate(cert_path) is True

    def test_pem_file_contains_certificate_false(self, temp_dir: Path) -> None:
        """Test that key-only file returns False."""
        _, key_pem = generate_self_signed_cert(hostname="test", valid_days=365)
        key_path = temp_dir / "key.pem"
        key_path.write_bytes(key_pem)

        assert pem_file_contains_certificate(key_path) is False

    def test_pem_file_contains_key_true(
        self, temp_dir: Path, cert_and_key: tuple
    ) -> None:
        """Test detecting private key in PEM file."""
        _, key_pem = cert_and_key
        key_path = temp_dir / "key.pem"
        key_path.write_bytes(key_pem)

        assert pem_file_contains_key(key_path) is True

    def test_pem_file_contains_key_false(
        self, temp_dir: Path, cert_and_key: tuple
    ) -> None:
        """Test that cert-only file returns False."""
        cert_pem, _ = cert_and_key
        cert_path = temp_dir / "cert.pem"
        cert_path.write_bytes(cert_pem)

        assert pem_file_contains_key(cert_path) is False

    def test_is_combined_pem_file_true(
        self, temp_dir: Path, cert_and_key: tuple
    ) -> None:
        """Test detecting combined PEM file."""
        cert_pem, key_pem = cert_and_key
        combined_path = temp_dir / "combined.pem"
        combined_path.write_bytes(cert_pem + key_pem)

        assert is_combined_pem_file(combined_path) is True

    def test_is_combined_pem_file_false_cert_only(
        self, temp_dir: Path, cert_and_key: tuple
    ) -> None:
        """Test that cert-only file is not combined."""
        cert_pem, _ = cert_and_key
        cert_path = temp_dir / "cert.pem"
        cert_path.write_bytes(cert_pem)

        assert is_combined_pem_file(cert_path) is False

    def test_is_combined_pem_file_false_key_only(
        self, temp_dir: Path, cert_and_key: tuple
    ) -> None:
        """Test that key-only file is not combined."""
        _, key_pem = cert_and_key
        key_path = temp_dir / "key.pem"
        key_path.write_bytes(key_pem)

        assert is_combined_pem_file(key_path) is False

    def test_extract_cert_from_pem(self, cert_and_key: tuple) -> None:
        """Test extracting certificate from combined PEM."""
        cert_pem, key_pem = cert_and_key
        combined = cert_pem.decode() + key_pem.decode()

        extracted = extract_cert_from_pem(combined)

        assert "-----BEGIN CERTIFICATE-----" in extracted
        assert "-----END CERTIFICATE-----" in extracted
        assert "PRIVATE KEY" not in extracted

    def test_extract_key_from_pem(self, cert_and_key: tuple) -> None:
        """Test extracting key from combined PEM."""
        cert_pem, key_pem = cert_and_key
        combined = cert_pem.decode() + key_pem.decode()

        extracted = extract_key_from_pem(combined)

        assert "PRIVATE KEY-----" in extracted
        assert "-----BEGIN CERTIFICATE-----" not in extracted

    def test_pem_file_nonexistent(self, temp_dir: Path) -> None:
        """Test handling of nonexistent file."""
        nonexistent = temp_dir / "nonexistent.pem"

        assert pem_file_contains_certificate(nonexistent) is False
        assert pem_file_contains_key(nonexistent) is False
        assert is_combined_pem_file(nonexistent) is False


class TestImportCustomFiles:
    """Tests for importing custom certificate files."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_source_dir(self):
        """Create a temporary source directory for cert files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> IdentityManager:
        """Create IdentityManager with temp storage."""
        return IdentityManager(config_dir=temp_config_dir)

    @pytest.fixture
    def cert_and_key(self):
        """Generate a certificate and key pair."""
        return generate_self_signed_cert(hostname="test.example.com", valid_days=365)

    def test_import_separate_files(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test importing from separate cert and key files."""
        cert_pem, key_pem = cert_and_key
        cert_path = temp_source_dir / "my-cert.pem"
        key_path = temp_source_dir / "my-key.key"
        cert_path.write_bytes(cert_pem)
        key_path.write_bytes(key_pem)

        identity = manager.import_identity_from_custom_files(
            name="My Custom Cert",
            cert_path=cert_path,
            key_path=key_path,
        )

        assert identity.name == "My Custom Cert"
        assert identity.cert_path.exists()
        assert identity.key_path.exists()
        assert identity in manager.get_all_identities()

    def test_import_combined_pem(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test importing from combined PEM file."""
        cert_pem, key_pem = cert_and_key
        combined_path = temp_source_dir / "combined.pem"
        combined_path.write_bytes(cert_pem + key_pem)

        identity = manager.import_identity_from_custom_files(
            name="Combined PEM Cert",
            cert_path=combined_path,
            key_path=None,  # Combined mode
        )

        assert identity.name == "Combined PEM Cert"
        assert identity.cert_path.exists()
        assert identity.key_path.exists()
        # Files should be separated
        assert pem_file_contains_certificate(identity.cert_path)
        assert pem_file_contains_key(identity.key_path)

    def test_import_combined_pem_fails_without_key(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test that combined mode fails if file has no key."""
        cert_pem, _ = cert_and_key
        cert_only_path = temp_source_dir / "cert-only.pem"
        cert_only_path.write_bytes(cert_pem)

        with pytest.raises(ValueError, match="does not contain both"):
            manager.import_identity_from_custom_files(
                name="Should Fail",
                cert_path=cert_only_path,
                key_path=None,
            )

    def test_import_cert_file_not_found(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
    ) -> None:
        """Test error when certificate file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Certificate file not found"):
            manager.import_identity_from_custom_files(
                name="Should Fail",
                cert_path=temp_source_dir / "nonexistent.pem",
                key_path=temp_source_dir / "key.key",
            )

    def test_import_key_file_not_found(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test error when key file doesn't exist."""
        cert_pem, _ = cert_and_key
        cert_path = temp_source_dir / "cert.pem"
        cert_path.write_bytes(cert_pem)

        with pytest.raises(FileNotFoundError, match="Key file not found"):
            manager.import_identity_from_custom_files(
                name="Should Fail",
                cert_path=cert_path,
                key_path=temp_source_dir / "nonexistent.key",
            )

    def test_import_duplicate_fingerprint(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test error when certificate already exists."""
        cert_pem, key_pem = cert_and_key
        cert_path = temp_source_dir / "cert.pem"
        key_path = temp_source_dir / "key.key"
        cert_path.write_bytes(cert_pem)
        key_path.write_bytes(key_pem)

        # Import first time
        manager.import_identity_from_custom_files(
            name="First Import",
            cert_path=cert_path,
            key_path=key_path,
        )

        # Try to import again
        with pytest.raises(ValueError, match="already exists"):
            manager.import_identity_from_custom_files(
                name="Second Import",
                cert_path=cert_path,
                key_path=key_path,
            )

    def test_import_sets_key_permissions(
        self,
        manager: IdentityManager,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test that imported key has restrictive permissions."""
        cert_pem, key_pem = cert_and_key
        cert_path = temp_source_dir / "cert.pem"
        key_path = temp_source_dir / "key.key"
        cert_path.write_bytes(cert_pem)
        key_path.write_bytes(key_pem)

        identity = manager.import_identity_from_custom_files(
            name="Secure Import",
            cert_path=cert_path,
            key_path=key_path,
        )

        mode = identity.key_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_import_persists(
        self,
        temp_config_dir: Path,
        temp_source_dir: Path,
        cert_and_key: tuple,
    ) -> None:
        """Test that imported identities persist across manager instances."""
        cert_pem, key_pem = cert_and_key
        cert_path = temp_source_dir / "cert.pem"
        key_path = temp_source_dir / "key.key"
        cert_path.write_bytes(cert_pem)
        key_path.write_bytes(key_pem)

        # Import with first manager
        manager1 = IdentityManager(config_dir=temp_config_dir)
        identity = manager1.import_identity_from_custom_files(
            name="Persistent Cert",
            cert_path=cert_path,
            key_path=key_path,
        )
        identity_id = identity.id

        # Load with second manager
        manager2 = IdentityManager(config_dir=temp_config_dir)
        loaded = manager2.get_identity(identity_id)

        assert loaded is not None
        assert loaded.name == "Persistent Cert"
