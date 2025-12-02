# Navigation

This guide covers efficient navigation techniques in Astronomo.

## Opening URLs

### Address Bar

1. Focus the address bar (click or press your focus key)
2. Type or paste a URL
3. Press ++enter++

!!! tip
    You can omit `gemini://` - Astronomo adds it automatically for bare URLs.

### From Command Line

```bash
# Open directly to a URL
astronomo gemini://example.com/

# Open to a path
astronomo gemini://example.com/page.gmi
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

## Tips for Efficient Browsing

1. **Use keyboard shortcuts** - Faster than reaching for the mouse
2. **Set a home page** - Start each session at your favorite capsule
3. **Bookmark frequently** - Press ++ctrl+d++ to save interesting pages
4. **Use history** - ++backspace++ is your friend
