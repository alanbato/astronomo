# Client Certificates

This guide explains how to create and manage client certificates for authenticated Gemini sites.

## Understanding Client Certificates

Some Gemini sites use client certificates for:

- User identification
- Access control
- Persistent sessions

When a site requests a certificate, Astronomo prompts you to select or create one.

## Creating a Certificate

### When Prompted

1. Visit a site that requests a certificate
2. Astronomo shows a certificate selection dialog
3. Choose "Create New Identity"
4. Enter a name for this identity (e.g., "My Gemini Identity")
5. The certificate is generated and saved

### From Settings

1. Press ++ctrl+comma++ to open Settings
2. Navigate to the Certificates section
3. Select "Create New Identity"
4. Enter identity details

## Selecting a Certificate

### Proactive Selection (Session-Based)

When navigating to a site where you have one or more identities with matching URL prefixes:

1. A dialog automatically appears before the request is made
2. Shows all matching identities plus "Continue without identity" option
3. Select an identity or browse anonymously
4. Your choice is remembered for the **current session** (until you quit Astronomo)

This allows you to choose which identity to use when you have multiple options, without permanently associating an identity with the site.

### Server-Requested Selection (Status 60)

When a site explicitly requests a certificate:

1. A dialog shows your available identities
2. Select the one to use for this site
3. Optionally check "Remember for this host" to permanently associate the identity
4. Astronomo also remembers your choice for the current session

## Managing Identities

### Viewing Identities

1. Open Settings (++ctrl+comma++)
2. Navigate to Certificates section
3. View list of all identities

### Identity Details

Each identity includes:

- Name (your label for it)
- Creation date
- Associated hosts (sites using this identity)

### Deleting Identities

!!! warning
    Deleting an identity removes the certificate permanently. Sites using it will no longer recognize you.

1. Open Settings
2. Navigate to Certificates
3. Select the identity to delete
4. Confirm deletion

## Host Associations

### Session Associations (Temporary)

When you select an identity via the proactive selection dialog:

- The choice is stored in memory for the current session
- Applies to the host (e.g., `gemini://example.com/`)
- Lost when you quit Astronomo
- Use this when you want to temporarily use a specific identity

### Persistent Associations (Permanent)

When you check "Remember for this host" in the status 60 dialog:

- The URL prefix is added to the identity's stored associations
- Saved to disk in `~/.config/astronomo/identities.toml`
- Persists across sessions
- Triggers the proactive selection dialog on future visits (if multiple identities match)

### Changing Association

To use a different identity for a site:

**For session associations:**
- Simply quit and restart Astronomo, then select a different identity

**For persistent associations:**
1. Open Settings (++ctrl+comma++)
2. Navigate to Certificates
3. Select the identity and choose "Manage URLs"
4. Remove the URL association
5. Visit the site again and select a different identity

## Certificate Storage

Certificates are stored in `~/.config/astronomo/`:

```
~/.config/astronomo/
├── identities.toml           # Metadata and host mappings
└── certificates/
    ├── {uuid}.pem            # Certificate file
    └── {uuid}.key            # Private key file
```

!!! warning "Security Note"
    Private key files contain sensitive data. Ensure appropriate file permissions and backup securely.

## Backup and Restore

### Backup

```bash
# Backup identity metadata and certificates
cp ~/.config/astronomo/identities.toml ~/astronomo-backup/
cp -r ~/.config/astronomo/certificates ~/astronomo-backup/
```

### Restore

```bash
cp ~/astronomo-backup/identities.toml ~/.config/astronomo/
cp -r ~/astronomo-backup/certificates ~/.config/astronomo/
```

## Troubleshooting

### Certificate Not Accepted

- The site may require a specific certificate format
- Try creating a new identity specifically for that site
- Check if the site has specific requirements in their documentation

### Lost Identity

If you've lost access to an identity:

1. Create a new identity
2. Sites will see you as a new user
3. You may need to re-register on sites that require identification

### Permission Errors

Ensure proper file permissions:

```bash
chmod 700 ~/.config/astronomo/certificates
chmod 600 ~/.config/astronomo/certificates/*.key
```

## Best Practices

1. **Use descriptive names** - Label identities by purpose or site
2. **One identity per context** - Separate personal/work identities
3. **Regular backups** - Certificate loss means losing access
4. **Secure storage** - Protect the identities directory
