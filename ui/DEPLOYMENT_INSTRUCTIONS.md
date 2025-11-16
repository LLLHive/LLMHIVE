# V0 Frontend Deployment Instructions

## Prerequisites

1. **Download v0 code:**
   - In v0, click the three dots (⋮) in top right
   - Select "Download ZIP"
   - Extract to a location (e.g., `~/Downloads/llm-hive-project`)

2. **Clone LLMHIVE repository (if not already):**
   \`\`\`bash
   cd ~/Projects  # or your preferred location
   git clone https://github.com/LLLHive/LLMHIVE.git
   cd LLMHIVE
   \`\`\`

## Deployment Steps

### Step 1: Configure the Script

1. Open `scripts/deploy-v0-frontend.sh` in an editor
2. Update these two paths at the top:
   \`\`\`bash
   V0_SOURCE_PATH="${HOME}/Downloads/llm-hive-project"  # Your v0 extracted folder
   LLMHIVE_REPO_PATH="${HOME}/Projects/LLMHIVE"         # Your LLMHIVE repo location
   \`\`\`

### Step 2: Make Scripts Executable

\`\`\`bash
cd ~/Projects/LLMHIVE  # Navigate to your repo
chmod +x scripts/deploy-v0-frontend.sh
chmod +x scripts/rollback-frontend.sh
\`\`\`

### Step 3: Run Deployment Script

\`\`\`bash
./scripts/deploy-v0-frontend.sh
\`\`\`

The script will:
- ✓ Validate all paths exist
- ✓ Create timestamped backup of existing /ui folder
- ✓ Clear old /ui contents
- ✓ Copy new v0 code to /ui
- ✓ Verify structure
- ✓ Show git status

### Step 4: Review Changes

\`\`\`bash
# Check what changed
git status

# Review specific files if needed
git diff ui/components/sidebar.tsx
git diff ui/components/chat-header.tsx
\`\`\`

### Step 5: Test Locally (Optional but Recommended)

\`\`\`bash
cd ui
npm install  # or pnpm install
npm run dev
\`\`\`

Open http://localhost:3000 to verify everything works.

### Step 6: Commit and Push

\`\`\`bash
cd ..  # Back to repo root
git add .
git commit -m "Update UI with improved v0 frontend - enhanced design and functionality"
git push origin main
\`\`\`

### Step 7: Verify Deployment

Vercel will auto-deploy (if connected to GitHub):
1. Go to Vercel dashboard
2. Wait for deployment to complete (~2-3 minutes)
3. Check your live site: https://llmhive.vercel.app

## If Problems Occur - ROLLBACK

### Quick Rollback

\`\`\`bash
./scripts/rollback-frontend.sh
git add .
git commit -m "Rollback UI to previous version"
git push origin main
\`\`\`

### Manual Rollback

\`\`\`bash
# Remove new ui folder
rm -rf ui

# Restore from backup (use the backup folder name shown in deployment output)
mv ui_backup_20250115_183000 ui  # Replace with your actual backup folder name

# Commit rollback
git add .
git commit -m "Rollback UI to previous version"
git push origin main
\`\`\`

## Vercel Settings Checklist

Ensure these settings in Vercel → Settings → Build and Deployment:

- **Root Directory:** `ui`
- **Framework Preset:** Next.js
- **Build Command:** `npm run build` (or leave default)
- **Output Directory:** `.next` (or leave default)
- **Install Command:** `npm install` (or `pnpm install` if using pnpm)
- **Node.js Version:** 18.x or 20.x

## Troubleshooting

### Error: "V0 source path not found"
- Update `V0_SOURCE_PATH` in the script to match where you extracted the v0 ZIP

### Error: "LLMHIVE repository not found"
- Update `LLMHIVE_REPO_PATH` to match where you cloned the repository

### Deployment succeeds but site has errors
- Check browser console for errors
- Check Vercel deployment logs
- Run rollback script if needed

### Need to try again
- Run rollback script
- Fix any issues
- Run deployment script again

## What Gets Backed Up

The script creates a timestamped backup folder like:
\`\`\`
LLMHIVE/ui_backup_20250115_183000/
\`\`\`

This contains your entire old /ui folder and can be used for rollback.

## Safety Features

1. **Automatic Backup:** Old /ui folder is backed up before any changes
2. **Validation:** Script checks all paths exist before proceeding
3. **Verification:** Confirms required files/folders are present after copy
4. **Easy Rollback:** Single command to restore previous version
5. **Non-Destructive:** Backend code untouched (app/, llmhive/, Programing/ folders safe)
6. **Review Before Push:** You see git changes before committing

## Questions?

If you encounter any issues:
1. Check the backup folder exists: `ls -la ui_backup_*`
2. Review git status: `git status`
3. Run rollback if needed: `./scripts/rollback-frontend.sh`
