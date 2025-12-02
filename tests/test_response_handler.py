"""Tests for the response_handler module."""

from unittest.mock import MagicMock

from astronomo.parser import LineType
from astronomo.response_handler import format_response


def create_mock_response(
    status=20,
    body="# Test\n\nContent",
    meta="text/gemini",
    redirect_url=None,
):
    """Helper to create mock GeminiResponse objects."""
    response = MagicMock()
    response.status = status
    response.body = body
    response.meta = meta
    response.redirect_url = redirect_url
    response.is_success.return_value = 20 <= status < 30
    response.is_redirect.return_value = 30 <= status < 40
    return response


class TestFormatSuccessResponse:
    """Tests for successful response formatting (status 20-29)."""

    def test_parses_gemtext_content(self):
        """Test that successful responses parse Gemtext correctly."""
        response = create_mock_response(
            status=20,
            body="# Hello World\n\nThis is a paragraph.\n\n=> /link A link",
        )

        result = format_response("gemini://example.com/", response)

        assert len(result) == 5  # heading, blank, text, blank, link
        assert result[0].line_type == LineType.HEADING_1
        assert result[0].content == "Hello World"
        assert result[4].line_type == LineType.LINK

    def test_handles_empty_body(self):
        """Test that empty responses show appropriate message."""
        response = create_mock_response(status=20, body="")

        result = format_response("gemini://example.com/", response)

        assert len(result) == 1
        assert "(empty response)" in result[0].content

    def test_handles_whitespace_only_body(self):
        """Test that whitespace-only responses are treated as empty."""
        response = create_mock_response(status=20, body="   \n\n   ")

        result = format_response("gemini://example.com/", response)

        assert "(empty response)" in result[0].content

    def test_handles_none_body(self):
        """Test that None body is handled gracefully."""
        response = create_mock_response(status=20, body=None)

        result = format_response("gemini://example.com/", response)

        assert "(empty response)" in result[0].content


class TestFormatRedirectResponse:
    """Tests for redirect response formatting (status 30-39)."""

    def test_shows_redirect_info(self):
        """Test that redirect responses show status and target URL."""
        response = create_mock_response(
            status=31,
            redirect_url="gemini://example.com/new-page",
        )

        result = format_response("gemini://example.com/", response)

        # Should show heading, status, redirect URL
        content = "\n".join(line.content for line in result)
        assert "Redirect" in content
        assert "31" in content
        assert "gemini://example.com/new-page" in content

    def test_handles_missing_redirect_url(self):
        """Test fallback when redirect_url is None."""
        response = create_mock_response(status=31, redirect_url=None)

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "(no redirect URL)" in content


class TestFormatInputResponse:
    """Tests for input request formatting (status 10-11)."""

    def test_shows_input_prompt(self):
        """Test that input requests show the server prompt."""
        response = create_mock_response(status=10, meta="Enter your search query")

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "Input Required" in content
        assert "Enter your search query" in content

    def test_sensitive_input_indicated(self):
        """Test that status 11 indicates sensitive input."""
        response = create_mock_response(status=11, meta="Enter password")

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "sensitive" in content.lower()


class TestFormatErrorResponse:
    """Tests for error response formatting (status 40-59)."""

    def test_shows_error_status_and_message(self):
        """Test that error responses show status code and message."""
        response = create_mock_response(status=51, meta="Not found")

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "Error" in content
        assert "51" in content
        assert "Not found" in content

    def test_handles_missing_meta(self):
        """Test fallback when meta is None."""
        response = create_mock_response(status=40, meta=None)

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "Unknown error" in content


class TestFormatCertificateResponses:
    """Tests for certificate-related response formatting (status 60-62)."""

    def test_certificate_required_status_60(self):
        """Test certificate required message."""
        response = create_mock_response(status=60, meta="Please provide certificate")

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "Certificate Required" in content
        assert "Please provide certificate" in content

    def test_certificate_not_authorized_status_61(self):
        """Test certificate not authorized message."""
        response = create_mock_response(status=61, meta="Access denied")

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "Not Authorized" in content
        assert "Access denied" in content

    def test_certificate_not_valid_status_62(self):
        """Test certificate not valid message."""
        response = create_mock_response(status=62, meta="Certificate expired")

        result = format_response("gemini://example.com/", response)

        content = "\n".join(line.content for line in result)
        assert "Not Valid" in content
        assert "Certificate expired" in content
