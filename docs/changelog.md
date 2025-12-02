# Changelog

All notable changes to Astronomo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentation site with MkDocs
- Session-based identity selection: When navigating to a site with matching identities, a modal prompts users to select which identity to use or browse anonymously. The choice persists for the session (until app quits)
- `get_all_identities_for_url()` method in `IdentityManager` to retrieve all matching identities for a URL

## [0.1.0] - 2025-01-XX

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

[Unreleased]: https://github.com/alanbato/astronomo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/alanbato/astronomo/releases/tag/v0.1.0
