# Frontend Deployment - Quick Start Guide

## One Script Does Everything

The `manage-frontend.sh` script handles deployment, rollback, and configuration checking.

## Step 1: First Time Setup

Download v0 code from the v0 interface:
1. Click three dots (⋮) in top right of v0
2. Click "Download ZIP"
3. Extract to Downloads folder

## Step 2: Check Configuration

\`\`\`bash
cd /Users/camilodiaz/LLMHIVE
chmod +x scripts/manage-frontend.sh
./scripts/manage-frontend.sh check
\`\`\`

If paths are wrong, edit `scripts/manage-frontend.sh` lines 19-21.

## Step 3: Deploy

\`\`\`bash
./scripts/manage-frontend.sh deploy
\`\`\`

This will:
- Automatically backup your current /ui folder
- Copy v0 code to /ui
- Verify the deployment
- Show git status

## Step 4: Push to GitHub

\`\`\`bash
git add .
git commit -m "Update frontend with v0 improvements"
git push origin main
\`\`\`

Vercel will automatically deploy (Root Directory = "ui")

## If Problems Occur: Rollback

\`\`\`bash
./scripts/manage-frontend.sh rollback
git add .
git commit -m "Rollback frontend"
git push origin main
\`\`\`

## Troubleshooting

**"V0 download path NOT found"**
- Run: `./scripts/manage-frontend.sh check`
- It will show what's in Downloads/Desktop
- Update the V0_DOWNLOAD_PATH in the script to match the actual folder name

**"Permission denied"**
- Run: `chmod +x scripts/manage-frontend.sh`

**"Scripts folder doesn't exist"**
- Create it: `mkdir -p scripts`
- Copy the script file from v0 download
</parameter>
