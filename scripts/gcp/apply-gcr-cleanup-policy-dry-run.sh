#!/usr/bin/env bash
# Apply Artifact Registry cleanup policies to gcr.io in DRY-RUN only.
# Does not delete images. Google's background job logs validateOnly=true for ~1 day.
# To enable live deletion after review: CONFIRM_LIVE_GCR_CLEANUP=yes ./scripts/gcp/apply-gcr-cleanup-policy.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:-llmhive-orchestrator}"
LOCATION="${GCP_AR_LOCATION:-us}"
REPOSITORY="${GCP_AR_REPOSITORY:-gcr.io}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_FILE="${SCRIPT_DIR}/gcr-io-cleanup-policies.json"

if [[ ! -f "$POLICY_FILE" ]]; then
  echo "Missing policy file: $POLICY_FILE" >&2
  exit 1
fi

python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$POLICY_FILE"

echo "Applying DRY-RUN cleanup policies"
echo "  project=$PROJECT location=$LOCATION repository=$REPOSITORY"
echo "  policy=$POLICY_FILE"
echo

gcloud artifacts repositories set-cleanup-policies "$REPOSITORY" \
  --project="$PROJECT" \
  --location="$LOCATION" \
  --policy="$POLICY_FILE" \
  --dry-run

echo
echo "Confirming repository still has dry-run enabled:"
gcloud artifacts repositories describe "$REPOSITORY" \
  --project="$PROJECT" \
  --location="$LOCATION" \
  --format='yaml(name,cleanupPolicyDryRun,cleanupPolicies)'
