"""Feed fetcher for Astronomo.

This module handles fetching and parsing RSS/Atom feeds via the Gemini protocol.
"""

import asyncio
import logging
import ssl
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import feedparser
from nauyaca.client import GeminiClient

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    """Represents a single item from a feed.

    Attributes:
        title: Title of the feed item
        link: URL of the feed item
        summary: Description or summary of the item
        published: Publication date (if available)
        author: Author name (if available)
    """

    title: str
    link: str
    summary: str | None = None
    published: datetime | None = None
    author: str | None = None


@dataclass
class FeedData:
    """Represents parsed feed data.

    Attributes:
        title: Title of the feed
        description: Description of the feed
        link: URL of the feed's website
        items: List of feed items
        error: Error message if parsing failed
    """

    title: str | None = None
    description: str | None = None
    link: str | None = None
    items: list[FeedItem] | None = None
    error: str | None = None


async def fetch_feed(
    url: str,
    timeout: int = 30,
    max_redirects: int = 5,
    client_cert: str | None = None,
    client_key: str | None = None,
) -> FeedData:
    """Fetch and parse a feed from a Gemini URL.

    Args:
        url: The Gemini URL of the feed
        timeout: Request timeout in seconds
        max_redirects: Maximum number of redirects to follow
        client_cert: Path to client certificate (if needed)
        client_key: Path to client key (if needed)

    Returns:
        FeedData containing the parsed feed or error information
    """
    # Build client arguments
    client_kwargs: dict[str, Any] = {
        "timeout": timeout,
        "max_redirects": max_redirects,
    }

    if client_cert and client_key:
        client_kwargs["client_cert"] = client_cert
        client_kwargs["client_key"] = client_key

    try:
        # Fetch the feed via Gemini protocol
        async with GeminiClient(**client_kwargs) as client:
            response = await client.get(url)

        # Check if the response is successful
        if not response.is_success():
            error_msg = response.meta or f"Request failed with status {response.status}"
            return FeedData(error=error_msg)

        # Parse the feed content
        content = response.body or ""
        if not content.strip():
            return FeedData(error="Empty feed content")

        # Use feedparser to parse the feed
        parsed = feedparser.parse(content)

        # Check for parsing errors
        if parsed.bozo and parsed.bozo_exception:
            return FeedData(error=f"Feed parsing error: {parsed.bozo_exception}")

        # Extract feed metadata
        feed_info = parsed.get("feed", {})
        feed_title = feed_info.get("title")
        feed_description = feed_info.get("description") or feed_info.get("subtitle")
        feed_link = feed_info.get("link")

        # Extract feed items
        items = []
        for entry in parsed.get("entries", []):
            # Get title (required)
            title = entry.get("title", "(No title)")

            # Get link (required)
            link = entry.get("link", "")
            if not link:
                # Skip items without links
                continue

            # Get summary/description
            summary = (
                entry.get("summary")
                or entry.get("description")
                or entry.get("content", [{}])[0].get("value")
            )

            # Get published date
            published = None
            if "published_parsed" in entry and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass
            elif "updated_parsed" in entry and entry.updated_parsed:
                try:
                    published = datetime(*entry.updated_parsed[:6])
                except (TypeError, ValueError):
                    pass

            # Get author
            author = entry.get("author") or entry.get("author_detail", {}).get("name")

            items.append(
                FeedItem(
                    title=title,
                    link=link,
                    summary=summary,
                    published=published,
                    author=author,
                )
            )

        return FeedData(
            title=feed_title,
            description=feed_description,
            link=feed_link,
            items=items,
        )

    except asyncio.TimeoutError:
        return FeedData(error=f"Request timed out for {url}")
    except ssl.SSLError as e:
        return FeedData(error=f"SSL/TLS error: {e}")
    except (ConnectionError, OSError) as e:
        return FeedData(error=f"Network error: {e}")
    except Exception as e:
        # Log unexpected errors for debugging
        logger.exception("Unexpected error fetching feed from %s", url)
        return FeedData(error=f"Error fetching feed: {e}")
