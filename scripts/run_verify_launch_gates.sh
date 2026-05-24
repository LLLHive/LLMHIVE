#!/usr/bin/env bash
# Step 2 launch checklist — run all automated go/no-go probes.
# Usage: ./scripts/run_verify_launch_gates.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT="${GCP_PROJECT:-llmhive-orchestrator}"
export CLOUD_RUN_REVISION="${CLOUD_RUN_REVISION:-llmhive-orchestrator-02461-2h4}"

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
