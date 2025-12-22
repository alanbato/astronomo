# Changelog

All notable changes to Astronomo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Emoji display mode setting: toggle between showing Unicode emoji or text descriptions (e.g., `(grinning face)`) in Settings > Appearance
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

### Changed
- Switched type checker from mypy to ty for faster type checking

### Fixed
- Settings modal tab navigation no longer stops on invisible scroll containers

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
