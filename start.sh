#!/bin/sh
# Cloud Run entrypoint script for LLMHive
# - binds Gunicorn/Uvicorn to the PORT provided by Cloud Run
# - logs non-sensitive environment diagnostics for provider secrets
# - runs the FastAPI application via gunicorn with a uvicorn worker

set -e

PORT=${PORT:-8080}
WORKERS=${WEB_CONCURRENCY:-1}

echo "=== start.sh: starting container ==="
echo "PORT=${PORT}"
echo "WEB_CONCURRENCY=${WORKERS}"
# Emit whether critical secrets are set without leaking their values
>&2 echo "OPENAI_API_KEY is ${OPENAI_API_KEY:+set}"
>&2 echo "GROK_API_KEY is ${GROK_API_KEY:+set}"
>&2 echo "ANTHROPIC_API_KEY is ${ANTHROPIC_API_KEY:+set}"

sleep 0.1

exec gunicorn -k uvicorn.workers.UvicornWorker \
  llmhive.app.main:app \
  --bind 0.0.0.0:${PORT} \
  --workers ${WORKERS} \
  --timeout 120 \
  --log-level info
