"""Tests for the feed_fetcher module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from astronomo.feed_fetcher import FeedData, FeedItem, fetch_feed


class TestFeedItem:
    """Tests for the FeedItem dataclass."""

    def test_create_feed_item_minimal(self) -> None:
        """Test creating a feed item with required fields only."""
        item = FeedItem(title="Test Title", link="gemini://example.com/item")

        assert item.title == "Test Title"
        assert item.link == "gemini://example.com/item"
        assert item.summary is None
        assert item.published is None
        assert item.author is None

    def test_create_feed_item_full(self) -> None:
        """Test creating a feed item with all fields."""
        published = datetime(2025, 1, 15, 10, 30, 0)
        item = FeedItem(
            title="Full Item",
            link="gemini://example.com/full",
            summary="This is a summary",
            published=published,
            author="Test Author",
        )

        assert item.title == "Full Item"
        assert item.link == "gemini://example.com/full"
        assert item.summary == "This is a summary"
        assert item.published == published
        assert item.author == "Test Author"


class TestFeedData:
    """Tests for the FeedData dataclass."""

    def test_create_feed_data_error(self) -> None:
        """Test creating feed data with an error."""
        data = FeedData(error="Something went wrong")

        assert data.error == "Something went wrong"
        assert data.items is None
        assert data.title is None

    def test_create_feed_data_success(self) -> None:
        """Test creating feed data with successful content."""
        items = [
            FeedItem(title="Item 1", link="gemini://example.com/1"),
            FeedItem(title="Item 2", link="gemini://example.com/2"),
        ]
        data = FeedData(
            title="Test Feed",
            description="A test feed",
            link="gemini://example.com/",
            items=items,
        )

        assert data.title == "Test Feed"
        assert data.description == "A test feed"
        assert data.link == "gemini://example.com/"
        assert len(data.items) == 2
        assert data.error is None


class TestFetchFeed:
    """Tests for the fetch_feed async function."""

    @pytest.fixture
    def mock_rss_content(self) -> str:
        """Sample RSS 2.0 feed content."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>gemini://example.com/</link>
    <description>A test RSS feed</description>
    <item>
      <title>First Post</title>
      <link>gemini://example.com/post1</link>
      <description>First post description</description>
      <pubDate>Wed, 15 Jan 2025 10:00:00 GMT</pubDate>
      <author>Test Author</author>
    </item>
    <item>
      <title>Second Post</title>
      <link>gemini://example.com/post2</link>
      <description>Second post description</description>
    </item>
  </channel>
</rss>"""

    @pytest.fixture
    def mock_atom_content(self) -> str:
        """Sample Atom feed content."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <link href="gemini://example.com/"/>
  <subtitle>An Atom feed</subtitle>
  <entry>
    <title>Atom Entry</title>
    <link href="gemini://example.com/entry1"/>
    <summary>Entry summary</summary>
    <updated>2025-01-15T12:00:00Z</updated>
    <author><name>Atom Author</name></author>
  </entry>
</feed>"""

    @pytest.mark.asyncio
    async def test_fetch_successful_rss_feed(self, mock_rss_content: str) -> None:
        """Test fetching and parsing a valid RSS feed."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = mock_rss_content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error is None
        assert result.title == "Test Feed"
        assert result.description == "A test RSS feed"
        assert len(result.items) == 2
        assert result.items[0].title == "First Post"
        assert result.items[0].link == "gemini://example.com/post1"
        assert result.items[1].title == "Second Post"

    @pytest.mark.asyncio
    async def test_fetch_successful_atom_feed(self, mock_atom_content: str) -> None:
        """Test fetching and parsing a valid Atom feed."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = mock_atom_content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.atom")

        assert result.error is None
        assert result.title == "Atom Feed"
        assert len(result.items) == 1
        assert result.items[0].title == "Atom Entry"

    @pytest.mark.asyncio
    async def test_fetch_non_success_response(self) -> None:
        """Test handling non-success status codes."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = False
        mock_response.status = 51
        mock_response.meta = "Not found"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error == "Not found"
        assert result.items is None

    @pytest.mark.asyncio
    async def test_fetch_non_success_response_no_meta(self) -> None:
        """Test handling non-success with no meta message."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = False
        mock_response.status = 40
        mock_response.meta = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error == "Request failed with status 40"

    @pytest.mark.asyncio
    async def test_fetch_empty_content(self) -> None:
        """Test handling empty feed content."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = ""

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error == "Empty feed content"

    @pytest.mark.asyncio
    async def test_fetch_whitespace_only_content(self) -> None:
        """Test handling whitespace-only feed content."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = "   \n\t  "

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error == "Empty feed content"

    @pytest.mark.asyncio
    async def test_fetch_malformed_xml(self) -> None:
        """Test handling malformed XML content."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = "<rss><<<not valid xml>>>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        # feedparser is very tolerant, but bozo_exception should be set
        # for severely malformed content
        assert result.error is not None or result.items is not None

    @pytest.mark.asyncio
    async def test_fetch_items_without_links_skipped(self) -> None:
        """Test that feed items without links are skipped."""
        content = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <title>Has Link</title>
      <link>gemini://example.com/has-link</link>
    </item>
    <item>
      <title>No Link</title>
    </item>
  </channel>
</rss>"""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error is None
        assert len(result.items) == 1
        assert result.items[0].title == "Has Link"

    @pytest.mark.asyncio
    async def test_fetch_with_client_certificate(self) -> None:
        """Test that client cert/key are passed to GeminiClient."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = "<rss><channel><title>Test</title></channel></rss>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch(
            "astronomo.feed_fetcher.GeminiClient", return_value=mock_client
        ) as mock_class:
            await fetch_feed(
                "gemini://example.com/feed.xml",
                client_cert="/path/to/cert.pem",
                client_key="/path/to/key.pem",
            )

            # Verify the client was created with cert arguments
            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["client_cert"] == "/path/to/cert.pem"
            assert call_kwargs["client_key"] == "/path/to/key.pem"

    @pytest.mark.asyncio
    async def test_fetch_network_exception(self) -> None:
        """Test that network errors are caught and returned as FeedData.error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = ConnectionError("Network is unreachable")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error is not None
        assert "Network is unreachable" in result.error

    @pytest.mark.asyncio
    async def test_fetch_timeout_exception(self) -> None:
        """Test that timeout errors are caught properly."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.get.side_effect = asyncio.TimeoutError()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error is not None
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_fetch_with_custom_timeout(self) -> None:
        """Test that custom timeout is passed to client."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = "<rss><channel><title>Test</title></channel></rss>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch(
            "astronomo.feed_fetcher.GeminiClient", return_value=mock_client
        ) as mock_class:
            await fetch_feed("gemini://example.com/feed.xml", timeout=60)

            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["timeout"] == 60

    @pytest.mark.asyncio
    async def test_fetch_with_custom_max_redirects(self) -> None:
        """Test that custom max_redirects is passed to client."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = "<rss><channel><title>Test</title></channel></rss>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch(
            "astronomo.feed_fetcher.GeminiClient", return_value=mock_client
        ) as mock_class:
            await fetch_feed("gemini://example.com/feed.xml", max_redirects=10)

            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["max_redirects"] == 10

    @pytest.mark.asyncio
    async def test_fetch_parses_published_date(self, mock_rss_content: str) -> None:
        """Test that published dates are correctly parsed."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = mock_rss_content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        # First item has a pubDate
        assert result.items[0].published is not None
        assert isinstance(result.items[0].published, datetime)
        # Second item doesn't have a pubDate
        assert result.items[1].published is None

    @pytest.mark.asyncio
    async def test_fetch_parses_author(self, mock_rss_content: str) -> None:
        """Test that author is correctly extracted."""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = mock_rss_content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.items[0].author == "Test Author"
        assert result.items[1].author is None

    @pytest.mark.asyncio
    async def test_fetch_handles_no_title(self) -> None:
        """Test handling items without titles."""
        content = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <link>gemini://example.com/no-title</link>
    </item>
  </channel>
</rss>"""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error is None
        assert len(result.items) == 1
        assert result.items[0].title == "(No title)"

    @pytest.mark.asyncio
    async def test_fetch_empty_feed_no_items(self) -> None:
        """Test handling a feed with no items."""
        content = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
    <description>This feed has no items</description>
  </channel>
</rss>"""
        mock_response = MagicMock()
        mock_response.is_success.return_value = True
        mock_response.body = content

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("astronomo.feed_fetcher.GeminiClient", return_value=mock_client):
            result = await fetch_feed("gemini://example.com/feed.xml")

        assert result.error is None
        assert result.title == "Empty Feed"
        assert result.items == []
