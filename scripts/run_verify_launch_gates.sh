#!/usr/bin/env bash
# Step 2 launch checklist — run all automated go/no-go probes.
# Usage: ./scripts/run_verify_launch_gates.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT="${GCP_PROJECT:-llmhive-orchestrator}"
# Live traffic revision. Override with CLOUD_RUN_REVISION / LAUNCH_CERTIFIED_REVISION if pinning.
if [[ -z "${CLOUD_RUN_REVISION:-}" ]]; then
  CLOUD_RUN_REVISION="$(gcloud run services describe llmhive-orchestrator \
    --region us-east1 --project "${PROJECT}" \
    --format="value(status.traffic[0].revisionName)" 2>/dev/null || true)"
fi
export CLOUD_RUN_REVISION

echo "Loading secrets from GCP (${PROJECT})..."
export API_KEY
API_KEY=$(gcloud secrets versions access latest --secret=api-key --project="${PROJECT}" 2>/dev/null || true)
export LLMHIVE_SCHEDULED_BENCHMARK_SECRET
LLMHIVE_SCHEDULED_BENCHMARK_SECRET=$(gcloud secrets versions access latest --secret=scheduled-benchmark-secret --project="${PROJECT}" 2>/dev/null || true)

if [[ -z "${API_KEY}" ]]; then
  echo "::warning::api-key not loaded — chat probe will be skipped"
fi
if [[ -z "${LLMHIVE_SCHEDULED_BENCHMARK_SECRET}" ]]; then
  echo "::warning::scheduled-benchmark-secret not loaded — chat probe will be skipped"
fi

exec python3 scripts/verify_launch_gates.py
