#!/usr/bin/env python3
"""
Git History Rewrite Script using git-filter-repo

This script rewrites Git history to replace GitHub web-flow committer 
with the repository owner's name and email.

WARNING: This is a destructive operation that rewrites Git history.
Make sure you have a backup before running this script.

Requirements:
    - Python 3.6+
    - git-filter-repo (install with: pip install git-filter-repo)

Author: Hardik Jain
Repository: hardikjain1704/AutoFinQA
"""

import subprocess
import sys
import os
from datetime import datetime

# Configuration
NEW_COMMITTER_NAME = b"Hardik Jain"
NEW_COMMITTER_EMAIL = b"hardikjain1704@gmail.com"
OLD_COMMITTER_EMAIL = "noreply@github.com"

# ANSI colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_colored(message, color=NC):
    """Print colored message"""
    print(f"{color}{message}{NC}")


def run_command(command, capture_output=True):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result.stdout.strip() if capture_output else ""
    except subprocess.CalledProcessError as e:
        return None


def check_git_repo():
    """Check if we're in a git repository"""
    if not os.path.isdir('.git'):
        print_colored("Error: Not in a git repository!", RED)
        print("Please run this script from the root of your repository.")
        sys.exit(1)


def check_git_filter_repo():
    """Check if git-filter-repo is installed"""
    result = run_command("git filter-repo --version")
    if result is None:
        print_colored("Error: git-filter-repo is not installed!", RED)
        print("\nInstall it with:")
        print("  pip install git-filter-repo")
        print("  or download from: https://github.com/newren/git-filter-repo")
        sys.exit(1)
    return result


def count_webflow_commits():
    """Count commits with web-flow committer"""
    result = run_command(f"git log --all --format='%ce' | grep -c '{OLD_COMMITTER_EMAIL}' || true")
    return int(result) if result else 0


def get_sample_commits():
    """Get sample commits with web-flow committer"""
    result = run_command(
        f"git log --all --format='%h - %s (Committer: %cn <%ce>)' | grep '{OLD_COMMITTER_EMAIL}' | head -5"
    )
    return result if result else "None found"


def create_backup_tag():
    """Create a backup tag before rewriting"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_tag = f"backup-before-rewrite-{timestamp}"
    run_command(f"git tag {backup_tag}")
    return backup_tag


def get_current_branch():
    """Get current branch name"""
    return run_command("git branch --show-current")


def get_remote_url():
    """Get remote URL"""
    url = run_command("git remote get-url origin")
    return url if url else "No remote configured"


def verify_changes():
    """Verify that changes were applied correctly"""
    remaining = count_webflow_commits()
    return remaining == 0, remaining


def main():
    print_colored("=" * 50, YELLOW)
    print_colored("Git History Rewrite Script (git-filter-repo)", YELLOW)
    print_colored("=" * 50, YELLOW)
    print()

    # Check prerequisites
    check_git_repo()
    
    print("Checking for git-filter-repo installation...")
    version = check_git_filter_repo()
    print_colored(f"✓ git-filter-repo version: {version}", GREEN)
    print()

    # Get remote URL before running git-filter-repo (it will be removed)
    remote_url = get_remote_url()
    
    # Display current repository info
    print(f"Repository: {remote_url}")
    print(f"Current branch: {get_current_branch()}")
    print()

    # Check for commits with web-flow committer
    print("Checking for commits with web-flow committer...")
    webflow_count = count_webflow_commits()

    if webflow_count == 0:
        print_colored(f"No commits found with {OLD_COMMITTER_EMAIL}", GREEN)
        print("Nothing to rewrite. Exiting.")
        sys.exit(0)

    print_colored(f"Found {webflow_count} commits with '{OLD_COMMITTER_EMAIL}' as committer", YELLOW)
    print()

    # Display sample commits
    print("Sample commits that will be rewritten:")
    print(get_sample_commits())
    print()

    # Warning prompt
    print_colored("WARNING: This operation will rewrite Git history!", RED)
    print_colored("This is irreversible and will require force-push to remote.", RED)
    print()
    print("The following changes will be made:")
    print(f"  - All commits where committer email = '{OLD_COMMITTER_EMAIL}'")
    print(f"  - Will be rewritten with committer: {NEW_COMMITTER_NAME.decode()} <{NEW_COMMITTER_EMAIL.decode()}>")
    print("  - Authors will remain unchanged")
    print("  - All branches and tags will be affected")
    print()
    print_colored("Before proceeding:", YELLOW)
    print("  1. Make sure you have a backup of your repository")
    print("  2. Inform all collaborators about this change")
    print("  3. They will need to re-clone the repository after force-push")
    print()

    # Confirmation
    confirm = input("Do you want to proceed? (type 'yes' to continue): ")
    if confirm != "yes":
        print("Operation cancelled.")
        sys.exit(0)

    print()
    print("Starting history rewrite...")
    print()

    # Create a backup tag
    backup_tag = create_backup_tag()
    print(f"Creating backup tag: {backup_tag}")
    print_colored(f"Backup tag created: {backup_tag}", GREEN)
    print()

    # Perform the history rewrite using git-filter-repo
    print("Rewriting history using git-filter-repo...")
    print("This may take a while depending on repository size...")
    print()

    # Create the callback script content
    # git-filter-repo expects the script to operate on global 'commit' and 'metadata' variables
    callback_script = f"""
# Only modify committer if it matches the old email
if commit.committer_email == b'{OLD_COMMITTER_EMAIL}':
    commit.committer_name = b'{NEW_COMMITTER_NAME.decode()}'
    commit.committer_email = b'{NEW_COMMITTER_EMAIL.decode()}'
"""

    # Write callback to temporary file
    callback_file = '.git_filter_repo_callback.py'
    with open(callback_file, 'w') as f:
        f.write(callback_script)

    try:
        # Run git-filter-repo with the callback file
        result = subprocess.run(
            ['git', 'filter-repo', '--force', '--commit-callback', callback_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_colored("Error during history rewrite:", RED)
            print(result.stderr)
            sys.exit(1)

    finally:
        # Clean up callback file
        if os.path.exists(callback_file):
            os.remove(callback_file)

    print()
    print_colored("History rewrite completed!", GREEN)
    print()

    # Note: After git-filter-repo, we need to re-add the remote
    print("Re-adding remote origin...")
    if remote_url != "No remote configured":
        run_command(f"git remote add origin {remote_url}", capture_output=False)
        print_colored("✓ Remote origin re-added", GREEN)
    print()

    # Verify changes
    print("Verifying changes...")
    success, remaining = verify_changes()

    if success:
        print_colored(f"✓ Success! No commits with '{OLD_COMMITTER_EMAIL}' found.", GREEN)
    else:
        print_colored(f"⚠ Warning: Still found {remaining} commits with '{OLD_COMMITTER_EMAIL}'", YELLOW)

    print()
    print("Sample of rewritten commits:")
    sample = run_command("git log --oneline --format='%h - %s (Committer: %cn <%ce>)' -10")
    print(sample)
    print()

    # Force push instructions
    print_colored("=" * 50, YELLOW)
    print_colored("Next Steps:", YELLOW)
    print_colored("=" * 50, YELLOW)
    print()
    print("To push the rewritten history to remote, run:")
    print()
    print_colored("git push --force --all", GREEN)
    print_colored("git push --force --tags", GREEN)
    print()
    print("⚠ WARNING: This will overwrite the remote repository history!")
    print()
    print("After force-push, all collaborators must:")
    print("  1. Backup their local changes")
    print("  2. Delete their local repository")
    print("  3. Clone the repository fresh")
    print()
    print("If you want to restore the original history:")
    print(f"  git reset --hard {backup_tag}")
    print()
    print_colored("Script completed successfully!", GREEN)


if __name__ == "__main__":
    main()
