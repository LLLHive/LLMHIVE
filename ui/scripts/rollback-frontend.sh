#!/bin/bash

#=============================================================================
# ROLLBACK SCRIPT - Use this if deployment causes issues
#=============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}==============================================================================${NC}"
echo -e "${RED}         ROLLBACK V0 FRONTEND DEPLOYMENT${NC}"
echo -e "${RED}==============================================================================${NC}"
echo ""

# Path to your LLMHIVE repository (UPDATE THIS)
LLMHIVE_REPO_PATH="${HOME}/Projects/LLMHIVE"

cd "$LLMHIVE_REPO_PATH"

# Find the most recent backup
BACKUP_DIR=$(ls -dt ui_backup_* 2>/dev/null | head -1)

if [ -z "$BACKUP_DIR" ]; then
    echo -e "${RED}ERROR: No backup found${NC}"
    echo -e "${YELLOW}Looking for folders matching: ui_backup_*${NC}"
    exit 1
fi

echo -e "${YELLOW}Found backup: $BACKUP_DIR${NC}"
echo -e "${YELLOW}Rolling back...${NC}"
echo ""

# Remove current ui folder
rm -rf ui

# Restore from backup
mv "$BACKUP_DIR" ui

echo -e "${GREEN}✓ Rollback complete!${NC}"
echo ""
echo -e "${YELLOW}To apply rollback to GitHub:${NC}"
echo -e "   ${BLUE}git add .${NC}"
echo -e "   ${BLUE}git commit -m 'Rollback UI to previous version'${NC}"
echo -e "   ${BLUE}git push origin main${NC}"
echo ""
