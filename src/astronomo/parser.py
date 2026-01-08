"""Gemtext parser for the Astronomo Gemini browser.

This module implements a parser for the Gemtext markup format as specified at:
https://geminiprotocol.net/docs/gemtext.gmi
"""

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Literal

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Backport for Python 3.10
    class StrEnum(str, Enum):
        """String enum backport for Python 3.10."""

        pass


class LineType(StrEnum):
    """Enum representing the different types of Gemtext lines."""

    TEXT = "text"
    LINK = "link"
    INPUT_LINK = "input_link"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    LIST_ITEM = "list_item"
    BLOCKQUOTE = "blockquote"
    PREFORMATTED = "preformatted"


@dataclass
class GemtextLine:
    """Represents a parsed line of Gemtext."""

    line_type: LineType
    content: str
    raw: str


@dataclass
class GemtextLink(GemtextLine):
    """Represents a parsed link line."""

    url: str
    label: str | None
    is_input_link: bool = False

    def __init__(
        self, raw: str, url: str, label: str | None = None, is_input_link: bool = False
    ):
        self.line_type = LineType.INPUT_LINK if is_input_link else LineType.LINK
        self.url = url
        self.label = label
        self.is_input_link = is_input_link
        self.content = label if label else url
        self.raw = raw


@dataclass
class GemtextHeading(GemtextLine):
    """Represents a parsed heading line."""

    level: Literal[1, 2, 3]

    def __init__(self, raw: str, level: Literal[1, 2, 3], content: str):
        self.line_type = LineType(f"heading_{level}")
        self.level = level
        self.content = content
        self.raw = raw


@dataclass
class GemtextPreformatted(GemtextLine):
    """Represents a parsed preformatted text block with optional language hint."""

    alt_text: str | None

    def __init__(self, raw: str, content: str, alt_text: str | None = None):
        self.line_type = LineType.PREFORMATTED
        self.content = content
        self.raw = raw
        self.alt_text = alt_text


@dataclass
class PreformattedBlock:
    """Represents a preformatted text block."""

    lines: list[str]
    alt_text: str | None

    def __init__(self, alt_text: str | None = None):
        self.lines = []
        self.alt_text = alt_text


class GemtextParser:
    """Parser for Gemtext markup format.

    The parser processes Gemtext line by line according to the specification.
    It handles all standard Gemtext elements: text, links, headings, lists,
    blockquotes, and preformatted text blocks.
    """

    def __init__(self):
        self._in_preformatted = False
        self._current_preformatted: PreformattedBlock | None = None
        self._parsed_lines: list[GemtextLine] = []

    def parse(self, content: str) -> list[GemtextLine]:
        """Parse a complete Gemtext document.

        Args:
            content: The Gemtext content as a string.

        Returns:
            A list of GemtextLine objects representing the parsed content.
        """
        self._reset()
        lines = content.split("\n")

        for line in lines:
            self._parse_line(line)

        # If we're still in a preformatted block at the end, close it
        if self._in_preformatted and self._current_preformatted:
            self._close_preformatted_block()

        return self._parsed_lines

    def _reset(self):
        """Reset the parser state."""
        self._in_preformatted = False
        self._current_preformatted = None
        self._parsed_lines = []

    def _parse_line(self, line: str):
        """Parse a single line of Gemtext.

        Args:
            line: A single line from the Gemtext document.
        """
        # Handle preformatted toggle
        if line.startswith("```"):
            self._toggle_preformatted(line)
            return

        # If we're in a preformatted block, add the line as-is
        if self._in_preformatted and self._current_preformatted:
            self._current_preformatted.lines.append(line)
            return

        # Parse normal lines
        parsed = self._parse_normal_line(line)
        if parsed:
            self._parsed_lines.append(parsed)

    def _toggle_preformatted(self, line: str):
        """Toggle preformatted mode and handle alt text.

        Args:
            line: The line containing the preformatted toggle (```).
        """
        if not self._in_preformatted:
            # Starting a preformatted block
            alt_text = line[3:].strip() if len(line) > 3 else None
            self._current_preformatted = PreformattedBlock(alt_text=alt_text)
            self._in_preformatted = True
        else:
            # Closing a preformatted block
            self._close_preformatted_block()
            self._in_preformatted = False

    def _close_preformatted_block(self):
        """Close the current preformatted block and add it to parsed lines."""
        if self._current_preformatted:
            # Join all lines with newlines and create a GemtextPreformatted
            content = "\n".join(self._current_preformatted.lines)
            alt_text = self._current_preformatted.alt_text
            self._parsed_lines.append(
                GemtextPreformatted(
                    raw=f"```{alt_text or ''}\n{content}\n```",
                    content=content,
                    alt_text=alt_text,
                )
            )
            self._current_preformatted = None

    def _parse_normal_line(self, line: str) -> GemtextLine | None:
        """Parse a normal (non-preformatted) line.

        Args:
            line: The line to parse.

        Returns:
            A GemtextLine object, or None for blank lines.
        """
        # Input link lines (Spartan protocol)
        # Check =: before => since both start with =
        if line.startswith("=:"):
            return self._parse_link(line, is_input_link=True)

        # Regular link lines
        if line.startswith("=>"):
            return self._parse_link(line)

        # Heading lines
        if line.startswith("#"):
            return self._parse_heading(line)

        # List item lines
        if line.startswith("* "):
            return GemtextLine(
                line_type=LineType.LIST_ITEM,
                content=line[2:],
                raw=line,
            )

        # Blockquote lines
        if line.startswith(">"):
            return GemtextLine(
                line_type=LineType.BLOCKQUOTE,
                content=line[1:],
                raw=line,
            )

        # Regular text lines (including blank lines)
        return GemtextLine(
            line_type=LineType.TEXT,
            content=line,
            raw=line,
        )

    def _parse_link(self, line: str, is_input_link: bool = False) -> GemtextLink:
        """Parse a link line.

        Args:
            line: A line starting with '=>' or '=:'.
            is_input_link: True if this is a Spartan input link (=:)

        Returns:
            A GemtextLink object.
        """
        # Remove the '=>' or '=:' prefix
        content = line[2:].lstrip()

        if not content:
            # Empty link line
            return GemtextLink(
                raw=line, url="", label=None, is_input_link=is_input_link
            )

        # Split on whitespace to separate URL and label
        parts = content.split(maxsplit=1)
        url = parts[0]
        label = parts[1] if len(parts) > 1 else None

        return GemtextLink(raw=line, url=url, label=label, is_input_link=is_input_link)

    def _parse_heading(self, line: str) -> GemtextHeading | GemtextLine:
        """Parse a heading line.

        Args:
            line: A line starting with '#'.

        Returns:
            A GemtextHeading object if valid, otherwise a regular text line.
        """
        # Determine heading level
        level = 0
        for char in line:
            if char == "#":
                level += 1
            else:
                break

        # Only levels 1-3 are valid
        if level > 3:
            # Too many # symbols, treat as regular text
            return GemtextLine(
                line_type=LineType.TEXT,
                content=line,
                raw=line,
            )

        # Check for mandatory space after the # symbols
        if len(line) <= level or line[level] != " ":
            # No space after #, treat as regular text
            return GemtextLine(
                line_type=LineType.TEXT,
                content=line,
                raw=line,
            )

        content = line[level + 1 :]
        return GemtextHeading(
            raw=line,
            level=level,  # type: ignore
            content=content,
        )


def parse_gemtext(content: str) -> list[GemtextLine]:
    """Convenience function to parse Gemtext content.

    Args:
        content: The Gemtext content as a string.

    Returns:
        A list of GemtextLine objects representing the parsed content.
    """
    parser = GemtextParser()
    return parser.parse(content)
