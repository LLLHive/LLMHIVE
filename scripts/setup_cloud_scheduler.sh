#!/bin/bash
# =============================================================================
# LLMHive Cloud Scheduler Setup Script
# =============================================================================
#
# This script creates Cloud Scheduler jobs for automated syncing:
# 1. Model Sync (every 6 hours) - Keeps model catalog up-to-date
# 2. Rankings Sync (weekly) - Updates category rankings from OpenRouter
# 3. Research Agent (daily) - Scans for AI developments
#
# Prerequisites:
# - gcloud CLI installed and configured
# - Cloud Scheduler API enabled
# - Service account with Cloud Run invoker permissions
#
# Usage:
#   ./scripts/setup_cloud_scheduler.sh [PROJECT_ID] [REGION]
#
# =============================================================================

set -euo pipefail

# Configuration
PROJECT_ID="${1:-$(gcloud config get-value project)}"
REGION="${2:-us-east1}"
SERVICE_NAME="llmhive-orchestrator"
SERVICE_URL="https://${SERVICE_NAME}-${PROJECT_ID}.${REGION}.run.app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LLMHive Cloud Scheduler Setup ===${NC}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service URL: ${SERVICE_URL}"
echo ""

# Check if Cloud Scheduler API is enabled
echo -e "${YELLOW}Checking Cloud Scheduler API...${NC}"
if ! gcloud services list --enabled --filter="name:cloudscheduler.googleapis.com" --project="${PROJECT_ID}" | grep -q cloudscheduler; then
    echo "Enabling Cloud Scheduler API..."
    gcloud services enable cloudscheduler.googleapis.com --project="${PROJECT_ID}"
fi
echo -e "${GREEN}✓ Cloud Scheduler API enabled${NC}"

# Get or create service account for scheduler
SA_NAME="llmhive-scheduler"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${YELLOW}Checking service account...${NC}"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "Creating service account: ${SA_NAME}"
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="LLMHive Cloud Scheduler" \
        --description="Service account for Cloud Scheduler to invoke Cloud Run" \
        --project="${PROJECT_ID}"
    
    # Grant Cloud Run invoker role
    gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/run.invoker" \
        --region="${REGION}" \
        --project="${PROJECT_ID}"
fi
echo -e "${GREEN}✓ Service account ready: ${SA_EMAIL}${NC}"

# =============================================================================
# Job 1: Model Sync (Every 6 hours)
# =============================================================================
JOB_NAME="llmhive-model-sync"
echo ""
echo -e "${YELLOW}Creating job: ${JOB_NAME} (every 6 hours)${NC}"

gcloud scheduler jobs delete "${JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || true

gcloud scheduler jobs create http "${JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --schedule="0 */6 * * *" \
    --time-zone="UTC" \
    --uri="${SERVICE_URL}/api/v1/openrouter/sync" \
    --http-method="POST" \
    --headers="Content-Type=application/json" \
    --message-body='{"dry_run": false, "enrich_endpoints": true}' \
    --oidc-service-account-email="${SA_EMAIL}" \
    --oidc-token-audience="${SERVICE_URL}" \
    --attempt-deadline="600s" \
    --description="Sync OpenRouter model catalog every 6 hours"

echo -e "${GREEN}✓ Created: ${JOB_NAME}${NC}"

# =============================================================================
# Job 2: Full Rankings Sync (Weekly - Sunday 3am UTC)
# =============================================================================
JOB_NAME="llmhive-rankings-sync-weekly"
echo ""
echo -e "${YELLOW}Creating job: ${JOB_NAME} (weekly)${NC}"

gcloud scheduler jobs delete "${JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || true

gcloud scheduler jobs create http "${JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --schedule="0 3 * * 0" \
    --time-zone="UTC" \
    --uri="${SERVICE_URL}/api/v1/openrouter/admin/run-full-sync?group=usecase&view=week&limit=10" \
    --http-method="POST" \
    --headers="Content-Type=application/json" \
    --oidc-service-account-email="${SA_EMAIL}" \
    --oidc-token-audience="${SERVICE_URL}" \
    --attempt-deadline="900s" \
    --description="Full OpenRouter rankings sync every Sunday 3am UTC"

echo -e "${GREEN}✓ Created: ${JOB_NAME}${NC}"

# =============================================================================
# Job 3: Research Agent (Daily - 6am UTC)
# =============================================================================
JOB_NAME="llmhive-research-agent"
echo ""
echo -e "${YELLOW}Creating job: ${JOB_NAME} (daily)${NC}"

gcloud scheduler jobs delete "${JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || true

gcloud scheduler jobs create http "${JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --schedule="0 6 * * *" \
    --time-zone="UTC" \
    --uri="${SERVICE_URL}/api/v1/agents/research/execute" \
    --http-method="POST" \
    --headers="Content-Type=application/json" \
    --oidc-service-account-email="${SA_EMAIL}" \
    --oidc-token-audience="${SERVICE_URL}" \
    --attempt-deadline="600s" \
    --description="Run Research Agent daily to scan for AI developments"

echo -e "${GREEN}✓ Created: ${JOB_NAME}${NC}"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Created scheduler jobs:"
gcloud scheduler jobs list --location="${REGION}" --project="${PROJECT_ID}" --filter="name~llmhive" --format="table(name,schedule,state)"

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Initialize the database:"
echo "   curl -X POST '${SERVICE_URL}/api/v1/openrouter/admin/init-db?run_sync=true'"
echo ""
echo "2. Verify jobs are running:"
echo "   gcloud scheduler jobs list --location=${REGION}"
echo ""
echo "3. Manually trigger a job (optional):"
echo "   gcloud scheduler jobs run llmhive-rankings-sync-weekly --location=${REGION}"
echo ""
echo -e "${GREEN}Done!${NC}"

