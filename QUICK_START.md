# Git History Rewrite - Quick Start Guide

## 🎯 Goal
Replace GitHub "web-flow" committer with "Hardik Jain" in all commits.

## ⚠️ WARNING
This rewrites Git history! Create backups first!

## 📋 Quick Steps

### 1. Backup (REQUIRED!)
```bash
cd /path/to/AutoFinQA
tar -czf ../AutoFinQA-backup-$(date +%Y%m%d).tar.gz .
```

### 2. Choose Your Method

#### Method A: Python Script (Recommended - Faster)
```bash
# Install git-filter-repo
pip install git-filter-repo

# Run the script
python3 rewrite_git_history.py
```

#### Method B: Bash Script (No Installation Required)
```bash
# Run the script
./rewrite_git_history.sh
```

### 3. Review and Confirm
- Script shows affected commits
- Type `yes` to proceed
- Wait for completion

### 4. Push Changes
```bash
git push --force --all
git push --force --tags
```

### 5. Team Action Required
All team members must:
```bash
# Backup local changes first!
cd /path/to/AutoFinQA
git fetch origin
git reset --hard origin/main  # or origin/your-branch
# Or simply re-clone the repository
```

## 📝 What Changes?
- **Before**: Committer = GitHub (noreply@github.com)
- **After**: Committer = Hardik Jain (hardikjain1704@gmail.com)
- Authors remain unchanged

## 🔄 Rollback (If needed, before force-push)
```bash
git tag | grep backup-before-rewrite
git reset --hard backup-before-rewrite-YYYYMMDD-HHMMSS
```

## 📖 Full Documentation
See [GIT_HISTORY_REWRITE_GUIDE.md](./GIT_HISTORY_REWRITE_GUIDE.md) for complete details.

## ✅ Verification
After pushing, verify no web-flow commits remain:
```bash
git log --all --format="%cn <%ce>" | grep noreply
# Should return nothing
```

## 💡 Tips
- Run during off-hours
- Notify team members in advance
- Test on a clone first if unsure
- Keep backup until verified successful
