"""Syntax highlighting utilities for Astronomo.

This module provides language detection and syntax highlighting for
preformatted code blocks using Textual's highlight module.
"""

from textual.content import Content
from textual.highlight import guess_language, highlight

# Common language aliases to normalize input
LANGUAGE_ALIASES: dict[str, str] = {
    # Python
    "py": "python",
    "python3": "python",
    "py3": "python",
    # JavaScript
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    # TypeScript
    "ts": "typescript",
    # Shell
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    # Ruby
    "rb": "ruby",
    # Markdown
    "md": "markdown",
    # C++
    "c++": "cpp",
    "cxx": "cpp",
    # C#
    "c#": "csharp",
    "cs": "csharp",
    # Common variations
    "yml": "yaml",
    "dockerfile": "docker",
    "rs": "rust",
}


def normalize_language(alt_text: str | None) -> str | None:
    """Extract and normalize language identifier from alt_text.

    Args:
        alt_text: The alt text from a preformatted block
                  (e.g., "python", "code.py", "Python Code")

    Returns:
        Normalized language name suitable for Pygments, or None if not detected
    """
    if not alt_text:
        return None

    # Clean up the alt_text
    lang = alt_text.strip().lower()

    # Handle empty string after strip
    if not lang:
        return None

    # Take only the first word (some pages use "python example code")
    lang = lang.split()[0]

    # Check aliases first
    if lang in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lang]

    # Return the language as-is; Pygments/highlight() will handle unknown languages
    return lang


def highlight_code(code: str, language: str | None = None) -> Content:
    """Apply syntax highlighting to code with auto-detection fallback.

    Args:
        code: The code to highlight
        language: Optional language identifier. If None, attempts auto-detection.

    Returns:
        Content object with syntax highlighting applied
    """
    # If no language specified, attempt auto-detection
    if language is None:
        language = guess_language(code, path=None)

    return highlight(code, language=language)
