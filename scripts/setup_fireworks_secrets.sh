#!/usr/bin/env bash
# Upload Fireworks model catalog to GCP Secret Manager.
# API key: create separately as fireworks-key (Cloud Run env FIREWORKS_KEY or FIREWORKS_API_KEY).
#
# Usage:
#   ./scripts/setup_fireworks_secrets.sh

set -euo pipefail

PROJECT="${PROJECT:-llmhive-orchestrator}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_FILE="${SCRIPT_DIR}/fireworks-models.json"

if [[ ! -f "${MODELS_FILE}" ]]; then
  echo "Missing ${MODELS_FILE}"
  exit 1
fi

if gcloud secrets describe fireworks-models --project="${PROJECT}" &>/dev/null; then
  gcloud secrets versions add fireworks-models \
    --project="${PROJECT}" \
    --data-file="${MODELS_FILE}"
  echo "Updated secret: fireworks-models"
else
  gcloud secrets create fireworks-models \
    --project="${PROJECT}" \
    --replication-policy=automatic \
    --data-file="${MODELS_FILE}"
  echo "Created secret: fireworks-models"
fi

echo ""
echo "Mount on Cloud Run (if not already):"
echo "  FIREWORKS_KEY=fireworks-key:latest"
echo "  FIREWORKS_MODELS=fireworks-models:latest"
