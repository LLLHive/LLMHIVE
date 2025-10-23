#!/bin/sh
# Docker entrypoint script for Cloud Run deployment
# This script ensures uvicorn listens on the PORT environment variable set by Cloud Run

set -e

# Use PORT environment variable if set, otherwise default to 8080
PORT=${PORT:-8080}

echo "Starting uvicorn on port $PORT..."
exec uvicorn llmhive.app.main:app --host 0.0.0.0 --port "$PORT"
