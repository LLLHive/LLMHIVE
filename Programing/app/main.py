"""FastAPI application entry point for LLMHIVE."""

from typing import Any, Dict

from fastapi import FastAPI

from .database import get_settings

app = FastAPI(title="LLMHIVE API", version="1.0.0")


@app.get("/healthz", tags=["health"], summary="Health check")
def health_check() -> Dict[str, Any]:
    """Return application health status."""

    settings = get_settings()
    # Ensure the database URL setting is loaded so misconfigurations surface quickly.
    database_url = settings.database_url
    return {"status": "ok", "database_url_configured": bool(database_url)}


@app.get("/")
def root() -> Dict[str, str]:
    """Simple root endpoint for smoke testing."""

    return {"message": "Welcome to LLMHIVE"}
