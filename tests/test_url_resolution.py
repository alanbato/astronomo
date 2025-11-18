"""Tests for URL resolution in Astronomo."""

from urllib.parse import urljoin, uses_netloc, uses_relative

import pytest


@pytest.fixture(autouse=True)
def register_gemini_scheme():
    """Ensure gemini scheme is registered for all tests."""
    if "gemini" not in uses_relative:
        uses_relative.append("gemini")
    if "gemini" not in uses_netloc:
        uses_netloc.append("gemini")


class TestGeminiURLResolution:
    """Test that Gemini URLs are resolved correctly using urljoin."""

    def test_absolute_path_resolution(self):
        """Test that absolute paths (starting with /) are resolved correctly."""
        base = "gemini://example.com/some/page"
        link = "/user/blog_post/"
        expected = "gemini://example.com/user/blog_post/"

        result = urljoin(base, link)
        assert result == expected

    def test_relative_path_resolution(self):
        """Test that relative paths are resolved correctly."""
        base = "gemini://example.com/some/page"
        link = "relative/path"
        expected = "gemini://example.com/some/relative/path"

        result = urljoin(base, link)
        assert result == expected

    def test_parent_directory_resolution(self):
        """Test that parent directory paths (../) are resolved correctly."""
        base = "gemini://example.com/some/page/"
        link = "../up/one"
        expected = "gemini://example.com/some/up/one"

        result = urljoin(base, link)
        assert result == expected

    def test_full_url_unchanged(self):
        """Test that full URLs are not modified."""
        base = "gemini://example.com/some/page"
        link = "gemini://other.com/full/path"
        expected = "gemini://other.com/full/path"

        result = urljoin(base, link)
        assert result == expected

    def test_root_domain_with_absolute_path(self):
        """Test resolving absolute paths against root domain."""
        base = "gemini://example.com"
        link = "/user/post/"
        expected = "gemini://example.com/user/post/"

        result = urljoin(base, link)
        assert result == expected

    def test_root_domain_with_trailing_slash(self):
        """Test resolving absolute paths against root domain with trailing slash."""
        base = "gemini://example.com/"
        link = "/user/post/"
        expected = "gemini://example.com/user/post/"

        result = urljoin(base, link)
        assert result == expected

    def test_relative_to_directory(self):
        """Test relative path when base URL ends with /."""
        base = "gemini://example.com/dir/"
        link = "file.gmi"
        expected = "gemini://example.com/dir/file.gmi"

        result = urljoin(base, link)
        assert result == expected

    def test_relative_to_file(self):
        """Test relative path when base URL is a file (no trailing /)."""
        base = "gemini://example.com/dir/file.gmi"
        link = "other.gmi"
        expected = "gemini://example.com/dir/other.gmi"

        result = urljoin(base, link)
        assert result == expected
