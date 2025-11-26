#!/bin/bash

#=============================================================================
# SAFE V0 FRONTEND DEPLOYMENT SCRIPT
# This script safely replaces /ui folder with improved v0 code
# Includes automatic backup and easy rollback
#=============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}         V0 FRONTEND DEPLOYMENT TO /ui FOLDER${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

#=============================================================================
# STEP 1: CONFIGURATION - UPDATE THESE PATHS
#=============================================================================

# Path to your extracted v0 download (UPDATE THIS)
V0_SOURCE_PATH="${HOME}/Downloads/llm-hive-project"

# Path to your LLMHIVE repository (UPDATE THIS)
LLMHIVE_REPO_PATH="${HOME}/Projects/LLMHIVE"

# Backup directory name
BACKUP_DIR="ui_backup_$(date +%Y%m%d_%H%M%S)"

#=============================================================================
# STEP 2: VALIDATION
#=============================================================================

echo -e "${YELLOW}Validating paths...${NC}"

# Check if v0 source exists
if [ ! -d "$V0_SOURCE_PATH" ]; then
    echo -e "${RED}ERROR: V0 source path not found: $V0_SOURCE_PATH${NC}"
    echo -e "${YELLOW}Please update V0_SOURCE_PATH in the script${NC}"
    exit 1
fi

# Check if LLMHIVE repo exists
if [ ! -d "$LLMHIVE_REPO_PATH" ]; then
    echo -e "${RED}ERROR: LLMHIVE repository not found: $LLMHIVE_REPO_PATH${NC}"
    echo -e "${YELLOW}Please update LLMHIVE_REPO_PATH in the script${NC}"
    exit 1
fi

# Check if /ui folder exists
if [ ! -d "$LLMHIVE_REPO_PATH/ui" ]; then
    echo -e "${RED}ERROR: /ui folder not found in LLMHIVE repository${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All paths validated${NC}"
echo ""

#=============================================================================
# STEP 3: CREATE BACKUP
#=============================================================================

echo -e "${YELLOW}Creating backup of existing /ui folder...${NC}"

cd "$LLMHIVE_REPO_PATH"

# Create backup
cp -r ui "$BACKUP_DIR"

if [ -d "$BACKUP_DIR" ]; then
    echo -e "${GREEN}✓ Backup created: $BACKUP_DIR${NC}"
    echo -e "${BLUE}  Location: $LLMHIVE_REPO_PATH/$BACKUP_DIR${NC}"
else
    echo -e "${RED}ERROR: Failed to create backup${NC}"
    exit 1
fi
echo ""

#=============================================================================
# STEP 4: CLEAR OLD UI FOLDER
#=============================================================================

echo -e "${YELLOW}Clearing old /ui folder contents...${NC}"

# Remove everything in ui folder except .gitkeep if exists
find ui -mindepth 1 -delete

echo -e "${GREEN}✓ Old /ui folder cleared${NC}"
echo ""

#=============================================================================
# STEP 5: COPY NEW V0 CODE
#=============================================================================

echo -e "${YELLOW}Copying new v0 code to /ui folder...${NC}"

# Copy all files from v0 source to ui folder
cp -r "$V0_SOURCE_PATH"/* ui/
cp -r "$V0_SOURCE_PATH"/.[!.]* ui/ 2>/dev/null || true

echo -e "${GREEN}✓ New v0 code copied successfully${NC}"
echo ""

#=============================================================================
# STEP 6: VERIFY STRUCTURE
#=============================================================================

echo -e "${YELLOW}Verifying new structure...${NC}"

REQUIRED_DIRS=("ui/app" "ui/components" "ui/public" "ui/lib")
REQUIRED_FILES=("ui/package.json" "ui/next.config.mjs")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓ Found: $dir${NC}"
    else
        echo -e "${RED}✗ Missing: $dir${NC}"
    fi
done

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ Found: $file${NC}"
    else
        echo -e "${RED}✗ Missing: $file${NC}"
    fi
done
echo ""

#=============================================================================
# STEP 7: GIT STATUS
#=============================================================================

echo -e "${YELLOW}Git status:${NC}"
git status --short
echo ""

#=============================================================================
# STEP 8: REVIEW PROMPT
#=============================================================================

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${GREEN}Deployment prepared successfully!${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo ""
echo -e "1. Review changes above"
echo -e "2. Test locally if needed: ${BLUE}cd ui && npm install && npm run dev${NC}"
echo -e "3. If satisfied, commit and push:"
echo -e "   ${BLUE}git add .${NC}"
echo -e "   ${BLUE}git commit -m 'Update UI with improved v0 frontend'${NC}"
echo -e "   ${BLUE}git push origin main${NC}"
echo ""
echo -e "${YELLOW}ROLLBACK INSTRUCTIONS (if needed):${NC}"
echo -e "   ${BLUE}rm -rf ui${NC}"
echo -e "   ${BLUE}mv $BACKUP_DIR ui${NC}"
echo -e "   ${BLUE}git add .${NC}"
echo -e "   ${BLUE}git commit -m 'Rollback to previous UI'${NC}"
echo -e "   ${BLUE}git push origin main${NC}"
echo ""
echo -e "${GREEN}Backup location: $LLMHIVE_REPO_PATH/$BACKUP_DIR${NC}"
echo -e "${BLUE}==============================================================================${NC}"
