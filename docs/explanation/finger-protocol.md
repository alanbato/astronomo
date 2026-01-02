# Finger Protocol

This page explains the Finger protocol that Astronomo supports alongside Gemini.

## What is Finger?

Finger is a user information protocol from 1977, standardized in 1991. It was designed to provide information about users on a system—whether they're logged in, their full name, office location, and custom "plan" files.

### Historical Context

In the early days of networked computing, Finger was a common way to:

- Check if someone was online before sending email
- Read their `.plan` file (a text file users could customize)
- Find contact information for users at remote systems

While largely replaced by modern systems, Finger survives in hobbyist and retro-computing communities.

## How It Works

### URLs

Finger URLs can use two formats:

```
finger://user@host
finger://host/user
```

- **host** - Server hostname
- **user** - Username to query (optional)

Examples:
```
finger://user@example.com
finger://example.com/user
finger://example.com
```

If no user is specified, the server may return a list of all logged-in users.

### Request/Response

1. Client opens TCP connection to server (port 79)
2. Client sends username + CRLF (or just CRLF for server info)
3. Server sends user information
4. Connection closes

Like Gopher, Finger connections are unencrypted.

## Finger in Astronomo

### Smart URL Detection

Astronomo recognizes Finger URLs automatically:

- `user@example.com` → treated as `finger://user@example.com`
- Just type a user@host address in the URL bar

### Display

Finger responses appear as preformatted text with a header:

```
# Finger: user@example.com

[Response content displayed here]
```

The response preserves the original formatting from the server.

### Navigation

From the address bar:
1. Type `user@host` or `finger://user@host`
2. Press ++enter++
3. View the user's information

## Common Finger Content

### Plan Files

Many Finger servers display the contents of a user's `~/.plan` file. Users customize these to share:

- Current projects or status
- Contact information
- ASCII art
- Random thoughts or quotes

### Project Files

Some systems also serve `~/.project` files, typically containing a one-line project description.

## Finger vs Gemini

| Aspect | Finger | Gemini |
|--------|--------|--------|
| Year | 1977 | 2019 |
| Purpose | User info lookup | Document browsing |
| Encryption | None | TLS required |
| Port | 79 | 1965 |
| Content | Plain text | Gemtext |
| Interactivity | Query only | Links, input prompts |

Finger is a simple query protocol, while Gemini is a full document browsing protocol. They complement each other—you might Finger someone to check their status, then visit their Gemini capsule for more content.

## Places to Explore

- `finger://happynetbox.com` - Community Finger server
- `finger://plan.cat` - Plan file hosting service

!!! note
    Many traditional Finger servers have been decommissioned. The protocol is now mainly used by hobbyists and retro-computing enthusiasts.

## Further Reading

- [RFC 1288](https://datatracker.ietf.org/doc/html/rfc1288) - The Finger User Information Protocol
- [Finger on Wikipedia](https://en.wikipedia.org/wiki/Finger_(protocol)) - History and overview
