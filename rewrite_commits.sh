#!/bin/bash

# Script to rewrite all commit history to attribute commits to Hardik Jain
# This script uses git filter-branch to rewrite author and committer information
# 
# NOTE: git filter-branch is considered deprecated but is used here because:
# - It's available in all Git installations (no additional tools needed)
# - It's suitable for small repositories like this one
# - For larger repositories or repeated use, consider git filter-repo instead

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Target author information
TARGET_NAME="Hardik Jain"
TARGET_EMAIL="hardikjain1704@gmail.com"
BACKUP_BRANCH="backup-before-rewrite"

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Git Commit History Rewriter${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository!${NC}"
    exit 1
fi

# Warn the user about the operation
echo -e "${YELLOW}WARNING: This script will rewrite the entire commit history!${NC}"
echo -e "${YELLOW}All commits will be attributed to:${NC}"
echo -e "  Name: ${TARGET_NAME}"
echo -e "  Email: ${TARGET_EMAIL}"
echo ""
echo -e "${YELLOW}This operation cannot be easily undone!${NC}"
echo ""

# Ask for confirmation
read -p "Do you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${RED}Operation cancelled.${NC}"
    exit 0
fi

# Get current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}Current branch: ${CURRENT_BRANCH}${NC}"
echo ""

# Create backup branch
echo -e "${GREEN}Step 1: Creating backup branch '${BACKUP_BRANCH}'...${NC}"
if git show-ref --verify --quiet refs/heads/${BACKUP_BRANCH}; then
    echo -e "${YELLOW}Backup branch already exists. Deleting old backup...${NC}"
    git branch -D ${BACKUP_BRANCH}
fi
git branch ${BACKUP_BRANCH}
echo -e "${GREEN}✓ Backup branch created successfully${NC}"
echo ""

# Perform the rewrite
echo -e "${GREEN}Step 2: Rewriting commit history...${NC}"
echo -e "${YELLOW}This may take a while depending on repository size...${NC}"
echo ""

git filter-branch -f --env-filter '
CORRECT_NAME="'"${TARGET_NAME}"'"
CORRECT_EMAIL="'"${TARGET_EMAIL}"'"

export GIT_AUTHOR_NAME="$CORRECT_NAME"
export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
export GIT_COMMITTER_NAME="$CORRECT_NAME"
export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
' --tag-name-filter cat -- --branches --tags

echo ""
echo -e "${GREEN}✓ Commit history rewritten successfully${NC}"
echo ""

# Clean up backup refs created by filter-branch
echo -e "${GREEN}Step 3: Cleaning up...${NC}"
REFS_TO_DELETE=$(git for-each-ref --format="%(refname)" refs/original/ 2>/dev/null || true)
if [ -n "$REFS_TO_DELETE" ]; then
    echo "$REFS_TO_DELETE" | xargs -n 1 git update-ref -d
    echo -e "${GREEN}✓ Cleanup complete${NC}"
else
    echo -e "${GREEN}✓ No cleanup needed${NC}"
fi
echo ""

# Display summary
echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Rewrite Complete!${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "1. Verify the changes with: ${GREEN}git log --all --format='%an <%ae> | %cn <%ce> | %s'${NC}"
echo -e "2. Force push to remote: ${GREEN}git push --force --all origin${NC}"
echo -e "3. Force push tags (if any): ${GREEN}git push --force --tags origin${NC}"
echo ""
echo -e "${YELLOW}If something went wrong, restore from backup:${NC}"
echo -e "  ${GREEN}git reset --hard ${BACKUP_BRANCH}${NC}"
echo ""
echo -e "${RED}IMPORTANT: Force pushing will rewrite history on the remote!${NC}"
echo -e "${RED}All collaborators will need to re-clone the repository.${NC}"
echo ""
