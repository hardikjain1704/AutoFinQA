#!/bin/bash
# Fully automatic commit history rewrite - NO confirmations needed
# This script rewrites ALL commits to: Hardik Jain <hardikjain1704@gmail.com>

set -e
export FILTER_BRANCH_SQUELCH_WARNING=1

TARGET_NAME="Hardik Jain"
TARGET_EMAIL="hardikjain1704@gmail.com"

echo "Rewriting commit history to: $TARGET_NAME <$TARGET_EMAIL>"

# Create backup
if git show-ref --quiet refs/heads/backup-before-rewrite; then
    git branch -D backup-before-rewrite
fi
git branch backup-before-rewrite
echo "✓ Backup created: backup-before-rewrite"

# Rewrite history
git filter-branch -f --env-filter '
export GIT_AUTHOR_NAME="'"${TARGET_NAME}"'"
export GIT_AUTHOR_EMAIL="'"${TARGET_EMAIL}"'"
export GIT_COMMITTER_NAME="'"${TARGET_NAME}"'"
export GIT_COMMITTER_EMAIL="'"${TARGET_EMAIL}"'"
' --tag-name-filter cat -- --branches --tags 2>/dev/null

# Cleanup
git for-each-ref --format="%(refname)" refs/original/ 2>/dev/null | xargs -r -n 1 git update-ref -d 2>/dev/null || true

echo "✓ History rewritten!"
echo "✓ All commits now show: $TARGET_NAME <$TARGET_EMAIL>"
echo ""
echo "Next: git push --force --all origin"
