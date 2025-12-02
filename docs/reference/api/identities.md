# Identities API

The identities module manages client certificates for authenticated Gemini sites.

## Overview

Some Gemini sites require client certificates for authentication. Astronomo can:

- Generate new self-signed certificates
- Store certificates persistently
- Associate certificates with specific hosts
- Present certificates when requested

Certificates are stored in `~/.config/astronomo/identities/`.

## API Reference

::: astronomo.identities
    options:
      show_root_heading: true
      show_source: true
      members:
        - Identity
        - IdentityManager

## Example Usage

```python
from astronomo.identities import IdentityManager, Identity

# Load identity manager
manager = IdentityManager()

# Create a new identity (generates certificate)
identity = manager.create_identity(
    name="My Identity",
    common_name="user@example.com",
)

# Associate identity with a host
manager.set_identity_for_host("example.com", identity.id)

# Get identity for a host
identity = manager.get_identity_for_host("example.com")
if identity:
    print(f"Using identity: {identity.name}")
    print(f"Certificate: {identity.cert_path}")
    print(f"Key: {identity.key_path}")

# List all identities
for identity in manager.list_identities():
    print(f"- {identity.name}")
```

## Certificate Storage

Each identity is stored as:

```
~/.config/astronomo/identities/
├── identities.toml      # Identity metadata and host mappings
├── <uuid>.crt           # Certificate file
└── <uuid>.key           # Private key file
```
