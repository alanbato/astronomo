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

When a site requests a certificate:

1. A dialog shows your available identities
2. Select the one to use for this site
3. Astronomo remembers your choice for this host

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

### Automatic Association

When you select an identity for a site, Astronomo remembers the association:

- Host: `example.com`
- Identity: Your selected certificate

Future requests to that host automatically use the same identity.

### Changing Association

To use a different identity for a site:

1. Clear the current association in Settings
2. Visit the site again
3. Select a different identity when prompted

## Certificate Storage

Certificates are stored in `~/.config/astronomo/identities/`:

```
~/.config/astronomo/identities/
├── identities.toml      # Metadata and host mappings
├── abc123.crt           # Certificate file
└── abc123.key           # Private key file
```

!!! warning "Security Note"
    Private key files contain sensitive data. Ensure appropriate file permissions and backup securely.

## Backup and Restore

### Backup

```bash
# Backup the entire identities directory
cp -r ~/.config/astronomo/identities ~/identities-backup
```

### Restore

```bash
cp -r ~/identities-backup ~/.config/astronomo/identities
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
chmod 700 ~/.config/astronomo/identities
chmod 600 ~/.config/astronomo/identities/*.key
```

## Best Practices

1. **Use descriptive names** - Label identities by purpose or site
2. **One identity per context** - Separate personal/work identities
3. **Regular backups** - Certificate loss means losing access
4. **Secure storage** - Protect the identities directory
