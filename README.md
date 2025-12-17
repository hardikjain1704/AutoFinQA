# AutoFinQA

Financial Question Answering System

## Git History Rewrite Tools

This repository includes tools to rewrite Git history and replace GitHub web-flow committer information with the repository owner's details.

### �� Documentation

- **[Quick Start Guide](QUICK_START.md)** - Fast setup and execution (5 minutes)
- **[Complete Guide](GIT_HISTORY_REWRITE_GUIDE.md)** - Comprehensive documentation with troubleshooting

### 🛠️ Available Scripts

1. **`rewrite_git_history.sh`** - Bash script (no installation required)
2. **`rewrite_git_history.py`** - Python script (faster, recommended)
3. **GitHub Actions Workflow** - Automated option via `.github/workflows/rewrite_git_history.yml`

### ⚡ Quick Start

```bash
# Method 1: Python (Recommended)
pip install git-filter-repo
python3 rewrite_git_history.py

# Method 2: Bash
./rewrite_git_history.sh

# Method 3: GitHub Actions
# Go to Actions tab → "Git History Rewrite" → Run workflow
```

### ⚠️ Important Notes

- **This rewrites Git history** - Create backups first!
- Requires force-push to remote repository
- All collaborators must re-clone after the change
- See documentation for detailed instructions

---

For questions or issues with the Git history rewrite, please refer to the documentation files listed above.
