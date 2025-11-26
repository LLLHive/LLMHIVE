#!/bin/bash

# LLM Hive - Deploy v0 Root to UI Folder
# Run this script in Cursor from the v0 downloaded project root

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  LLM Hive UI Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Detect current directory
CURRENT_DIR=$(pwd)
echo -e "${YELLOW}Current directory: $CURRENT_DIR${NC}"
echo ""

# Validate we're in the v0 project
if [ ! -f "package.json" ] || [ ! -d "app" ] || [ ! -d "components" ]; then
    echo -e "${RED}ERROR: This doesn't look like the v0 project directory${NC}"
    echo -e "${YELLOW}Please run this script from the extracted v0 project folder${NC}"
    echo ""
    echo "Expected structure:"
    echo "  - app/"
    echo "  - components/"
    echo "  - public/"
    echo "  - package.json"
    exit 1
fi

echo -e "${GREEN}✓ V0 project structure validated${NC}"
echo ""

# Prompt for LLMHIVE path
echo -e "${YELLOW}Enter the full path to your LLMHIVE repository:${NC}"
echo -e "${BLUE}(Default: /Users/camilodiaz/LLMHIVE)${NC}"
read -p "Path: " LLMHIVE_PATH

# Use default if empty
if [ -z "$LLMHIVE_PATH" ]; then
    LLMHIVE_PATH="/Users/camilodiaz/LLMHIVE"
fi

echo ""
echo -e "${YELLOW}Target: $LLMHIVE_PATH/ui${NC}"
echo ""

# Validate LLMHIVE path
if [ ! -d "$LLMHIVE_PATH" ]; then
    echo -e "${RED}ERROR: Directory not found: $LLMHIVE_PATH${NC}"
    exit 1
fi

if [ ! -d "$LLMHIVE_PATH/.git" ]; then
    echo -e "${RED}ERROR: Not a git repository: $LLMHIVE_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✓ LLMHIVE repository validated${NC}"
echo ""

# Create backup
BACKUP_DIR="$HOME/llmhive-backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/ui_backup_$TIMESTAMP"

if [ -d "$LLMHIVE_PATH/ui" ] && [ "$(ls -A $LLMHIVE_PATH/ui)" ]; then
    echo -e "${YELLOW}Creating backup of existing ui/ folder...${NC}"
    mkdir -p "$BACKUP_DIR"
    cp -r "$LLMHIVE_PATH/ui" "$BACKUP_PATH"
    echo -e "${GREEN}✓ Backup created: $BACKUP_PATH${NC}"
else
    echo -e "${YELLOW}No existing ui/ folder to backup${NC}"
fi
echo ""

# Confirm before proceeding
echo -e "${YELLOW}This will:${NC}"
echo "  1. Delete everything in $LLMHIVE_PATH/ui/"
echo "  2. Copy all v0 files from $CURRENT_DIR to $LLMHIVE_PATH/ui/"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi
echo ""

# Remove old ui contents
echo -e "${YELLOW}Removing old ui/ contents...${NC}"
rm -rf "$LLMHIVE_PATH/ui"
mkdir -p "$LLMHIVE_PATH/ui"
echo -e "${GREEN}✓ Cleaned${NC}"
echo ""

# Copy v0 files to ui/
echo -e "${YELLOW}Copying v0 files to ui/...${NC}"

# Copy all directories and files
cp -r "$CURRENT_DIR"/* "$LLMHIVE_PATH/ui/" 2>/dev/null || true

# Copy hidden files (like .gitignore, .env.example)
cp -r "$CURRENT_DIR"/.[!.]* "$LLMHIVE_PATH/ui/" 2>/dev/null || true

# Don't copy these unnecessary folders
rm -rf "$LLMHIVE_PATH/ui/.git" 2>/dev/null || true
rm -rf "$LLMHIVE_PATH/ui/node_modules" 2>/dev/null || true

echo -e "${GREEN}✓ Files copied${NC}"
echo ""

# Verify structure
echo -e "${YELLOW}Verifying deployment...${NC}"
if [ -d "$LLMHIVE_PATH/ui/app" ] && \
   [ -d "$LLMHIVE_PATH/ui/components" ] && \
   [ -f "$LLMHIVE_PATH/ui/package.json" ]; then
    echo -e "${GREEN}✓ Deployment successful!${NC}"
else
    echo -e "${RED}ERROR: Verification failed - required directories not found${NC}"
    
    # Offer to rollback
    if [ -d "$BACKUP_PATH" ]; then
        echo ""
        read -p "Rollback to backup? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$LLMHIVE_PATH/ui"
            cp -r "$BACKUP_PATH" "$LLMHIVE_PATH/ui"
            echo -e "${GREEN}✓ Rollback completed${NC}"
        fi
    fi
    exit 1
fi
echo ""

# Show what was copied
echo -e "${BLUE}Deployed structure:${NC}"
ls -la "$LLMHIVE_PATH/ui" | head -20
echo ""

# Git status
cd "$LLMHIVE_PATH"
echo -e "${YELLOW}Git status:${NC}"
git status --short ui/
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  cd $LLMHIVE_PATH"
echo "  git add ui/"
echo "  git status"
echo "  git commit -m 'Update UI with v0 improvements'"
echo "  git push origin main"
echo ""
echo -e "${YELLOW}Backup location: $BACKUP_PATH${NC}"
echo ""
echo -e "${BLUE}To rollback if needed:${NC}"
echo "  rm -rf $LLMHIVE_PATH/ui"
echo "  cp -r $BACKUP_PATH $LLMHIVE_PATH/ui"
echo ""
