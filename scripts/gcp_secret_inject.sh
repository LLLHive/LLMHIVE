#!/usr/bin/env bash
# =============================================================================
# GCP Secret Manager Injection Script
# =============================================================================
#
# Securely pulls secrets from Google Secret Manager and exports them as
# environment variables. Designed for local development and CI where secrets
# aren't already injected by the platform (Cloud Run, Vercel, etc.).
#
# USAGE:
#   source scripts/gcp_secret_inject.sh          # Inject secrets to current shell
#   source scripts/gcp_secret_inject.sh --check  # Check which vars are set
#   bash scripts/gcp_secret_inject.sh --exec "python my_script.py"
#
# SECURITY:
#   - Never logs secret values
#   - Never writes secrets to files
#   - Only fetches secrets if env vars are empty/unset
#   - Requires: gcloud CLI + secretmanager.versions.access permission
#
# ENV OVERRIDES:
#   GCP_PROJECT            - Override project ID
#   PINECONE_SECRET_NAME   - Override secret name (default: pinecone-api-key)
#   OPENROUTER_SECRET_NAME - Override secret name (default: open-router-key)
#
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Default secret names in Secret Manager
PINECONE_SECRET_NAME="${PINECONE_SECRET_NAME:-pinecone-api-key}"
OPENROUTER_SECRET_NAME="${OPENROUTER_SECRET_NAME:-open-router-key}"

# Track if we're being sourced or executed
_GCP_INJECT_SOURCED=false
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  _GCP_INJECT_SOURCED=true
fi

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

_gcp_inject_log() {
  echo "[gcp-secret-inject] $*" >&2
}

_gcp_inject_error() {
  echo "[gcp-secret-inject] ❌ ERROR: $*" >&2
}

_gcp_inject_check_gcloud() {
  if ! command -v gcloud &>/dev/null; then
    _gcp_inject_error "gcloud CLI not found."
    _gcp_inject_log ""
    _gcp_inject_log "To install gcloud:"
    _gcp_inject_log "  macOS: brew install --cask google-cloud-sdk"
    _gcp_inject_log "  Linux: curl https://sdk.cloud.google.com | bash"
    _gcp_inject_log "  Then:  gcloud auth login && gcloud config set project YOUR_PROJECT"
    _gcp_inject_log ""
    return 1
  fi
  return 0
}

_gcp_inject_get_project() {
  local project=""
  
  # Priority 1: Explicit override
  if [[ -n "${GCP_PROJECT:-}" ]]; then
    project="$GCP_PROJECT"
  # Priority 2: GOOGLE_CLOUD_PROJECT env var
  elif [[ -n "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
    project="$GOOGLE_CLOUD_PROJECT"
  # Priority 3: gcloud config
  else
    project="$(gcloud config get-value project 2>/dev/null || true)"
  fi
  
  if [[ -z "$project" || "$project" == "(unset)" ]]; then
    _gcp_inject_error "Cannot determine GCP project."
    _gcp_inject_log ""
    _gcp_inject_log "Fix by ONE of:"
    _gcp_inject_log "  1. export GOOGLE_CLOUD_PROJECT=your-project-id"
    _gcp_inject_log "  2. export GCP_PROJECT=your-project-id"
    _gcp_inject_log "  3. gcloud config set project your-project-id"
    _gcp_inject_log ""
    return 1
  fi
  
  echo "$project"
}

_gcp_inject_fetch_secret() {
  local project="$1"
  local secret_name="$2"
  local version="${3:-latest}"
  
  local value
  if ! value="$(gcloud secrets versions access "$version" \
    --secret="$secret_name" \
    --project="$project" 2>&1)"; then
    # Check for common errors
    if echo "$value" | grep -q "NOT_FOUND"; then
      _gcp_inject_error "Secret '$secret_name' not found in project '$project'."
      _gcp_inject_log "  Create it: gcloud secrets create $secret_name --project=$project"
    elif echo "$value" | grep -q "PERMISSION_DENIED"; then
      _gcp_inject_error "Permission denied for secret '$secret_name'."
      _gcp_inject_log "  Grant access: gcloud secrets add-iam-policy-binding $secret_name \\"
      _gcp_inject_log "    --member=user:\$(gcloud config get-value account) \\"
      _gcp_inject_log "    --role=roles/secretmanager.secretAccessor \\"
      _gcp_inject_log "    --project=$project"
    else
      _gcp_inject_error "Failed to access secret '$secret_name': $value"
    fi
    return 1
  fi
  
  # NEVER log the value
  echo "$value"
}

# -----------------------------------------------------------------------------
# Main Functions
# -----------------------------------------------------------------------------

gcp_inject_check() {
  # Check mode: print which vars are set (without values) and exit 0/2
  local all_set=true
  
  echo "=== GCP Secret Injection Status ==="
  echo ""
  
  # Check PINECONE_API_KEY
  if [[ -n "${PINECONE_API_KEY:-}" ]]; then
    echo "✅ PINECONE_API_KEY: SET (${#PINECONE_API_KEY} chars)"
  else
    echo "❌ PINECONE_API_KEY: NOT SET"
    all_set=false
  fi
  
  # Check OPENROUTER_API_KEY
  if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
    echo "✅ OPENROUTER_API_KEY: SET (${#OPENROUTER_API_KEY} chars)"
  else
    echo "❌ OPENROUTER_API_KEY: NOT SET"
    all_set=false
  fi
  
  echo ""
  
  # Check gcloud availability
  if command -v gcloud &>/dev/null; then
    local project
    project="$(gcloud config get-value project 2>/dev/null || echo "(unset)")"
    echo "gcloud: available"
    echo "gcloud project: $project"
    echo "GOOGLE_CLOUD_PROJECT: ${GOOGLE_CLOUD_PROJECT:-(not set)}"
    echo "GCP_PROJECT: ${GCP_PROJECT:-(not set)}"
  else
    echo "gcloud: NOT INSTALLED"
  fi
  
  echo ""
  
  if $all_set; then
    echo "✅ All required secrets are set."
    return 0
  else
    echo "❌ Some secrets are missing."
    echo ""
    echo "To inject from Secret Manager:"
    echo "  source scripts/gcp_secret_inject.sh"
    return 2
  fi
}

gcp_inject_secrets() {
  # Inject secrets from Secret Manager if not already set
  
  _gcp_inject_check_gcloud || return 1
  
  local project
  project="$(_gcp_inject_get_project)" || return 1
  
  _gcp_inject_log "Using project: $project"
  
  local injected=0
  local failed=0
  
  # PINECONE_API_KEY
  if [[ -z "${PINECONE_API_KEY:-}" ]]; then
    _gcp_inject_log "Fetching PINECONE_API_KEY from secret '$PINECONE_SECRET_NAME'..."
    local value
    if value="$(_gcp_inject_fetch_secret "$project" "$PINECONE_SECRET_NAME")"; then
      export PINECONE_API_KEY="$value"
      _gcp_inject_log "✅ Set PINECONE_API_KEY from Secret Manager"
      ((injected++))
    else
      ((failed++))
    fi
  else
    _gcp_inject_log "PINECONE_API_KEY already set (skipping)"
  fi
  
  # OPENROUTER_API_KEY
  if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    _gcp_inject_log "Fetching OPENROUTER_API_KEY from secret '$OPENROUTER_SECRET_NAME'..."
    local value
    if value="$(_gcp_inject_fetch_secret "$project" "$OPENROUTER_SECRET_NAME")"; then
      export OPENROUTER_API_KEY="$value"
      _gcp_inject_log "✅ Set OPENROUTER_API_KEY from Secret Manager"
      ((injected++))
    else
      ((failed++))
    fi
  else
    _gcp_inject_log "OPENROUTER_API_KEY already set (skipping)"
  fi
  
  _gcp_inject_log ""
  _gcp_inject_log "Summary: $injected injected, $failed failed"
  
  if [[ $failed -gt 0 ]]; then
    return 1
  fi
  return 0
}

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------

_gcp_inject_main() {
  local mode="inject"
  local exec_cmd=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check)
        mode="check"
        shift
        ;;
      --exec)
        mode="exec"
        exec_cmd="$2"
        shift 2
        ;;
      --help|-h)
        echo "Usage:"
        echo "  source scripts/gcp_secret_inject.sh          # Inject secrets"
        echo "  source scripts/gcp_secret_inject.sh --check  # Check status"
        echo "  bash scripts/gcp_secret_inject.sh --exec 'cmd' # Inject then run"
        echo ""
        echo "Environment overrides:"
        echo "  GCP_PROJECT            - Override project ID"
        echo "  PINECONE_SECRET_NAME   - Secret name (default: pinecone-api-key)"
        echo "  OPENROUTER_SECRET_NAME - Secret name (default: open-router-key)"
        return 0
        ;;
      *)
        _gcp_inject_error "Unknown argument: $1"
        return 1
        ;;
    esac
  done
  
  case "$mode" in
    check)
      gcp_inject_check
      ;;
    inject)
      gcp_inject_secrets
      ;;
    exec)
      gcp_inject_secrets || exit 1
      exec $exec_cmd
      ;;
  esac
}

# Only run main if not being sourced without args, or if args provided
if [[ "${1:-}" != "" ]] || ! $_GCP_INJECT_SOURCED; then
  _gcp_inject_main "$@"
elif $_GCP_INJECT_SOURCED; then
  # Being sourced without args - inject secrets
  gcp_inject_secrets
fi

