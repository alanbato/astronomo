"""Tests for emoji translation utilities."""

from astronomo.emoji_utils import translate_emoji


class TestTranslateEmoji:
    """Tests for the translate_emoji function."""

    def test_emoji_converted(self):
        """Single emoji is converted to text description."""
        # Using Unicode escape for grinning face emoji U+1F600
        text = "Hello \U0001f600!"
        result = translate_emoji(text)
        assert "grinning" in result.lower()
        assert "(" in result
        assert ")" in result

    def test_text_without_emoji_unchanged(self):
        """Plain text without emoji returns unchanged."""
        text = "Hello, world! This is plain text."
        result = translate_emoji(text)
        assert result == text

    def test_mixed_content(self):
        """Text with multiple emoji converts all of them."""
        # U+1F440 (eyes) and U+1F4A1 (light bulb)
        text = "Check this out \U0001f440 for tips \U0001f4a1"
        result = translate_emoji(text)
        # Both emoji should be converted
        assert "\U0001f440" not in result
        assert "\U0001f4a1" not in result
        assert "(" in result  # At least one parenthesis pair

    def test_empty_string(self):
        """Empty string returns unchanged."""
        result = translate_emoji("")
        assert result == ""

    def test_unicode_text_preserved(self):
        """Non-emoji Unicode characters are preserved."""
        text = "Caf\u00e9 r\u00e9sum\u00e9 na\u00efve"
        result = translate_emoji(text)
        assert result == text

    def test_delimiter_format(self):
        """Emoji descriptions use parentheses delimiters with spaces."""
        # U+1F600 grinning face
        result = translate_emoji("\U0001f600")
        # Should use (description) format with spaces, not underscores
        # Parentheses are used to avoid Rich markup conflicts with []
        assert "(" in result
        assert ")" in result
        assert "_" not in result  # Underscores replaced with spaces
        assert "grinning face" in result
