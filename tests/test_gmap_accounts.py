"""Tests for GMAP account management."""

from datetime import datetime

import pytest

from astronomo.gmap_accounts import GmapAccount, GmapAccountManager


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory."""
    return tmp_path / "config"


@pytest.fixture
def manager(config_dir):
    """Create a GmapAccountManager with a temp directory."""
    return GmapAccountManager(config_dir=config_dir)


class TestGmapAccount:
    def test_create(self):
        account = GmapAccount.create(
            name="Test Mail",
            hostname="mail.example.com",
            mailbox="alice",
        )
        assert account.name == "Test Mail"
        assert account.hostname == "mail.example.com"
        assert account.mailbox == "alice"
        assert account.port == 1960
        assert account.gmap_address == "gmap@mail.example.com"
        assert account.id  # UUID should be set

    def test_create_custom_gmap_address(self):
        account = GmapAccount.create(
            name="Test",
            hostname="host.com",
            gmap_address="custom@host.com",
        )
        assert account.gmap_address == "custom@host.com"

    def test_to_dict_from_dict_roundtrip(self):
        account = GmapAccount.create(
            name="Test Mail",
            hostname="mail.example.com",
            port=1961,
            mailbox="bob",
            identity_id="test-id",
            gmap_address="gmap@mail.example.com",
        )
        account.last_sync = datetime(2026, 1, 15, 10, 0, 0)

        data = account.to_dict()
        restored = GmapAccount.from_dict(data)

        assert restored.id == account.id
        assert restored.name == account.name
        assert restored.hostname == account.hostname
        assert restored.port == account.port
        assert restored.mailbox == account.mailbox
        assert restored.identity_id == account.identity_id
        assert restored.gmap_address == account.gmap_address
        assert restored.last_sync == account.last_sync

    def test_from_dict_defaults(self):
        data = {
            "id": "test-id",
            "name": "Test",
            "hostname": "host.com",
            "created_at": datetime.now().isoformat(),
        }
        account = GmapAccount.from_dict(data)
        assert account.port == 1960
        assert account.mailbox == ""
        assert account.last_sync is None


class TestGmapAccountManager:
    def test_add_account(self, manager):
        account = manager.add_account(
            name="Test Mail",
            hostname="mail.example.com",
            mailbox="alice",
        )
        assert account.name == "Test Mail"
        assert len(manager.accounts) == 1

    def test_persistence(self, config_dir):
        # Create and add account
        manager1 = GmapAccountManager(config_dir=config_dir)
        manager1.add_account(
            name="Test Mail",
            hostname="mail.example.com",
            mailbox="alice",
            identity_id="some-id",
        )

        # Create new manager from same dir
        manager2 = GmapAccountManager(config_dir=config_dir)
        assert len(manager2.accounts) == 1
        assert manager2.accounts[0].name == "Test Mail"
        assert manager2.accounts[0].hostname == "mail.example.com"

    def test_remove_account(self, manager):
        account = manager.add_account(
            name="Test",
            hostname="host.com",
        )
        assert manager.remove_account(account.id)
        assert len(manager.accounts) == 0

    def test_remove_nonexistent(self, manager):
        assert not manager.remove_account("nonexistent-id")

    def test_update_account(self, manager):
        account = manager.add_account(
            name="Original",
            hostname="host.com",
        )
        assert manager.update_account(account.id, name="Updated")
        assert manager.get_account(account.id).name == "Updated"

    def test_update_last_sync(self, manager):
        account = manager.add_account(name="Test", hostname="host.com")
        sync_time = datetime(2026, 2, 11, 12, 0, 0)
        manager.update_account(account.id, last_sync=sync_time)

        retrieved = manager.get_account(account.id)
        assert retrieved.last_sync == sync_time

    def test_get_account(self, manager):
        account = manager.add_account(name="Test", hostname="host.com")
        retrieved = manager.get_account(account.id)
        assert retrieved.id == account.id

    def test_get_nonexistent(self, manager):
        assert manager.get_account("nonexistent") is None

    def test_get_all_accounts(self, manager):
        manager.add_account(name="A", hostname="a.com")
        manager.add_account(name="B", hostname="b.com")
        accounts = manager.get_all_accounts()
        assert len(accounts) == 2

    def test_empty_load(self, config_dir):
        manager = GmapAccountManager(config_dir=config_dir)
        assert len(manager.accounts) == 0

    def test_corrupted_file(self, config_dir):
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "gmap_accounts.toml").write_text("invalid toml {{{{")
        manager = GmapAccountManager(config_dir=config_dir)
        assert len(manager.accounts) == 0
