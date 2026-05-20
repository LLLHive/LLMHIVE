#!/usr/bin/env bash
# Upload Hyperbolic model catalog to GCP Secret Manager.
# API key: Hyperbolic-key (Cloud Run env HYPERBOLIC_KEY or HYPERBOLIC_API_KEY).
#
# Usage:
#   ./scripts/setup_hyperbolic_secrets.sh

set -euo pipefail

PROJECT="${PROJECT:-llmhive-orchestrator}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_FILE="${SCRIPT_DIR}/hyperbolic-models.json"

if [[ ! -f "${MODELS_FILE}" ]]; then
  echo "Missing ${MODELS_FILE}"
  exit 1
fi

printf '%s' 'https://api.hyperbolic.xyz/v1' | \
  gcloud secrets create hyperbolic-base-url --project="${PROJECT}" --replication-policy=automatic --data-file=- 2>/dev/null || \
  printf '%s' 'https://api.hyperbolic.xyz/v1' | \
  gcloud secrets versions add hyperbolic-base-url --project="${PROJECT}" --data-file=-

if gcloud secrets describe hyperbolic-models --project="${PROJECT}" &>/dev/null; then
  gcloud secrets versions add hyperbolic-models \
    --project="${PROJECT}" \
    --data-file="${MODELS_FILE}"
  echo "Updated secret: hyperbolic-models"
else
  gcloud secrets create hyperbolic-models \
    --project="${PROJECT}" \
    --replication-policy=automatic \
    --data-file="${MODELS_FILE}"
  echo "Created secret: hyperbolic-models"
fi

echo "Done. Mount on Cloud Run:"
echo "  HYPERBOLIC_KEY=Hyperbolic-key:latest"
echo "  HYPERBOLIC_MODELS=hyperbolic-models:latest"
echo "  HYPERBOLIC_BASE_URL=hyperbolic-base-url:latest"
