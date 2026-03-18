# Branch Cleanup Workflow

This document explains how branch cleanup is automated and configured in this repository.

## Overview

Merged branches are automatically cleaned up through multiple mechanisms:

1. **GitHub Auto-Delete** - Primary mechanism (enabled in Settings)
2. **GitHub Actions Workflow** - Weekly safety net for stragglers
3. **Manual Cleanup Script** - On-demand cleanup when needed

## 1. GitHub Auto-Delete (Primary)

### Configuration

Enable automatic deletion of head branches on merge:

1. Go to repository **Settings** → **General**
2. Under "Pull Requests" section, enable:
   - ✅ **Always suggest updating pull request branches**
   - ✅ **Automatically delete head branches**

### How It Works

When a PR is merged (either via "Merge pull request", "Squash and merge", or "Rebase and merge"):
- The head branch is automatically deleted from remote
- This is the most reliable cleanup mechanism

### Status

Check if this is enabled:
```bash
gh api repos/{owner}/{repo} --jq '.delete_branch_on_merge'
```

Should return `true`.

## 2. GitHub Actions Workflow (Weekly)

### Purpose

Catches merged branches that weren't auto-deleted (e.g., from old PRs before auto-delete was enabled).

### Configuration

File: `.github/workflows/cleanup-branches.yml`

- **Trigger**: Runs weekly on Sundays at midnight UTC
- **Manual trigger**: Can be run manually from Actions tab
- **Permissions**: Requires `contents: write` to delete branches

### How It Works

1. Fetches all branches from remote
2. Identifies branches merged to `main`
3. Deletes them from remote
4. Logs results for audit trail

### Running Manually

```bash
gh workflow run cleanup-branches.yml
```

Or via GitHub UI:
- Settings → Actions → Workflows → "Cleanup Stale Branches" → Run workflow

## 3. Manual Cleanup Script

### Purpose

On-demand cleanup when needed (e.g., cleaning up many old branches).

### Usage

```bash
# Using bash directly
bash scripts/cleanup-branches.sh

# Using poe (if installed)
poe cleanup-branches
```

### What It Does

1. Fetches latest from origin
2. Deletes remote branches merged to `main`
3. Deletes local branches merged to `main`
4. Prunes stale remote references

### Example Output

```
🧹 Cleaning up merged branches...

📍 Remote branches (merged to main):
  Deleting feature/old-feature...
  Deleting fix/old-bug...

📍 Local branches (merged to main):
  ✅ No local branches to clean

📍 Pruning stale remote references...

✅ Cleanup complete!
```

## Best Practices

### For Developers

1. **Ensure auto-delete is enabled** in Settings (check on first setup)
2. **Use "Delete branch" option** when GitHub prompts after merge
3. **Run cleanup manually** periodically:
   ```bash
   poe cleanup-branches
   ```

### For Repository Maintainers

1. **Verify auto-delete is enabled** when onboarding
2. **Monitor cleanup workflow** in Actions for failures
3. **Document this workflow** in contributor guide
4. **Review branch protection rules** to ensure they don't prevent cleanup

## Protected Branches

The cleanup scripts will **never delete**:
- The `main` branch
- `origin/main` reference
- Branches listed in branch protection rules

To verify branch protection:
```bash
gh api repos/{owner}/{repo}/branches/main/protection
```

## Troubleshooting

### Cleanup workflow fails silently

This is expected - it continues even if individual branches fail to delete (e.g., if already deleted).

Check the workflow run logs:
```bash
gh workflow view cleanup-branches.yml --json runs -q '.[0]'
```

### Branches not deleted after merge

Possible causes:
1. Auto-delete not enabled in Settings
2. Branch protection rules preventing deletion
3. Manual merge without "Delete branch" option

**Fix**: Run manual cleanup
```bash
poe cleanup-branches
```

### Local branch still exists after cleanup

Local branches only deleted if merged to local `main`. Make sure local `main` is up to date:
```bash
git fetch origin
git checkout main
git pull origin main
poe cleanup-branches
```

## Configuration Changes

### Changing Schedule

Edit `.github/workflows/cleanup-branches.yml`:

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Change this cron expression
```

Cron format: `minute hour day-of-month month day-of-week`

Examples:
- `'0 0 * * 0'` - Weekly (Sunday midnight UTC)
- `'0 0 * * *'` - Daily (midnight UTC)
- `'0 2 * * 1'` - Mondays at 2 AM UTC

### Excluding Branches

Edit `.github/workflows/cleanup-branches.yml` to add exclusions:

```yaml
# Add after "grep -v "origin/HEAD"" line
branches=$(git branch -r --merged origin/main | grep -v "origin/main" | grep -v "origin/HEAD" | grep -v "origin/keep-this-branch")
```

## Related Documentation

- [Git Workflow](./GIT_WORKFLOW.md) - PR and branching strategy
- [GitHub Actions](https://docs.github.com/en/actions) - CI/CD configuration
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches) - Protection rules
