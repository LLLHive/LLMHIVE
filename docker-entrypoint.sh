#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# shellcheck disable=SC2039 # dash compatibility: using POSIX constructs only

maybe_source_env_file() {
    file="$1"
    if [ -f "$file" ]; then
        # Export variables defined in the env file without polluting the shell on failure
        set -a
        # shellcheck disable=SC1090
        . "$file"
        set +a
    fi
}

maybe_export_from_file() {
    var="$1"
    file_var="${var}_FILE"

    var_value=$(eval "printf '%s' \"\${$var:-}\"")
    if [ -n "$var_value" ]; then
        return
    fi

    file_value=$(eval "printf '%s' \"\${$file_var:-}\"")
    if [ -n "$file_value" ] && [ -f "$file_value" ]; then
        export "$var"="$(cat "$file_value")"
        return
    fi

    for candidate in "/secrets/$var" "/var/run/secrets/$var"; do
        if [ -f "$candidate" ]; then
            export "$var"="$(cat "$candidate")"
            return
        fi
    done
}

# Load environment variables if a .env file is present in common locations
maybe_source_env_file "/app/src/.env"
maybe_source_env_file "/app/.env"
maybe_source_env_file ".env"

# Ensure GEMINI_API_KEY is populated when provided as a mounted secret file
maybe_export_from_file "GEMINI_API_KEY"

# Use PORT environment variable if set by Cloud Run, otherwise default to 8080
PORT=${PORT:-8080}

# Guarantee the modern package layout is importable even in minimalist runtime
# environments that do not honour the Dockerfile PYTHONPATH.
export PYTHONPATH="${PYTHONPATH:-}:$(pwd):$(pwd)/llmhive/src"

exec gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT main:app
