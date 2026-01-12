#!/bin/bash
# =============================================================================
# LLMHIVE Comprehensive Backup & Safeguard Script
# =============================================================================
# Run this before making major changes to create a complete backup
# Usage: ./scripts/backup-and-safeguard.sh [tag-name]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
TAG_NAME="${1:-stable-$TIMESTAMP}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}LLMHIVE Backup & Safeguard Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. Create backup directory
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✓${NC} Created backup directory: $BACKUP_DIR"

# 2. Check for uncommitted changes
echo -e "\n${YELLOW}Checking for uncommitted changes...${NC}"
if [[ -n $(git -C "$PROJECT_ROOT" status --porcelain) ]]; then
    echo -e "${YELLOW}⚠ You have uncommitted changes. Committing them first...${NC}"
    git -C "$PROJECT_ROOT" add -A
    git -C "$PROJECT_ROOT" commit -m "Pre-backup snapshot - $TIMESTAMP" || true
fi
echo -e "${GREEN}✓${NC} Working directory is clean"

# 3. Create Git tag for current state
echo -e "\n${YELLOW}Creating Git tag: $TAG_NAME${NC}"
git -C "$PROJECT_ROOT" tag -a "$TAG_NAME" -m "Stable backup before major changes - $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null || {
    echo -e "${YELLOW}Tag already exists, creating with timestamp suffix${NC}"
    TAG_NAME="$TAG_NAME-$TIMESTAMP"
    git -C "$PROJECT_ROOT" tag -a "$TAG_NAME" -m "Stable backup before major changes - $(date '+%Y-%m-%d %H:%M:%S')"
}
echo -e "${GREEN}✓${NC} Created tag: $TAG_NAME"

# 4. Push tag to remote
echo -e "\n${YELLOW}Pushing tag to remote...${NC}"
git -C "$PROJECT_ROOT" push origin "$TAG_NAME" 2>/dev/null || echo -e "${YELLOW}⚠ Could not push to remote (check network/auth)${NC}"
echo -e "${GREEN}✓${NC} Tag pushed to origin"

# 5. Backup environment files (if they exist)
echo -e "\n${YELLOW}Backing up environment files...${NC}"
ENV_BACKUP="$BACKUP_DIR/env_backup_$TIMESTAMP"
mkdir -p "$ENV_BACKUP"

# Find and copy all .env files (these are gitignored but critical)
find "$PROJECT_ROOT" -name ".env*" -type f 2>/dev/null | while read -r envfile; do
    if [[ -f "$envfile" ]]; then
        rel_path="${envfile#$PROJECT_ROOT/}"
        mkdir -p "$ENV_BACKUP/$(dirname "$rel_path")"
        cp "$envfile" "$ENV_BACKUP/$rel_path"
        echo -e "  ${GREEN}✓${NC} Backed up: $rel_path"
    fi
done

# 6. Backup database files
echo -e "\n${YELLOW}Backing up database files...${NC}"
DB_BACKUP="$BACKUP_DIR/db_backup_$TIMESTAMP"
mkdir -p "$DB_BACKUP"

if [[ -f "$PROJECT_ROOT/llmhive.db" ]]; then
    cp "$PROJECT_ROOT/llmhive.db" "$DB_BACKUP/"
    echo -e "  ${GREEN}✓${NC} Backed up: llmhive.db"
fi

find "$PROJECT_ROOT" -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" 2>/dev/null | while read -r dbfile; do
    if [[ -f "$dbfile" ]]; then
        rel_path="${dbfile#$PROJECT_ROOT/}"
        mkdir -p "$DB_BACKUP/$(dirname "$rel_path")"
        cp "$dbfile" "$DB_BACKUP/$rel_path"
        echo -e "  ${GREEN}✓${NC} Backed up: $rel_path"
    fi
done

# 7. Backup configuration files
echo -e "\n${YELLOW}Backing up configuration files...${NC}"
CONFIG_BACKUP="$BACKUP_DIR/config_backup_$TIMESTAMP"
mkdir -p "$CONFIG_BACKUP"

config_files=(
    "vercel.json"
    "cloudbuild.yaml"
    "docker-compose.yml"
    "Dockerfile"
    "Dockerfile.production"
    "next.config.mjs"
    "package.json"
    "package-lock.json"
    "tsconfig.json"
    "pytest.ini"
    "playwright.config.ts"
    "components.json"
    "postcss.config.mjs"
)

for config in "${config_files[@]}"; do
    if [[ -f "$PROJECT_ROOT/$config" ]]; then
        cp "$PROJECT_ROOT/$config" "$CONFIG_BACKUP/"
        echo -e "  ${GREEN}✓${NC} Backed up: $config"
    fi
done

# 8. Export current deployment info
echo -e "\n${YELLOW}Exporting deployment information...${NC}"
DEPLOY_INFO="$BACKUP_DIR/deployment_info_$TIMESTAMP.txt"
{
    echo "LLMHIVE Deployment Snapshot"
    echo "==========================="
    echo "Timestamp: $(date)"
    echo "Git Tag: $TAG_NAME"
    echo "Git Commit: $(git -C "$PROJECT_ROOT" rev-parse HEAD)"
    echo "Git Branch: $(git -C "$PROJECT_ROOT" branch --show-current)"
    echo ""
    echo "Node Version: $(node --version 2>/dev/null || echo 'N/A')"
    echo "NPM Version: $(npm --version 2>/dev/null || echo 'N/A')"
    echo "Python Version: $(python3 --version 2>/dev/null || echo 'N/A')"
    echo ""
    echo "Remote Origins:"
    git -C "$PROJECT_ROOT" remote -v
} > "$DEPLOY_INFO"
echo -e "${GREEN}✓${NC} Exported deployment info to: $DEPLOY_INFO"

# 9. Create a restore script
RESTORE_SCRIPT="$BACKUP_DIR/restore_$TIMESTAMP.sh"
cat > "$RESTORE_SCRIPT" << EOF
#!/bin/bash
# Restore script for backup: $TIMESTAMP
# Tag: $TAG_NAME

echo "Restoring LLMHIVE to tag: $TAG_NAME"
echo "============================================"

# Option 1: Checkout the tag (detached HEAD)
# git checkout $TAG_NAME

# Option 2: Create a new branch from the tag
# git checkout -b restore-$TAG_NAME $TAG_NAME

# Option 3: Reset main to the tag (DESTRUCTIVE - loses new commits)
# git checkout main
# git reset --hard $TAG_NAME
# git push --force origin main

echo ""
echo "Choose your restore method:"
echo "1. git checkout $TAG_NAME                    (detached HEAD, safe)"
echo "2. git checkout -b restore-branch $TAG_NAME  (new branch from backup)"
echo "3. git reset --hard $TAG_NAME                (reset main, destructive)"

# Restore environment files
echo ""
echo "To restore environment files:"
echo "cp -r $ENV_BACKUP/* $PROJECT_ROOT/"

# Restore database files
echo ""
echo "To restore database files:"
echo "cp -r $DB_BACKUP/* $PROJECT_ROOT/"
EOF
chmod +x "$RESTORE_SCRIPT"
echo -e "${GREEN}✓${NC} Created restore script: $RESTORE_SCRIPT"

# 10. Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}BACKUP COMPLETE!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Backup Location: ${YELLOW}$BACKUP_DIR${NC}"
echo -e "Git Tag: ${YELLOW}$TAG_NAME${NC}"
echo ""
echo -e "To restore to this state:"
echo -e "  ${BLUE}git checkout $TAG_NAME${NC}"
echo ""
echo -e "Backup contents:"
echo -e "  - $ENV_BACKUP/ (environment files)"
echo -e "  - $DB_BACKUP/ (database files)"
echo -e "  - $CONFIG_BACKUP/ (configuration files)"
echo -e "  - $DEPLOY_INFO"
echo -e "  - $RESTORE_SCRIPT"
echo ""
echo -e "${YELLOW}TIP: The backups directory is gitignored for security.${NC}"
echo -e "${YELLOW}Consider copying it to an external location for extra safety.${NC}"
