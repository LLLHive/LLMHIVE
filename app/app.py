# app/app.py

from __future__ import annotations

import logging
import os
import sys
from types import SimpleNamespace, ModuleType
from typing import Final

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import router as api_router
from app.config import settings
# Use the advanced orchestrator from llmhive instead of the simple orchestrator.
from llmhive.app.api.orchestration import router as advanced_orchestration_router

try:  # pragma: no cover - optional dependency in local tests
    from google.cloud import secretmanager  # type: ignore
except Exception:  # pragma: no cover - handled gracefully below
    secretmanager = SimpleNamespace(SecretManagerServiceClient=None)  # type: ignore

try:  # pragma: no cover - optional dependency in local tests
    from pythonjsonlogger import jsonlogger
except Exception as exc:  # pragma: no cover - logging configured without JSON formatting
    fallback_module = ModuleType("pythonjsonlogger")

    class _FallbackJsonFormatter(logging.Formatter):
        """Minimal drop-in replacement used when python-json-logger is absent."""
        pass

    fallback_module.jsonlogger = SimpleNamespace(JsonFormatter=_FallbackJsonFormatter)
    sys.modules.setdefault("pythonjsonlogger", fallback_module)
    jsonlogger = fallback_module.jsonlogger  # type: ignore
    logging.getLogger(__name__).warning(
        "python-json-logger is unavailable (%s); using fallback formatter.",
        exc,
    )

# 1. CONFIGURE STRUCTURED LOGGING
# This must happen first to ensure all subsequent logs are structured.
logger = logging.getLogger("llmhive")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
log_handler = logging.StreamHandler()
if jsonlogger:
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    log_handler.setFormatter(formatter)

# Clear existing handlers to avoid duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(log_handler)

# 2. DEFINE THE SECRET FETCHER FUNCTION
def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """Retrieves a secret from Google Cloud Secret Manager."""
    if not secretmanager:
        logger.debug(
            "Secret Manager client unavailable; returning empty secret for %s.",
            secret_id,
        )
        return ""

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        logger.info("Successfully fetched secret from Secret Manager")
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        # Log error type without exposing sensitive details
        error_type = type(exc).__name__
        logger.error(
            "Failed to fetch secret '%s' from Secret Manager: %s",
            secret_id,
            error_type,
        )
        # Return empty string to allow app to start with fallback behavior
        return ""

# 3. INITIALIZE AND CONFIGURE THE FASTAPI APP
app = FastAPI(
    title="LLMHive Orchestrator",
    description="API for orchestrating LLM agent interactions.",
    version="1.0.0"
)

def _parse_cors_origins(raw_origins: str) -> list[str]:
    """Convert a comma-separated string of origins into a list."""
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]

configured_origins = _parse_cors_origins(settings.CORS_ALLOW_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if "*" in configured_origins:
    logger.info("CORS configured to allow all origins (development default).")
else:
    logger.info("CORS configured for origins: %s", ", ".join(configured_origins))

HEALTH_ENDPOINTS: Final[set[str]] = {"/healthz", "/health", "/_ah/health"}

def _health_payload() -> dict[str, str]:
    """Return the canonical payload used by every health endpoint."""
    return {"status": "ok"}

def _health_head_response() -> Response:
    """Return an empty 200 response for HEAD health probes."""
    return Response(status_code=200)

@app.middleware("http")
async def healthz_fallback_middleware(request: Request, call_next):
    """Ensure health endpoints always respond even if routing fails in production."""
    normalized_path = request.url.path.rstrip("/") or "/"
    if normalized_path in HEALTH_ENDPOINTS and request.method in {"GET", "HEAD"}:
        try:
            response = await call_next(request)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            logger.warning("%s route raised 404; serving fallback response", normalized_path)
            return _health_head_response() if request.method == "HEAD" else JSONResponse(_health_payload())
        except Exception:  # pragma: no cover - defensive safety net
            logger.exception(
                "Unhandled exception while serving %s; returning fallback health response",
                normalized_path,
            )
            return _health_head_response() if request.method == "HEAD" else JSONResponse(_health_payload())

        if response.status_code != 404:
            return response

        logger.warning("%s route returned 404; serving fallback response", normalized_path)
        return _health_head_response() if request.method == "HEAD" else JSONResponse(_health_payload())

    return await call_next(request)

@app.get("/", tags=["Service Information"])
async def root() -> dict[str, str]:
    """Provide a friendly response for the service root URL."""
    return {
        "service": "llmhive-orchestrator",
        "status": "ok",
        "docs": "/docs",
        "health": "/healthz",
        "api_health": "/api/v1/healthz",
    }

@app.on_event("startup")
async def startup_event():
    """
    On application startup, load secrets into the settings object.
    """
    logger.info("Application startup sequence initiated.")

    # Load OPENAI_API_KEY from Secret Manager if not set
    if not settings.OPENAI_API_KEY:
        api_key = get_secret(settings.PROJECT_ID, "OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY secret could not be loaded. OpenAI provider will use stub fallback.")
        else:
            logger.info("OPENAI_API_KEY loaded from Secret Manager.")
        settings.OPENAI_API_KEY = api_key

    # Load TAVILY_API_KEY from Secret Manager if not set
    if not settings.TAVILY_API_KEY:
        api_key = get_secret(settings.PROJECT_ID, "TAVILY_API_KEY")
        if not api_key:
            logger.warning("TAVILY_API_KEY secret could not be loaded. Web search functionality may not work.")
        else:
            logger.info("TAVILY_API_KEY loaded from Secret Manager.")
        settings.TAVILY_API_KEY = api_key

    logger.info("Application startup complete.")

# 4. ADD THE HEALTH CHECK ENDPOINT
@app.get("/healthz", tags=["Health Check"], summary="Health check", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Health check endpoint for Cloud Run readiness and liveness probes."""
    return _health_payload()

@app.head("/healthz", tags=["Health Check"], include_in_schema=False)
async def health_check_head() -> Response:
    """Fast HEAD response for Cloud Run health checks that use HEAD requests."""
    return _health_head_response()

@app.get("/_ah/health", tags=["Health Check"], include_in_schema=False)
async def app_engine_health_check() -> dict[str, str]:
    """Compatibility endpoint for Google health checks that probe /_ah/health."""
    return _health_payload()

@app.head("/_ah/health", tags=["Health Check"], include_in_schema=False)
async def app_engine_health_check_head() -> Response:
    """HEAD variant for /_ah/health used by certain Google load balancers."""
    return _health_head_response()

@app.get("/health", tags=["Health Check"], include_in_schema=False)
async def simple_health_alias() -> dict[str, str]:
    """Backward-compatible root health endpoint alias."""
    return _health_payload()

@app.head("/health", tags=["Health Check"], include_in_schema=False)
async def simple_health_alias_head() -> Response:
    """HEAD variant for the /health alias."""
    return _health_head_response()

# 5. INCLUDE THE PUBLIC API ROUTER (STREAMING CAPABLE)
app.include_router(api_router, prefix="/api")

# 6. MOUNT VERSIONED ROUTES UNDER /api/v1 FOR CONSISTENCY WITH DOCUMENTATION
#
# The advanced orchestrator is mounted here.  It accepts complex requests with
# fields such as prompt, models, enable_memory, enable_knowledge, user_id, etc.,
# and exposes GET /api/v1/orchestration/providers.
app.include_router(advanced_orchestration_router, prefix="/api/v1/orchestration")

@app.get("/api/v1/healthz", tags=["Health Check"])
async def api_health_check():
    """Health check endpoint aligned with documented /api/v1 path."""
    return await health_check()
