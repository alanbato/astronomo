# Parser API

The parser module provides utilities for parsing Gemtext content.

## Overview

Gemtext is the text format used by Gemini. It supports:

- Three levels of headings (`#`, `##`, `###`)
- Links (`=>` prefix)
- Unordered lists (`*` prefix)
- Blockquotes (`>` prefix)
- Preformatted blocks (``` fences)
- Plain text

## API Reference

::: astronomo.parser
    options:
      show_root_heading: true
      show_source: true
      members:
        - LineType
        - GemtextLine
        - parse_gemtext

## Example Usage

```python
from astronomo.parser import parse_gemtext, LineType

gemtext = """# Welcome
=> gemini://example.com/ Example Site
Some plain text.
"""

lines = parse_gemtext(gemtext)
for line in lines:
    if line.line_type == LineType.LINK:
        print(f"Link: {line.url} -> {line.text}")
    elif line.line_type == LineType.HEADING:
        print(f"H{line.level}: {line.text}")
```
