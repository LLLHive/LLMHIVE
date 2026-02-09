"""API endpoints for query status updates and system diagnostics."""
from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import tracing utilities for diagnostics
try:
    from ..telemetry.tracing import (
        OTEL_AVAILABLE,
        OTLP_AVAILABLE,
        GCP_TRACE_AVAILABLE,
        get_tracer,
        get_current_span,
        trace_tool,
        is_tracing_initialized,
        get_tracing_config,
    )
    from opentelemetry import trace as otel_trace
    TRACING_IMPORTS_OK = True
except ImportError as e:
    OTEL_AVAILABLE = False
    OTLP_AVAILABLE = False
    GCP_TRACE_AVAILABLE = False
    TRACING_IMPORTS_OK = False
    is_tracing_initialized = lambda: False
    get_tracing_config = lambda: None
    otel_trace = None
    logger.info("Tracing imports not available: %s", e)

# Import SymPy status
try:
    import sympy
    SYMPY_AVAILABLE = True
    SYMPY_VERSION = sympy.__version__
except ImportError:
    SYMPY_AVAILABLE = False
    SYMPY_VERSION = None

# Included in api/__init__.py with prefix "/status"
router = APIRouter()

# In-memory status store (in production, use Redis or database)
_status_store: Dict[str, Dict[str, Any]] = {}


@router.get("/{query_id}", status_code=status.HTTP_200_OK)
def get_status(query_id: str) -> Dict[str, Any]:
    """
    Get the current status of a query.
    
    Returns status information including:
    - stage: Current processing stage (e.g., "planning", "model_query", "verification", "complete")
    - status: Status of current stage (e.g., "running", "completed", "error")
    - model: Current model being used (if applicable)
    - progress: Progress percentage (0-100)
    - message: Human-readable status message
    - timestamp: Last update timestamp
    """
    if query_id not in _status_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID '{query_id}' not found"
        )
    
    return _status_store[query_id]


@router.post("/{query_id}", status_code=status.HTTP_200_OK)
def update_status(
    query_id: str,
    stage: str,
    status_value: str = "running",
    model: Optional[str] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update the status of a query.
    
    This endpoint is called internally by the orchestrator to update query status.
    """
    _status_store[query_id] = {
        "query_id": query_id,
        "stage": stage,
        "status": status_value,
        "model": model,
        "progress": progress,
        "message": message or f"Processing: {stage}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.debug("Status updated for query %s: %s - %s", query_id, stage, status_value)
    return _status_store[query_id]


@router.delete("/{query_id}", status_code=status.HTTP_200_OK)
def clear_status(query_id: str) -> Dict[str, str]:
    """Clear status for a query (cleanup after completion)."""
    if query_id in _status_store:
        del _status_store[query_id]
        logger.debug("Status cleared for query %s", query_id)
    return {"message": f"Status cleared for query {query_id}"}


# =============================================================================
# DIAGNOSTICS ENDPOINTS
# =============================================================================

@router.get("/diagnostics/tracing", status_code=status.HTTP_200_OK)
def get_tracing_diagnostics() -> Dict[str, Any]:
    """
    Get OpenTelemetry tracing diagnostics and status.
    
    Returns comprehensive information about:
    - Whether OpenTelemetry is installed and available
    - Which exporters are configured (OTLP, GCP Trace, Console)
    - Current span/trace IDs if tracing is active
    - Environment variable configuration
    
    Use this endpoint to verify tracing is working correctly.
    """
    # Get current tracing state dynamically (not at module load time)
    tracing_initialized = is_tracing_initialized() if TRACING_IMPORTS_OK else False
    tracing_config = get_tracing_config() if TRACING_IMPORTS_OK else None
    
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "opentelemetry": {
            "available": OTEL_AVAILABLE,
            "imports_ok": TRACING_IMPORTS_OK,
            "initialized": tracing_initialized,
        },
        "exporters": {
            "otlp_available": OTLP_AVAILABLE,
            "gcp_trace_available": GCP_TRACE_AVAILABLE,
        },
        "environment": {
            "OTEL_EXPORTER_OTLP_ENDPOINT": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "(not set)"),
            "OTEL_USE_GCP_TRACE": os.getenv("OTEL_USE_GCP_TRACE", "(not set)"),
            "OTEL_CONSOLE_EXPORT": os.getenv("OTEL_CONSOLE_EXPORT", "(not set)"),
            "GCP_PROJECT_ID": os.getenv("GCP_PROJECT_ID", "(not set)"),
            "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT", "(not set)"),
            "OTEL_SAMPLE_RATE": os.getenv("OTEL_SAMPLE_RATE", "(not set, default 1.0)"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "(not set, default development)"),
        },
        "current_span": None,
        "recommendations": [],
    }
    
    # Check tracing configuration
    if TRACING_IMPORTS_OK and tracing_config:
        diagnostics["config"] = {
            "service_name": tracing_config.service_name,
            "service_version": tracing_config.service_version,
            "environment": tracing_config.environment,
            "otlp_endpoint": tracing_config.otlp_endpoint,
            "use_gcp_trace": tracing_config.use_gcp_trace,
            "use_console_exporter": tracing_config.use_console_exporter,
            "sample_rate": tracing_config.sample_rate,
        }
    
    # Get current span info if available
    if OTEL_AVAILABLE and otel_trace:
        try:
            span = otel_trace.get_current_span()
            if span and hasattr(span, 'get_span_context'):
                ctx = span.get_span_context()
                if ctx and ctx.is_valid:
                    diagnostics["current_span"] = {
                        "trace_id": format(ctx.trace_id, '032x'),
                        "span_id": format(ctx.span_id, '016x'),
                        "is_recording": span.is_recording() if hasattr(span, 'is_recording') else None,
                    }
        except Exception as e:
            diagnostics["current_span"] = {"error": str(e)}
    
    # Generate recommendations
    if not OTEL_AVAILABLE:
        diagnostics["recommendations"].append(
            "Install OpenTelemetry: pip install opentelemetry-api opentelemetry-sdk"
        )
    if not OTLP_AVAILABLE:
        diagnostics["recommendations"].append(
            "Install OTLP exporter: pip install opentelemetry-exporter-otlp"
        )
    if not GCP_TRACE_AVAILABLE:
        diagnostics["recommendations"].append(
            "Install GCP Trace: pip install opentelemetry-exporter-gcp-trace"
        )
    if OTEL_AVAILABLE and not tracing_initialized:
        diagnostics["recommendations"].append(
            "Tracing not initialized - check startup logs for errors"
        )
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") and not os.getenv("OTEL_USE_GCP_TRACE"):
        diagnostics["recommendations"].append(
            "Set OTEL_EXPORTER_OTLP_ENDPOINT or OTEL_USE_GCP_TRACE=true to enable trace export"
        )
    
    if not diagnostics["recommendations"]:
        diagnostics["recommendations"].append("✓ Tracing appears to be configured correctly")
    
    return diagnostics


@router.get("/diagnostics/tracing/test", status_code=status.HTTP_200_OK)
async def test_tracing_span() -> Dict[str, Any]:
    """
    Create a test span to verify tracing is working.
    
    This endpoint:
    1. Creates a test span with sample attributes
    2. Logs the trace/span ID for verification
    3. Returns the IDs for manual checking in your trace backend
    
    Check your trace backend (GCP Trace, Jaeger, etc.) for this span.
    """
    import time
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_name": "tracing_verification_test",
        "tracing_available": OTEL_AVAILABLE,
        "span_created": False,
        "trace_id": None,
        "span_id": None,
    }
    
    if not OTEL_AVAILABLE or not TRACING_IMPORTS_OK:
        result["error"] = "OpenTelemetry not available"
        return result
    
    try:
        tracer = get_tracer()
        if not tracer:
            result["error"] = "Tracer not initialized"
            return result
        
        # Create a test span
        with tracer.start_as_current_span(
            "diagnostics.tracing.test",
            attributes={
                "test.type": "manual_verification",
                "test.timestamp": result["timestamp"],
                "test.endpoint": "/api/v1/system/diagnostics/tracing/test",
            }
        ) as span:
            # Simulate some work
            time.sleep(0.01)
            
            # Add more attributes
            span.set_attribute("test.step", "processing")
            span.add_event("test_event", {"detail": "Verification test running"})
            
            # Get span context
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                result["trace_id"] = format(ctx.trace_id, '032x')
                result["span_id"] = format(ctx.span_id, '016x')
                result["span_created"] = True
                
                # Log for easy verification
                logger.info(
                    "Tracing test span created: trace_id=%s span_id=%s",
                    result["trace_id"],
                    result["span_id"]
                )
            
            # Simulate more work
            time.sleep(0.01)
            span.set_attribute("test.step", "completed")
        
        result["message"] = (
            f"Test span created. Look for trace_id={result['trace_id']} "
            "in your trace backend (GCP Trace, Jaeger, etc.)"
        )
        
    except Exception as e:
        result["error"] = str(e)
        logger.exception("Tracing test failed: %s", e)
    
    return result


@router.get("/diagnostics/sympy", status_code=status.HTTP_200_OK)
def get_sympy_diagnostics() -> Dict[str, Any]:
    """
    Get SymPy diagnostics for math verification.
    
    Returns:
    - Whether SymPy is installed
    - Version information
    - Test calculation to verify it's working
    """
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sympy": {
            "available": SYMPY_AVAILABLE,
            "version": SYMPY_VERSION,
        },
        "test_result": None,
        "recommendations": [],
    }
    
    if SYMPY_AVAILABLE:
        try:
            # Run a simple test
            x = sympy.Symbol('x')
            expr = x**2 + 2*x + 1
            factored = sympy.factor(expr)
            
            diagnostics["test_result"] = {
                "expression": str(expr),
                "factored": str(factored),
                "success": str(factored) == "(x + 1)**2",
            }
            
            # Test equation solving
            solution = sympy.solve(x**2 - 4, x)
            diagnostics["test_result"]["equation_solve"] = {
                "equation": "x² - 4 = 0",
                "solutions": [str(s) for s in solution],
            }
            
        except Exception as e:
            diagnostics["test_result"] = {"error": str(e)}
    else:
        diagnostics["recommendations"].append(
            "Install SymPy for advanced math verification: pip install sympy>=1.12"
        )
    
    return diagnostics


@router.get("/diagnostics/config", status_code=status.HTTP_200_OK)
def get_config_diagnostics() -> Dict[str, Any]:
    """
    Get configuration and environment variable loading diagnostics.
    
    CRITICAL: Use this endpoint to verify environment variables are properly
    loaded on serverless cold starts. This helps diagnose intermittent
    "API key not found" errors.
    
    Returns:
    - Whether Pydantic BaseSettings is being used (lazy loading)
    - Which API keys are configured (without exposing values)
    - Configuration validation results
    - Timestamp for monitoring cold start behavior
    """
    from ..config import get_settings, reset_settings
    
    # Force fresh load to test current environment state
    reset_settings()
    settings = get_settings()
    
    diagnostics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config_system": "Pydantic BaseSettings (lazy loading)",
        "environment": settings.environment,
        "debug_mode": settings.debug,
        "api_keys_loaded": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "claude": bool(settings.claude_api_key),
            "grok": bool(settings.grok_api_key),
            "gemini": bool(settings.gemini_api_key),
            "deepseek": bool(settings.deepseek_api_key),
            "manus": bool(settings.manus_api_key),
            "together": bool(settings.together_api_key),
            "pinecone": bool(settings.pinecone_api_key),
            "stripe": bool(settings.stripe_api_key),
            "llmhive_auth": bool(settings.api_key),
        },
        "provider_count": len([k for k, v in {
            "openai": settings.openai_api_key,
            "anthropic": settings.get_anthropic_key(),
            "grok": settings.grok_api_key,
            "gemini": settings.gemini_api_key,
            "deepseek": settings.deepseek_api_key,
            "together": settings.get_together_key(),
        }.items() if v]),
        "configuration": {
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "log_level": settings.log_level,
            "cors_origins_count": len(settings.cors_origins),
            "rate_limit_rpm": settings.rate_limit_requests_per_minute,
            "memory_ttl_days": settings.memory_ttl_days,
            "pinecone_index": settings.pinecone_index_name if settings.pinecone_api_key else None,
        },
        "recommendations": [],
    }
    
    # Validate configuration
    validation = settings.validate(strict=False)
    diagnostics["validation"] = {
        "is_valid": validation.is_valid,
        "providers_available": validation.available_providers,
        "warnings_count": len(validation.warnings),
        "errors_count": len(validation.errors),
        "warnings": validation.warnings,
        "errors": validation.errors,
    }
    
    # Generate recommendations
    if diagnostics["provider_count"] == 0:
        diagnostics["recommendations"].append(
            "⚠️ CRITICAL: No LLM provider API keys configured. "
            "Set at least one: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY"
        )
    elif diagnostics["provider_count"] < 3:
        diagnostics["recommendations"].append(
            f"ℹ️ Only {diagnostics['provider_count']} provider(s) configured. "
            "Consider adding more for redundancy and model diversity."
        )
    else:
        diagnostics["recommendations"].append(
            f"✓ Good: {diagnostics['provider_count']} LLM providers configured"
        )
    
    if not settings.pinecone_api_key:
        diagnostics["recommendations"].append(
            "ℹ️ PINECONE_API_KEY not set - RAG/memory features disabled"
        )
    
    if not settings.stripe_api_key:
        diagnostics["recommendations"].append(
            "ℹ️ STRIPE_SECRET_KEY not set - billing features disabled"
        )
    
    if settings.debug and settings.environment == "production":
        diagnostics["recommendations"].append(
            "⚠️ WARNING: DEBUG=true in production environment!"
        )
    
    if not diagnostics["recommendations"]:
        diagnostics["recommendations"].append("✓ Configuration looks healthy")
    
    return diagnostics


@router.get("/diagnostics/all", status_code=status.HTTP_200_OK)
async def get_all_diagnostics() -> Dict[str, Any]:
    """
    Get all system diagnostics in one call.
    
    Combines config, tracing, SymPy, and other diagnostic information.
    """
    config_diag = get_config_diagnostics()
    tracing = get_tracing_diagnostics()
    sympy_diag = get_sympy_diagnostics()
    tracing_test = await test_tracing_span()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config_diag,
        "tracing": tracing,
        "tracing_test": tracing_test,
        "sympy": sympy_diag,
        "overall_status": {
            "config_ok": config_diag["provider_count"] > 0,
            "tracing_ok": tracing["opentelemetry"]["initialized"] if tracing["opentelemetry"]["available"] else False,
            "sympy_ok": sympy_diag["sympy"]["available"],
            "all_ok": (
                config_diag["provider_count"] > 0
                and sympy_diag["sympy"]["available"]
            ),
        },
    }

