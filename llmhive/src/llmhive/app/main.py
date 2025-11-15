"""LLMHive FastAPI application main entry point."""
from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .database import engine
from .models import Base

# Configure comprehensive logging as early as possible so that import-time
# diagnostics (for example, when providers fail to configure) are captured.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="LLMHive Orchestrator API",
    description="Multi-model orchestration service for LLM interactions",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.warning(f"Database initialization failed: {e}")
    logger.warning("Application will continue but database operations may fail")

# Define root-level endpoints before including routers
@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint for basic verification."""
    logger.info("Root endpoint called")
    return {
        "service": "LLMHive Orchestrator API",
        "status": "online",
        "version": "1.0.0"
    }

HEALTH_PAYLOAD = {"status": "ok"}


@app.get("/healthz", summary="Health check", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Health check endpoint required by Cloud Run.

    Note: This is a root-level health check endpoint (/healthz) separate from
    the API-level health check (/api/v1/healthz). Cloud Run and other
    infrastructure components typically expect health checks at the root level.
    """
    logger.info("Health check endpoint called")
    return HEALTH_PAYLOAD


@app.head("/healthz", summary="Health check (HEAD)", include_in_schema=False)
async def health_check_head() -> Response:
    """Head-only health check variant for infrastructure probes."""
    return Response(status_code=200)


@app.get("/health", include_in_schema=False)
async def health_alias() -> dict[str, str]:
    """Backward compatible alias for legacy health checks."""
    logger.info("Health alias endpoint called")
    return HEALTH_PAYLOAD


@app.head("/health", include_in_schema=False)
async def health_alias_head() -> Response:
    """HEAD alias for /health."""
    return Response(status_code=200)


@app.get("/_ah/health", include_in_schema=False)
async def app_engine_health_alias() -> dict[str, str]:
    """Compatibility endpoint for Google load balancer probes."""
    logger.info("App Engine style health endpoint called")
    return HEALTH_PAYLOAD


@app.head("/_ah/health", include_in_schema=False)
async def app_engine_health_alias_head() -> Response:
    """HEAD alias for /_ah/health."""
    return Response(status_code=200)

# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    port = os.environ.get('PORT', '8080')
    logger.info(f"Application starting on port {port}")
    logger.info("LLMHive Orchestrator API is ready")
    
    # Log registered routes for debugging
    logger.info("Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            logger.info(f"  {','.join(route.methods)} {route.path}")
    
    # Log provider configuration status
    from .orchestrator import Orchestrator
    orch = Orchestrator()
    providers = list(orch.providers.keys())
    logger.info(f"Configured providers: {providers}")
    if len(providers) == 1 and providers[0] == "stub":
        logger.warning("⚠️  Only stub provider is configured! No real LLM API keys found.")
        logger.warning("   Set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, GROK_API_KEY, etc.")
    else:
        logger.info(f"✓ {len([p for p in providers if p != 'stub'])} real provider(s) configured")
