#!/usr/bin/env bash
# Deploy llmhive-orchestrator with ROUTING_V2 + direct provider clients.
# Preserves existing Cloud Run secret mounts via --update-secrets (additive).
set -euo pipefail

PROJECT="${GCP_PROJECT:-llmhive-orchestrator}"
REGION="${CLOUD_RUN_REGION:-us-east1}"
SERVICE="llmhive-orchestrator"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploy ${SERVICE} (ROUTING_V2) ==="
echo "Project: ${PROJECT}"
echo "Region:  ${REGION}"
echo

gcloud config set project "${PROJECT}" >/dev/null

COMMIT_SHA="$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || date +%s)"
echo "Build tag: ${COMMIT_SHA}"

gcloud builds submit \
  --config="${REPO_ROOT}/llmhive/cloudbuild.yaml" \
  --project="${PROJECT}" \
  --substitutions="COMMIT_SHA=${COMMIT_SHA}" \
  "${REPO_ROOT}"

echo
echo "=== Post-deploy: ensure ROUTING_V2 + build identity ==="
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
gcloud run services update "${SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT}" \
  --update-env-vars="ROUTING_V2_ENABLED=true,ROUTING_V2_STRICT_IDENTITY=true,ROUTING_V2_SKIP_OR_WHEN_DIRECT=false,ROUTING_V2_RESERVED_SPILL=true,FREE_P1_MESH_ENABLED=true,BUILD_COMMIT=${COMMIT_SHA},GIT_SHA=${COMMIT_SHA},BUILD_TIME=${BUILD_TIME}" \
  --quiet

NEW_REV="$(gcloud run services describe "${SERVICE}" \
  --region="${REGION}" --project="${PROJECT}" \
  --format='value(status.latestCreatedRevisionName)')"
if [[ -n "${NEW_REV}" ]]; then
  gcloud run services update-traffic "${SERVICE}" \
    --region="${REGION}" --project="${PROJECT}" \
    --to-revisions="${NEW_REV}=100" \
    --quiet
fi

URL=$(gcloud run services describe "${SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT}" \
  --format='value(status.url)')
echo "Service URL: ${URL}"
echo "Health: ${URL}/health"
BODY="$(curl -sf "${URL}/health" || true)"
echo "${BODY}"
echo "${BODY}" | grep -q "\"commit\":\"${COMMIT_SHA}\"" && echo " Health OK (commit matches ${COMMIT_SHA})" || echo " Health check pending / commit mismatch"

echo
echo "Run provider audit:"
echo "  python3 scripts/verify_direct_providers.py"
