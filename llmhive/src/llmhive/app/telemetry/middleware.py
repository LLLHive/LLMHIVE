"""FastAPI Middleware for OpenTelemetry Tracing.

Automatically traces all incoming HTTP requests with relevant metadata.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .tracing import (
    OTEL_AVAILABLE,
    init_tracing,
    get_current_span,
    add_span_attributes,
    record_exception,
    TracingConfig,
)

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FASTAPI_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    FASTAPI_INSTRUMENTATION_AVAILABLE = False
    FastAPIInstrumentor = None


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware that adds tracing context and correlation IDs to requests."""
    
    def __init__(
        self,
        app,
        config: Optional[TracingConfig] = None,
        exclude_paths: Optional[list] = None,
    ):
        """Initialize tracing middleware.
        
        Args:
            app: The FastAPI application.
            config: Tracing configuration.
            exclude_paths: Paths to exclude from tracing (e.g., health checks).
        """
        super().__init__(app)
        self.config = config or TracingConfig()
        self.exclude_paths = exclude_paths or [
            "/healthz",
            "/health",
            "/_ah/health",
            "/favicon.ico",
            "/metrics",
        ]
        
        # Initialize tracing
        init_tracing(self.config)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing context.
        
        Args:
            request: The incoming request.
            call_next: The next middleware/handler.
            
        Returns:
            The response with tracing headers.
        """
        # Skip tracing for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate or extract correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            request.headers.get("X-Request-ID", str(uuid.uuid4()))
        )
        
        # Store correlation ID in request state for use in handlers
        request.state.correlation_id = correlation_id
        
        # Record start time
        start_time = time.perf_counter()
        
        # Add request attributes to current span (if active)
        span = get_current_span()
        if span:
            add_span_attributes({
                "http.correlation_id": correlation_id,
                "http.method": request.method,
                "http.url": str(request.url),
                "http.route": request.url.path,
                "http.client_ip": request.client.host if request.client else "unknown",
                "http.user_agent": request.headers.get("user-agent", "unknown"),
            })
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Add response attributes
            if span:
                add_span_attributes({
                    "http.status_code": response.status_code,
                    "http.duration_ms": duration_ms,
                })
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-Duration-Ms"] = str(int(duration_ms))
            
            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": int(duration_ms),
                },
            )
            
            return response
            
        except Exception as e:
            # Record exception in span
            record_exception(e, {"http.correlation_id": correlation_id})
            
            # Calculate duration even for errors
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            logger.exception(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": int(duration_ms),
                    "error": str(e),
                },
            )
            raise


def setup_fastapi_tracing(app, config: Optional[TracingConfig] = None) -> None:
    """Set up automatic tracing for a FastAPI application.
    
    This uses the OpenTelemetry FastAPI instrumentation if available,
    otherwise falls back to the custom middleware.
    
    Args:
        app: The FastAPI application instance.
        config: Tracing configuration.
    """
    config = config or TracingConfig()
    
    # Initialize tracing first
    init_tracing(config)
    
    if FASTAPI_INSTRUMENTATION_AVAILABLE and OTEL_AVAILABLE:
        # Use OpenTelemetry's automatic instrumentation
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=",".join([
                "healthz",
                "health",
                "_ah/health",
                "favicon.ico",
                "metrics",
            ]),
        )
        logger.info("FastAPI automatic instrumentation enabled")
    
    # Always add our middleware for correlation IDs and custom attributes
    app.add_middleware(
        TracingMiddleware,
        config=config,
    )
    logger.info("Tracing middleware added to FastAPI app")
