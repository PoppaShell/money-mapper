# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dependency validation to setup wizard and improved error messages ([#22](https://github.com/PoppaShell/money-mapper/issues/22))
  - Setup wizard now checks dependencies BEFORE other setup steps
  - Clear error messages when dependencies are missing (toml, pandas, pypdf)
  - Option to continue setup despite missing dependencies (not recommended)
  - New check_dependencies() and format_dependency_status() utility functions in utils.py
  - New check-deps CLI command to verify all required packages
  - Improved import error messages with installation instructions for toml and pypdf
  - Verified with comprehensive test suite (13/13 tests passed)
- Comprehensive development workflow documentation in docs/ directory ([#26](https://github.com/PoppaShell/money-mapper/issues/26))
  - docs/DEVELOPMENT.md with complete workflow guide emphasizing testing-first approach
  - docs/RELEASE_NOTES_TEMPLATE.md for standardized releases
  - Updated README.md with Documentation section
- Additional wildcard patterns to public_mappings.toml ([#17](https://github.com/PoppaShell/money-mapper/issues/17))
  - 35+ wildcard patterns for national chains (McDonald's, Taco Bell, Walmart, etc.)
  - Consolidated duplicate patterns (e.g., "tractor supply*" replaces 3 exact matches)
  - Improved coverage for fast food, groceries, and retail stores
- 70+ new merchant mappings to public_mappings.toml
  - Expanded fast food coverage (Cava, Crave Cookies, Dunkin, In-N-Out, NafNaf, Papa Johns, Roots Chicken Shak, Sonic, Wendys)
  - Additional grocery stores (H-E-B variants, Winn-Dixie)
  - Restaurant chains (BJs, Hideaway Pizza, IHOP, Hungry Howies, various regional chains)
  - Clothing retailers (ALTARD STATE, Kohls, Tecovas, TJ Maxx, The Childrens Place)
  - Electronics (Best Buy online, Hak5)
  - Gift shops and specialty stores
  - Bank fees (Overdraft Protection)
  - Wildcard patterns for better matching flexibility

### Fixed
- Interactive prompts now display output correctly before requesting input ([#21](https://github.com/PoppaShell/money-mapper/issues/21))
  - Added flush=True to all print() statements before input() calls across 5 files
  - Fixes output buffering issues on Windows and other environments
  - Verified with comprehensive test suite (8/8 tests passed)
  - Affects interactive_mapper.py, utils.py, setup_wizard.py, mapping_processor.py, cli.py
- Wildcard consolidation now correctly assigns scope based on source file ([#17](https://github.com/PoppaShell/money-mapper/issues/17))
  - Wildcards from public_mappings.toml correctly assigned scope="public"
  - Wildcards from private_mappings.toml correctly assigned scope="private"
  - Fixed bug where all wildcards defaulted to scope="private" regardless of source
  - Added source_file parameter to _add_wildcard_to_new_mappings() method
  - Verified with comprehensive test suite (3/3 tests passed)

### Changed
- Updated development workflow to be issue-driven with comprehensive CLAUDE.md documentation
- Enforced testing-first workflow in DEVELOPMENT.md and CLAUDE.md
  - Clear numbered steps: Code → Test → Document → Commit
  - Added warning: "NEVER update CHANGELOG, README, or commit UNTIL testing passes!"

## [0.5.0] - 2025-10-25

### Fixed
- Interactive mapping builder now displays category and subcategory lists correctly ([#20](https://github.com/PoppaShell/money-mapper/issues/20))
  - Added description fields to all 104 categories in plaid_categories.toml
  - Fixed TOML parsing to handle nested dictionary structure
  - Switched from CSV to TOML as primary taxonomy source

## [0.4.0] - 2025-10-20

### Fixed
- Credit card parser no longer creates duplicate transactions from embedded dates ([#14](https://github.com/PoppaShell/money-mapper/issues/14))
  - Removed Pattern 2 (MM/DD/YYYY) that was matching posting dates
  - Removed Pattern 3 (MM/DD fallback) that created duplicates
  - Now uses only dual-date pattern (transaction date + posting date)
- Credit card reference numbers and account suffixes excluded from descriptions ([#15](https://github.com/PoppaShell/money-mapper/issues/15))
  - 4-digit reference numbers extracted to separate field
  - Last 4 digits of card extracted to account_suffix field
  - Descriptions now clean and consistent
- Fixed invalid Pattern 2 for Bank of America credit card format ([#16](https://github.com/PoppaShell/money-mapper/issues/16))
  - Updated to match actual BoA credit card statement format
  - Added support for interest charges (no ref# or acct#)

## [0.3.0] - 2025-10-19

### Added
- Wildcard pattern support for mapping keywords ([#13](https://github.com/PoppaShell/money-mapper/issues/13))
  - Support for `*` (matches any sequence) and `?` (matches single character)
  - Exact match → wildcard → fuzzy matching priority order
  - Pattern consolidation workflow to optimize existing mappings
- Wildcard Consolidation Analyzer ([#13](https://github.com/PoppaShell/money-mapper/issues/13) Phase 2)
  - Automatic detection of consolidation opportunities (60% similarity threshold)
  - Interactive review with edit/accept/skip options
  - Shows reduction percentage and pattern coverage
  - Integrated duplicate detection and cleanup workflow

### Changed
- CLI workflow improvements for mapping management
  - Streamlined wildcard consolidation process
  - Better user prompts and progress indicators

## [0.2.0] - 2025-10-18

### Added
- Interactive Mapping Builder for uncategorized transactions ([#5](https://github.com/PoppaShell/money-mapper/issues/5))
  - Guided workflow with frequency analysis
  - Smart keyword and name suggestions
  - Numbered category menus with descriptions
  - Scope selection (public vs private)
  - Batch processing with skip/back navigation
- First-run setup wizard ([#7](https://github.com/PoppaShell/money-mapper/issues/7))
  - Creates private config files from templates
  - Interactive privacy keyword configuration
  - Optional automatic statement processing
  - Integrated mapping builder launch
- Masked account numbers in transactions ([#4](https://github.com/PoppaShell/money-mapper/issues/4))
  - Format: ****1234 (last 4 digits visible)
  - Added to checking and savings transactions
- GitHub issue and pull request templates
  - bug_report.yml
  - feature_request.yml
  - documentation.yml
  - privacy_security.yml
  - pull_request_template.md

### Changed
- Separated private configuration files ([#7](https://github.com/PoppaShell/money-mapper/issues/7))
  - public_settings.toml (git-tracked)
  - private_settings.toml (gitignored)
  - public_mappings.toml (git-tracked)
  - private_mappings.toml (gitignored)
  - Templates provided for private files
- Setup wizard now automatically runs parsing and enrichment ([#10](https://github.com/PoppaShell/money-mapper/issues/10))
  - One-session complete setup
  - Optional vs manual processing choice
- Improved input prompts with defaults and validation ([#11](https://github.com/PoppaShell/money-mapper/issues/11))
  - Default "yes" for common prompts
  - Better input validation
  - Clearer prompt formatting

### Fixed
- Credit card account number extraction from PDFs ([#9](https://github.com/PoppaShell/money-mapper/issues/9))
  - Handles bold formatting on last 4 digits
  - More robust pattern matching
- Updated all settings.toml references to new config structure ([#8](https://github.com/PoppaShell/money-mapper/issues/8))
  - Migrated to config_manager system
  - Backwards compatibility maintained
- Outdated settings.toml reference in README ([#12](https://github.com/PoppaShell/money-mapper/issues/12))

## [0.1.0] - 2025-10-17

### Added
- Dual-date support for credit card transactions ([#2](https://github.com/PoppaShell/money-mapper/issues/2))
  - transaction_date: When purchase was made
  - posting_date: When transaction posted to account
  - Handles cross-year statements (Dec 2024 → Jan 2025)
  - Maintains backwards compatibility with date field
- Comprehensive privacy redaction system ([#1](https://github.com/PoppaShell/money-mapper/issues/1))
  - Fuzzy keyword matching (85% threshold)
  - Regex pattern matching for structured data
  - Supports names, employers, locations, custom keywords
  - Automatic redaction of account numbers, PII, reference numbers

### Fixed
- Privacy redaction now handles multiple keywords in same transaction ([#1](https://github.com/PoppaShell/money-mapper/issues/1))
- Normalized excessive whitespace in transaction descriptions ([#3](https://github.com/PoppaShell/money-mapper/issues/3))
  - Multiple spaces → single space
  - Cleaner transaction descriptions

### Changed
- Removed processing_timestamp fields (date_processed, time_processed)
  - Simplified transaction format
  - Focus on transaction data only

## [0.0.1] - 2025-10-16

### Added
- Initial release
- PDF bank statement parsing (Bank of America support)
  - Checking account transactions
  - Savings account transactions
  - Credit card transactions
- Transaction enrichment with Plaid PFC taxonomy
  - 16 PRIMARY categories
  - 104 DETAILED subcategories
- Merchant mapping system
  - Custom merchant mappings
  - Fuzzy matching (70% threshold)
  - Priority: custom → plaid → fuzzy
- Privacy features
  - Account number redaction
  - Configurable keyword redaction
- CLI interface
  - Interactive menu mode
  - Command-line mode (parse, enrich, pipeline, analyze)
  - Debug mode support
- Configuration system
  - TOML-based configuration
  - Merchant mappings
  - Statement parsing patterns
- Progress tracking
  - Visual progress indicators
  - Status messages
- JSON output format
  - Raw transactions
  - Enriched transactions
  - Analysis results

[Unreleased]: https://github.com/PoppaShell/money-mapper/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/PoppaShell/money-mapper/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/PoppaShell/money-mapper/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/PoppaShell/money-mapper/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/PoppaShell/money-mapper/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/PoppaShell/money-mapper/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/PoppaShell/money-mapper/releases/tag/v0.0.1
