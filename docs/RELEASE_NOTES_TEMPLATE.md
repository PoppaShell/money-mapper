# Release v[VERSION] - [DATE]

## Overview

[Brief 1-2 sentence summary of this release]

## Highlights

[2-3 most important changes in user-friendly language]

## Changes

### Added
- New feature 1 ([#N](link-to-issue))
- New feature 2 ([#N](link-to-issue))

### Changed
- Enhancement 1 ([#N](link-to-issue))
- Enhancement 2 ([#N](link-to-issue))

### Fixed
- Bug fix 1 ([#N](link-to-issue))
- Bug fix 2 ([#N](link-to-issue))

### Deprecated
- Feature scheduled for removal ([#N](link-to-issue))

### Removed
- Removed feature ([#N](link-to-issue))

### Security
- Security fix ([#N](link-to-issue))

## Breaking Changes

[If any, with migration instructions]

[If none: "No breaking changes in this release."]

## Upgrade Instructions

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## Known Issues

[Link to open issues if relevant]

[If none: "No known issues."]

## Full Changelog

See [CHANGELOG.md](https://github.com/PoppaShell/money-mapper/blob/main/CHANGELOG.md) for complete details.

---

## Example Release Notes

# Release v0.5.0 - October 25, 2025

## Overview

This release fixes critical bugs in the interactive mapping builder and wildcard consolidation workflows, and introduces comprehensive project documentation.

## Highlights

- Interactive mapping builder now displays category and subcategory menus correctly
- Wildcard patterns now preserve correct scope (public vs private)
- Complete CHANGELOG.md covering project history from v0.0.1

## Changes

### Fixed
- Interactive mapping builder category lists not displaying ([#20](https://github.com/PoppaShell/money-mapper/issues/20))
- Wildcard consolidation incorrect scope assignment ([#17](https://github.com/PoppaShell/money-mapper/issues/17))

### Added
- CHANGELOG.md with complete project history ([#23](https://github.com/PoppaShell/money-mapper/issues/23))

### Changed
- Improved .gitignore organization ([#24](https://github.com/PoppaShell/money-mapper/issues/24))

## Breaking Changes

No breaking changes in this release.

## Upgrade Instructions

```bash
git pull origin main
```

## Known Issues

- Interactive prompts may not display output due to buffering on Windows ([#21](https://github.com/PoppaShell/money-mapper/issues/21))
- Setup wizard missing dependency validation ([#22](https://github.com/PoppaShell/money-mapper/issues/22))

See all open issues: https://github.com/PoppaShell/money-mapper/issues

## Full Changelog

See [CHANGELOG.md](https://github.com/PoppaShell/money-mapper/blob/main/CHANGELOG.md) for complete details.
