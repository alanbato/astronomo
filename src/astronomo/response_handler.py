"""Handler for Gemini protocol responses."""

from nauyaca.protocol.response import GeminiResponse

from astronomo.parser import GemtextLine, parse_gemtext


def format_response(url: str, response: GeminiResponse) -> list[GemtextLine]:
    """
    Format a Gemini response for display.

    Args:
        url: The URL that was requested
        response: The Gemini response object

    Returns:
        List of parsed Gemtext lines ready for display
    """
    if response.is_success():
        return _format_success_response(url, response)
    elif response.is_redirect():
        return _format_redirect_response(response)
    elif 10 <= response.status < 20:
        return _format_input_response(response)
    else:
        return _format_error_response(response)


def _format_success_response(url: str, response: GeminiResponse) -> list[GemtextLine]:
    """Format a successful response by parsing the Gemtext body."""
    body = response.body or ""

    # If empty body, return a simple message
    if not body.strip():
        return parse_gemtext("(empty response)")

    # Parse the Gemtext content
    return parse_gemtext(body)


def _format_redirect_response(response: GeminiResponse) -> list[GemtextLine]:
    """Format a redirect response."""
    redirect_url = response.redirect_url or "(no redirect URL)"
    gemtext = (
        f"# Redirect\n\n"
        f"Status: {response.status}\n"
        f"Redirect to: {redirect_url}\n\n"
        f"Following redirects automatically..."
    )
    return parse_gemtext(gemtext)


def _format_input_response(response: GeminiResponse) -> list[GemtextLine]:
    """Format an input request response (fallback display).

    This is shown if input handling fails to trigger the modal.
    """
    prompt = response.meta or "Input required"
    status_type = "sensitive " if response.status == 11 else ""
    gemtext = (
        f"# Input Required\n\n"
        f"The server is requesting {status_type}input.\n\n"
        f"Prompt: {prompt}"
    )
    return parse_gemtext(gemtext)


def _format_error_response(response: GeminiResponse) -> list[GemtextLine]:
    """Format an error response."""
    error_msg = response.meta or "Unknown error"
    gemtext = f"# Error\n\nStatus: {response.status}\nMessage: {error_msg}"
    return parse_gemtext(gemtext)
