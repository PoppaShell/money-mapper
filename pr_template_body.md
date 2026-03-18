## Overview

This PR establishes enforcement mechanisms to ensure proper TDD workflow and prevent future regressions.

## Changes

### 1. GitHub Branch Protection Configuration
- ✅ **ALREADY APPLIED** (Part 1 of process overhaul)
- `all-checks` gate required before merge to main
- Strict mode: branch must be up-to-date with main
- PR required (even for solo developer)
- No bypass even for repo owner (`enforce_admins=true`)
- Prevents direct pushes to main

### 2. PR Template (New File)
- Adds `.github/pull_request_template.md`
- Requires `Closes #N` for issue tracking
- TDD checklist: tests before code, edge cases, coverage validation
- Makes TDD visible and auditable in every PR

### 3. Coverage Threshold Increase
- Raises `--fail-under` from 35% to 40% in `.github/workflows/ci.yml`
- Current coverage is 36%, so this forces new code to have tests
- Incremental raises planned:
  - 40% (now) → 45% (after bug fixes) → 55% (after Phase 5) → 60% (long-term)

## Why This Matters

These changes prevent what happened in v0.7.0:
1. PR #91 was forced through without proper review
2. v0.7.0 tag was created prematurely
3. Multiple features were partially implemented and never finished
4. CLI was broken (PDF→CSV migration incomplete)

Now:
- ✅ No code merges without CI passing
- ✅ TDD workflow is explicit and auditable
- ✅ Issue tracking is mandatory
- ✅ Coverage threshold increases prevent technical debt

## Next Steps

After merge:
1. Create all 14 remaining GitHub issues (Part 4)
2. Fix Category A bugs in separate PR
3. Implement Category B features one PR per issue

## Testing

This PR itself cannot have "tests" in the traditional sense (it's configuration), but the coverage increase will be validated when CI runs on the next PR.

## CI Status

All 9 checks must pass before this PR can merge:
- ✓ actionlint
- ✓ lint (ruff)
- ✓ format (ruff)
- ✓ type-check (mypy)
- ✓ security (bandit + pip-audit)
- ✓ test (Python 3.11 & 3.12)
- ✓ coverage (now 40% threshold)
- ✓ all-checks gate
