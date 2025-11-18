"""Unit tests for the Gemtext parser."""

from astronomo.parser import (
    GemtextHeading,
    GemtextLine,
    GemtextLink,
    GemtextParser,
    LineType,
    parse_gemtext,
)


class TestGemtextParser:
    """Test suite for the GemtextParser class."""

    def test_parse_empty_string(self):
        """Test parsing an empty string."""
        parser = GemtextParser()
        result = parser.parse("")
        assert len(result) == 1
        assert result[0].line_type == LineType.TEXT
        assert result[0].content == ""

    def test_parse_simple_text(self):
        """Test parsing simple text lines."""
        content = "This is a simple text line."
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.TEXT
        assert result[0].content == "This is a simple text line."

    def test_parse_multiple_text_lines(self):
        """Test parsing multiple text lines."""
        content = "Line 1\nLine 2\nLine 3"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 3
        assert all(line.line_type == LineType.TEXT for line in result)
        assert result[0].content == "Line 1"
        assert result[1].content == "Line 2"
        assert result[2].content == "Line 3"

    def test_parse_blank_lines(self):
        """Test that blank lines are preserved."""
        content = "Line 1\n\nLine 3"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 3
        assert result[0].content == "Line 1"
        assert result[1].content == ""
        assert result[2].content == "Line 3"

    def test_parse_link_with_label(self):
        """Test parsing a link with a label."""
        content = "=> https://example.com Example Website"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextLink)
        assert result[0].line_type == LineType.LINK
        assert result[0].url == "https://example.com"
        assert result[0].label == "Example Website"
        assert result[0].content == "Example Website"

    def test_parse_link_without_label(self):
        """Test parsing a link without a label."""
        content = "=> https://example.com"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextLink)
        assert result[0].url == "https://example.com"
        assert result[0].label is None
        assert result[0].content == "https://example.com"

    def test_parse_link_with_extra_whitespace(self):
        """Test parsing a link with extra whitespace."""
        content = "=>    https://example.com    Example Site"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextLink)
        assert result[0].url == "https://example.com"
        assert result[0].label == "Example Site"

    def test_parse_empty_link(self):
        """Test parsing an empty link line."""
        content = "=>"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextLink)
        assert result[0].url == ""
        assert result[0].label is None

    def test_parse_heading_level_1(self):
        """Test parsing a level 1 heading."""
        content = "# Heading 1"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextHeading)
        assert result[0].line_type == LineType.HEADING_1
        assert result[0].level == 1
        assert result[0].content == "Heading 1"

    def test_parse_heading_level_2(self):
        """Test parsing a level 2 heading."""
        content = "## Heading 2"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextHeading)
        assert result[0].line_type == LineType.HEADING_2
        assert result[0].level == 2
        assert result[0].content == "Heading 2"

    def test_parse_heading_level_3(self):
        """Test parsing a level 3 heading."""
        content = "### Heading 3"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert isinstance(result[0], GemtextHeading)
        assert result[0].line_type == LineType.HEADING_3
        assert result[0].level == 3
        assert result[0].content == "Heading 3"

    def test_parse_heading_without_space(self):
        """Test that headings without space are treated as text."""
        content = "#NoSpace"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.TEXT
        assert result[0].content == "#NoSpace"

    def test_parse_heading_too_many_hashes(self):
        """Test that more than 3 # symbols are treated as text."""
        content = "#### Too many hashes"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.TEXT
        assert result[0].content == "#### Too many hashes"

    def test_parse_list_item(self):
        """Test parsing a list item."""
        content = "* List item"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.LIST_ITEM
        assert result[0].content == "List item"

    def test_parse_multiple_list_items(self):
        """Test parsing multiple list items."""
        content = "* Item 1\n* Item 2\n* Item 3"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 3
        assert all(line.line_type == LineType.LIST_ITEM for line in result)
        assert result[0].content == "Item 1"
        assert result[1].content == "Item 2"
        assert result[2].content == "Item 3"

    def test_parse_list_without_space(self):
        """Test that * without space is treated as text."""
        content = "*NoSpace"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.TEXT
        assert result[0].content == "*NoSpace"

    def test_parse_blockquote(self):
        """Test parsing a blockquote."""
        content = "> This is a quote"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.BLOCKQUOTE
        assert result[0].content == " This is a quote"

    def test_parse_blockquote_no_space(self):
        """Test parsing a blockquote without space after >."""
        content = ">Quote"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.BLOCKQUOTE
        assert result[0].content == "Quote"

    def test_parse_preformatted_block(self):
        """Test parsing a preformatted text block."""
        content = "```\nLine 1\nLine 2\nLine 3\n```"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.PREFORMATTED
        assert result[0].content == "Line 1\nLine 2\nLine 3"

    def test_parse_preformatted_block_with_alt_text(self):
        """Test parsing a preformatted block with alt text."""
        content = "```python\nprint('Hello')\n```"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.PREFORMATTED
        assert result[0].content == "print('Hello')"

    def test_parse_preformatted_preserves_markup(self):
        """Test that preformatted blocks preserve markup characters."""
        content = "```\n# Not a heading\n=> Not a link\n* Not a list\n```"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.PREFORMATTED
        assert "# Not a heading" in result[0].content
        assert "=> Not a link" in result[0].content
        assert "* Not a list" in result[0].content

    def test_parse_unclosed_preformatted_block(self):
        """Test that unclosed preformatted blocks are handled."""
        content = "```\nLine 1\nLine 2"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.PREFORMATTED
        assert result[0].content == "Line 1\nLine 2"

    def test_parse_empty_preformatted_block(self):
        """Test parsing an empty preformatted block."""
        content = "```\n```"
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 1
        assert result[0].line_type == LineType.PREFORMATTED
        assert result[0].content == ""

    def test_parse_mixed_content(self):
        """Test parsing a document with mixed content types."""
        content = """# Welcome

This is a paragraph.

=> https://example.com Example Link

* Item 1
* Item 2

> A quote

```
Preformatted text
```

Another paragraph."""
        parser = GemtextParser()
        result = parser.parse(content)

        assert len(result) == 14
        assert result[0].line_type == LineType.HEADING_1
        assert result[1].line_type == LineType.TEXT  # blank line
        assert result[2].line_type == LineType.TEXT  # paragraph
        assert result[3].line_type == LineType.TEXT  # blank line
        assert result[4].line_type == LineType.LINK
        assert result[5].line_type == LineType.TEXT  # blank line
        assert result[6].line_type == LineType.LIST_ITEM
        assert result[7].line_type == LineType.LIST_ITEM
        assert result[8].line_type == LineType.TEXT  # blank line
        assert result[9].line_type == LineType.BLOCKQUOTE
        assert result[10].line_type == LineType.TEXT  # blank line
        assert result[11].line_type == LineType.PREFORMATTED
        assert result[12].line_type == LineType.TEXT  # blank line
        assert result[13].line_type == LineType.TEXT  # final paragraph

    def test_parse_gemtext_convenience_function(self):
        """Test the convenience function parse_gemtext."""
        content = "# Heading\nText line"
        result = parse_gemtext(content)

        assert len(result) == 2
        assert result[0].line_type == LineType.HEADING_1
        assert result[1].line_type == LineType.TEXT

    def test_parser_reuse(self):
        """Test that parser can be reused for multiple documents."""
        parser = GemtextParser()

        # First parse
        result1 = parser.parse("# Heading 1")
        assert len(result1) == 1
        assert result1[0].line_type == LineType.HEADING_1

        # Second parse
        result2 = parser.parse("=> https://example.com")
        assert len(result2) == 1
        assert result2[0].line_type == LineType.LINK

        # Results should be independent
        assert len(result1) == 1
        assert len(result2) == 1


class TestGemtextLineObjects:
    """Test suite for Gemtext line object classes."""

    def test_gemtext_link_with_label(self):
        """Test GemtextLink object with label."""
        link = GemtextLink(
            raw="=> https://example.com Example",
            url="https://example.com",
            label="Example",
        )

        assert link.line_type == LineType.LINK
        assert link.url == "https://example.com"
        assert link.label == "Example"
        assert link.content == "Example"
        assert link.raw == "=> https://example.com Example"

    def test_gemtext_link_without_label(self):
        """Test GemtextLink object without label."""
        link = GemtextLink(raw="=> https://example.com", url="https://example.com")

        assert link.label is None
        assert link.content == "https://example.com"

    def test_gemtext_heading(self):
        """Test GemtextHeading object."""
        heading = GemtextHeading(raw="# Heading", level=1, content="Heading")

        assert heading.line_type == LineType.HEADING_1
        assert heading.level == 1
        assert heading.content == "Heading"
        assert heading.raw == "# Heading"

    def test_gemtext_line(self):
        """Test basic GemtextLine object."""
        line = GemtextLine(
            line_type=LineType.TEXT, content="Some text", raw="Some text"
        )

        assert line.line_type == LineType.TEXT
        assert line.content == "Some text"
        assert line.raw == "Some text"
