"""FastAPI application entrypoint for LLMHIVE."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.v1 import router as api_router
from .core.errors import LLMHiveError
from .core.logging import configure_logging
from .core.settings import settings

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLMHIVE Orchestrator",
    version="0.1.0",
    description="Multi-LLM collaborative orchestration platform",
)


@app.on_event("startup")
async def on_startup() -> None:
    """Perform startup checks and log configuration."""
    logger.info("Starting LLMHIVE", extra={"env": settings.env})


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Health endpoint used for uptime checks."""
    return {"status": "ok"}


@app.exception_handler(LLMHiveError)
async def llmhive_error_handler(_: Request, exc: LLMHiveError) -> JSONResponse:
    """Convert domain errors into structured JSON responses."""
    logger.warning("LLMHiveError", extra={"error": exc.message, "context": exc.context})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(api_router, prefix="/api/v1")
