# Git History Rewrite Documentation

This directory contains scripts to rewrite Git history and replace GitHub web-flow committer information with the repository owner's details.

## ⚠️ Important Warning

**This is a destructive operation that permanently rewrites Git history. Before proceeding:**

1. **Create a complete backup** of your repository
2. **Inform all collaborators** about this change
3. **Understand** that this will require force-pushing to remote
4. **All collaborators** will need to re-clone the repository after the force-push

## Problem Description

Several merge commits in the repository show:
- **Author**: Hardik Jain (hardikjain1704@gmail.com) ✓
- **Committer**: GitHub web-flow (noreply@github.com) ✗

This occurs when pull requests are merged via GitHub's web interface.

## Solution Overview

We provide two scripts to rewrite Git history:

1. **`rewrite_git_history.sh`** - Bash script using `git filter-branch`
2. **`rewrite_git_history.py`** - Python script using `git-filter-repo` (recommended)

Both scripts will:
- Replace all commits where committer email = `noreply@github.com`
- Set committer to: Hardik Jain <hardikjain1704@gmail.com>
- Preserve all commit authors (they are already correct)
- Create a backup tag before making changes

## Prerequisites

### For Bash Script (rewrite_git_history.sh)
- Git installed
- Bash shell (Linux/macOS/WSL/Git Bash on Windows)
- No additional dependencies

### For Python Script (rewrite_git_history.py) - RECOMMENDED
- Python 3.6 or higher
- git-filter-repo tool

Install git-filter-repo:
```bash
pip install git-filter-repo
```

Or download directly from: https://github.com/newren/git-filter-repo

## Usage Instructions

### Step 1: Backup Your Repository

Before running any script, create a backup:

```bash
# Clone a backup copy
cd /path/to/parent/directory
git clone --mirror https://github.com/hardikjain1704/AutoFinQA AutoFinQA-backup

# Or create a local backup
cd /path/to/AutoFinQA
tar -czf ../AutoFinQA-backup-$(date +%Y%m%d).tar.gz .
```

### Step 2: Run the Script

#### Option A: Using Python Script (Recommended)

```bash
cd /path/to/AutoFinQA
python3 rewrite_git_history.py
```

#### Option B: Using Bash Script

```bash
cd /path/to/AutoFinQA
chmod +x rewrite_git_history.sh
./rewrite_git_history.sh
```

### Step 3: Review Changes

The script will:
1. Show you how many commits will be affected
2. Display sample commits that will be rewritten
3. Ask for confirmation before proceeding
4. Create a backup tag (e.g., `backup-before-rewrite-20250101-120000`)
5. Rewrite the history
6. Verify the changes

### Step 4: Force Push to Remote

After the script completes successfully, push the rewritten history:

```bash
# Push all branches
git push --force --all

# Push all tags
git push --force --tags
```

**⚠️ WARNING**: This will overwrite the remote repository history!

### Step 5: Inform Collaborators

All collaborators must:

1. **Backup** any uncommitted local changes
2. **Delete** their local repository
3. **Clone** the repository fresh:
   ```bash
   git clone https://github.com/hardikjain1704/AutoFinQA
   ```

## Verification

After running the script and force-pushing, verify the changes:

```bash
# Check that no noreply@github.com commits remain
git log --all --format="%cn <%ce>" | grep noreply

# Should return nothing if successful

# View recent commits with committer info
git log --format="%h - %s%nAuthor: %an <%ae>%nCommitter: %cn <%ce>%n" -5
```

## Reverting Changes

If something goes wrong before force-pushing, you can revert to the backup tag:

```bash
# Find the backup tag
git tag | grep backup-before-rewrite

# Reset to the backup
git reset --hard backup-before-rewrite-YYYYMMDD-HHMMSS
```

If you've already force-pushed and need to revert:

```bash
# Use your backup
cd /path/to/AutoFinQA-backup
git push --mirror https://github.com/hardikjain1704/AutoFinQA
```

## Script Details

### What Gets Changed

The scripts identify commits where:
- Committer name = "GitHub" OR "web-flow"
- Committer email = "noreply@github.com"

And replace them with:
- Committer name = "Hardik Jain"
- Committer email = "hardikjain1704@gmail.com"

### What Stays the Same

- Commit authors (already correct)
- Commit messages
- Commit timestamps
- Commit content (code changes)
- Branch structure
- Tag information (though they get new commits)

### Affected Commits (Examples)

The following merge commits will be updated:
- `9bcc822bb4af3d6c88eeb6c4d1dcadc6bf841255` - Merge pull request #8
- `46587f0cf7c1c2ee60c1dfaf1b3a1c594a29c120` - Merge pull request #5
- `9c586883baadc173ce0eb055c4135745154abfc3` - Merge pull request #3
- `7880dfed30b09acc48dcb368290e0fed006b9ac3` - Merge pull request #2
- `450bd66ba7a6c98df529d862c4ee4c9224e09b10` - Merge pull request #1
- `6a293d085f68de5aa7b1e1535f26888a3a96e3bb` - Update main.py

## Differences Between Scripts

### git filter-branch (Bash Script)
- ✅ Built into Git, no additional installation
- ✅ Simpler, more straightforward
- ⚠️ Slower for large repositories
- ⚠️ Deprecated by Git (still works but not recommended for new uses)

### git-filter-repo (Python Script)
- ✅ Faster and more efficient
- ✅ Recommended by Git maintainers
- ✅ Better handling of edge cases
- ⚠️ Requires separate installation
- ⚠️ Removes remote after operation (script re-adds it)

## Troubleshooting

### "git filter-repo not found"
Install it with: `pip install git-filter-repo`

### "Not in a git repository"
Make sure you're running the script from the repository root directory.

### "Authentication failed" when pushing
Make sure you have proper push permissions and authentication configured:
```bash
# For HTTPS
git remote set-url origin https://github.com/hardikjain1704/AutoFinQA

# For SSH
git remote set-url origin git@github.com:hardikjain1704/AutoFinQA.git
```

### Script hangs or takes too long
This is normal for large repositories. The filter-branch process needs to rewrite every commit. Be patient, or use the Python script with git-filter-repo which is faster.

### "refusing to overwrite" error
This means the remote has been updated since your last fetch. Since you're intentionally rewriting history, you need to use `--force`:
```bash
git push --force --all
```

## Best Practices

1. **Test first**: Run the script on a test clone before applying to production
2. **Communicate**: Give team members advance notice
3. **Choose off-hours**: Run during low-activity periods
4. **Document**: Keep records of when and why this was done
5. **One-time operation**: This should only be done once; future merges should use correct settings

## Future Prevention

To avoid web-flow commits in the future, configure Git locally:

```bash
git config --global user.name "Hardik Jain"
git config --global user.email "hardikjain1704@gmail.com"
```

And prefer merging via command line rather than GitHub web interface when possible.

## Support

If you encounter issues:
1. Check this documentation
2. Review the script output for error messages
3. Verify your Git version: `git --version` (should be 2.x)
4. Ensure you have proper permissions
5. Check the backup tag was created: `git tag | grep backup`

## References

- Git filter-branch: https://git-scm.com/docs/git-filter-branch
- Git filter-repo: https://github.com/newren/git-filter-repo
- Rewriting History: https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History
