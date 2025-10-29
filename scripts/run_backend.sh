#!/usr/bin/env bash
set -euo pipefail

# Determine project root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# If no virtual environment is active, try to use the local .venv
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ -x "${PROJECT_ROOT}/.venv/bin/activate" ]; then
    echo "Activating virtual environment at ${PROJECT_ROOT}/.venv" >&2
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.venv/bin/activate"
  else
    echo "Warning: .venv not found. Using system python3." >&2
  fi
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required to start the backend." >&2
  exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
APP_MODULE="app.app:app"

exec python3 -m uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}"
