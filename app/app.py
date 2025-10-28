from fastapi import FastAPI, Response, Request, HTTPException
from app.orchestration.router import (
    router as orchestration_router,
    versioned_router as orchestration_v1_router,
)
from app.config import settings
from google.cloud import secretmanager
from pythonjsonlogger import jsonlogger
from fastapi.responses import JSONResponse
import logging
import os
from typing import Final

# 1. CONFIGURE STRUCTURED LOGGING
# This must happen first to ensure all subsequent logs are structured.
logger = logging.getLogger("llmhive")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)
# Clear existing handlers to avoid duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(logHandler)


# 2. DEFINE THE SECRET FETCHER FUNCTION
def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """Retrieves a secret from Google Cloud Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        logger.info("Successfully fetched secret from Secret Manager")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        # Log error type without exposing sensitive details
        error_type = type(e).__name__
        logger.error(f"Failed to fetch secret from Secret Manager: {error_type}")
        # Return empty string to allow app to start with fallback behavior
        return ""


# 3. INITIALIZE AND CONFIGURE THE FASTAPI APP
app = FastAPI(
    title="LLMHive Orchestrator",
    description="API for orchestrating LLM agent interactions.",
    version="1.0.0"
)


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


# 5. INCLUDE THE EXISTING API ROUTER (CRITICAL)
app.include_router(orchestration_router, prefix="/api")


# 6. MOUNT VERSIONED ROUTES UNDER /api/v1 FOR CONSISTENCY WITH DOCUMENTATION
app.include_router(orchestration_v1_router, prefix="/api/v1")


@app.get("/api/v1/healthz", tags=["Health Check"])
async def api_health_check():
    """Health check endpoint aligned with documented /api/v1 path."""
    return await health_check()
