#!/usr/bin/env bash
# Apply Artifact Registry cleanup policies to gcr.io with LIVE deletion enabled.
# Google's background job runs about once a day. Keep policies win over delete.
#
# Usage:
#   CONFIRM_LIVE_GCR_CLEANUP=yes ./scripts/gcp/apply-gcr-cleanup-policy.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:-llmhive-orchestrator}"
LOCATION="${GCP_AR_LOCATION:-us}"
REPOSITORY="${GCP_AR_REPOSITORY:-gcr.io}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_FILE="${SCRIPT_DIR}/gcr-io-cleanup-policies.json"

if [[ "${CONFIRM_LIVE_GCR_CLEANUP:-}" != "yes" ]]; then
  echo "Refusing to enable live deletion without CONFIRM_LIVE_GCR_CLEANUP=yes" >&2
  exit 1
fi

if [[ ! -f "$POLICY_FILE" ]]; then
  echo "Missing policy file: $POLICY_FILE" >&2
  exit 1
fi

python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$POLICY_FILE"

echo "Applying LIVE cleanup policies (dry-run OFF)"
echo "  project=$PROJECT location=$LOCATION repository=$REPOSITORY"
echo "  policy=$POLICY_FILE"
echo

gcloud artifacts repositories set-cleanup-policies "$REPOSITORY" \
  --project="$PROJECT" \
  --location="$LOCATION" \
  --policy="$POLICY_FILE" \
  --no-dry-run

echo
echo "Confirming repository dry-run is disabled:"
gcloud artifacts repositories describe "$REPOSITORY" \
  --project="$PROJECT" \
  --location="$LOCATION" \
  --format='yaml(name,cleanupPolicyDryRun,sizeBytes,cleanupPolicies)'
