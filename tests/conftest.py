"""Shared pytest fixtures for Astronomo tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

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
