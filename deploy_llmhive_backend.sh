#!/usr/bin/env bash
set -euo pipefail

REGION="us-east1"
DEFAULT_SERVICE_NAME="llmhive-orchestrator"

echo "=== LLMHive backend deploy helper ==="
echo
echo "This script will:"
echo "  - Build a Docker image for your backend."
echo "  - Push it to Artifact Registry in region ${REGION}."
echo "  - Deploy/Update a Cloud Run service."
echo

# Ensure gcloud is available
if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI not found. Install Google Cloud SDK and run 'gcloud init' first."
  exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: No active GCP project in gcloud config. Run 'gcloud config set project YOUR_PROJECT_ID' and try again."
  exit 1
fi

echo "Detected GCP project: ${PROJECT_ID}"
echo

# Ask for Artifact Registry repo
read -rp "Enter Artifact Registry repo name in region ${REGION} (e.g. llmhive): " AR_REPO
if [[ -z "${AR_REPO}" ]]; then
  echo "ERROR: Artifact Registry repo name cannot be empty."
  exit 1
fi

# Optional: verify repo exists
if ! gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" >/dev/null 2>&1; then
  echo "WARNING: Artifact Registry repo '${AR_REPO}' not found in region ${REGION}."
  echo "If this is wrong, press Ctrl+C, create the repo, then re-run:"
  echo "  gcloud artifacts repositories create ${AR_REPO} --repository-format=docker --location=${REGION}"
  read -rp "Continue anyway? (y/N) " cont_repo
  if [[ "${cont_repo}" != "y" && "${cont_repo}" != "Y" ]]; then
    echo "Aborting."
    exit 1
  fi
fi

# Ask for Cloud Run service name (default from our history)
read -rp "Cloud Run service name [${DEFAULT_SERVICE_NAME}]: " SERVICE_NAME
SERVICE_NAME=${SERVICE_NAME:-$DEFAULT_SERVICE_NAME}

# Optional: VPC connector
read -rp "If you use a VPC connector, enter its name (or leave blank to skip): " VPC_CONNECTOR
if [[ -n "${VPC_CONNECTOR}" ]]; then
  if ! gcloud compute networks vpc-access connectors describe "${VPC_CONNECTOR}" --region="${REGION}" >/dev/null 2>&1; then
    echo "WARNING: VPC connector '${VPC_CONNECTOR}' not found in region ${REGION}."
    read -rp "Continue without VPC connector? (y/N) " cont_vpc
    if [[ "${cont_vpc}" != "y" && "${cont_vpc}" != "Y" ]]; then
      echo "Aborting."
      exit 1
    fi
    VPC_CONNECTOR=""
  fi
fi

# Optional: Secret for DATABASE_URL
read -rp "If you have a Secret Manager secret for DATABASE_URL, enter its name (or leave blank to skip): " DB_SECRET
if [[ -n "${DB_SECRET}" ]]; then
  if ! gcloud secrets describe "${DB_SECRET}" >/dev/null 2>&1; then
    echo "WARNING: Secret '${DB_SECRET}' not found."
    read -rp "Continue without setting DATABASE_URL from secret? (y/N) " cont_sec
    if [[ "${cont_sec}" != "y" && "${cont_sec}" != "Y" ]]; then
      echo "Aborting."
      exit 1
    fi
    DB_SECRET=""
  fi
fi

# Ensure Docker is available
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not installed or not in PATH. Install Docker Desktop and try again."
  exit 1
fi

# Ensure Dockerfile exists in current directory
if [[ ! -f "Dockerfile" ]]; then
  echo "ERROR: Dockerfile not found in current directory."
  echo "Run this script from the backend project root where your Dockerfile lives."
  exit 1
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/llmhive_fastapi:${TIMESTAMP}"

echo
echo "Plan:"
echo "  Project:      ${PROJECT_ID}"
echo "  Region:       ${REGION}"
echo "  Repo:         ${AR_REPO}"
echo "  Image tag:    ${IMAGE_TAG}"
echo "  Cloud Run svc:${SERVICE_NAME}"
[[ -n "${VPC_CONNECTOR}" ]] && echo "  VPC connector:${VPC_CONNECTOR}" || echo "  VPC connector: (none)"
[[ -n "${DB_SECRET}" ]] && echo "  DB secret:    ${DB_SECRET} -> env DATABASE_URL" || echo "  DB secret:    (none)"

echo
read -rp "Proceed with build, push, and deploy? (y/N) " confirm
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
  echo "Aborting."
  exit 0
fi

echo
echo "==> Configuring Docker auth for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev"

echo
echo "==> Building Docker image..."
docker build -t "${IMAGE_TAG}" .

echo
echo "==> Pushing image to Artifact Registry..."
docker push "${IMAGE_TAG}"

echo
echo "==> Deploying to Cloud Run..."
DEPLOY_ARGS=(
  run deploy "${SERVICE_NAME}"
  --image "${IMAGE_TAG}"
  --region "${REGION}"
  --platform managed
  --allow-unauthenticated
  --service-account "llmhive-orchestrator@llmhive-orchestrator.iam.gserviceaccount.com"
)

if [[ -n "${VPC_CONNECTOR}" ]]; then
  DEPLOY_ARGS+=(--vpc-connector "${VPC_CONNECTOR}")
fi

if [[ -n "${DB_SECRET}" ]]; then
  DEPLOY_ARGS+=(--set-secrets "DATABASE_URL=${DB_SECRET}:latest")
fi

gcloud "${DEPLOY_ARGS[@]}"

echo
echo "✅ Deployment finished."
echo "Check Cloud Run service '${SERVICE_NAME}' in region ${REGION} to confirm it's healthy."
