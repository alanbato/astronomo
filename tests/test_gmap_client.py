"""Tests for the GMAP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from astronomo.gmap_client import (
    GmapAuthError,
    GmapClient,
    GmapRequestError,
    GmapTempFailure,
    _parse_id_list,
)


class TestParseIdList:
    def test_empty(self):
        assert _parse_id_list("") == []

    def test_single(self):
        assert _parse_id_list("20260211T120000Z") == ["20260211T120000Z"]

    def test_multiple(self):
        result = _parse_id_list("id1, id2, id3")
        assert result == ["id1", "id2", "id3"]

    def test_whitespace(self):
        result = _parse_id_list("  id1 ,  id2  ")
        assert result == ["id1", "id2"]

    def test_trailing_comma(self):
        result = _parse_id_list("id1, id2,")
        assert result == ["id1", "id2"]


def _mock_response(status=20, meta="", body=""):
    """Create a mock Gemini response."""
    response = MagicMock()
    response.status = status
    response.meta = meta
    response.body = body
    return response


@pytest.fixture
def client():
    return GmapClient(
        hostname="mail.example.com",
        port=1960,
        cert_path="/tmp/cert.pem",
        key_path="/tmp/key.pem",
    )


class TestGmapClient:
    def test_build_url(self, client):
        url = client._build_url("/tag/Inbox")
        assert url == "gemini://mail.example.com:1960/tag/Inbox"

    def test_build_url_with_query(self, client):
        url = client._build_url("/tag/Inbox", query="msg123")
        assert url == "gemini://mail.example.com:1960/tag/Inbox?msg123"

    @pytest.mark.asyncio
    async def test_list_all(self, client):
        mock_resp = _mock_response(body="id1, id2, id3")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.list_all()
            assert result == ["id1", "id2", "id3"]

    @pytest.mark.asyncio
    async def test_list_by_tag(self, client):
        mock_resp = _mock_response(body="id1, id2")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.list_by_tag("Inbox")
            assert result == ["id1", "id2"]

    @pytest.mark.asyncio
    async def test_list_by_tag_not_found(self, client):
        mock_resp = _mock_response(status=51, meta="Not found")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.list_by_tag("EmptyTag")
            assert result == []

    @pytest.mark.asyncio
    async def test_get_message(self, client):
        raw = "alice@host.com\nbob@host.com\n2026-02-11T12:00:00Z\n# Subject\n\nBody\n"
        mock_resp = _mock_response(body=raw)

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            msg, raw_bytes = await client.get_message("msg1")
            assert msg.senders[0].mailbox == "alice"
            assert msg.subject == "Subject"

    @pytest.mark.asyncio
    async def test_add_tag(self, client):
        mock_resp = _mock_response(body="Tag added")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.add_tag("msg1", "Archive")
            assert result is True

    @pytest.mark.asyncio
    async def test_remove_tag(self, client):
        mock_resp = _mock_response(body="Tag removed")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.remove_tag("msg1", "Unread")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_message(self, client):
        mock_resp = _mock_response(body="Message deleted")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.delete_message("msg1")
            assert result is True

    @pytest.mark.asyncio
    async def test_auth_error(self, client):
        mock_resp = _mock_response(status=60, meta="Certificate required")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(GmapAuthError):
                await client.list_all()

    @pytest.mark.asyncio
    async def test_temp_failure(self, client):
        mock_resp = _mock_response(status=40, meta="Encrypted")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(GmapTempFailure):
                await client.list_all()

    @pytest.mark.asyncio
    async def test_bad_request(self, client):
        mock_resp = _mock_response(status=59, meta="Invalid tag")

        with patch("astronomo.gmap_client.GeminiClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(GmapRequestError):
                await client.add_tag("msg1", "invalid tag!")
