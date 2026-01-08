#!/bin/bash
# =============================================================================
# LLMHive Backend Deployment Script
# 
# Deploys the Python backend to Google Cloud Run
# 
# Prerequisites:
# 1. gcloud CLI installed and authenticated
# 2. Docker installed (for local builds)
# 3. Required secrets configured in Secret Manager
#
# Usage:
#   ./scripts/deploy.sh                    # Deploy to production
#   ./scripts/deploy.sh --dry-run          # Show what would be deployed
#   ./scripts/deploy.sh --local            # Build and run locally
# =============================================================================

set -euo pipefail

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-llmhive-prod}"
REGION="${CLOUD_RUN_REGION:-us-east1}"
SERVICE_NAME="llmhive-orchestrator"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
DRY_RUN=false
LOCAL_MODE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --local)
            LOCAL_MODE=true
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Change to the llmhive directory
cd "$(dirname "$0")/.."

log_info "🐝 LLMHive Backend Deployment"
log_info "Project: ${PROJECT_ID}"
log_info "Region: ${REGION}"
log_info "Service: ${SERVICE_NAME}"
echo ""

# Generate build tag
BUILD_TAG=$(date +%Y%m%d%H%M%S)
FULL_IMAGE="${IMAGE_NAME}:${BUILD_TAG}"

if [ "$LOCAL_MODE" = true ]; then
    log_info "🐳 Building and running locally..."
    
    # Build the image
    docker build -t llmhive-local .
    
    # Run locally
    log_info "Starting local server on http://localhost:8080"
    docker run --rm -it \
        -p 8080:8080 \
        -e ALLOW_STUB_PROVIDER=true \
        -e LOG_LEVEL=DEBUG \
        --env-file ../.env.local 2>/dev/null || \
    docker run --rm -it \
        -p 8080:8080 \
        -e ALLOW_STUB_PROVIDER=true \
        -e LOG_LEVEL=DEBUG \
        llmhive-local
    
    exit 0
fi

if [ "$DRY_RUN" = true ]; then
    log_warn "🔍 DRY RUN MODE - No changes will be made"
    echo ""
    log_info "Would build: ${FULL_IMAGE}"
    log_info "Would deploy to: ${SERVICE_NAME} in ${REGION}"
    echo ""
    log_info "Required secrets in Secret Manager:"
    echo "  - openai-api-key"
    echo "  - anthropic-api-key"
    echo "  - grok-api-key"
    echo "  - gemini-api-key"
    echo "  - deepseek-api-key"
    echo "  - tavily-api-key"
    echo "  - pinecone-api-key"
    echo "  - api-key"
    echo "  - stripe-secret-key"
    echo "  - stripe-webhook-secret"
    echo ""
    log_info "To deploy for real, run without --dry-run"
    exit 0
fi

# Verify gcloud is authenticated
log_info "Checking gcloud authentication..."
if ! gcloud auth print-identity-token &>/dev/null; then
    log_error "Not authenticated to gcloud. Run: gcloud auth login"
    exit 1
fi
log_success "gcloud authenticated"

# Verify project exists
log_info "Checking project ${PROJECT_ID}..."
if ! gcloud projects describe "${PROJECT_ID}" &>/dev/null; then
    log_error "Project ${PROJECT_ID} not found or not accessible"
    exit 1
fi
log_success "Project accessible"

# Build the Docker image
log_info "🐳 Building Docker image..."
docker build -t "${FULL_IMAGE}" .
log_success "Image built: ${FULL_IMAGE}"

# Push to Google Container Registry
log_info "📤 Pushing image to GCR..."
docker push "${FULL_IMAGE}"
log_success "Image pushed"

# Deploy to Cloud Run
log_info "🚀 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --image="${FULL_IMAGE}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --set-env-vars="ALLOW_STUB_PROVIDER=true,LOG_LEVEL=INFO" \
    --set-secrets="OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,GROK_API_KEY=grok-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,DEEPSEEK_API_KEY=deepseek-api-key:latest,TAVILY_API_KEY=tavily-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest,API_KEY=api-key:latest,STRIPE_SECRET_KEY=stripe-secret-key:latest,STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest"

log_success "Deployment complete!"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)')

echo ""
log_success "🎉 Service deployed successfully!"
log_info "Service URL: ${SERVICE_URL}"
log_info "Health check: ${SERVICE_URL}/health"
log_info "API docs: ${SERVICE_URL}/docs"
echo ""

# Run health check
log_info "Running health check..."
sleep 5
if curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" | grep -q "200"; then
    log_success "Health check passed! ✅"
else
    log_warn "Health check returned non-200. Service may still be starting."
fi

