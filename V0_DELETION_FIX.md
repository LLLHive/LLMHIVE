# Permanent Fix for V0/Vercel File Deletions

## Problem

Every time you publish changes from Vercel V0, critical backend files get deleted:
- `cloudbuild.yaml` - Required for Google Cloud Build triggers
- `Dockerfile` - Required for building the Docker image
- `llmhive/requirements.txt` - Required for Python dependencies
- `llmhive/src/llmhive/app/main.py` - Required for FastAPI application entry point

## Root Cause

V0/Vercel deployments are likely:
- Force pushing changes that overwrite the repository
- Only including frontend files in the deployment
- Not preserving backend infrastructure files

## Permanent Solution Implemented

### 1. Auto-Restore GitHub Actions Workflow

Created `.github/workflows/auto-restore-critical-files.yaml` that:
- ✅ Runs on every push to `main` branch
- ✅ Checks if critical files exist
- ✅ Automatically restores them from git history if missing
- ✅ Commits and pushes the restored files
- ✅ Provides a summary of file status

### 2. How It Works

1. **On every push to main:**
   - Workflow checks for all critical files
   - If any are missing, restores them from known good commits
   - Commits and pushes the restored files automatically

2. **File restoration sources:**
   - `cloudbuild.yaml` → commit `896cc246`
   - `Dockerfile` → commit `3bce4a1e`
   - `llmhive/requirements.txt` → commit `3bce4a1e`
   - `llmhive/src/llmhive/app/main.py` → commit `063aeed0` (or `3bce4a1e` as fallback)

### 3. Manual Restoration (If Needed)

If files are deleted and you need to restore immediately:

```bash
# Restore all critical files
./restore-all-critical-files.sh

# Or restore individually
git checkout 896cc246 -- cloudbuild.yaml
git checkout 3bce4a1e -- Dockerfile
git checkout 3bce4a1e -- llmhive/requirements.txt
git checkout 063aeed0 -- llmhive/src/llmhive/app/main.py

git add cloudbuild.yaml Dockerfile llmhive/requirements.txt llmhive/src/llmhive/app/main.py
git commit -m "Restore critical files"
git push
```

## What Happens Now

1. **V0 publishes changes** → Files might get deleted
2. **GitHub Actions workflow runs** → Detects missing files
3. **Files are automatically restored** → From git history
4. **Restored files are committed** → Back in repository
5. **Cloud Build works** → All files present

## Verification

To verify the workflow is working:

1. Check GitHub Actions: https://github.com/LLLHive/LLMHIVE/actions
2. Look for "Auto-Restore Critical Files" workflow
3. Check the summary for file status

## Files Protected

- ✅ `cloudbuild.yaml` - Cloud Build configuration
- ✅ `Dockerfile` - Docker image build instructions
- ✅ `llmhive/requirements.txt` - Python dependencies
- ✅ `llmhive/src/llmhive/app/main.py` - FastAPI entry point

## Status

✅ **Auto-restore workflow is active**
✅ **Files are restored and committed**
✅ **Workflow will run on every push**

The system will now automatically restore these files if V0 deletes them!

