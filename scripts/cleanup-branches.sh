#!/bin/bash
# Cleanup script to delete merged branches locally and remotely

set -e

echo "🧹 Cleaning up merged branches..."

# Fetch latest from remote
git fetch origin

# Delete remote branches that are merged to main
echo ""
echo "📍 Remote branches (merged to main):"
remote_branches=$(git branch -r --merged origin/main | grep -v "origin/main" | grep -v "origin/HEAD" || true)

if [ -z "$remote_branches" ]; then
  echo "  ✅ No remote branches to clean"
else
  echo "$remote_branches" | while read branch; do
    branch_name=$(echo "$branch" | sed 's|origin/||')
    echo "  Deleting $branch_name..."
    git push origin --delete "$branch_name" 2>/dev/null || echo "    (Already deleted or protected)"
  done
fi

# Delete local branches that are merged to main
echo ""
echo "📍 Local branches (merged to main):"
local_branches=$(git branch --merged main | grep -v "main" | grep -v "^\*" || true)

if [ -z "$local_branches" ]; then
  echo "  ✅ No local branches to clean"
else
  echo "$local_branches" | while read branch; do
    echo "  Deleting $branch..."
    git branch -d "$branch" 2>/dev/null || echo "    (Already deleted)"
  done
fi

# Prune stale remote references
echo ""
echo "📍 Pruning stale remote references..."
git remote prune origin

echo ""
echo "✅ Cleanup complete!"
