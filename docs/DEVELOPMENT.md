# Development Workflow Guide

This document outlines the development practices and workflows for Money Mapper.

## Table of Contents

- [Issue-Driven Development](#issue-driven-development)
- [Issue Creation Guidelines](#issue-creation-guidelines)
- [CHANGELOG Maintenance](#changelog-maintenance)
- [Commit Message Conventions](#commit-message-conventions)
- [Pre-Commit Checklist](#pre-commit-checklist)
- [Release Process](#release-process)
- [Testing Requirements](#testing-requirements)
- [Code Style Guidelines](#code-style-guidelines)

---

## Issue-Driven Development

**ALL development work must be driven by GitHub issues.** This ensures:
- Clear documentation of what changed and why
- Traceability between commits and requirements
- Organized, focused development
- Prevention of scope creep

### Workflow

1. **Before making any changes**: Create a GitHub issue
2. **Reference the issue** in commit messages
3. **Close the issue** with a resolution comment when done
4. **Update CHANGELOG.md** with the issue reference

### When to Create Issues

Create issues for:
- Bug fixes
- New features
- Enhancements
- Documentation updates
- Refactoring work
- Dependency updates

Do NOT create issues for:
- Typo fixes in comments
- Whitespace cleanup
- Minor formatting (unless part of larger work)

---

## Issue Creation Guidelines

### Issue Types

Money Mapper uses three issue templates:

#### 1. Bug Report

Use when something doesn't work as expected.

**Required sections:**
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details
- Relevant logs or screenshots

#### 2. Feature Request

Use for new functionality.

**Required sections:**
- Problem statement (what need does this address?)
- Proposed solution
- Alternatives considered
- Benefits and use cases
- Implementation considerations

#### 3. Enhancement

Use for improvements to existing functionality.

**Required sections:**
- Current behavior
- Proposed improvement
- Rationale
- Impact assessment

### Issue Best Practices

- **Be specific**: Clear, descriptive titles
- **Be detailed**: Provide context and examples
- **Link related issues**: Reference dependencies
- **Use labels**: Apply appropriate labels (bug, enhancement, documentation, etc.)
- **Estimate scope**: Note if issue is small, medium, or large effort

---

## CHANGELOG Maintenance

Money Mapper follows [Keep a Changelog](https://keepachangelog.com/) format.

### Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature description ([#N](link))

### Changed
- Enhancement description ([#N](link))

### Fixed
- Bug fix description ([#N](link))

## [X.Y.Z] - YYYY-MM-DD

### Added
- Completed feature ([#N](link))
```

### Categories

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features marked for removal
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security-related changes

### Update Process

1. **During development**: Add entries to `[Unreleased]` section
2. **Before release**: Move `[Unreleased]` entries to new version section
3. **Format**: `- Description ([#N](link-to-issue))`
4. **Order**: Most recent versions at top
5. **Links**: Include issue/PR links for all entries

### Example Entry

```markdown
## [Unreleased]

### Fixed
- Interactive mapping builder now displays category lists correctly ([#20](https://github.com/PoppaShell/money-mapper/issues/20))
```

---

## Commit Message Conventions

### Format

```
Type: Brief description (fixes #N)

Detailed explanation of what changed and why (optional).
Multiple lines are fine.

https://github.com/PoppaShell/money-mapper/issues/N
```

### Commit Types

- **Fix**: Bug fixes
- **Feature**: New features
- **Enhancement**: Improvements to existing features
- **Refactor**: Code restructuring without behavior changes
- **Docs**: Documentation changes
- **Test**: Test additions or modifications
- **Chore**: Maintenance tasks (dependencies, config, etc.)

### Examples

```
Fix: Resolve interactive mapping builder display issue (fixes #20)

Updated load_category_taxonomy() to properly parse nested TOML structure
and load category descriptions. Added test script to verify 16 primary
and 104 detailed categories load correctly.

https://github.com/PoppaShell/money-mapper/issues/20
```

```
Docs: Add CHANGELOG.md with complete project history (fixes #23)

Created CHANGELOG.md following Keep a Changelog format, documenting
all versions from v0.0.1 to v0.5.0 based on closed issues and git history.

https://github.com/PoppaShell/money-mapper/issues/23
```

### Best Practices

- **First line**: 72 characters or less
- **Issue reference**: Include `(fixes #N)` or `(refs #N)`
- **Detail level**: Match detail to change significance
- **Issue link**: Include full GitHub URL on last line
- **NO Unicode**: Windows compatibility (no emojis or special characters)

---

## Pre-Commit Checklist

Before committing code, verify:

### Code Quality
- [ ] Code follows project style guidelines
- [ ] No Unicode characters or emojis (Windows compatibility)
- [ ] No debug print statements or commented-out code
- [ ] Functions have clear, descriptive names
- [ ] Complex logic has explanatory comments

### Testing
- [ ] Changes tested manually
- [ ] Relevant test scripts run successfully
- [ ] No new errors or warnings introduced
- [ ] Edge cases considered and tested

### Documentation
- [ ] CHANGELOG.md updated in `[Unreleased]` section
- [ ] Code comments updated if behavior changed
- [ ] README.md updated if user-facing changes
- [ ] TOML config files updated if needed

### Git Workflow
- [ ] GitHub issue exists for this work
- [ ] Commit message follows conventions
- [ ] Issue referenced in commit message
- [ ] Only relevant files staged (check `git status`)
- [ ] No sensitive data in commit (API keys, credentials, etc.)

### Files to Exclude
- Do NOT commit: `config/private_settings.toml`
- Do NOT commit: `config/private_mappings.toml`
- Do NOT commit: `statements/` directory contents
- Do NOT commit: Personal development tools or configurations

---

## Release Process

### Preparation

1. **Review closed issues** since last release
2. **Update CHANGELOG.md**:
   - Move `[Unreleased]` entries to new version section
   - Add version number and date: `## [X.Y.Z] - YYYY-MM-DD`
   - Verify all issue links are correct
3. **Review git log** for any unlisted changes
4. **Test thoroughly** to ensure stability

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

### Creating a Release

1. **Draft release notes** using [RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md)
2. **Commit CHANGELOG** updates
3. **Create git tag**:
   ```bash
   git tag -a v0.X.0 -m "Version 0.X.0"
   ```
4. **Push tag**:
   ```bash
   git push origin v0.X.0
   ```
5. **Create GitHub Release**:
   ```bash
   gh release create v0.X.0 --title "Release v0.X.0" --notes-file release-notes.md
   ```
   Or use GitHub web interface

### Post-Release

1. **Verify release** appears on GitHub
2. **Update README.md** if major release
3. **Announce** in appropriate channels (if applicable)
4. **Start new `[Unreleased]`** section in CHANGELOG.md

---

## Testing Requirements

### Manual Testing

Before committing:
- Test changed functionality end-to-end
- Test with realistic data (use test CSV files)
- Test edge cases (empty files, malformed data, etc.)
- Test on Windows (primary platform)

### Test Scripts

Create test scripts for complex features:
- Test scripts should be self-contained
- Test scripts should provide clear output
- Test scripts should NOT use Unicode characters

Example:
```python
# test_feature.py
print("Testing feature...")
result = test_function()
if result:
    print("PASS: Feature works correctly")
else:
    print("FAIL: Feature has issues")
```

### Regression Testing

When fixing bugs:
- Verify the bug is actually fixed
- Ensure the fix doesn't break other features
- Test related functionality

---

## Code Style Guidelines

### Python Style

- **PEP 8 compliance**: Follow Python style guide
- **Line length**: 100 characters maximum (soft limit)
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Standard library, third-party, local (in that order)
- **Functions**: Clear names, single responsibility
- **Comments**: Explain "why", not "what"

### Special Requirements

**NO Unicode Characters**:
- Windows terminal uses cp1252 encoding
- Avoid emojis, checkmarks, special symbols
- Use standard ASCII only
- Example: Use "PASS" instead of checkmark symbol

**Configuration Files**:
- TOML format for all config files
- Clear comments explaining each setting
- Example values provided
- Nested structure for organization

**Privacy Requirements**:
- NO hardcoded sensitive data
- Use `config/private_settings.toml` for secrets
- Always check `.gitignore` before committing
- Redact sensitive data in examples

### File Organization

```
money-mapper/
├── src/                    # Source code
│   ├── cli.py             # Main entry point
│   ├── *.py               # Feature modules
├── config/                # Configuration files
│   ├── *.toml             # Public configs (versioned)
│   ├── private_*.toml     # Private configs (gitignored)
├── docs/                  # Documentation
├── statements/            # Financial data (gitignored)
├── output/                # Generated files (gitignored)
├── backups/               # Backups (gitignored)
└── README.md              # Project overview
```

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **README.md**: Project overview and usage instructions
- **CHANGELOG.md**: See what changed between versions
- **Configuration files**: Comments explain each setting

---

## Contributing

We welcome contributions! Please:

1. **Create an issue** before starting work
2. **Follow this workflow** for consistency
3. **Test thoroughly** before submitting
4. **Update documentation** as needed
5. **Keep commits focused** on single issues

Thank you for contributing to Money Mapper!
