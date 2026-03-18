# Branch Cleanup Workflow

This document explains how branch cleanup is automated and configured in this repository.

## Overview

Merged branches are cleaned up through:

1. **GitHub Auto-Delete** - Primary mechanism (enabled in Settings)
2. **Manual Cleanup Script** - On-demand cleanup when needed

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

## 2. Manual Cleanup Script

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
3. **Run cleanup manually** before starting new work:
   ```bash
   poe cleanup-branches
   ```

### For Repository Maintainers

1. **Verify auto-delete is enabled** when onboarding
2. **Document this workflow** in contributor guide
3. **Review branch protection rules** to ensure they don't prevent cleanup

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

## Customization

### Excluding Branches

Edit `scripts/cleanup-branches.sh` or `scripts/cleanup-branches.bat` to add exclusions:

For example, to exclude a branch from deletion:

```bash
# In cleanup-branches.sh, modify the grep to exclude
branches=$(git branch -r --merged origin/main | grep -v "origin/main" | grep -v "origin/HEAD" | grep -v "origin/keep-this-branch")
```

## Related Documentation

- [Git Workflow](./GIT_WORKFLOW.md) - PR and branching strategy
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches) - Protection rules
