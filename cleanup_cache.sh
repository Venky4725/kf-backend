#!/bin/bash
# Cleanup script to remove Python cache files and directories

echo "============================================================"
echo "Cleaning up Python cache files..."
echo "============================================================"
echo ""

# Remove __pycache__ directories from git tracking
echo "Removing __pycache__ from git tracking..."
git rm -r --cached app/__pycache__ 2>/dev/null
git rm -r --cached app/api/__pycache__ 2>/dev/null
git rm -r --cached app/core/__pycache__ 2>/dev/null
git rm -r --cached app/db/__pycache__ 2>/dev/null
git rm -r --cached app/models/__pycache__ 2>/dev/null
git rm -r --cached app/routers/__pycache__ 2>/dev/null
git rm -r --cached app/schemas/__pycache__ 2>/dev/null
git rm -r --cached app/services/__pycache__ 2>/dev/null
git rm -r --cached scripts/__pycache__ 2>/dev/null

# Remove __pycache__ directories from filesystem
echo "Removing __pycache__ directories from filesystem..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Remove .pyc files
echo "Removing .pyc files..."
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Remove .DS_Store files (Mac)
echo "Removing .DS_Store files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null

echo ""
echo "============================================================"
echo "✅ Cleanup complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Review changes: git status"
echo "2. Add updated .gitignore: git add .gitignore"
echo "3. Commit changes: git commit -m 'chore: update .gitignore and remove cache files'"
echo "4. Push to GitHub: git push"
echo ""
