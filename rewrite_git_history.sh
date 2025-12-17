#!/bin/bash

# Git History Rewrite Script
# This script rewrites Git history to replace GitHub web-flow committer 
# with the repository owner's name and email.
#
# WARNING: This is a destructive operation that rewrites Git history.
# Make sure you have a backup before running this script.
#
# Author: Hardik Jain
# Repository: hardikjain1704/AutoFinQA

set -e  # Exit on error

# Configuration
NEW_COMMITTER_NAME="Hardik Jain"
NEW_COMMITTER_EMAIL="hardikjain1704@gmail.com"
OLD_COMMITTER_EMAIL="noreply@github.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Git History Rewrite Script${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo -e "${RED}Error: Not in a git repository!${NC}"
    echo "Please run this script from the root of your repository."
    exit 1
fi

# Display current repository info
echo "Repository: $(git remote get-url origin 2>/dev/null || echo 'No remote configured')"
echo "Current branch: $(git branch --show-current)"
echo ""

# Check for commits with web-flow committer
echo "Checking for commits with web-flow committer..."
WEBFLOW_COMMITS=$(git log --all --format="%H|%cn|%ce" | grep -c "$OLD_COMMITTER_EMAIL" || true)

if [ "$WEBFLOW_COMMITS" -eq 0 ]; then
    echo -e "${GREEN}No commits found with $OLD_COMMITTER_EMAIL${NC}"
    echo "Nothing to rewrite. Exiting."
    exit 0
fi

echo -e "${YELLOW}Found $WEBFLOW_COMMITS commits with '$OLD_COMMITTER_EMAIL' as committer${NC}"
echo ""

# Display sample commits
echo "Sample commits that will be rewritten:"
git log --all --format="%h - %s (Committer: %cn <%ce>)" | grep "$OLD_COMMITTER_EMAIL" | head -5
echo ""

# Warning prompt
echo -e "${RED}WARNING: This operation will rewrite Git history!${NC}"
echo -e "${RED}This is irreversible and will require force-push to remote.${NC}"
echo ""
echo "The following changes will be made:"
echo "  - All commits where committer email = '$OLD_COMMITTER_EMAIL'"
echo "  - Will be rewritten with committer: $NEW_COMMITTER_NAME <$NEW_COMMITTER_EMAIL>"
echo "  - Authors will remain unchanged"
echo "  - All branches and tags will be affected"
echo ""
echo -e "${YELLOW}Before proceeding:${NC}"
echo "  1. Make sure you have a backup of your repository"
echo "  2. Inform all collaborators about this change"
echo "  3. They will need to re-clone the repository after force-push"
echo ""

# Confirmation
read -p "Do you want to proceed? (type 'yes' to continue): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo ""
echo "Starting history rewrite..."
echo ""

# Create a backup tag
BACKUP_TAG="backup-before-rewrite-$(date +%Y%m%d-%H%M%S)"
echo "Creating backup tag: $BACKUP_TAG"
git tag "$BACKUP_TAG"
echo -e "${GREEN}Backup tag created: $BACKUP_TAG${NC}"
echo ""

# Remove any previous filter-branch backup
if [ -d .git/refs/original ]; then
    echo "Removing previous filter-branch backup..."
    rm -rf .git/refs/original
fi

# Perform the history rewrite using filter-branch
echo "Rewriting history using git filter-branch..."
echo "This may take a while depending on repository size..."
echo ""

git filter-branch --env-filter '
OLD_EMAIL="'"$OLD_COMMITTER_EMAIL"'"
NEW_NAME="'"$NEW_COMMITTER_NAME"'"
NEW_EMAIL="'"$NEW_COMMITTER_EMAIL"'"

if [ "$GIT_COMMITTER_EMAIL" = "$OLD_EMAIL" ]; then
    export GIT_COMMITTER_NAME="$NEW_NAME"
    export GIT_COMMITTER_EMAIL="$NEW_EMAIL"
fi
' --tag-name-filter cat -- --branches --tags

echo ""
echo -e "${GREEN}History rewrite completed!${NC}"
echo ""

# Verify changes
echo "Verifying changes..."
REMAINING_WEBFLOW=$(git log --all --format="%ce" | grep -c "$OLD_COMMITTER_EMAIL" || true)

if [ "$REMAINING_WEBFLOW" -eq 0 ]; then
    echo -e "${GREEN}✓ Success! No commits with '$OLD_COMMITTER_EMAIL' found.${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Still found $REMAINING_WEBFLOW commits with '$OLD_COMMITTER_EMAIL'${NC}"
fi

echo ""
echo "Sample of rewritten commits:"
git log --oneline --format="%h - %s (Committer: %cn <%ce>)" -10
echo ""

# Force push instructions
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "To push the rewritten history to remote, run:"
echo ""
echo -e "${GREEN}git push --force --all${NC}"
echo -e "${GREEN}git push --force --tags${NC}"
echo ""
echo "⚠ WARNING: This will overwrite the remote repository history!"
echo ""
echo "After force-push, all collaborators must:"
echo "  1. Backup their local changes"
echo "  2. Delete their local repository"
echo "  3. Clone the repository fresh"
echo ""
echo "If you want to restore the original history:"
echo "  git reset --hard $BACKUP_TAG"
echo ""
echo -e "${GREEN}Script completed successfully!${NC}"
