# Safe Development Workflow for Major Changes

This document outlines the recommended workflow for making large changes to LLMHIVE without risking the production-stable codebase.

## 🎯 Strategy Overview

```
main (protected) ←── Feature branches ←── Your changes
     ↑
     └── Tagged releases (v1.0.0-stable, etc.)
```

## 📋 Pre-Development Checklist

### 1. Create a Backup (Already Done!)

Your current stable state has been tagged as `v1.0.0-stable`. To create additional backups:

```bash
./scripts/backup-and-safeguard.sh [optional-tag-name]
```

This script:
- Creates a Git tag
- Backs up environment files (`.env*`)
- Backs up database files (`*.db`)
- Backs up configuration files
- Creates a restore script

### 2. Feature Branch Workflow (Recommended)

**Never develop directly on `main`**. Instead:

```bash
# Create a feature branch for your changes
git checkout -b feature/major-frontend-changes

# Work on your changes...
# Commit frequently with descriptive messages
git add .
git commit -m "feat: description of change"

# Push your feature branch (safe - doesn't affect main)
git push origin feature/major-frontend-changes
```

### 3. Testing Before Merge

Before merging to main:

```bash
# Run frontend tests
npm run test
npm run lint
npm run build  # Ensure build succeeds

# Run backend tests
cd llmhive
pytest tests/

# Optional: Test in staging environment
vercel --prod=false  # Deploy to preview URL
```

## 🔧 Git Worktree Setup (Advanced)

Git worktree allows you to have multiple branches checked out simultaneously. This is ideal for:
- Comparing changes between branches
- Testing features without switching contexts
- Running old and new versions side-by-side

### Setting Up Worktrees

```bash
# Create a worktree for the stable version (in a separate directory)
git worktree add ../LLMHIVE-stable v1.0.0-stable

# Create a worktree for your feature branch
git worktree add ../LLMHIVE-feature feature/major-frontend-changes

# List all worktrees
git worktree list
```

Now you have:
- `/Users/camilodiaz/LLMHIVE` → main branch
- `/Users/camilodiaz/LLMHIVE-stable` → v1.0.0-stable (backup)
- `/Users/camilodiaz/LLMHIVE-feature` → Your feature branch

### Benefits of Worktrees

1. **Quick comparison**: Open both directories to compare implementations
2. **Safe fallback**: If something breaks, the stable worktree is untouched
3. **Parallel testing**: Run both versions simultaneously on different ports
4. **No context switching**: No need to stash/checkout when switching between tasks

### Cleanup Worktrees

```bash
# When done with a worktree
git worktree remove ../LLMHIVE-stable
git worktree remove ../LLMHIVE-feature

# Force remove if there are uncommitted changes
git worktree remove --force ../LLMHIVE-feature
```

## 🚀 Recommended Development Flow

### Phase 1: Preparation
```bash
# 1. Ensure you're on main and up-to-date
git checkout main
git pull origin main

# 2. Create backup tag
./scripts/backup-and-safeguard.sh pre-major-changes

# 3. Create feature branch
git checkout -b feature/your-feature-name

# 4. (Optional) Create stable worktree for reference
git worktree add ../LLMHIVE-stable v1.0.0-stable
```

### Phase 2: Development
```bash
# Work on your feature branch
# Commit frequently
git add .
git commit -m "feat: implement X"

# Push regularly to remote (backup)
git push origin feature/your-feature-name

# Pull latest main periodically and rebase
git fetch origin main
git rebase origin/main
```

### Phase 3: Testing
```bash
# Run all tests
npm run test && npm run lint && npm run build
cd llmhive && pytest tests/

# Deploy to staging/preview
vercel  # Creates preview URL

# Or test locally with production build
npm run build && npm start
```

### Phase 4: Merge (Only When Confident)
```bash
# 1. Final test
npm run test && npm run build

# 2. Merge to main
git checkout main
git pull origin main
git merge feature/your-feature-name

# 3. Push to main
git push origin main

# 4. Tag the new stable release
git tag -a v1.1.0 -m "New feature: description"
git push origin v1.1.0

# 5. Deploy to production
# (Your CI/CD should handle this, or run manually)
```

## 🔙 Rollback Procedures

### Quick Rollback (Git Revert)
```bash
# Revert the last commit (creates new commit)
git revert HEAD

# Revert multiple commits
git revert HEAD~3..HEAD
```

### Full Rollback (Reset to Tag)
```bash
# See what the tag points to
git show v1.0.0-stable

# Reset to the stable tag (DESTRUCTIVE - loses commits after tag)
git checkout main
git reset --hard v1.0.0-stable
git push --force origin main  # ⚠️ Force push required
```

### Rollback Using Worktree
```bash
# If you have a stable worktree, you can copy files from it
cp -r ../LLMHIVE-stable/app ./app
# Or selectively copy specific files
```

## 📁 What's Backed Up

| Item | Location | Notes |
|------|----------|-------|
| Code | Git tags | `v1.0.0-stable`, etc. |
| Env files | `backups/env_backup_*` | Not in Git (gitignored) |
| Database | `backups/db_backup_*` | Local SQLite files |
| Configs | `backups/config_backup_*` | vercel.json, cloudbuild.yaml, etc. |

## ⚠️ Important Notes

1. **Environment files are NOT in Git** - They're backed up locally in the `backups/` folder
2. **Copy backups externally** - Consider copying `backups/` to Dropbox/Drive for extra safety
3. **Vercel/Cloud configs** - Some settings are in the Vercel/GCP dashboards, not in code
4. **Database backups** - If using external databases (Postgres, Pinecone, etc.), back those up separately

## 🛡️ Production Deployment Safety

### Before Deploying to Production

1. ✅ All tests pass
2. ✅ Preview deployment works correctly
3. ✅ Backup tag created
4. ✅ Team has reviewed changes (if applicable)
5. ✅ Rollback procedure documented and tested

### Vercel Preview Deployments

Every push to a non-main branch creates a preview deployment:

```bash
# Push feature branch
git push origin feature/my-feature

# Vercel automatically creates:
# https://llmhive-git-feature-my-feature-yourteam.vercel.app
```

### Manual Preview Deployment

```bash
# Deploy current state to preview (not production)
vercel

# Deploy to production only when ready
vercel --prod
```

## 📞 Quick Reference Commands

```bash
# Create backup
./scripts/backup-and-safeguard.sh

# View all tags
git tag -l

# Checkout a specific tag
git checkout v1.0.0-stable

# Create feature branch
git checkout -b feature/name

# List worktrees
git worktree list

# Reset to stable (careful!)
git reset --hard v1.0.0-stable
```
