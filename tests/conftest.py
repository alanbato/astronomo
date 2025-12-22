"""Shared pytest fixtures for Astronomo tests."""

import tempfile
from pathlib import Path

import pytest
import tomli_w
from unittest.mock import AsyncMock, MagicMock

from astronomo.bookmarks import BookmarkManager
from astronomo.config import ConfigManager
from astronomo.identities import Identity, IdentityManager
from nauyaca.security.certificates import generate_self_signed_cert

# Sample Gemtext content with multiple links for testing link scrolling
MOCK_FAQ_CONTENT = """# Gemini FAQ

Welcome to the Gemini Protocol FAQ page.

=> /docs/specification.gmi Specification
=> /docs/best-practices.gmi Best Practices
=> /docs/clients.gmi Gemini Clients
=> /docs/servers.gmi Gemini Servers
=> /docs/software.gmi Software List
=> /docs/history.gmi Project History
=> /docs/faq.gmi FAQ (this page)
=> /docs/news.gmi News
=> /docs/community.gmi Community
=> / Home

## What is Gemini?

Gemini is a new internet protocol which:

* Is heavier than gopher
* Is lighter than the web
* Will not replace either
* Strives for maximum power to weight ratio
* Takes user privacy very seriously

=> gemini://geminiprotocol.net/ Gemini Protocol Homepage
=> gemini://geminispace.info/ Geminispace aggregator

## Frequently Asked Questions

### Why another protocol?

The web has become too complex and too centralized.

### Is Gemini secure?

Yes, Gemini mandates TLS for all connections.

### Can I use Gemini today?

Absolutely! There are many clients and servers available.

=> /docs/software.gmi See the software list
"""


@pytest.fixture
def mock_gemini_response():
    """Factory fixture to create mock GeminiResponse objects.

    Usage:
        def test_something(mock_gemini_response):
            response = mock_gemini_response(status=20, body="# Hello")
            response = mock_gemini_response(status=31, redirect_url="/other")
    """

    def _create(
        status=20,
        body=MOCK_FAQ_CONTENT,
        meta="text/gemini",
        redirect_url=None,
        mime_type=None,
    ):
        response = MagicMock()
        response.status = status
        response.body = body
        response.meta = meta
        response.mime_type = mime_type or ("text/gemini" if 20 <= status < 30 else None)
        response.is_success.return_value = 20 <= status < 30
        response.is_redirect.return_value = 30 <= status < 40
        response.redirect_url = redirect_url
        return response

    return _create


@pytest.fixture
def mock_gemini_client(monkeypatch, mock_gemini_response):
    """Mock GeminiClient to avoid network requests.

    This fixture patches nauyaca.client.GeminiClient at the astronomo_app
    module level, so all tests using this fixture will get mocked responses
    instead of making real network requests.

    Usage:
        @pytest.mark.asyncio
        async def test_something(mock_gemini_client):
            app = Astronomo(initial_url="gemini://example.com/")
            # App will receive mocked content instead of real network response
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_gemini_response())

    mock_class = MagicMock(return_value=mock_client)
    monkeypatch.setattr("astronomo.astronomo_app.GeminiClient", mock_class)
    return mock_client


@pytest.fixture
def temp_config_path():
    """Create a temporary config file with no home_page set.

    This isolates tests from the user's real config file, ensuring
    that tests relying on no initial URL aren't affected by the
    user's configured home_page.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        # Create minimal config without home_page
        config_path.write_text(
            """\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5
"""
        )
        yield config_path


# --- Manager Fixtures ---


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.toml")


@pytest.fixture
def identity_manager(tmp_path: Path) -> IdentityManager:
    """Create an IdentityManager with temporary storage."""
    return IdentityManager(config_dir=tmp_path)


@pytest.fixture
def bookmark_manager(tmp_path: Path) -> BookmarkManager:
    """Create a BookmarkManager with temporary storage."""
    return BookmarkManager(config_dir=tmp_path)


# --- Config File Fixtures ---


@pytest.fixture
def minimal_config_file(tmp_path: Path) -> Path:
    """Create a minimal config file with default settings.

    Returns the path to config.toml with basic [appearance] and [browsing] sections.
    """
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5
"""
    )
    return config_path


@pytest.fixture
def config_with_identity_prompt(tmp_path: Path) -> Path:
    """Create a config file with identity_prompt set to 'remember_choice'."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """\
[appearance]
theme = "textual-dark"

[browsing]
timeout = 30
max_redirects = 5
identity_prompt = "remember_choice"
"""
    )
    return config_path


# --- Certificate Fixtures ---


@pytest.fixture
def cert_and_key() -> tuple[bytes, bytes]:
    """Generate a self-signed certificate and key pair.

    Returns:
        Tuple of (cert_pem, key_pem) as bytes.
    """
    return generate_self_signed_cert(hostname="test.example.com", valid_days=365)


@pytest.fixture
def temp_lagrange_dir(tmp_path: Path) -> Path:
    """Create an empty Lagrange-style idents directory.

    Tests can add certificate/key files as needed.
    """
    lagrange_dir = tmp_path / "lagrange_idents"
    lagrange_dir.mkdir()
    return lagrange_dir


# --- Identity Fixtures ---


@pytest.fixture
def sample_identity(tmp_path: Path, cert_and_key: tuple[bytes, bytes]) -> Identity:
    """Create a sample Identity with valid certificate files on disk.

    The certificate and key are written to tmp_path/certificates/.
    """
    from datetime import datetime

    cert_pem, key_pem = cert_and_key

    certs_dir = tmp_path / "certificates"
    certs_dir.mkdir(parents=True, exist_ok=True)

    cert_path = certs_dir / "test-identity.pem"
    key_path = certs_dir / "test-identity.key"

    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    return Identity(
        id="test-identity-id",
        name="Test Identity",
        fingerprint="SHA256:test-fingerprint",
        cert_path=cert_path,
        key_path=key_path,
        url_prefixes=["gemini://example.com/"],
        created_at=datetime(2025, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def identity_manager_with_identity(
    identity_manager: IdentityManager, cert_and_key: tuple[bytes, bytes]
) -> IdentityManager:
    """Create an IdentityManager pre-populated with one identity.

    Returns the manager with a test identity already created and saved.
    """
    # Create a real identity using the manager's create method
    identity_manager.create_identity(
        name="Test Identity",
        hostname="example.com",
        valid_days=365,
    )
    return identity_manager


# --- Session Choices Fixture ---


@pytest.fixture
def session_choices_file(tmp_path: Path) -> Path:
    """Create a session_choices.toml file with sample data.

    Contains choices for gemini://example.com/ (test-id) and
    gemini://other.com/ (anonymous).
    """
    session_file = tmp_path / "session_choices.toml"
    with open(session_file, "wb") as f:
        tomli_w.dump(
            {
                "choices": {
                    "gemini://example.com/": "test-id",
                    "gemini://other.com/": "anonymous",
                }
            },
            f,
        )
    return session_file
