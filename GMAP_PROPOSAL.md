# GMAP Client Support for Astronomo

**Proposal: Integrating Misfin Mail into a Terminal Gemini Browser**

## 1. Context and Motivation

### What is GMAP?

GMAP (Gemini-Misfin Access Protocol) is "IMAP for Misfin" — it provides programmatic mailbox access over Gemini requests with TLS client certificates. A GMAP server (like titlani) exposes endpoints to list, read, tag, untag, and delete messages stored in a Misfin mailbox. The wire format uses standard Gemini `gemini://` URLs and response codes, so any Gemini-capable client can speak GMAP with minimal additions.

### Why Astronomo?

Astronomo already supports five protocols (Gemini, Gopher, Finger, Nex, Spartan), has full TLS client certificate management via nauyaca, and uses a Textual TUI with rich screen/widget infrastructure. Adding GMAP support gives users a complete terminal mail experience connected to titlani-based Misfin servers.

### Key Design Decision: Dedicated Screen, Not a Formatter

Astronomo's formatters (`formatters/gopher.py`, `formatters/finger.py`, etc.) are stateless functions that convert protocol responses into Gemtext for passive viewing. Mail is fundamentally different — it requires:

- Persistent state (accounts, tags, read/unread tracking)
- Interactive operations (archive, delete, compose, tag)
- Multi-pane navigation (tags sidebar, message list, preview)
- Background sync

Therefore GMAP support should be a **dedicated `MailScreen`** (like `FeedsScreen`), not a formatter.

---

## 2. GMAP Protocol Reference

Everything a client implementer needs, extracted from titlani's implementation.

### 2.1 Connection

| Property         | Value                                  |
|------------------|----------------------------------------|
| Transport        | TLS over TCP                           |
| Default port     | 1960 (`DEFAULT_GMAP_PORT`)             |
| URL scheme       | `gemini://`                            |
| Request format   | `gemini://hostname:port/path?query\r\n` |
| Response format  | `<status> <meta>\r\n<body>`            |
| Max request size | 1024 bytes                             |
| Request timeout  | 30.0 seconds                           |
| Encoding         | UTF-8                                  |
| Client cert      | **Required** (TLS handshake)           |

> **Why a separate port from Misfin (1958)?** GMAP requires `request_client_cert=True` to validate identity, while Misfin uses `request_client_cert=False` to accept arbitrary self-signed certs from unknown senders. OpenSSL 3.x rejects unverified self-signed certs during handshake, so separate TLS contexts are required.

### 2.2 Authentication

The client MUST present an X.509 certificate during TLS handshake containing:

| Certificate Field | Purpose                        | Example                 |
|-------------------|--------------------------------|-------------------------|
| `USER_ID`         | Mailbox name                   | `alice`                 |
| `SAN DNS`         | Server hostname                | `mail.example.com`      |
| `CN` (Common Name)| Human-readable blurb (optional)| `Alice Developer`       |

The server extracts `USER_ID` to determine which mailbox to access. If the server has registered per-mailbox fingerprints (via `titlani identity generate --install`), it also verifies the certificate's SHA-256 fingerprint matches.

### 2.3 Status Codes

| Code | Meaning              | When Used                                        |
|------|----------------------|--------------------------------------------------|
| 20   | Success              | Request succeeded; body follows                  |
| 30   | Redirect (temporary) | Redirect to different host/port only             |
| 40   | Temporary failure    | Encrypted message, server error                  |
| 51   | Not found            | Message/tag/mailbox not found; not in Trash       |
| 59   | Bad request          | Invalid tag name, missing query, malformed URL   |
| 60   | Client cert required | No certificate presented                         |
| 61   | Cert not authorized  | Invalid cert, fingerprint mismatch, unregistered |

> Servers MUST NOT respond with `1x` (input) status codes. `3x` redirects MUST only change hostname/port, never path/query.

### 2.4 Endpoints

#### Retrieve Message

```
GET gemini://hostname:port/msgid/<msgid>
```

- **Response 20**: `text/plain` — raw gemmail format (3 metadata lines + gemtext body)
- **Response 40**: Message is encrypted (`.gemmail.enc`)
- **Response 51**: Message ID not found

#### List All Message IDs (excluding Trash)

```
GET gemini://hostname:port/tag/
```

- **Response 20**: `text/plain` — comma-separated message IDs
- Excludes messages tagged `Trash`

#### List Messages by Tag

```
GET gemini://hostname:port/tag/<tagname>
```

- **Response 20**: `text/plain` — comma-separated message IDs with this tag
- Messages tagged `Trash` are hidden from all tags except `Trash` itself
- **Response 51**: Tag not found (no messages with this tag)

#### List Messages by Tag Since Timestamp

```
GET gemini://hostname:port/tag/<tagname>/<YYYY-MM-DDTHH:MM:SSZ>
```

- Returns only messages received **after** the given timestamp
- **Response 40**: Invalid timestamp format

#### Add Tag

```
GET gemini://hostname:port/tag/<tagname>?<msgid>
```

- **Response 20**: `Tag added` — idempotent (re-tagging updates timestamp)
- **Response 51**: Message not found
- **Response 59**: Invalid tag name

#### Remove Tag

```
GET gemini://hostname:port/untag/<tagname>?<msgid>
```

- **Response 20**: `Tag removed`
- **Response 51**: Message not found
- **Response 59**: Missing query

#### Delete Message (permanent)

```
GET gemini://hostname:port/delete?<msgid>
```

- **Precondition**: Message MUST be tagged `Trash` first
- **Response 20**: `Message deleted` — file removed from disk
- **Response 51**: Message not in Trash (or doesn't exist)
- **Response 59**: Missing query

Two-step deletion workflow:
```
1. gemini://host/tag/Trash?<msgid>     → tag as Trash
2. gemini://host/delete?<msgid>        → permanent delete
```

### 2.5 Message ID Format

Message IDs are **opaque strings** chosen by the server. Clients MUST NOT assign semantic meaning to them. Titlani uses the format `YYYYMMDDTHHMMSSZ` (compact ISO 8601 UTC), derived from the `.gemmail` filename stem, but other servers may use hashes, integers, or UUIDs.

### 2.6 Gemmail Message Format

Three metadata lines followed by a gemtext body:

```
<senders-line>
<recipients-line>
<timestamps-line>
<gemtext body>
```

**Senders line**: Comma-separated `mailbox@hostname [optional blurb]`
**Recipients line**: Comma-separated addresses (MAY be empty if single recipient = requesting account)
**Timestamps line**: Comma-separated ISO 8601 UTC (`2026-02-11T12:00:00Z`)

Each metadata line is capped at 1024 bytes. The body is standard gemtext.

**Parsing in Python** (using titlani):
```python
from titlani.content.gemmail import GemmailMessage

msg = GemmailMessage.from_bytes(response_body)
msg.senders     # list[MisfinAddress]
msg.recipients  # list[MisfinAddress]
msg.timestamps  # list[datetime]
msg.body        # str (gemtext)
msg.subject     # str | None (first # or ## heading, stripped of leading #)
```

**Example message:**
```
alice@mail.example.com Alice
bob@mail.example.com Bob
2026-02-11T12:00:00Z
# Re: Meeting tomorrow

Sounds good, see you at 3pm!

> Original message quoted here
```

### 2.7 Tag System

**Required tags:**

| Tag       | Type   | Purpose                                     |
|-----------|--------|---------------------------------------------|
| `Inbox`   | Folder | New messages land here by default            |
| `Archive` | Folder | Received mail kept but not in Inbox/Trash    |
| `Sent`    | Folder | Messages sent by the user                    |
| `Drafts`  | Folder | Composed but unsent messages                 |
| `Trash`   | Status | Marked for deletion; hidden from other tags  |
| `Unread`  | Status | Auto-assigned to new messages                |

**Custom tags**: Must match `[a-zA-Z0-9_-]+` (letters, digits, underscore, hyphen). No dots, spaces, or special characters. Hierarchy/nesting is client-side only.

**Trash behavior**: Messages tagged `Trash` are completely hidden from all other tag listings. When `Trash` is removed, other tags are restored. This means `/tag/Inbox` never includes trashed messages.

### 2.8 Sent Mail and Drafts

To record sent messages, the client sends a **copy** of the outgoing message to the server's GMAP mailbox (default: `gmap@hostname`). The message MUST include recipients metadata, SHOULD include timestamps, and MAY include sender metadata.

For draft updates, the client sends a message to the GMAP address with the body prefixed by `MGID:<msgid>`, where `<msgid>` is the previous draft's message ID. The server replaces the old draft content.

---

## 3. Architecture: How It Fits Into Astronomo

### 3.1 Existing Patterns to Follow

| Astronomo Pattern        | GMAP Equivalent              | Reference File                        |
|--------------------------|------------------------------|---------------------------------------|
| `FeedsScreen`            | `MailScreen`                 | `screens/feeds.py`                    |
| `FeedManager` (TOML)     | `GmapAccountManager` (TOML) | `feeds.py`                            |
| `IdentityManager`        | Certificate import           | `identities.py`                       |
| `ConfigManager`          | Mail settings                | `config.py`                           |
| `FeedListPanel` / `FeedItemsPanel` | `TagListPanel` / `MessageListPanel` / `MessagePreviewPanel` | `screens/feeds.py` |
| `AddFeedModal`           | `AddAccountModal`            | `widgets/feeds/add_feed_modal.py`     |
| `@work(exclusive=True)`  | Async GMAP fetches           | `astronomo_app.py`                    |
| `ModalScreen[T]`         | Compose/confirm modals       | `widgets/feeds/*.py`                  |

### 3.2 New Module Overview

```
src/astronomo/
├── gmap_client.py           # Async GMAP client wrapping nauyaca GeminiClient
├── gmap_accounts.py         # Account manager with TOML persistence
├── mail_cache.py            # SQLite message cache
├── screens/
│   └── mail.py              # Three-pane MailScreen
├── widgets/
│   ├── mail/
│   │   ├── tag_list_panel.py
│   │   ├── message_list_panel.py
│   │   ├── message_preview_panel.py
│   │   ├── add_account_modal.py
│   │   ├── compose_modal.py
│   │   ├── tag_manage_modal.py
│   │   └── confirm_delete_modal.py
│   └── settings/
│       └── mail.py          # Mail settings tab
```

### 3.3 Dependency: titlani

Add `titlani` as a dependency in `pyproject.toml`. Use:

- `titlani.content.GemmailMessage` — Parse gemmail wire format into structured data
- `titlani.content.MisfinAddress` — Address parsing with mailbox/hostname/blurb
- `titlani.client.MisfinClient` — Send Misfin messages (for compose/reply)

This avoids reimplementing wire format parsing and Misfin sending.

---

## 4. New Modules: Detailed Design

### 4.1 `gmap_client.py` — Async GMAP Client

Wraps nauyaca's `GeminiClient` with GMAP-specific methods.

```python
class GmapClient:
    """Async GMAP client for a single account."""

    def __init__(
        self,
        hostname: str,
        port: int = 1960,
        cert_path: Path,
        key_path: Path,
        timeout: int = 30,
    ): ...

    async def list_by_tag(self, tag: str, since: datetime | None = None) -> list[str]:
        """GET /tag/<tag>[/<timestamp>] → list of message IDs."""

    async def list_all(self) -> list[str]:
        """GET /tag/ → all message IDs (excluding Trash)."""

    async def get_message(self, msgid: str) -> GemmailMessage:
        """GET /msgid/<msgid> → parsed GemmailMessage."""

    async def add_tag(self, msgid: str, tag: str) -> bool:
        """GET /tag/<tag>?<msgid> → True on success."""

    async def remove_tag(self, msgid: str, tag: str) -> bool:
        """GET /untag/<tag>?<msgid> → True on success."""

    async def delete_message(self, msgid: str) -> bool:
        """GET /delete?<msgid> → True on success (must be in Trash)."""
```

**Implementation**: Each method builds a `gemini://` URL, creates a `GeminiClient` with `client_cert`/`client_key`, calls `await client.get(url)`, checks the status code, and parses the response.

**Error handling**: Map status codes to specific exceptions (`GmapAuthError` for 60/61, `GmapNotFoundError` for 51, `GmapRequestError` for 59, `GmapTempFailure` for 40).

### 4.2 `gmap_accounts.py` — Account Manager

Follows the `FeedManager` pattern: dataclasses with `to_dict()`/`from_dict()`, TOML persistence, auto-save after mutations.

```python
@dataclass
class GmapAccount:
    id: str                      # UUID
    name: str                    # Display name ("Work Mail")
    hostname: str                # GMAP server hostname
    port: int = 1960             # GMAP port
    mailbox: str = ""            # Mailbox name (from cert USER_ID)
    identity_id: str = ""        # Reference to IdentityManager identity
    gmap_address: str = ""       # For sent mail (default: gmap@hostname)
    last_sync: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> Self: ...

class GmapAccountManager:
    VERSION = "1.0"

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "astronomo"
        self.accounts_file = self.config_dir / "gmap_accounts.toml"
        self.accounts: list[GmapAccount] = []
        self._load()

    def add_account(self, name: str, hostname: str, ...) -> GmapAccount: ...
    def remove_account(self, account_id: str) -> bool: ...
    def update_account(self, account_id: str, **kwargs) -> bool: ...
    def get_account(self, account_id: str) -> GmapAccount | None: ...
    def get_all_accounts(self) -> list[GmapAccount]: ...
```

**Persistence format** (`~/.config/astronomo/gmap_accounts.toml`):
```toml
version = "1.0"

[[accounts]]
id = "uuid-here"
name = "Personal Mail"
hostname = "mail.example.com"
port = 1960
mailbox = "alice"
identity_id = "identity-uuid"
gmap_address = "gmap@mail.example.com"
last_sync = "2026-02-11T14:22:00"
created_at = "2026-01-15T10:00:00"
```

### 4.3 `mail_cache.py` — SQLite Message Cache

TOML is not suitable for potentially thousands of messages. SQLite (`sqlite3` stdlib) provides indexed queries for fast tag filtering, search, and offline access.

```python
class MailCache:
    """SQLite cache for GMAP messages."""

    def __init__(self, cache_dir: Path | None = None):
        self.db_path = (cache_dir or default_cache_dir()) / "mail_cache.db"
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    # Schema:
    # accounts(account_id TEXT PK, hostname TEXT, last_sync TEXT)
    # messages(account_id TEXT, msgid TEXT, raw_bytes BLOB,
    #          sender TEXT, subject TEXT, timestamp TEXT,
    #          cached_at TEXT, PK(account_id, msgid))
    # message_tags(account_id TEXT, msgid TEXT, tag TEXT,
    #              PK(account_id, msgid, tag))
    # + indexes on (account_id, tag) and (account_id, timestamp)

    def store_message(self, account_id: str, msgid: str, raw: bytes, tags: list[str]): ...
    def get_message(self, account_id: str, msgid: str) -> CachedMessage | None: ...
    def list_by_tag(self, account_id: str, tag: str) -> list[CachedMessage]: ...
    def update_tags(self, account_id: str, msgid: str, tags: list[str]): ...
    def remove_message(self, account_id: str, msgid: str): ...
    def get_last_sync(self, account_id: str) -> datetime | None: ...
    def set_last_sync(self, account_id: str, ts: datetime): ...
    def get_all_tags(self, account_id: str) -> list[str]: ...
```

**Cache location**: `~/.cache/astronomo/mail_cache.db` (XDG cache dir).

### 4.4 `screens/mail.py` — MailScreen

A full-screen modal (like `FeedsScreen`) with three-pane layout.

```python
class MailScreen(Screen):
    """Three-pane mail interface: tags | message list | preview."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("tab", "cycle_panel", "Next Panel", priority=True),
        Binding("shift+tab", "cycle_panel_back", "Prev Panel", priority=True),
        Binding("ctrl+n", "compose", "Compose"),
        Binding("ctrl+r", "sync", "Sync"),
        Binding("a", "archive", "Archive"),
        Binding("d", "trash", "Trash"),
        Binding("u", "toggle_unread", "Unread"),
        Binding("r", "reply", "Reply"),
        Binding("t", "manage_tags", "Tags"),
        Binding("enter", "open_message", "Open", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("ctrl+a", "add_account", "Add Account"),
    ]

    def __init__(
        self,
        account_manager: GmapAccountManager,
        identity_manager: IdentityManager,
        cache: MailCache,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.account_manager = account_manager
        self.identity_manager = identity_manager
        self.cache = cache
        self.current_account: GmapAccount | None = None
        self.current_tag: str = "Inbox"
        self.current_msgid: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="mail-content"):
            yield TagListPanel(id="tag-panel")
            yield MessageListPanel(id="message-panel")
            yield MessagePreviewPanel(id="preview-panel")
        yield Footer()
```

---

## 5. UI Design

### 5.1 Three-Pane Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Mail — alice@mail.example.com                        [Ctrl+R Sync] │
├──────────┬──────────────────────────────┬───────────────────────┤
│ Tags     │ Inbox (3 unread)             │ From: bob@host Bob    │
│          │                              │ Date: 2026-02-11      │
│ > Inbox 3│ ● Re: Meeting tomorrow       │                       │
│   Archive│   bob@host · 2m ago          │ # Re: Meeting tomorrow│
│   Sent   │ ● Project update             │                       │
│   Drafts │   carol@host · 1h ago        │ Sounds good, see you  │
│   Trash  │   Security advisory          │ at 3pm!               │
│ ──────── │   admin@host · 3h ago        │                       │
│ Custom:  │                              │ > Original message    │
│   Work   │                              │ > quoted here         │
│   Personal                              │                       │
│          │                              │                       │
├──────────┴──────────────────────────────┴───────────────────────┤
│ ESC Close │ TAB Panel │ a Archive │ d Trash │ r Reply │ t Tags  │
└─────────────────────────────────────────────────────────────────┘
```

- **Left panel (TagListPanel)**: Account selector at top, then required tags with unread counts, separator, custom tags. `●` bullet for tags with unread messages.
- **Center panel (MessageListPanel)**: Messages in selected tag, sorted newest-first. Unread messages shown with `●` indicator. Shows sender, subject (first `#` heading), and relative timestamp.
- **Right panel (MessagePreviewPanel)**: Full message display for the selected message — metadata header (From, To, Date) followed by gemtext body rendered with astronomo's `GemtextViewer` or `parse_gemtext`.

### 5.2 Widget Classes

```
TagListPanel(VerticalScroll, can_focus=True)
├── TagWidget(Static)              # One per tag row
│
MessageListPanel(VerticalScroll, can_focus=True)
├── MessageWidget(Static, can_focus=True)  # One per message row
│
MessagePreviewPanel(VerticalScroll, can_focus=True)
├── (rendered gemtext content)
```

**Custom Messages:**

```python
class TagListPanel(VerticalScroll, can_focus=True):
    class TagSelected(Message):
        def __init__(self, tag: str) -> None: ...

class MessageListPanel(VerticalScroll, can_focus=True):
    class MessageSelected(Message):
        def __init__(self, msgid: str) -> None: ...
```

### 5.3 Keybindings Summary

| Key         | Action                 | Context      |
|-------------|------------------------|--------------|
| `Escape`    | Close MailScreen       | Any          |
| `Tab`       | Cycle to next panel    | Any          |
| `Shift+Tab` | Cycle to previous panel| Any          |
| `Up/Down`   | Navigate items         | Any panel    |
| `Enter`     | Select tag / open msg  | Tags / List  |
| `Ctrl+N`    | Compose new message    | Any          |
| `Ctrl+R`    | Sync with server       | Any          |
| `a`         | Archive selected msg   | Message list |
| `d`         | Move to Trash          | Message list |
| `D`         | Permanent delete       | Trash view   |
| `u`         | Toggle unread          | Message list |
| `r`         | Reply to message       | Preview      |
| `t`         | Manage tags on message | Message list |
| `Ctrl+A`    | Add new account        | Any          |

---

## 6. Certificate Integration

### The Identity Gap

Astronomo's `IdentityManager` generates certificates via nauyaca's `generate_self_signed_cert()`, which puts the hostname in `CN` (Common Name). Misfin certificates require a different layout:

| Field     | nauyaca cert     | Misfin cert (titlani) |
|-----------|------------------|-----------------------|
| `USER_ID` | (not set)        | Mailbox name          |
| `CN`      | Hostname         | Blurb                 |
| `SAN DNS` | (not set)        | Hostname              |

### Solution: Import-Based Approach

Do NOT modify astronomo's identity generation. Instead:

1. User generates a Misfin identity using titlani CLI:
   ```bash
   titlani identity generate alice mail.example.com --blurb "Alice"
   ```
   This produces `alice.pem` and `alice.key` with the correct Misfin certificate layout.

2. User imports the certificate into astronomo using the existing `import_identity_from_custom_files()` method:
   ```python
   identity = identity_manager.import_identity_from_custom_files(
       name="alice@mail.example.com",
       cert_path=Path("alice.pem"),
       key_path=Path("alice.key"),
   )
   ```

3. The `AddAccountModal` guides the user through this: select an existing imported identity OR provide paths to cert/key files to import inline.

4. The `GmapAccount.identity_id` references the imported `Identity` object, so `GmapClient` can resolve the cert/key paths for TLS.

### Why Not Generate Misfin Certs in Astronomo?

- It would require adding `cryptography` as a direct dependency (currently only nauyaca uses it)
- The server admin typically generates and installs the cert (to register the fingerprint)
- Import keeps astronomo's identity system generic and protocol-agnostic

---

## 7. Sync Strategy

### Incremental Sync Flow

```
1. Get last_sync timestamp for account from cache
2. For each required tag (Inbox, Archive, Sent, Drafts, Trash, Unread):
     GET /tag/<tag>/<last_sync_timestamp>
     → new_msgids for this tag
3. For each new_msgid not in cache:
     GET /msgid/<msgid>
     → store raw bytes + parsed metadata in cache
4. Update tag associations in cache
5. Set last_sync = now
```

### First Sync (No Timestamp)

On first sync, omit the timestamp filter — fetch full message ID lists for each tag. Then fetch each message individually. This may be slow for large mailboxes; consider a progress indicator.

### Offline Behavior

When the server is unreachable:
- Display cached messages from SQLite
- Show a "Last synced: X ago" indicator
- Queue tag operations (archive, trash, read) locally
- Apply queued operations on next successful sync

### Background Sync

Use Textual's `@work` decorator for non-blocking sync:

```python
@work(exclusive=True, group="mail-sync")
async def _sync_account(self, account: GmapAccount) -> None:
    client = GmapClient(
        hostname=account.hostname,
        port=account.port,
        cert_path=identity.cert_path,
        key_path=identity.key_path,
    )
    # ... incremental sync logic
    self.app.notify(f"Synced {account.name}: {new_count} new messages")
```

---

## 8. Data Flows

### 8.1 Fetch Inbox

```
User opens MailScreen
  → MailScreen.__init__ loads GmapAccountManager
  → If accounts exist, select first account
  → _sync_account(account) runs as @work
    → GmapClient.list_by_tag("Inbox", since=last_sync)
    → For each new msgid: GmapClient.get_message(msgid)
    → MailCache.store_message(account_id, msgid, raw, tags=["Inbox", "Unread"])
    → MailCache.set_last_sync(account_id, now)
  → Post SyncComplete message
  → MessageListPanel.refresh() reads from MailCache
  → TagListPanel.refresh() updates unread counts from cache
```

### 8.2 Read Message

```
User selects message in MessageListPanel
  → Post MessageSelected(msgid)
  → MailScreen handles: load from cache (or fetch if not cached)
  → Parse with GemmailMessage.from_bytes(raw)
  → Render metadata header + parse_gemtext(msg.body) in PreviewPanel
  → GmapClient.remove_tag(msgid, "Unread")  (background)
  → MailCache.update_tags(account_id, msgid, remove="Unread")
  → TagListPanel.refresh() decrements Inbox unread count
```

### 8.3 Archive Message

```
User presses 'a' on a message
  → GmapClient.remove_tag(msgid, "Inbox")
  → GmapClient.add_tag(msgid, "Archive")
  → MailCache.update_tags(...)
  → Remove from MessageListPanel
  → Select next message
```

### 8.4 Delete Message (Two-Step)

```
User presses 'd' on a message
  → GmapClient.add_tag(msgid, "Trash")
  → Message hidden from current view (Trash hides from all tags)
  → Notify "Moved to Trash"

User views Trash, presses 'D' on a message
  → Show ConfirmDeleteModal("Permanently delete?")
  → On confirm: GmapClient.delete_message(msgid)
  → MailCache.remove_message(account_id, msgid)
  → Remove from MessageListPanel
```

### 8.5 Compose and Send

```
User presses Ctrl+N
  → Show ComposeModal(account)
  → User enters: recipient address, body (gemtext)
  → On send:
    → Build GemmailMessage with senders, recipients, timestamps, body
    → Use titlani.client.MisfinClient to send to recipient (Misfin protocol, port 1958)
    → Send copy to gmap@hostname (GMAP address) for Sent folder
    → Notify "Message sent"
```

### 8.6 Reply

```
User presses 'r' on a message
  → Show ComposeModal(account, reply_to=msg)
  → Pre-fill recipient = original sender
  → Pre-fill body with quoted original (> prefixed lines)
  → Same send flow as compose
```

---

## 9. Implementation Phases

### Phase 1: Core Networking
**Goal**: GMAP client can connect, authenticate, and fetch data.

- [ ] Create `gmap_client.py` with `GmapClient` class
- [ ] Implement all GMAP endpoints as async methods
- [ ] Add error handling and status code mapping
- [ ] Write unit tests with mocked responses

### Phase 2: Account Management
**Goal**: Users can add, edit, and remove GMAP accounts.

- [ ] Create `gmap_accounts.py` with `GmapAccountManager`
- [ ] Create `widgets/mail/add_account_modal.py`
- [ ] Support certificate import during account setup
- [ ] TOML persistence at `~/.config/astronomo/gmap_accounts.toml`

### Phase 3: Message Cache
**Goal**: Messages are stored locally for performance and offline access.

- [ ] Create `mail_cache.py` with SQLite schema
- [ ] Implement incremental sync logic
- [ ] Store raw bytes + parsed metadata + tags
- [ ] Indexed queries by tag and timestamp

### Phase 4: Mail Screen UI
**Goal**: Three-pane mail interface with keyboard navigation.

- [ ] Create `screens/mail.py` with `MailScreen`
- [ ] Create `widgets/mail/tag_list_panel.py`
- [ ] Create `widgets/mail/message_list_panel.py`
- [ ] Create `widgets/mail/message_preview_panel.py`
- [ ] Implement panel cycling (Tab/Shift+Tab)
- [ ] Wire up tag selection → message list → preview flow
- [ ] Add keybinding to `astronomo_app.py` (e.g., `Ctrl+M` → `action_open_mail`)
- [ ] Initialize `GmapAccountManager` and `MailCache` in `Astronomo.__init__`

### Phase 5: Tag Operations and Compose
**Goal**: Full read/write mail workflow.

- [ ] Implement archive, trash, unread toggle actions
- [ ] Create `widgets/mail/tag_manage_modal.py` for custom tags
- [ ] Create `widgets/mail/compose_modal.py`
- [ ] Implement reply with quoted body
- [ ] Implement send via `titlani.client.MisfinClient`
- [ ] Send copy to GMAP address for Sent folder
- [ ] Create `widgets/mail/confirm_delete_modal.py`

### Phase 6: Settings and Polish
**Goal**: Configurable and production-ready.

- [ ] Create `widgets/settings/mail.py` settings tab
- [ ] Add mail config section to `ConfigManager`
- [ ] Settings: default account, sync interval, cache size limit
- [ ] Background auto-sync on MailScreen mount
- [ ] "Last synced" indicator in UI
- [ ] Offline mode with queued operations
- [ ] Notification badge on mail keybinding label

---

## 10. File Inventory

### New Files

| File                                      | Purpose                                |
|-------------------------------------------|----------------------------------------|
| `src/astronomo/gmap_client.py`            | Async GMAP client                      |
| `src/astronomo/gmap_accounts.py`          | Account manager (TOML persistence)     |
| `src/astronomo/mail_cache.py`             | SQLite message cache                   |
| `src/astronomo/screens/mail.py`           | Three-pane MailScreen                  |
| `src/astronomo/widgets/mail/__init__.py`  | Mail widgets package                   |
| `src/astronomo/widgets/mail/tag_list_panel.py` | Tags sidebar widget              |
| `src/astronomo/widgets/mail/message_list_panel.py` | Message list widget          |
| `src/astronomo/widgets/mail/message_preview_panel.py` | Message preview widget   |
| `src/astronomo/widgets/mail/add_account_modal.py` | Account setup modal           |
| `src/astronomo/widgets/mail/compose_modal.py` | Compose/reply modal              |
| `src/astronomo/widgets/mail/tag_manage_modal.py` | Tag management modal          |
| `src/astronomo/widgets/mail/confirm_delete_modal.py` | Delete confirmation modal |
| `src/astronomo/widgets/settings/mail.py`  | Mail settings tab                      |
| `tests/test_gmap_client.py`              | Client unit tests                       |
| `tests/test_gmap_accounts.py`            | Account manager tests                   |
| `tests/test_mail_cache.py`               | Cache tests                             |

### Modified Files

| File                                      | Change                                 |
|-------------------------------------------|----------------------------------------|
| `pyproject.toml`                          | Add `titlani` dependency               |
| `src/astronomo/astronomo_app.py`          | Add `GmapAccountManager`, `MailCache` init; add `Ctrl+M` binding; add `action_open_mail` |
| `src/astronomo/config.py`                 | Add `MailConfig` dataclass with settings |
| `src/astronomo/screens/settings.py`       | Add mail settings tab                  |
