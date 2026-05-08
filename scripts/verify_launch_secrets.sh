#!/usr/bin/env bash
# verify_launch_secrets.sh
#
# One-shot launch readiness check for the LLMHive orchestrator on Cloud Run.
# Confirms (a) which build is currently serving traffic, (b) that all required
# Stripe / Clerk / API secrets exist in Secret Manager, (c) that the live
# /healthz endpoint matches the Cloud Run revision the gcloud API reports.
#
# Usage:
#   scripts/verify_launch_secrets.sh                 # use defaults
#   PROJECT_ID=my-gcp REGION=us-east1 scripts/verify_launch_secrets.sh
#
# Required tooling: gcloud (authenticated), curl, jq (optional but pretty).
# This script does NOT print secret values, only existence and metadata.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-llmhive-orchestrator}"
REGION="${REGION:-us-east1}"
SERVICE="${SERVICE:-llmhive-orchestrator}"

ok()    { printf "  \033[32m✓\033[0m %s\n" "$*"; }
warn()  { printf "  \033[33m!\033[0m %s\n" "$*"; }
fail()  { printf "  \033[31m✗\033[0m %s\n" "$*"; FAIL=1; }
hr()    { printf "\n\033[1m==> %s\033[0m\n" "$*"; }

FAIL=0

if ! command -v gcloud >/dev/null 2>&1; then
  printf "gcloud CLI is required.\n" >&2
  exit 2
fi

# Confirm the caller is authenticated against the right project.
ACTIVE_ACCOUNT="$(gcloud config get-value account 2>/dev/null || true)"
ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
hr "gcloud context"
if [[ -z "${ACTIVE_ACCOUNT}" || "${ACTIVE_ACCOUNT}" == "(unset)" ]]; then
  fail "no active gcloud account; run: gcloud auth login"
else
  ok "account: ${ACTIVE_ACCOUNT}"
fi
if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
  warn "active project '${ACTIVE_PROJECT}' != target '${PROJECT_ID}' — using --project flag"
else
  ok "project:  ${ACTIVE_PROJECT}"
fi

# 1) Cloud Run service revision currently serving traffic.
hr "Cloud Run service: ${SERVICE} (${REGION})"
SERVICE_DESC=$(gcloud run services describe "${SERVICE}" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format='value(status.latestReadyRevisionName,status.url)' 2>/dev/null || true)

if [[ -z "${SERVICE_DESC}" ]]; then
  fail "service ${SERVICE} not found in ${REGION} of ${PROJECT_ID}"
else
  LATEST_REV="$(printf "%s" "${SERVICE_DESC}" | awk '{print $1}')"
  SERVICE_URL="$(printf "%s" "${SERVICE_DESC}" | awk '{print $2}')"
  ok "latest ready revision: ${LATEST_REV}"
  ok "service URL:           ${SERVICE_URL}"

  TRAFFIC_INFO=$(gcloud run services describe "${SERVICE}" \
    --region="${REGION}" --project="${PROJECT_ID}" \
    --format='value(status.traffic)' 2>/dev/null || true)
  if [[ -n "${TRAFFIC_INFO}" ]]; then
    ok "traffic split:         ${TRAFFIC_INFO}"
  fi

  # 2) Curl /healthz and compare commit/revision to gcloud's view.
  hr "Live /healthz"
  HEALTH_BODY="$(curl --max-time 8 -fsS "${SERVICE_URL}/healthz" 2>/dev/null || true)"
  if [[ -z "${HEALTH_BODY}" ]]; then
    fail "/healthz did not respond at ${SERVICE_URL}"
  else
    ok "response: ${HEALTH_BODY}"
    LIVE_REV="$(printf "%s" "${HEALTH_BODY}" | sed -E 's/.*"revision"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' | head -n1)"
    if [[ "${LIVE_REV}" == "${LATEST_REV}" ]]; then
      ok "/healthz revision matches Cloud Run latestReadyRevision"
    else
      warn "/healthz revision (${LIVE_REV:-unset}) differs from latestReadyRevision (${LATEST_REV})"
    fi
  fi
fi

# 3) Required Secret Manager secrets — existence only, no values.
hr "Required secrets (Secret Manager)"
REQUIRED_SECRETS=(
  api-key
  stripe-secret-key
  stripe-webhook-secret
  stripe-publishable-key
  stripe-price-id-standard-monthly
  stripe-price-id-standard-annual
  stripe-price-id-premium-monthly
  stripe-price-id-premium-annual
  clerk-secret-key
  resend-api-key
)

for s in "${REQUIRED_SECRETS[@]}"; do
  META=$(gcloud secrets versions list "${s}" \
    --project="${PROJECT_ID}" \
    --filter="state=ENABLED" \
    --format='value(name,createTime)' \
    --limit=1 2>/dev/null || true)
  if [[ -z "${META}" ]]; then
    fail "secret '${s}' not found or has no ENABLED version"
  else
    VERSION=$(printf "%s" "${META}" | awk '{print $1}')
    CREATED=$(printf "%s" "${META}" | awk '{print $2}')
    ok "${s}  (latest enabled v${VERSION}, created ${CREATED})"
  fi
done

# 4) Frontend env-var sanity (only when run from a Vercel-linked workspace).
hr "Frontend (informational)"
if command -v vercel >/dev/null 2>&1; then
  ok "vercel CLI present — run 'vercel env ls' to confirm LLMHIVE_API_KEY, ORCHESTRATOR_API_BASE_URL, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY"
else
  warn "vercel CLI not installed locally — verify these env vars in your hosting dashboard:"
  printf "      LLMHIVE_API_KEY (must equal Cloud Run API_KEY)\n"
  printf "      ORCHESTRATOR_API_BASE_URL (= %s)\n" "${SERVICE_URL:-<service-url>}"
  printf "      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY\n"
  printf "      CLERK_SECRET_KEY\n"
  printf "      RESEND_API_KEY (for transactional email)\n"
fi

hr "Result"
if [[ "${FAIL}" -eq 0 ]]; then
  printf "  \033[32mAll automated checks passed.\033[0m Manual checks still required:\n"
  printf "   - Compare stripe-webhook-secret value against Stripe Dashboard signing secret.\n"
  printf "   - Compare price-id values against Stripe Dashboard live prices.\n"
  printf "   - Buy one real subscription end-to-end and refund yourself.\n"
  exit 0
else
  printf "  \033[31mOne or more checks failed.\033[0m Address the above before launching.\n"
  exit 1
fi
