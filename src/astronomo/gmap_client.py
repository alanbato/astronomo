"""GMAP (Gemini-Misfin Access Protocol) client for Astronomo.

Wraps nauyaca's GeminiClient with GMAP-specific endpoints for
mailbox access over Gemini with TLS client certificates.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from nauyaca.client import GeminiClient

if TYPE_CHECKING:
    from titlani.content.gemmail import GemmailMessage

logger = logging.getLogger(__name__)

DEFAULT_GMAP_PORT = 1960


class GmapError(Exception):
    """Base exception for GMAP errors."""


class GmapAuthError(GmapError):
    """Status 60/61: Client certificate required or not authorized."""


class GmapNotFoundError(GmapError):
    """Status 51: Resource not found."""


class GmapRequestError(GmapError):
    """Status 59: Bad request."""


class GmapTempFailure(GmapError):
    """Status 40: Temporary failure (e.g., encrypted message)."""


class GmapClient:
    """Async GMAP client for a single account.

    Each method builds a gemini:// URL targeting the GMAP server,
    creates a GeminiClient with client certificate, and parses the response.

    Args:
        hostname: GMAP server hostname
        port: GMAP server port (default 1960)
        cert_path: Path to client certificate PEM file
        key_path: Path to client private key PEM file
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        hostname: str,
        port: int = DEFAULT_GMAP_PORT,
        cert_path: Path | str = "",
        key_path: Path | str = "",
        timeout: int = 30,
    ) -> None:
        self.hostname = hostname
        self.port = port
        self.cert_path = str(cert_path)
        self.key_path = str(key_path)
        self.timeout = timeout

    def _build_url(self, path: str, query: str = "") -> str:
        """Build a GMAP URL.

        Args:
            path: URL path (e.g., "/tag/Inbox")
            query: Optional query string (e.g., message ID)

        Returns:
            Full gemini:// URL
        """
        url = f"gemini://{self.hostname}:{self.port}{path}"
        if query:
            url += f"?{query}"
        return url

    async def _request(self, path: str, query: str = "") -> tuple[int, str, str]:
        """Make a GMAP request and return (status, meta, body).

        Args:
            path: URL path
            query: Optional query string

        Returns:
            Tuple of (status_code, meta, body)

        Raises:
            GmapAuthError: On status 60/61
            GmapNotFoundError: On status 51
            GmapRequestError: On status 59
            GmapTempFailure: On status 40
            GmapError: On unexpected status codes
        """
        url = self._build_url(path, query)

        async with GeminiClient(
            timeout=self.timeout,
            client_cert=self.cert_path,
            client_key=self.key_path,
        ) as client:
            response = await client.get(url)

        status = response.status
        meta = response.meta or ""
        raw_body = response.body
        # GMAP responses are always text; coerce bytes if needed
        if isinstance(raw_body, bytes):
            body = raw_body.decode("utf-8", errors="replace")
        else:
            body = raw_body or ""

        if status == 20:
            return status, meta, body

        if status == 30:
            # Redirect — return for caller to handle
            return status, meta, body

        if status == 40:
            raise GmapTempFailure(meta)

        if status == 51:
            raise GmapNotFoundError(meta)

        if status == 59:
            raise GmapRequestError(meta)

        if status in (60, 61):
            raise GmapAuthError(meta)

        raise GmapError(f"Unexpected status {status}: {meta}")

    async def list_all(self) -> list[str]:
        """List all message IDs (excluding Trash).

        Returns:
            List of message ID strings
        """
        _status, _meta, body = await self._request("/tag/")
        return _parse_id_list(body)

    async def list_by_tag(self, tag: str, since: datetime | None = None) -> list[str]:
        """List message IDs for a tag, optionally filtered by timestamp.

        Args:
            tag: Tag name (e.g., "Inbox", "Unread")
            since: Only return messages after this timestamp

        Returns:
            List of message ID strings
        """
        path = f"/tag/{tag}"
        if since is not None:
            path += f"/{since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        try:
            _status, _meta, body = await self._request(path)
        except GmapNotFoundError:
            # No messages with this tag
            return []

        return _parse_id_list(body)

    async def get_message(self, msgid: str) -> tuple[GemmailMessage, bytes]:
        """Retrieve and parse a message.

        Args:
            msgid: Message ID

        Returns:
            Tuple of (parsed GemmailMessage, raw bytes)
        """
        from titlani.content.gemmail import GemmailMessage as _GemmailMessage

        _status, _meta, body = await self._request(f"/msgid/{msgid}")
        raw = body.encode("utf-8")
        msg = _GemmailMessage.from_bytes(raw)
        return msg, raw

    async def add_tag(self, msgid: str, tag: str) -> bool:
        """Add a tag to a message.

        Args:
            msgid: Message ID
            tag: Tag name to add

        Returns:
            True on success
        """
        _status, _meta, _body = await self._request(f"/tag/{tag}", query=msgid)
        return True

    async def remove_tag(self, msgid: str, tag: str) -> bool:
        """Remove a tag from a message.

        Args:
            msgid: Message ID
            tag: Tag name to remove

        Returns:
            True on success
        """
        _status, _meta, _body = await self._request(f"/untag/{tag}", query=msgid)
        return True

    async def delete_message(self, msgid: str) -> bool:
        """Permanently delete a message (must be tagged Trash first).

        Args:
            msgid: Message ID

        Returns:
            True on success
        """
        _status, _meta, _body = await self._request("/delete", query=msgid)
        return True


def _parse_id_list(body: str) -> list[str]:
    """Parse a comma-separated list of message IDs from response body."""
    body = body.strip()
    if not body:
        return []
    return [msgid.strip() for msgid in body.split(",") if msgid.strip()]
