#!/usr/bin/env bash
# Upload Microsoft Foundry config to GCP Secret Manager.
#
# Usage:
#   export FOUNDRY_KEY='paste-api-key-from-foundry-overview'
#   ./scripts/setup_azure_foundry_secrets.sh
#
# Optional:
#   export FOUNDRY_URL='https://llmhive.services.ai.azure.com'
#   export PROJECT=llmhive-orchestrator

set -euo pipefail

PROJECT="${PROJECT:-llmhive-orchestrator}"
# Resource name in Azure is LLNHive → hostname llnhive (not llmhive)
FOUNDRY_URL="${FOUNDRY_URL:-https://llnhive.services.ai.azure.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENTS_FILE="${SCRIPT_DIR}/foundry-deployments.json"

if [[ ! -f "${DEPLOYMENTS_FILE}" ]]; then
  echo "Missing ${DEPLOYMENTS_FILE}"
  exit 1
fi

if [[ -z "${FOUNDRY_KEY:-}" ]]; then
  echo "Set FOUNDRY_KEY first (Overview → Endpoints and keys → API Key → Copy):"
  echo "  export FOUNDRY_KEY='your-copied-key'"
  exit 1
fi

_upsert_secret() {
  local name="$1"
  local data="$2"
  if gcloud secrets describe "${name}" --project="${PROJECT}" &>/dev/null; then
    printf '%s' "${data}" | gcloud secrets versions add "${name}" --project="${PROJECT}" --data-file=-
    echo "Updated secret: ${name}"
  else
    printf '%s' "${data}" | gcloud secrets create "${name}" --project="${PROJECT}" --replication-policy=automatic --data-file=-
    echo "Created secret: ${name}"
  fi
}

echo "Project: ${PROJECT}"
echo "Endpoint: ${FOUNDRY_URL}"

_upsert_secret "azure-foundry-api-key" "${FOUNDRY_KEY}"
_upsert_secret "azure-foundry-endpoint" "${FOUNDRY_URL}"

if gcloud secrets describe azure-foundry-deployments --project="${PROJECT}" &>/dev/null; then
  gcloud secrets versions add azure-foundry-deployments \
    --project="${PROJECT}" \
    --data-file="${DEPLOYMENTS_FILE}"
  echo "Updated secret: azure-foundry-deployments"
else
  gcloud secrets create azure-foundry-deployments \
    --project="${PROJECT}" \
    --replication-policy=automatic \
    --data-file="${DEPLOYMENTS_FILE}"
  echo "Created secret: azure-foundry-deployments"
fi

echo ""
echo "Done. Optional — mount on Cloud Run:"
echo "  gcloud run services update llmhive-orchestrator --region=us-east1 --project=${PROJECT} \\"
echo "    --update-secrets=AZURE_FOUNDRY_API_KEY=azure-foundry-api-key:latest,AZURE_FOUNDRY_ENDPOINT=azure-foundry-endpoint:latest,AZURE_FOUNDRY_DEPLOYMENTS=azure-foundry-deployments:latest"
