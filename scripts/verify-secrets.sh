#!/bin/bash
# =============================================================================
# Verify Secrets Configuration
# =============================================================================
# This script checks that all required secrets exist in both:
# 1. Google Cloud Secret Manager
# 2. cloudbuild.yaml (so they get deployed)
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLOUDBUILD="$PROJECT_ROOT/cloudbuild.yaml"

echo "=========================================="
echo "LLMHIVE Secrets Verification"
echo "=========================================="
echo ""

# All required secrets (Secret Manager ID -> Environment Variable)
declare -A REQUIRED_SECRETS=(
    ["openai-api-key"]="OPENAI_API_KEY"
    ["anthropic-api-key"]="ANTHROPIC_API_KEY"
    ["grok-api-key"]="GROK_API_KEY"
    ["gemini-api-key"]="GEMINI_API_KEY"
    ["deepseek-api-key"]="DEEPSEEK_API_KEY"
    ["tavily-api-key"]="TAVILY_API_KEY"
    ["pinecone-api-key"]="PINECONE_API_KEY"
    ["open-router-key"]="OPENROUTER_API_KEY"
    ["api-key"]="API_KEY"
    ["stripe-secret-key"]="STRIPE_SECRET_KEY"
    ["stripe-webhook-secret"]="STRIPE_WEBHOOK_SECRET"
    ["clerk-secret-key"]="CLERK_SECRET_KEY"
    ["stripe-price-id-basic-annual"]="STRIPE_PRICE_ID_BASIC_ANNUAL"
    ["stripe-price-id-basic-monthly"]="STRIPE_PRICE_ID_BASIC_MONTHLY"
    ["stripe-price-id-enterprise-annual"]="STRIPE_PRICE_ID_ENTERPRISE_ANNUAL"
    ["stripe-price-id-enterprise-monthly"]="STRIPE_PRICE_ID_ENTERPRISE_MONTHLY"
    ["stripe-price-id-pro-annual"]="STRIPE_PRICE_ID_PRO_ANNUAL"
    ["stripe-price-id-pro-monthly"]="STRIPE_PRICE_ID_PRO_MONTHLY"
    ["stripe-price-id-maximum-annual"]="STRIPE_PRICE_ID_MAXIMUM_ANNUAL"
    ["stripe-price-id-maximum-monthly"]="STRIPE_PRICE_ID_MAXIMUM_MONTHLY"
    ["stripe-publishable-key"]="STRIPE_PUBLISHABLE_KEY"
    ["pinecone-host-orchestrator-kb"]="PINECONE_HOST_ORCHESTRATOR_KB"
    ["pinecone-host-model-knowledge"]="PINECONE_HOST_MODEL_KNOWLEDGE"
    ["pinecone-host-memory"]="PINECONE_HOST_MEMORY"
    ["pinecone-host-rlhf-feedback"]="PINECONE_HOST_RLHF_FEEDBACK"
    ["pinecone-host-agentic-quickstart-test"]="PINECONE_HOST_AGENTIC_QUICKSTART_TEST"
)

MISSING_IN_CLOUDBUILD=()
MISSING_IN_SECRET_MANAGER=()

echo "Checking cloudbuild.yaml..."
echo ""

for secret_id in "${!REQUIRED_SECRETS[@]}"; do
    env_var="${REQUIRED_SECRETS[$secret_id]}"
    
    # Check if in cloudbuild.yaml
    if grep -q "$secret_id:latest" "$CLOUDBUILD" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $env_var → $secret_id"
    else
        echo -e "  ${RED}✗${NC} $env_var → $secret_id ${YELLOW}(missing in cloudbuild.yaml)${NC}"
        MISSING_IN_CLOUDBUILD+=("$secret_id")
    fi
done

echo ""
echo "=========================================="

# Check Secret Manager if gcloud is available
if command -v gcloud &> /dev/null; then
    echo ""
    echo "Checking Google Cloud Secret Manager..."
    echo "(This requires gcloud authentication)"
    echo ""
    
    # Get list of secrets
    SECRETS_LIST=$(gcloud secrets list --format="value(name)" 2>/dev/null | xargs -I{} basename {} || echo "")
    
    if [[ -n "$SECRETS_LIST" ]]; then
        for secret_id in "${!REQUIRED_SECRETS[@]}"; do
            if echo "$SECRETS_LIST" | grep -q "^${secret_id}$"; then
                echo -e "  ${GREEN}✓${NC} $secret_id exists in Secret Manager"
            else
                echo -e "  ${RED}✗${NC} $secret_id ${YELLOW}(not found in Secret Manager)${NC}"
                MISSING_IN_SECRET_MANAGER+=("$secret_id")
            fi
        done
    else
        echo -e "  ${YELLOW}⚠ Could not list secrets (check gcloud auth)${NC}"
    fi
    
    echo ""
    echo "=========================================="
fi

# Summary
echo ""
echo "SUMMARY"
echo "=========================================="

if [[ ${#MISSING_IN_CLOUDBUILD[@]} -eq 0 ]]; then
    echo -e "${GREEN}✓ All secrets are in cloudbuild.yaml${NC}"
else
    echo -e "${RED}✗ ${#MISSING_IN_CLOUDBUILD[@]} secrets missing from cloudbuild.yaml:${NC}"
    for secret in "${MISSING_IN_CLOUDBUILD[@]}"; do
        echo "    - $secret"
    done
    echo ""
    echo "Add them to --update-secrets in cloudbuild.yaml"
fi

if [[ ${#MISSING_IN_SECRET_MANAGER[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}✗ ${#MISSING_IN_SECRET_MANAGER[@]} secrets missing from Secret Manager:${NC}"
    for secret in "${MISSING_IN_SECRET_MANAGER[@]}"; do
        echo "    - $secret"
    done
    echo ""
    echo "Create them with:"
    echo "  gcloud secrets create <secret-id> --replication-policy=\"automatic\""
    echo "  gcloud secrets versions add <secret-id> --data-file=- <<< \"value\""
fi

echo ""
