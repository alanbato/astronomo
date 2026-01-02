# Navigation

This guide covers efficient navigation techniques in Astronomo.

## Opening URLs

### Address Bar

1. Focus the address bar (click or press your focus key)
2. Type or paste a URL
3. Press ++enter++

!!! tip
    You can omit `gemini://` - Astronomo adds it automatically for bare URLs. See [Smart URL Detection](#smart-url-detection) for other protocols.

### From Command Line

```bash
# Open a Gemini capsule
astronomo gemini://example.com/

# Browse a Gopher server
astronomo gopher://gopher.floodgap.com/

# Query a Finger server
astronomo user@example.com
```

## Following Links

### Keyboard Navigation

1. Press ++arrow-right++ to select the next link
2. Press ++arrow-left++ to select the previous link
3. Press ++enter++ to open the selected link

The selected link is visually highlighted.

### Mouse Navigation

Click any link to follow it immediately.

## History Navigation

### Going Back

- **Keyboard:** Press ++backspace++
- **Mouse:** Click the ◀ button

### Going Forward

- **Keyboard:** Press ++shift+backspace++
- **Mouse:** Click the ▶ button

!!! note
    History is preserved within a session. When you go back, your scroll position and selected link are restored.

## Quick Navigation

Press ++ctrl+k++ to open the quick navigation modal - a fuzzy finder for quickly jumping to bookmarks and history entries.

### Using Quick Navigation

1. Press ++ctrl+k++ to open the modal
2. Start typing to search
3. Use ++arrow-up++ / ++arrow-down++ to navigate results
4. Press ++enter++ to open the selected item
5. Press ++escape++ to cancel

### Search Features

The fuzzy search supports several matching strategies:

- **Title matches** - Highest priority, searches bookmark titles
- **URL matches** - Searches within URLs
- **Acronym matches** - Type "gp" to find "Gemini Protocol"
- **Word boundary matches** - Matches at the start of words

!!! tip
    When the search field is empty, the modal shows your 20 most recent items sorted by timestamp.

## Page Scrolling

| Key | Action |
|-----|--------|
| ++arrow-up++ / ++arrow-down++ | Scroll by line |
| ++page-up++ / ++page-down++ | Scroll by page |
| ++home++ | Jump to top |
| ++end++ | Jump to bottom |

Mouse scroll wheel also works.

## Refreshing Pages

Press ++ctrl+r++ to reload the current page.

This fetches fresh content from the server.

## Handling Input Prompts

Some Gemini pages request input (status 10 and 11 responses):

1. A modal dialog appears
2. Type your response
3. Press ++enter++ to submit
4. Press ++escape++ to cancel

For sensitive input (status 11), the field is masked like a password field.

## Handling Redirects

Astronomo automatically follows redirects up to the configured limit (default: 5).

If a redirect loop is detected or the limit is exceeded, you'll see an error message.

## Multi-Protocol Navigation

Astronomo supports browsing Gopher and Finger servers in addition to Gemini.

### Smart URL Detection

When you enter a URL without a scheme, Astronomo automatically detects the protocol:

| Pattern | Detected Protocol |
|---------|------------------|
| `user@host` | `finger://user@host` |
| `gopher.example.com` | `gopher://gopher.example.com` |
| `host:70/...` | `gopher://host:70/...` |
| Everything else | `gemini://...` |

You can always specify the scheme explicitly (e.g., `gopher://example.com`).

### Browsing Gopher

Gopher menus display with type indicators:

- `[DIR]` — Directory (click to enter)
- `[TXT]` — Text file
- `[SEARCH]` — Search input
- `[BIN]` — Binary download
- `[IMG]` — Image file
- `[EXT]` — External HTTP link

Navigate Gopher menus just like Gemini pages—use arrow keys or click to follow links.

### Gopher Search

When you activate a search item (`[SEARCH]`):

1. A modal dialog prompts for your query
2. Enter search terms and press ++enter++
3. Results display as a new Gopher menu

### Downloading Gopher Files

Binary files (type 9, images, etc.) download automatically:

1. Activate the `[BIN]` or `[IMG]` link
2. File saves to `~/Downloads/`
3. A notification confirms the download

Duplicate filenames are auto-incremented (e.g., `file(1).txt`).

### Querying Finger

To look up user information:

1. Enter `user@host` in the address bar
2. Press ++enter++
3. User info displays as preformatted text

Or use the explicit format: `finger://user@host`

### Cross-Protocol Links

Pages can link between protocols. For example:

- A Gemini page can link to `gopher://...`
- A Gopher menu can link to `finger://...`

HTTP/HTTPS links open in your system's default browser.

## Tips for Efficient Browsing

1. **Use keyboard shortcuts** - Faster than reaching for the mouse
2. **Use quick navigation** - Press ++ctrl+k++ to instantly jump to any bookmark or recent page
3. **Set a home page** - Start each session at your favorite capsule
4. **Bookmark frequently** - Press ++ctrl+d++ to save interesting pages
5. **Use history** - ++backspace++ is your friend
