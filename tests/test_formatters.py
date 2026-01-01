"""Tests for protocol response formatters."""

from unittest.mock import MagicMock

import pytest

from astronomo.formatters.gopher import (
    GopherFetchResult,
    build_gopher_url,
    format_gopher_menu,
    parse_gopher_url,
)
from astronomo.parser import GemtextLink, LineType


class TestParseGopherUrl:
    """Tests for parse_gopher_url function."""

    def test_basic_directory_url(self) -> None:
        """Test parsing a basic directory URL."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://gopher.example.com/1/path/to/menu"
        )
        assert host == "gopher.example.com"
        assert port == 70
        assert item_type == "1"
        assert selector == "/path/to/menu"

    def test_text_file_url(self) -> None:
        """Test parsing a text file URL."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://gopher.example.com/0/documents/readme.txt"
        )
        assert host == "gopher.example.com"
        assert port == 70
        assert item_type == "0"
        assert selector == "/documents/readme.txt"

    def test_url_with_custom_port(self) -> None:
        """Test parsing URL with custom port."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://gopher.example.com:7070/1/menu"
        )
        assert host == "gopher.example.com"
        assert port == 7070
        assert item_type == "1"
        assert selector == "/menu"

    def test_search_url(self) -> None:
        """Test parsing a search URL (type 7)."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://search.example.com/7/search"
        )
        assert host == "search.example.com"
        assert port == 70
        assert item_type == "7"
        assert selector == "/search"

    def test_binary_url(self) -> None:
        """Test parsing a binary file URL (type 9)."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://files.example.com/9/archive.zip"
        )
        assert host == "files.example.com"
        assert port == 70
        assert item_type == "9"
        assert selector == "/archive.zip"

    def test_image_url(self) -> None:
        """Test parsing an image URL (type I)."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://images.example.com/I/photo.jpg"
        )
        assert host == "images.example.com"
        assert port == 70
        assert item_type == "I"
        assert selector == "/photo.jpg"

    def test_url_without_type(self) -> None:
        """Test parsing URL without item type defaults to directory."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://gopher.example.com/"
        )
        assert host == "gopher.example.com"
        assert port == 70
        assert item_type == "1"  # Default to directory
        assert selector == ""

    def test_empty_selector(self) -> None:
        """Test parsing URL with empty selector."""
        host, port, item_type, selector = parse_gopher_url(
            "gopher://gopher.example.com/1"
        )
        assert host == "gopher.example.com"
        assert port == 70
        assert item_type == "1"
        assert selector == ""


class TestBuildGopherUrl:
    """Tests for build_gopher_url function."""

    def test_build_directory_url(self) -> None:
        """Test building a directory URL."""
        item = MagicMock()
        item.hostname = "gopher.example.com"
        item.port = 70
        item.item_type.value = "1"
        item.selector = "/menu"

        url = build_gopher_url(item)
        assert url == "gopher://gopher.example.com/1/menu"

    def test_build_url_with_custom_port(self) -> None:
        """Test building URL with non-standard port."""
        item = MagicMock()
        item.hostname = "gopher.example.com"
        item.port = 7070
        item.item_type.value = "1"
        item.selector = "/menu"

        url = build_gopher_url(item)
        assert url == "gopher://gopher.example.com:7070/1/menu"

    def test_build_text_file_url(self) -> None:
        """Test building a text file URL."""
        item = MagicMock()
        item.hostname = "gopher.example.com"
        item.port = 70
        item.item_type.value = "0"
        item.selector = "/file.txt"

        url = build_gopher_url(item)
        assert url == "gopher://gopher.example.com/0/file.txt"


class TestFormatGopherMenu:
    """Tests for format_gopher_menu function."""

    def _make_item(
        self,
        item_type_value: str,
        display_text: str,
        selector: str = "/path",
        hostname: str = "gopher.example.com",
        port: int = 70,
        *,
        is_informational: bool = False,
        is_directory: bool = False,
        is_text: bool = False,
        is_search: bool = False,
        is_binary: bool = False,
        is_external: bool = False,
    ) -> MagicMock:
        """Create a mock GopherItem."""
        item = MagicMock()
        item.display_text = display_text
        item.selector = selector
        item.hostname = hostname
        item.port = port
        item.item_type.value = item_type_value
        item.item_type.is_informational = is_informational
        item.item_type.is_directory = is_directory
        item.item_type.is_text = is_text
        item.item_type.is_search = is_search
        item.item_type.is_binary = is_binary
        item.item_type.is_external = is_external
        return item

    def test_informational_item_becomes_text(self) -> None:
        """Test that informational items become plain text."""
        item = self._make_item("i", "Welcome to Gopher!", is_informational=True)
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert lines[0].line_type == LineType.TEXT
        assert lines[0].content == "Welcome to Gopher!"

    def test_directory_item_becomes_link(self) -> None:
        """Test that directory items become links with [DIR] prefix."""
        item = self._make_item("1", "About Us", selector="/about", is_directory=True)
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert isinstance(lines[0], GemtextLink)
        assert "[DIR]" in lines[0].label
        assert "About Us" in lines[0].label
        assert lines[0].url == "gopher://gopher.example.com/1/about"

    def test_text_item_becomes_link(self) -> None:
        """Test that text file items become links with [TXT] prefix."""
        item = self._make_item("0", "README", selector="/readme.txt", is_text=True)
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert isinstance(lines[0], GemtextLink)
        assert "[TXT]" in lines[0].label
        assert "README" in lines[0].label
        assert lines[0].url == "gopher://gopher.example.com/0/readme.txt"

    def test_search_item_becomes_link(self) -> None:
        """Test that search items become links with [SEARCH] prefix."""
        item = self._make_item(
            "7", "Search Archives", selector="/search", is_search=True
        )
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert isinstance(lines[0], GemtextLink)
        assert "[SEARCH]" in lines[0].label
        assert "Search Archives" in lines[0].label

    def test_binary_item_becomes_link(self) -> None:
        """Test that binary items become links with [BIN] prefix."""
        item = self._make_item(
            "9", "archive.zip", selector="/archive.zip", is_binary=True
        )
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert isinstance(lines[0], GemtextLink)
        assert "[BIN]" in lines[0].label
        assert "archive.zip" in lines[0].label

    def test_image_item_becomes_link_with_img_prefix(self) -> None:
        """Test that image items become links with [IMG] prefix."""
        item = self._make_item("I", "photo.jpg", selector="/photo.jpg", is_binary=True)
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert isinstance(lines[0], GemtextLink)
        assert "[IMG]" in lines[0].label

    def test_gif_item_becomes_link_with_img_prefix(self) -> None:
        """Test that GIF items become links with [IMG] prefix."""
        item = self._make_item(
            "g", "animation.gif", selector="/animation.gif", is_binary=True
        )
        lines = format_gopher_menu([item])

        assert len(lines) == 1
        assert isinstance(lines[0], GemtextLink)
        assert "[IMG]" in lines[0].label

    def test_mixed_menu_items(self) -> None:
        """Test formatting a menu with mixed item types."""
        items = [
            self._make_item("i", "Welcome!", is_informational=True),
            self._make_item("1", "Directory", selector="/dir", is_directory=True),
            self._make_item("0", "File", selector="/file.txt", is_text=True),
        ]
        lines = format_gopher_menu(items)

        assert len(lines) == 3
        assert lines[0].line_type == LineType.TEXT
        assert isinstance(lines[1], GemtextLink)
        assert isinstance(lines[2], GemtextLink)


class TestGopherFetchResult:
    """Tests for GopherFetchResult dataclass."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        result = GopherFetchResult()
        assert result.content == []
        assert result.requires_search is False
        assert result.search_prompt is None
        assert result.is_binary is False
        assert result.binary_data is None
        assert result.filename is None

    def test_search_result(self) -> None:
        """Test creating a search-required result."""
        result = GopherFetchResult(
            requires_search=True,
            search_prompt="Enter search term",
        )
        assert result.requires_search is True
        assert result.search_prompt == "Enter search term"

    def test_binary_result(self) -> None:
        """Test creating a binary download result."""
        data = b"binary content"
        result = GopherFetchResult(
            is_binary=True,
            binary_data=data,
            filename="test.bin",
        )
        assert result.is_binary is True
        assert result.binary_data == data
        assert result.filename == "test.bin"


class TestNormalizeUrl:
    """Tests for URL normalization in Astronomo app."""

    @pytest.fixture
    def app(self):
        """Create a minimal app instance for testing."""
        from astronomo.astronomo_app import Astronomo

        return Astronomo()

    def test_gemini_url_preserved(self, app) -> None:
        """Test that gemini:// URLs are preserved."""
        assert app._normalize_url("gemini://example.com/") == "gemini://example.com/"

    def test_gopher_url_preserved(self, app) -> None:
        """Test that gopher:// URLs are preserved."""
        assert app._normalize_url("gopher://example.com/") == "gopher://example.com/"

    def test_finger_url_preserved(self, app) -> None:
        """Test that finger:// URLs are preserved."""
        assert app._normalize_url("finger://user@host") == "finger://user@host"

    def test_user_at_host_becomes_finger(self, app) -> None:
        """Test that user@host pattern becomes finger://."""
        assert app._normalize_url("user@example.com") == "finger://user@example.com"

    def test_gopher_domain_detected(self, app) -> None:
        """Test that gopher.* domains become gopher://."""
        assert app._normalize_url("gopher.example.com") == "gopher://gopher.example.com"

    def test_port_70_detected_as_gopher(self, app) -> None:
        """Test that :70 port is detected as gopher."""
        assert app._normalize_url("example.com:70") == "gopher://example.com:70"

    def test_default_to_gemini(self, app) -> None:
        """Test that plain hostnames default to gemini://."""
        assert app._normalize_url("example.com") == "gemini://example.com"
        assert app._normalize_url("example.com/path") == "gemini://example.com/path"

    def test_http_url_preserved(self, app) -> None:
        """Test that http:// URLs are preserved (even though unsupported)."""
        assert app._normalize_url("http://example.com/") == "http://example.com/"
