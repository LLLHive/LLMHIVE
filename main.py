"""
Main entry point for the LLMHIVE FastAPI application.
This module imports and exposes the FastAPI app instance for Gunicorn.

IMPORTANT: This is the ONLY entry point used by:
- Dockerfile: CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app -k uvicorn.workers.UvicornWorker"]
- Cloud Run deployment
- Local development with uvicorn

Do NOT create alternative entry points as they will cause import conflicts and service unavailability errors.
"""

# With PYTHONPATH=/app, we can import directly using absolute imports
from app.app import app

__all__ = ["app"]
