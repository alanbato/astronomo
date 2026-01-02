# Gopher Protocol

This page explains the Gopher protocol that Astronomo supports alongside Gemini.

## What is Gopher?

Gopher is an internet protocol from 1991, predating the World Wide Web. It was designed at the University of Minnesota (whose mascot is a golden gopher) to distribute documents and files across a network.

### Design Goals

- **Hierarchical navigation** - Menu-based browsing
- **Simple protocol** - Easy to implement
- **Efficient** - Minimal overhead
- **Text-focused** - Primarily serves text content

## How It Works

### URLs

Gopher URLs follow this format:

```
gopher://host[:port]/Tselector
```

- **host** - Server hostname
- **port** - Optional, defaults to 70
- **T** - Single-character item type (see below)
- **selector** - Resource path

Examples:
```
gopher://gopher.floodgap.com/
gopher://gopher.floodgap.com/1/
gopher://gopher.floodgap.com/0/gopher/welcome
```

### Item Types

Gopher uses single-character codes to identify content types:

| Type | Name | Description |
|------|------|-------------|
| `0` | Text | Plain text file |
| `1` | Directory | Menu of items |
| `7` | Search | Full-text search query |
| `9` | Binary | Generic binary file |
| `g` | GIF | GIF image |
| `I` | Image | Other image formats |
| `i` | Info | Informational text (not a link) |
| `h` | HTML | External HTML link |

### Request/Response

1. Client opens TCP connection to server (port 70)
2. Client sends selector string + CRLF
3. Server sends response data
4. Connection closes

Unlike Gemini, Gopher connections are unencrypted.

## Gopher in Astronomo

### Type Indicators

Astronomo displays visual indicators for each item type:

| Indicator | Meaning |
|-----------|---------|
| `[DIR]` | Directory listing |
| `[TXT]` | Text file |
| `[SEARCH]` | Search input |
| `[BIN]` | Binary download |
| `[IMG]` | Image file |
| `[EXT]` | External link (HTTP/Telnet) |

Info lines (`i` type) display as plain text without indicators.

### Navigation

Gopher menus are converted to Gemtext format for a unified browsing experience:

- Click or press ++enter++ on directory items to navigate
- Text files display in a preformatted block
- Search items prompt for a query term

### Search Support

Gopher type 7 (search) items work interactively:

1. Activate a search link
2. Enter your query in the modal dialog
3. Results appear as a new Gopher menu

### Binary Downloads

When you activate a binary file link (type `9`, `g`, or `I`):

1. The file downloads automatically
2. Saved to `~/Downloads/` with the original filename
3. Duplicate filenames are auto-incremented (e.g., `file(1).txt`)

## Gopher vs Gemini

| Aspect | Gopher | Gemini |
|--------|--------|--------|
| Year | 1991 | 2019 |
| Encryption | None | TLS required |
| Content format | Plain text + menus | Gemtext |
| Port | 70 | 1965 |
| Authentication | None | Client certificates |
| Inline text styles | No | No |

Both protocols share a philosophy of simplicity over complexity, but Gemini adds modern security (TLS) while maintaining the minimalist approach.

## Gopherspace

"Gopherspace" refers to the network of Gopher servers, similar to "Geminispace" for Gemini.

### Places to Explore

- `gopher://gopher.floodgap.com/` - Floodgap, a major Gopher hub
- `gopher://gopher.quux.org/` - Quux Gopher server
- `gopher://sdf.org/` - SDF Public Access UNIX System
- `gopher://gopher.club/` - Gopher community

## Further Reading

- [RFC 1436](https://datatracker.ietf.org/doc/html/rfc1436) - The Gopher Protocol Specification
- [Gopher on Wikipedia](https://en.wikipedia.org/wiki/Gopher_(protocol)) - History and overview
