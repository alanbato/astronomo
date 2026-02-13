"""Tests for the mail cache."""

from datetime import UTC, datetime

import pytest

from astronomo.mail_cache import MailCache


def _make_gemmail(
    sender: str = "alice@host.com Alice",
    recipient: str = "bob@host.com Bob",
    timestamp: str = "2026-02-11T12:00:00Z",
    subject: str = "Test Subject",
    body: str = "Hello!",
) -> bytes:
    """Build a raw gemmail message."""
    return f"{sender}\n{recipient}\n{timestamp}\n# {subject}\n\n{body}\n".encode()


@pytest.fixture
def cache(tmp_path):
    """Create a MailCache with a temp directory."""
    return MailCache(cache_dir=tmp_path)


@pytest.fixture
def account_id():
    return "test-account-id"


class TestMailCache:
    def test_store_and_retrieve(self, cache, account_id):
        raw = _make_gemmail()
        cache.store_message(account_id, "msg1", raw, ["Inbox", "Unread"])

        msg = cache.get_message(account_id, "msg1")
        assert msg is not None
        assert msg.msgid == "msg1"
        assert msg.raw_bytes == raw
        assert "alice@host.com" in msg.sender
        assert msg.subject == "Test Subject"
        assert set(msg.tags) == {"Inbox", "Unread"}

    def test_get_nonexistent(self, cache, account_id):
        assert cache.get_message(account_id, "nonexistent") is None

    def test_list_by_tag(self, cache, account_id):
        cache.store_message(
            account_id,
            "msg1",
            _make_gemmail(timestamp="2026-02-11T12:00:00Z"),
            ["Inbox", "Unread"],
        )
        cache.store_message(
            account_id,
            "msg2",
            _make_gemmail(timestamp="2026-02-11T13:00:00Z"),
            ["Inbox"],
        )
        cache.store_message(
            account_id,
            "msg3",
            _make_gemmail(timestamp="2026-02-11T14:00:00Z"),
            ["Archive"],
        )

        inbox = cache.list_by_tag(account_id, "Inbox")
        assert len(inbox) == 2

        archive = cache.list_by_tag(account_id, "Archive")
        assert len(archive) == 1
        assert archive[0].msgid == "msg3"

    def test_list_by_tag_sorted_newest_first(self, cache, account_id):
        cache.store_message(
            account_id,
            "old",
            _make_gemmail(timestamp="2026-02-10T12:00:00Z"),
            ["Inbox"],
        )
        cache.store_message(
            account_id,
            "new",
            _make_gemmail(timestamp="2026-02-12T12:00:00Z"),
            ["Inbox"],
        )

        messages = cache.list_by_tag(account_id, "Inbox")
        assert messages[0].msgid == "new"
        assert messages[1].msgid == "old"

    def test_update_tags_add(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox"])
        cache.update_tags(account_id, "msg1", add=["Archive"])

        msg = cache.get_message(account_id, "msg1")
        assert "Archive" in msg.tags
        assert "Inbox" in msg.tags  # Not removed

    def test_update_tags_remove(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox", "Unread"])
        cache.update_tags(account_id, "msg1", remove=["Unread"])

        msg = cache.get_message(account_id, "msg1")
        assert "Unread" not in msg.tags
        assert "Inbox" in msg.tags

    def test_update_tags_add_and_remove(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox"])
        cache.update_tags(account_id, "msg1", add=["Archive"], remove=["Inbox"])

        msg = cache.get_message(account_id, "msg1")
        assert "Archive" in msg.tags
        assert "Inbox" not in msg.tags

    def test_remove_message(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox"])
        cache.remove_message(account_id, "msg1")

        assert cache.get_message(account_id, "msg1") is None
        assert len(cache.list_by_tag(account_id, "Inbox")) == 0

    def test_last_sync(self, cache, account_id):
        assert cache.get_last_sync(account_id) is None

        ts = datetime(2026, 2, 11, 12, 0, 0, tzinfo=UTC)
        cache.set_last_sync(account_id, ts)

        retrieved = cache.get_last_sync(account_id)
        assert retrieved is not None
        assert retrieved.year == 2026

    def test_get_all_tags(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox", "Unread"])
        cache.store_message(account_id, "msg2", _make_gemmail(), ["Inbox"])
        cache.store_message(account_id, "msg3", _make_gemmail(), ["Archive"])

        tags = cache.get_all_tags(account_id)
        assert "Inbox" in tags
        assert "Unread" in tags
        assert "Archive" in tags

    def test_get_tag_counts(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox", "Unread"])
        cache.store_message(account_id, "msg2", _make_gemmail(), ["Inbox"])
        cache.store_message(account_id, "msg3", _make_gemmail(), ["Archive"])

        counts = cache.get_tag_counts(account_id)
        assert counts["Inbox"] == 2
        assert counts["Unread"] == 1
        assert counts["Archive"] == 1

    def test_get_unread_count(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox", "Unread"])
        cache.store_message(account_id, "msg2", _make_gemmail(), ["Inbox"])
        cache.store_message(account_id, "msg3", _make_gemmail(), ["Inbox", "Unread"])

        assert cache.get_unread_count(account_id, "Inbox") == 2

    def test_has_message(self, cache, account_id):
        assert not cache.has_message(account_id, "msg1")

        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox"])
        assert cache.has_message(account_id, "msg1")

    def test_store_replaces_existing(self, cache, account_id):
        cache.store_message(account_id, "msg1", _make_gemmail(), ["Inbox"])
        cache.store_message(
            account_id,
            "msg1",
            _make_gemmail(subject="Updated"),
            ["Archive"],
        )

        msg = cache.get_message(account_id, "msg1")
        assert msg.subject == "Updated"
        assert "Archive" in msg.tags
        assert "Inbox" not in msg.tags

    def test_parse_cached_message(self, cache, account_id):
        raw = _make_gemmail(
            sender="alice@host.com Alice",
            body="Hello world!",
        )
        cache.store_message(account_id, "msg1", raw, ["Inbox"])

        msg = cache.get_message(account_id, "msg1")
        parsed = msg.parse()
        assert len(parsed.senders) == 1
        assert parsed.senders[0].mailbox == "alice"
        assert "Hello world!" in parsed.body

    def test_multiple_accounts(self, cache):
        cache.store_message("acc1", "msg1", _make_gemmail(), ["Inbox"])
        cache.store_message("acc2", "msg1", _make_gemmail(), ["Archive"])

        acc1_msg = cache.get_message("acc1", "msg1")
        acc2_msg = cache.get_message("acc2", "msg1")

        assert "Inbox" in acc1_msg.tags
        assert "Archive" in acc2_msg.tags

    def test_close_and_reopen(self, tmp_path, account_id):
        cache1 = MailCache(cache_dir=tmp_path)
        cache1.store_message(account_id, "msg1", _make_gemmail(), ["Inbox"])
        cache1.close()

        cache2 = MailCache(cache_dir=tmp_path)
        msg = cache2.get_message(account_id, "msg1")
        assert msg is not None
        assert msg.msgid == "msg1"
        cache2.close()
