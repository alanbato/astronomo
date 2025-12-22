"""Emoji translation utilities for Astronomo."""

import re

import emoji


def translate_emoji(text: str) -> str:
    """Convert all emoji in text to readable text descriptions.

    Uses parentheses for delimiters to avoid conflicts with Rich markup
    which uses square brackets for styling.

    Args:
        text: The text containing emoji to translate.

    Returns:
        Text with emoji replaced by descriptions.

    Example:
        >>> translate_emoji("Hello 😀!")
        'Hello (grinning face)!'
    """
    result = emoji.demojize(text, delimiters=("(", ")"))
    # Replace underscores with spaces inside parentheses
    return re.sub(r"\(([^)]+)\)", lambda m: f"({m.group(1).replace('_', ' ')})", result)
