"""Tests for color picker widget and utilities."""

from astronomo.widgets.color_picker import PRESET_COLORS, is_valid_hex_color


class TestIsValidHexColor:
    """Tests for the is_valid_hex_color function."""

    def test_valid_hex_lowercase(self):
        """Test valid hex color with lowercase letters."""
        assert is_valid_hex_color("#4a4a5a") is True

    def test_valid_hex_uppercase(self):
        """Test valid hex color with uppercase letters."""
        assert is_valid_hex_color("#4A4A5A") is True

    def test_valid_hex_mixed_case(self):
        """Test valid hex color with mixed case letters."""
        assert is_valid_hex_color("#4a4A5a") is True

    def test_valid_hex_all_numbers(self):
        """Test valid hex color with all numbers."""
        assert is_valid_hex_color("#123456") is True

    def test_invalid_no_hash(self):
        """Test that hex without hash prefix is invalid."""
        assert is_valid_hex_color("4a4a5a") is False

    def test_invalid_short(self):
        """Test that 3-digit hex is invalid."""
        assert is_valid_hex_color("#4a5") is False

    def test_invalid_too_long(self):
        """Test that 8-digit hex is invalid."""
        assert is_valid_hex_color("#4a4a5a00") is False

    def test_invalid_chars(self):
        """Test that non-hex characters are invalid."""
        assert is_valid_hex_color("#gggggg") is False

    def test_invalid_empty(self):
        """Test that empty string is invalid."""
        assert is_valid_hex_color("") is False

    def test_invalid_only_hash(self):
        """Test that just hash is invalid."""
        assert is_valid_hex_color("#") is False

    def test_invalid_spaces(self):
        """Test that spaces are invalid."""
        assert is_valid_hex_color("#4a4 a5a") is False


class TestPresetColors:
    """Tests for the preset color palette."""

    def test_all_presets_are_valid(self):
        """Test that all preset colors are valid hex colors."""
        for hex_color, _name in PRESET_COLORS:
            assert is_valid_hex_color(hex_color), f"{hex_color} is not valid"

    def test_preset_count(self):
        """Test that we have 12 preset colors."""
        assert len(PRESET_COLORS) == 12

    def test_presets_are_tuples(self):
        """Test that presets are (hex, name) tuples."""
        for preset in PRESET_COLORS:
            assert isinstance(preset, tuple)
            assert len(preset) == 2
            hex_color, name = preset
            assert isinstance(hex_color, str)
            assert isinstance(name, str)
            assert hex_color.startswith("#")
            assert len(name) > 0

    def test_preset_colors_are_unique(self):
        """Test that all preset colors are unique."""
        colors = [hex_color for hex_color, _name in PRESET_COLORS]
        assert len(colors) == len(set(colors))
