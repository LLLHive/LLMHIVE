#!/bin/sh
set -e

PORT=${PORT:-8080}
WORKERS=${WEB_CONCURRENCY:-1}

echo "=== start.sh: starting container ==="
echo "PORT=${PORT}"
echo "WEB_CONCURRENCY=${WORKERS}"
# Print presence (not values) of key env vars so logs show if secrets are attached
echo "OPENAI_API_KEY is ${OPENAI_API_KEY:+set}"
echo "GROK_API_KEY is ${GROK_API_KEY:+set}"
echo "ANTHROPIC_API_KEY is ${ANTHROPIC_API_KEY:+set}"
echo "LLMHIVE_FAIL_ON_STUB is ${LLMHIVE_FAIL_ON_STUB:-unset}"

sleep 0.1

exec gunicorn -k uvicorn.workers.UvicornWorker \
  llmhive.app.main:app \
  --bind 0.0.0.0:${PORT} \
  --workers ${WORKERS} \
  --timeout 120 \
  --log-level info
