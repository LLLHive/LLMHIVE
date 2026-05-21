#!/usr/bin/env bash
# Upload HuggingFace inference token to GCP Secret Manager.
#
# Prerequisites:
#   1. Create a token at https://huggingface.co/settings/tokens
#      - Type: "Read" is enough for whoami + Inference API
#      - For gated models (Llama), accept the model license on the model page first
#   2. Export HF_TOKEN before running, or pass as first argument:
#        export HF_TOKEN=hf_...
#        ./scripts/setup_hf_secret.sh
#        ./scripts/setup_hf_secret.sh hf_xxxxxxxx
#
# Mount on Cloud Run (also in llmhive/cloudbuild.yaml after merge):
#   HF_TOKEN=Hf-token:latest

set -euo pipefail

PROJECT="${PROJECT:-llmhive-orchestrator}"
SECRET_NAME="${HF_SECRET_NAME:-Hf-token}"

TOKEN="${1:-${HF_TOKEN:-}}"
if [[ -z "${TOKEN}" ]]; then
  echo "HF_TOKEN is required."
  echo "  export HF_TOKEN=hf_... && $0"
  echo "  $0 hf_..."
  exit 1
fi

if [[ ! "${TOKEN}" =~ ^hf_ ]]; then
  echo "Warning: HuggingFace tokens usually start with hf_"
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
printf '%s' "${TOKEN}" >"${tmp}"

if gcloud secrets describe "${SECRET_NAME}" --project="${PROJECT}" &>/dev/null; then
  gcloud secrets versions add "${SECRET_NAME}" \
    --project="${PROJECT}" \
    --data-file="${tmp}"
  echo "Updated secret: ${SECRET_NAME}"
else
  gcloud secrets create "${SECRET_NAME}" \
    --project="${PROJECT}" \
    --replication-policy=automatic \
    --data-file="${tmp}"
  echo "Created secret: ${SECRET_NAME}"
fi

echo
echo "Local verify:"
echo "  export HF_TOKEN=\$(gcloud secrets versions access latest --secret=${SECRET_NAME} --project=${PROJECT})"
echo "  ./scripts/run_verify_with_gcp_secrets.sh   # after adding HF_TOKEN to that script"
echo
echo "Redeploy orchestrator so Cloud Run mounts HF_TOKEN:"
echo "  ./scripts/deploy_orchestrator_routing_v2.sh"
