"""Handler for Gemini protocol responses."""

from nauyaca.protocol.response import GeminiResponse


def format_response(url: str, response: GeminiResponse) -> str:
    """
    Format a Gemini response for display.

    Args:
        url: The URL that was requested
        response: The Gemini response object

    Returns:
        Formatted string representation of the response
    """
    if response.is_success():
        return _format_success_response(url, response)
    elif response.is_redirect():
        return _format_redirect_response(response)
    elif 10 <= response.status < 20:
        return _format_input_response(response)
    else:
        return _format_error_response(response)


def _format_success_response(url: str, response: GeminiResponse) -> str:
    """Format a successful response."""
    mime_type = response.mime_type or "unknown"
    body = response.body or "(empty response)"
    return f"# {url}\n\n**Content-Type:** {mime_type}\n\n---\n\n{body}"


def _format_redirect_response(response: GeminiResponse) -> str:
    """Format a redirect response."""
    redirect_url = response.redirect_url or "(no redirect URL)"
    return (
        f"# Redirect\n\n**Status:** {response.status}\n"
        f"**Redirect to:** {redirect_url}\n\n"
        f"Following redirects automatically..."
    )


def _format_input_response(response: GeminiResponse) -> str:
    """Format an input request response."""
    prompt = response.meta or "Input required"
    return (
        f"# Input Required\n\n**Prompt:** {prompt}\n\n"
        f"(Interactive input not yet implemented)"
    )


def _format_error_response(response: GeminiResponse) -> str:
    """Format an error response."""
    error_msg = response.meta or "Unknown error"
    return f"# Error\n\n**Status:** {response.status}\n**Message:** {error_msg}"
