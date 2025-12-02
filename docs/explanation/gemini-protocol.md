# Gemini Protocol

This page explains the Gemini protocol that Astronomo speaks.

## What is Gemini?

Gemini is an internet protocol designed as a middle ground between the simplicity of Gopher and the complexity of the modern web. It was created in 2019 by "Solderpunk" (a pseudonym).

### Design Goals

- **Simplicity** - Easy to implement clients and servers
- **Privacy** - No tracking, cookies, or JavaScript
- **Minimalism** - Content over presentation
- **Security** - TLS required for all connections

## How It Works

### URLs

Gemini URLs look like web URLs but with a different scheme:

```
gemini://example.com/page.gmi
```

The default port is 1965.

### Request/Response

1. Client opens TLS connection to server
2. Client sends URL (one line, max 1024 bytes)
3. Server sends response header (status code + meta)
4. Server sends response body (for success responses)
5. Connection closes

Unlike HTTP, there are no request headers, cookies, or persistent connections.

### Status Codes

| Range | Category | Meaning |
|-------|----------|---------|
| 10-19 | Input | Server needs input from user |
| 20-29 | Success | Request successful |
| 30-39 | Redirect | Resource moved |
| 40-49 | Temporary Failure | Try again later |
| 50-59 | Permanent Failure | Don't try again |
| 60-69 | Client Certificate | Certificate required |

## Gemtext

Gemtext is the native content format for Gemini, similar to Markdown but simpler.

### Syntax

```
# Heading 1
## Heading 2
### Heading 3

Plain text paragraph.

=> gemini://example.com/ Link text
=> /relative/path Another link

* List item
* Another item

> Blockquote text

\```
Preformatted text (code, ASCII art, etc.)
\```
```

### Key Differences from Markdown

- Only one link per line
- No inline formatting (bold, italic)
- No images (though links can point to images)
- Preformatted blocks with optional alt text

## Geminispace

"Geminispace" refers to the collective network of Gemini servers, analogous to "the web" for HTTP.

### Content Types

Common content in Geminispace:

- **Gemlogs** - Personal blogs
- **Capsules** - Gemini sites (like "websites")
- **Aggregators** - Collections of gemlog posts
- **Wikis** - Collaborative content

### Discovering Content

- [Gemini Protocol](gemini://geminiprotocol.net/) - Official project site
- [Antenna](gemini://warmedal.se/~antenna/) - Gemlog aggregator
- [CAPCOM](gemini://gemini.circumlunar.space/capcom/) - Another aggregator
- [GUS](gemini://gus.guru/) - Gemini search engine

## Why Gemini?

### Compared to the Web

| Web | Gemini |
|-----|--------|
| Complex rendering | Simple text |
| JavaScript | No scripts |
| Tracking pixels | No tracking |
| Cookies | No cookies |
| Megabytes per page | Kilobytes per page |
| Ads everywhere | No ads |

### Use Cases

- Distraction-free reading
- Low-bandwidth environments
- Privacy-conscious browsing
- Simple publishing
- Learning protocols

## Client Certificates

Gemini uses TLS client certificates for optional authentication:

- No usernames/passwords
- No cookies or sessions
- Identity tied to certificate
- User controls their identity

When a server requests a certificate, you can:

1. Provide an existing certificate
2. Create a new certificate
3. Decline (anonymous access)

## Further Reading

- [Gemini Protocol Specification](gemini://geminiprotocol.net/docs/specification.gmi)
- [Gemini FAQ](gemini://geminiprotocol.net/docs/faq.gmi)
- [Gemini Wikipedia Entry](https://en.wikipedia.org/wiki/Gemini_(protocol))
