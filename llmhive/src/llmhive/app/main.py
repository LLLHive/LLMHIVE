"""LLMHive FastAPI application main entry point."""
from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .api import api_router
from .startup_checks import validate_startup_config

# Import error handling modules
try:
    from .errors import (
        LLMHiveError,
        ErrorCode,
        build_error_response,
        get_correlation_id,
        set_correlation_id,
        generate_correlation_id,
        get_circuit_breaker,
    )
    from .logging_config import (
        configure_logging,
        request_id_var,
        user_id_var,
        session_id_var,
        start_request_metrics,
        end_request_metrics,
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError as e:
    ERROR_HANDLING_AVAILABLE = False
    logging.getLogger(__name__).warning("Error handling modules not available: %s", e)

# Database imports are optional; some minimal deployments may not use the DB.
try:
    from .db import engine  # type: ignore
    from .models import Base  # type: ignore
except Exception as exc:  # pragma: no cover - defensive logging only
    engine = None  # type: ignore
    Base = None  # type: ignore
    logging.getLogger(__name__).warning("Database imports failed: %s", exc)

# OpenTelemetry tracing imports (optional)
try:
    from .telemetry import init_tracing, TracingConfig
    from .telemetry.middleware import setup_fastapi_tracing
    TRACING_AVAILABLE = True
except ImportError as e:
    TRACING_AVAILABLE = False
    logging.getLogger(__name__).info("OpenTelemetry tracing not available: %s", e)

# Configure logging - use structured logging if available
if ERROR_HANDLING_AVAILABLE:
    json_format = os.environ.get("LOG_FORMAT", "").lower() == "json"
    configure_logging(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        json_format=json_format,
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events using the modern lifespan pattern
    instead of deprecated @app.on_event decorators.
    """
    # === STARTUP ===
    port = os.environ.get('PORT', '8080')
    logger.info(f"Application starting on port {port}")
    logger.info("LLMHive Orchestrator API is ready")
    validate_startup_config()
    
    # Initialize OpenTelemetry tracing (SDK only, not middleware)
    # NOTE: Middleware cannot be added during lifespan in newer FastAPI versions
    # The tracing middleware is now set up before app.include_router() calls
    if TRACING_AVAILABLE:
        tracing_config = TracingConfig(
            service_name="llmhive-orchestrator",
            service_version="1.0.0",
            otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
            use_console_exporter=os.environ.get("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
        )
        if init_tracing(tracing_config):
            logger.info("✓ OpenTelemetry tracing SDK initialized")
            # NOTE: setup_fastapi_tracing is now called after app creation, not here
        else:
            logger.warning("OpenTelemetry tracing initialization failed")
    else:
        logger.info("OpenTelemetry tracing not available (install opentelemetry packages)")
    
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
    
    yield  # Application runs here
    
    # === SHUTDOWN ===
    logger.info("Application shutting down")


# Initialize FastAPI application with lifespan handler
app = FastAPI(
    title="LLMHive Orchestrator API",
    description="Multi-model orchestration service for LLM interactions",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS with specific origins
origins = [
    "https://llmhive.vercel.app",
    "https://llmhive.ai",
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Allow Vercel preview deployments (e.g., https://llmhive-*.vercel.app)
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request Tracking Middleware
# =============================================================================

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and correlation IDs.
    
    Adds:
    - X-Request-ID header (generated or from client)
    - X-Correlation-ID header for request tracing
    - Request timing metrics
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            if ERROR_HANDLING_AVAILABLE:
                correlation_id = generate_correlation_id()
            else:
                correlation_id = str(uuid.uuid4())[:8]
        
        # Set context variables
        if ERROR_HANDLING_AVAILABLE:
            set_correlation_id(correlation_id)
            request_id_var.set(request_id)
            
            # Extract user/session IDs if present
            user_id = request.headers.get("X-User-ID", "")
            session_id = request.headers.get("X-Session-ID", "")
            user_id_var.set(user_id)
            session_id_var.set(session_id)
            
            # Start request metrics
            metrics = start_request_metrics(request_id, correlation_id)
        
        # Store in request state for access in routes
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Add tracking headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.0f}"
            
            # Log request completion
            logger.info(
                "%s %s %d %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            
            # End request metrics
            if ERROR_HANDLING_AVAILABLE:
                end_request_metrics(success=response.status_code < 400)
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            logger.error(
                "%s %s failed after %.0fms: %s",
                request.method,
                request.url.path,
                duration_ms,
                str(e),
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            
            # End request metrics with error
            if ERROR_HANDLING_AVAILABLE:
                end_request_metrics(success=False, error=str(e))
            
            raise


# =============================================================================
# Error Handling Middleware
# =============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling.
    
    Catches all exceptions and returns standardized error responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
            
        except Exception as e:
            # Get request tracking info
            request_id = getattr(request.state, "request_id", None)
            correlation_id = getattr(request.state, "correlation_id", None)
            
            # Build error response
            if ERROR_HANDLING_AVAILABLE and isinstance(e, LLMHiveError):
                error_response = build_error_response(e, request_id=request_id)
                status_code = self._get_status_code(e.code)
            elif ERROR_HANDLING_AVAILABLE:
                # Wrap generic exceptions
                error_response = build_error_response(e, request_id=request_id)
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            else:
                # Fallback without error handling module
                error_response = type('ErrorResponse', (), {
                    'to_dict': lambda self: {
                        "error": {
                            "code": "E1000",
                            "message": str(e),
                            "details": {},
                            "recoverable": True,
                        },
                        "correlation_id": correlation_id or "unknown",
                        "request_id": request_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                })()
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            response = JSONResponse(
                status_code=status_code,
                content=error_response.to_dict(),
            )
            
            # Add tracking headers
            if request_id:
                response.headers["X-Request-ID"] = request_id
            if correlation_id:
                response.headers["X-Correlation-ID"] = correlation_id
            
            return response
    
    def _get_status_code(self, error_code) -> int:
        """Map error code to HTTP status code."""
        if not ERROR_HANDLING_AVAILABLE:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        
        status_mapping = {
            ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
            ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
            ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
            ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
            ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
            ErrorCode.PROVIDER_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.PROVIDER_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
            ErrorCode.PROVIDER_RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.ALL_PROVIDERS_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.CIRCUIT_OPEN: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
            ErrorCode.CONTENT_POLICY_VIOLATION: status.HTTP_400_BAD_REQUEST,
            ErrorCode.TIER_LIMIT_EXCEEDED: status.HTTP_403_FORBIDDEN,
            ErrorCode.QUOTA_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
        }
        return status_mapping.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Add middleware (order matters - error handling should be first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestTrackingMiddleware)

# Set up OpenTelemetry tracing middleware (must be done before app starts)
if TRACING_AVAILABLE:
    try:
        tracing_config = TracingConfig(
            service_name="llmhive-orchestrator",
            service_version="1.0.0",
            otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
            use_console_exporter=os.environ.get("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
        )
        setup_fastapi_tracing(app, tracing_config)
        logger.info("OpenTelemetry tracing middleware configured")
    except Exception as e:
        logger.warning(f"Failed to setup OpenTelemetry tracing: {e}")


# Create database tables (if DB is configured)
if Base is not None and engine is not None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.warning("Application will continue but database operations may fail")

# Define root-level endpoints before including routers
# IMPORTANT: Health check endpoints must be defined FIRST to ensure proper registration
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


@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint for basic verification."""
    logger.info("Root endpoint called")
    return {
        "service": "LLMHive Orchestrator API",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/health/ready", include_in_schema=False)
async def readiness_check() -> dict:
    """Readiness check with provider and circuit breaker status."""
    from .orchestrator import Orchestrator
    orch = Orchestrator()
    providers = list(orch.providers.keys())
    
    result = {
        "status": "ready",
        "providers": providers,
        "provider_count": len(providers),
    }
    
    # Add circuit breaker status if available
    if ERROR_HANDLING_AVAILABLE:
        breaker = get_circuit_breaker()
        result["circuit_breakers"] = breaker.get_all_stats()
    
    return result


@app.get("/health/live", include_in_schema=False)
async def liveness_check() -> dict[str, str]:
    """Simple liveness check (just confirms the process is running)."""
    return {"status": "alive"}

# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Include execute router (at /v1/execute/python)
from .routers import execute as execute_router
app.include_router(execute_router.router)

# Include stub endpoints (file analysis, image generation, data visualization, collaboration)
from .routers import stubs as stubs_router
app.include_router(stubs_router.router)

# Include chat router (at /v1/chat)
from .routers import chat as chat_router
app.include_router(chat_router.router)

# Include agents router (at /v1/agents)
from .routers import agents as agents_router
app.include_router(agents_router.router)

# Include reasoning config router (at /v1/reasoning-config)
from .routers import reasoning_config as reasoning_config_router
app.include_router(reasoning_config_router.router)

# Include clarification router (at /v1/clarify)
from .routers import clarification as clarification_router
app.include_router(clarification_router.router)
