# Known Hosts (TOFU)

This guide explains how Astronomo manages server certificate trust using TOFU (Trust On First Use).

## Understanding TOFU

Gemini uses TLS encryption for all connections. Unlike the web's certificate authority (CA) system, Gemini typically uses **Trust On First Use (TOFU)**:

- The first time you visit a server, its certificate is automatically trusted
- On subsequent visits, Astronomo verifies the certificate matches what was stored
- If a certificate changes unexpectedly, you're warned of a potential security issue

## Certificate Change Warnings

When a server's certificate changes, Astronomo shows a warning modal with:

- **Old fingerprint** — The previously trusted certificate
- **New fingerprint** — The certificate the server is now presenting
- **Trust timestamps** — When the original certificate was first and last seen

### Response Options

| Option | Action |
|--------|--------|
| **Accept** | Trust the new certificate and continue |
| **Reject** | Refuse the connection (stay safe) |
| **View Details** | See full fingerprint comparison |

!!! warning "Security Consideration"
    A certificate change could indicate:

    - The server legitimately renewed its certificate
    - A man-in-the-middle attack
    - Server compromise

    If unexpected, verify with the server operator before accepting.

## Managing Known Hosts

### Opening Known Hosts Settings

1. Press ++ctrl+comma++ to open Settings
2. Click the **Known Hosts** tab

### Features

The Known Hosts tab displays all trusted server certificates with:

- **Search filtering** — Type in the search box to filter hosts by hostname
- **Pagination** — Navigate through pages of 10 hosts using Prev/Next buttons
- **Host details** — Hostname, port, fingerprint, first seen, and last seen dates
- **Revoke button** — Remove trust for individual hosts

### Searching Hosts

1. Type in the "Filter by hostname..." search box
2. Results filter in real-time as you type
3. Search is case-insensitive
4. Pagination resets to page 1 when searching

### Revoking Trust

To remove a server from your trusted hosts:

1. Find the host in the list (use search if needed)
2. Click the **Revoke** button
3. The host is immediately removed

!!! note
    After revoking trust, the next visit to that server will treat it as a first-time connection, and the certificate will be trusted again automatically.

## Storage Location

Known hosts are stored by [Nauyaca](https://github.com/alanbato/nauyaca) in an SQLite database:

```
~/.nauyaca/tofu.db
```

## When to Revoke Trust

Consider revoking trust when:

- You know a server has legitimately changed certificates and want a clean slate
- You're troubleshooting connection issues
- You want to verify a server's current certificate

## Troubleshooting

### Too Many Hosts

If the Known Hosts list is slow to load:

- Use the search box to filter to specific hosts
- Pagination limits display to 10 hosts at a time

### Certificate Keeps Changing

If a server's certificate changes frequently:

1. Check if the server uses load balancing with different certificates
2. Contact the server operator
3. Consider if the site is safe to use

### Cannot Connect After Revoking

After revoking trust:

1. Try connecting again — the new certificate should be trusted automatically
2. If prompted about a certificate change, verify the fingerprint is expected
3. Check your network connection
