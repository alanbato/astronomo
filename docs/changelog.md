# Changelog

All notable changes to Astronomo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Quick navigation modal (Ctrl+K): Keyboard-driven fuzzy finder for quickly jumping to bookmarks and history entries
- `get_all_entries()` method in `HistoryManager` to retrieve all history entries
- Identity prompt behavior setting: control when the identity selection modal appears via Settings > Browsing. Options are "Every time" (always prompt), "When ambiguous" (auto-select if one match, prompt if multiple), and "Remember choice" (never prompt, reuse previous selection). Session identity choices are now persisted to disk and restored on app restart
- Emoji display mode setting: toggle between showing Unicode emoji or text descriptions (e.g., `(grinning face)`) in Settings > Appearance
- Max content width setting: limit text content to a configurable width (default 80 characters) with automatic centering. Preformatted blocks and code are excluded from the limit. Set to 0 to disable
- Settings button (cog icon) in the navigation bar for quick access to settings
- Folder color customization: set custom background colors for bookmark folders via the Edit Folder dialog
- Color picker with 12 preset colors (6 muted, 6 pastel) and custom hex input support
- Automatic text contrast for folder names on colored backgrounds
- Bookmarks sidebar items are now clickable: clicking a bookmark opens it, clicking a folder toggles expand/collapse
- Page snapshot save feature (Ctrl+S): Save current page as a .gmi file with configurable directory
- Improved error handling for snapshot saves with user-friendly notifications
- Better hostname sanitization for snapshot filenames (prevents filesystem issues)
- Import identities from Lagrange browser: Settings > Certificates now includes an "Import from Lagrange" button that discovers and imports existing Lagrange client certificates
- Import custom certificates: Settings > Certificates now includes an "Import Certificate" button to import existing certificate/key files. Supports both separate cert+key files and combined PEM files containing both certificate and private key. Includes a file browser for easy selection
- RSS/Atom feed subscription and management (Ctrl+J to open feeds screen)
- Feed folder organization for organizing subscriptions
- Read/unread tracking for feed items
- OPML import/export for feed portability (Ctrl+I/Ctrl+E in feeds screen)
- Search/filter functionality for feeds
- Feed refresh on-demand

### Changed
- All modal dialogs now use centered border titles instead of internal label titles for a cleaner, more consistent UI
- Settings screen now uses border title instead of internal header
- URL bar (Address input) now has a border title
- Feeds screen search input now has a border title
- Switched type checker from mypy to ty for faster type checking
- Refactored test suite to use shared pytest fixtures, reducing code duplication across test files
- CI workflow now only publishes to PyPI on version tags, with TestPyPI as a prerequisite step
- Feeds screen: Replaced button toolbar with keyboard bindings shown in footer for UI consistency
- Feeds screen: Fixed contrast issues by using `$surface` instead of `$primary` for header and panel titles
- Feeds screen: Ctrl+J now toggles the feeds screen (closes it when already open)
- Feeds screen: Moved search box to top of feed list column for cleaner layout
- Feeds screen: Removed redundant "Feeds" title from sidebar, now shown as border title
- Feeds screen: Added TAB to toggle focus between feed list and first feed item
- Feeds screen: Feed items now individually focusable with arrow key navigation
- Feeds screen: Panel borders highlight when focused/contains focus
- Feeds screen: Feed item timestamps now shown as human-readable relative time (e.g., "2 hours ago") in border title using `humanize` library

### Fixed
- Settings modal tab navigation no longer stops on invisible scroll containers
- Feed items panel crash when opening a feed with a description
- Feed item summaries now properly stripped of HTML tags and entities
- URL bar now updates when navigating to a page from feeds screen
- Feed item dates now correctly timezone-aware, future dates show as "today"

## [0.4.0] - 2025-12-02

### Added
- Documentation site with MkDocs
- Session-based identity selection: When navigating to a site with matching identities, a modal prompts users to select which identity to use or browse anonymously. The choice persists for the session (until app quits)
- `get_all_identities_for_url()` method in `IdentityManager` to retrieve all matching identities for a URL

### Fixed
- Home page from config is now properly loaded on startup

## [0.1.0] - 2025-01-05

### Added
- Initial release
- Interactive link navigation with keyboard and mouse
- Styled Gemtext rendering (headings, links, lists, blockquotes, preformatted)
- History navigation (back/forward) with scroll position preservation
- Bookmarks system with folder organization
- Configuration file support (`~/.config/astronomo/config.toml`)
- Interactive input support for status 10/11 responses (search, passwords)
- Client certificate/identity management
- Syntax highlighting for preformatted code blocks
- Theme support via Textual themes

[Unreleased]: https://github.com/alanbato/astronomo/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/alanbato/astronomo/compare/v0.1.0...v0.4.0
[0.1.0]: https://github.com/alanbato/astronomo/releases/tag/v0.1.0
