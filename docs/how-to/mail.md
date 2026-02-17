# GMAP Mail

This guide explains how to send, receive, and manage mail in Astronomo using the GMAP protocol and Misfin for message delivery.

## Prerequisites

Before using mail, you need a **client certificate** (identity) for authentication. If you don't have one yet, create it in Settings (++ctrl+comma++) under the **Certificates** tab. See the [Certificates guide](certificates.md) for details.

You also need access to a GMAP-compatible mail server.

## Opening the Mail Screen

Press ++ctrl+e++ to open the mail screen. Press ++ctrl+e++ or ++escape++ to close it and return to browsing.

If you haven't set up a mail account yet, press ++ctrl+a++ to add one.

## Setting Up an Account

1. Open the mail screen (++ctrl+e++)
2. Press ++ctrl+a++ to add a new account
3. Fill in the account details:

| Field | Description |
|-------|-------------|
| **Account Name** | Display name for the account |
| **GMAP Server Hostname** | Your mail server hostname |
| **Port** | Server port (default: 1960) |
| **Mailbox Name** | Your mailbox name (from certificate) |
| **Identity** | Client certificate to use for authentication |
| **GMAP Address** | Address for sent mail copies (default: `gmap@hostname`) |

4. Press ++enter++ to save

!!! tip
    The identity you select must be trusted by the GMAP server. Check with your server administrator if you're unsure which certificate to use.

## Reading Messages

### Three-Pane Layout

The mail screen has three panels:

| Panel | Description |
|-------|-------------|
| **Tags** (left) | Tag list with unread counts |
| **Messages** (center) | Messages in the selected tag |
| **Message** (right) | Full content of the selected message |

### Navigation

| Key | Action |
|-----|--------|
| ++tab++ / ++shift+tab++ | Switch between panels |
| ++arrow-left++ / ++arrow-right++ | Switch between panels |
| ++arrow-up++ / ++arrow-down++ | Navigate within current panel |
| ++enter++ | Select tag or message |

### Viewing a Message

1. Select a tag from the left panel (e.g., **Inbox**)
2. Use ++arrow-up++ / ++arrow-down++ to browse messages in the center panel
3. The selected message appears in the right panel with:
    - Sender and recipient addresses
    - Timestamp
    - Tags
    - Full message body (rendered as Gemtext)

## Tag Operations

Tags organize your messages. Every account starts with these built-in tags:

- **Inbox** — New incoming messages
- **Archive** — Messages you've archived
- **Sent** — Messages you've sent
- **Drafts** — Message drafts
- **Trash** — Messages marked for deletion

### Quick Actions

| Key | Action |
|-----|--------|
| ++a++ | Archive selected message (moves from Inbox to Archive) |
| ++d++ | Trash selected message (moves to Trash) |
| ++u++ | Toggle unread status |
| ++t++ | Manage tags (add/remove custom tags) |

### Custom Tags

1. Select a message
2. Press ++t++ to open the tag manager
3. Check or uncheck existing tags
4. Type a new tag name and press the **Add** button to create a custom tag

!!! note
    Tag names can only contain letters, numbers, underscores, and hyphens.

## Deleting Messages

Astronomo uses a **two-step delete** to prevent accidental data loss:

1. Press ++d++ to move a message to **Trash**
2. Select the **Trash** tag to view trashed messages
3. Select the message and press ++shift+d++ to permanently delete it
4. Confirm deletion in the dialog

!!! warning
    Permanent deletion cannot be undone. The message is removed from both the local cache and the server.

## Composing Messages

1. Press ++ctrl+n++ to open the compose window
2. Enter the recipient address (e.g., `alice@example.com`)
3. Optionally enter a subject
4. Write your message body in Gemtext format
5. Press **Send**

The message is sent via the Misfin protocol. A copy is automatically saved to your Sent folder on the GMAP server.

!!! tip
    The message body supports Gemtext formatting: headings (`# Title`), links (`=> url label`), lists (`* item`), and preformatted blocks (`` ``` ``).

## Replying to Messages

1. Select a message
2. Press ++r++ to reply
3. The compose window opens with:
    - **To** pre-filled with the original sender's address
    - **Subject** pre-filled with `Re: Original Subject`
    - **Body** pre-filled with the original message quoted using `>` markers
4. Write your reply and press **Send**

## Misfin Links

Gemtext pages can contain `misfin:` links that open the compose window with pre-filled fields:

- `misfin:alice@example.com` — compose to alice
- `misfin:alice@example.com?Hello%20there` — compose with body text

When you click a `misfin:` link or enter one in the address bar, the mail compose screen opens automatically.

## Syncing

Press ++ctrl+r++ to sync messages from the server. Syncing:

- Fetches new messages since your last sync
- Updates tags for existing messages
- Runs in the background without blocking the UI

The sync status is shown in the mail screen header.

## Storage

### Account Configuration

Accounts are stored at `~/.config/astronomo/gmap_accounts.toml`:

```toml
[accounts.uuid-here]
id = "uuid-here"
name = "My Account"
hostname = "mail.example.com"
port = 1960
mailbox = "alice"
identity_id = "cert-uuid"
gmap_address = "gmap@mail.example.com"
```

### Message Cache

Messages are cached locally in an SQLite database at `~/.cache/astronomo/mail_cache.db` for fast queries and offline access. The cache stores message content, metadata, and tags.

## Keyboard Reference

### Mail Screen

| Key | Action |
|-----|--------|
| ++escape++ or ++ctrl+e++ | Close mail screen |
| ++tab++ / ++shift+tab++ | Next / previous panel |
| ++arrow-left++ / ++arrow-right++ | Switch panels |
| ++arrow-up++ / ++arrow-down++ | Navigate within panel |
| ++enter++ | Select item |
| ++ctrl+n++ | Compose new message |
| ++ctrl+r++ | Sync messages |
| ++ctrl+a++ | Add account |

### Message Actions

| Key | Action |
|-----|--------|
| ++a++ | Archive message |
| ++d++ | Move to Trash |
| ++shift+d++ | Permanently delete (from Trash) |
| ++u++ | Toggle unread |
| ++r++ | Reply |
| ++t++ | Manage tags |

## Tips

1. **Set up your identity first** — Create a client certificate before adding a mail account
2. **Use tags to organize** — Archive messages you've read, use custom tags for projects
3. **Sync regularly** — Messages don't auto-sync; press ++ctrl+r++ to check for new mail
4. **Two-step delete** — You must Trash a message (++d++) before you can permanently delete it (++shift+d++)
5. **Gemtext formatting** — Use headings and links in your messages for rich content
