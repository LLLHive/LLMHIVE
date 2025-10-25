#!/bin/bash
set -e

# This is the command to start the Gunicorn server.
# Gunicorn is a production-grade server that manages Uvicorn workers.
#
# --workers 4: Starts 4 worker processes to handle requests.
# --worker-class uvicorn.workers.UvicornWorker: Tells Gunicorn to use Uvicorn for handling the application.
# --bind 0.0.0.0:$PORT: This is the critical part.
#   - 0.0.0.0: Binds to all available network interfaces in the container, making it accessible.
#   - $PORT: Uses the port number provided by the Google Cloud Run environment variable.
# llmhive.app.main:app: Points to our FastAPI application instance.
#   - llmhive.app.main: the file `llmhive/app/main.py`
#   - app: the `app = FastAPI()` object inside that file.

# Use PORT environment variable if set by Cloud Run, otherwise default to 8080
PORT=${PORT:-8080}

exec gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT llmhive.app.main:app
