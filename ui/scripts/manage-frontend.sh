#!/bin/bash

# LLM Hive Frontend Management Script
# Usage: ./scripts/manage-frontend.sh [deploy|rollback|check]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# CONFIGURATION - UPDATE THESE PATHS
# ============================================
V0_DOWNLOAD_PATH="/Users/camilodiaz/Downloads/llm-hive-project"
LLMHIVE_REPO_PATH="/Users/camilodiaz/LLMHIVE"
BACKUP_DIR="$HOME/llmhive-backups"

# ============================================
# FUNCTIONS
# ============================================

show_usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  ./scripts/manage-frontend.sh deploy    - Deploy v0 code to /ui folder"
    echo "  ./scripts/manage-frontend.sh rollback  - Restore previous version from backup"
    echo "  ./scripts/manage-frontend.sh check     - Check configuration and paths"
    echo ""
}

check_paths() {
    echo -e "${YELLOW}Checking configuration...${NC}"
    echo ""
    
    # Check v0 download path
    if [ -d "$V0_DOWNLOAD_PATH" ]; then
        echo -e "${GREEN}✓ V0 download path found: $V0_DOWNLOAD_PATH${NC}"
    else
        echo -e "${RED}✗ V0 download path NOT found: $V0_DOWNLOAD_PATH${NC}"
        echo -e "${YELLOW}  Checking common locations...${NC}"
        
        # Try to find it
        if [ -d "$HOME/Downloads" ]; then
            echo -e "${BLUE}  Contents of ~/Downloads:${NC}"
            ls -1 "$HOME/Downloads" 2>/dev/null | grep -i "llm\|hive\|v0" || echo "    No matching folders found"
        fi
        
        if [ -d "$HOME/Desktop" ]; then
            echo -e "${BLUE}  Contents of ~/Desktop:${NC}"
            ls -1 "$HOME/Desktop" 2>/dev/null | grep -i "llm\|hive\|v0" || echo "    No matching folders found"
        fi
        
        echo ""
        echo -e "${YELLOW}  Please update V0_DOWNLOAD_PATH in this script to the correct location.${NC}"
        return 1
    fi
    
    # Check LLMHIVE repo
    if [ -d "$LLMHIVE_REPO_PATH" ]; then
        echo -e "${GREEN}✓ LLMHIVE repo found: $LLMHIVE_REPO_PATH${NC}"
    else
        echo -e "${RED}✗ LLMHIVE repo NOT found: $LLMHIVE_REPO_PATH${NC}"
        return 1
    fi
    
    # Check git
    if [ -d "$LLMHIVE_REPO_PATH/.git" ]; then
        echo -e "${GREEN}✓ Git repository detected${NC}"
    else
        echo -e "${RED}✗ Not a git repository${NC}"
        return 1
    fi
    
    # Check v0 structure
    if [ -d "$V0_DOWNLOAD_PATH/app" ] && [ -d "$V0_DOWNLOAD_PATH/components" ]; then
        echo -e "${GREEN}✓ V0 project structure verified${NC}"
    else
        echo -e "${RED}✗ V0 project structure incomplete${NC}"
        echo -e "${YELLOW}  Make sure you have extracted the complete v0 download.${NC}"
        return 1
    fi
    
    # Check backups
    if [ -d "$BACKUP_DIR" ]; then
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)
        echo -e "${GREEN}✓ Backup directory exists ($BACKUP_COUNT backup(s) available)${NC}"
    else
        echo -e "${YELLOW}  Backup directory will be created${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}Configuration check complete!${NC}"
    return 0
}

deploy() {
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/ui_backup_$TIMESTAMP"
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Deploying v0 Frontend${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Check paths first
    if ! check_paths; then
        exit 1
    fi
    
    echo ""
    echo -e "${YELLOW}Creating backup...${NC}"
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$LLMHIVE_REPO_PATH/ui" ]; then
        cp -r "$LLMHIVE_REPO_PATH/ui" "$BACKUP_PATH"
        echo -e "${GREEN}✓ Backup created: $BACKUP_PATH${NC}"
    else
        echo -e "${YELLOW}  No existing /ui folder to backup${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}Deploying new frontend...${NC}"
    
    cd "$LLMHIVE_REPO_PATH"
    
    # Remove old ui folder
    if [ -d "ui" ]; then
        rm -rf ui
    fi
    
    # Create new ui folder
    mkdir -p ui
    
    # Copy v0 files
    cp -r "$V0_DOWNLOAD_PATH"/* ui/
    cp -r "$V0_DOWNLOAD_PATH"/.[!.]* ui/ 2>/dev/null || true
    
    echo -e "${GREEN}✓ Files copied to /ui folder${NC}"
    
    # Verify
    if [ -d "ui/app" ] && [ -d "ui/components" ]; then
        echo -e "${GREEN}✓ Deployment verified${NC}"
    else
        echo -e "${RED}✗ Deployment verification failed${NC}"
        if [ -d "$BACKUP_PATH" ]; then
            echo -e "${YELLOW}Rolling back...${NC}"
            rm -rf ui
            cp -r "$BACKUP_PATH" ui
            echo -e "${GREEN}✓ Rollback complete${NC}"
        fi
        exit 1
    fi
    
    echo ""
    echo -e "${YELLOW}Git status:${NC}"
    git status --short
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Review changes: git status"
    echo "2. Add files: git add ."
    echo "3. Commit: git commit -m 'Update frontend with v0 improvements'"
    echo "4. Push: git push origin main"
    echo ""
    echo -e "${BLUE}To rollback if needed:${NC}"
    echo "./scripts/manage-frontend.sh rollback"
}

rollback() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Rolling Back Frontend${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    if [ ! -d "$BACKUP_DIR" ]; then
        echo -e "${RED}✗ No backup directory found${NC}"
        exit 1
    fi
    
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR" 2>/dev/null | head -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        echo -e "${RED}✗ No backups found${NC}"
        exit 1
    fi
    
    BACKUP_PATH="$BACKUP_DIR/$LATEST_BACKUP"
    
    echo -e "${YELLOW}Found backup: $LATEST_BACKUP${NC}"
    echo -e "${YELLOW}Path: $BACKUP_PATH${NC}"
    echo ""
    
    read -p "Continue with rollback? (y/n) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Rollback cancelled${NC}"
        exit 0
    fi
    
    cd "$LLMHIVE_REPO_PATH"
    
    echo -e "${YELLOW}Removing current /ui folder...${NC}"
    rm -rf ui
    
    echo -e "${YELLOW}Restoring backup...${NC}"
    cp -r "$BACKUP_PATH" ui
    
    echo -e "${GREEN}✓ Rollback complete${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. git add ."
    echo "2. git commit -m 'Rollback frontend'"
    echo "3. git push origin main"
}

# ============================================
# MAIN
# ============================================

if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

case "$1" in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    check)
        check_paths
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
