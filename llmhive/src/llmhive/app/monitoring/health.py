"""Health Checks for LLMHive.

This module provides:
- Liveness and readiness probes
- Dependency health checks (Redis, DB, LLM providers)
- System resource monitoring
- Graceful degradation detection

Usage:
    checker = get_health_checker()
    
    # Quick liveness check
    is_alive = await checker.is_alive()
    
    # Full health check
    health = await checker.check_health()
"""
from __future__ import annotations

import asyncio
import logging
import os
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(slots=True)
class ComponentHealth:
    """Health status of a component."""
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    timestamp: datetime
    version: str
    uptime_seconds: float
    components: List[ComponentHealth] = field(default_factory=list)
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "latency_ms": round(c.latency_ms, 2),
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.components
            ],
            "system": self.system_metrics,
        }


# ==============================================================================
# Health Checker
# ==============================================================================

class HealthChecker:
    """Health checker for LLMHive.
    
    Provides comprehensive health monitoring:
    - Liveness: Is the app running?
    - Readiness: Can the app handle requests?
    - Component checks: Are dependencies healthy?
    
    Usage:
        checker = HealthChecker()
        
        # Register custom checks
        checker.register_check("database", check_database)
        
        # Run health check
        health = await checker.check_health()
    """
    
    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self._start_time = time.time()
        self._checks: Dict[str, Callable] = {}
        
        # Register default checks
        self._setup_default_checks()
    
    def _setup_default_checks(self) -> None:
        """Setup default health checks."""
        self.register_check("system", self._check_system)
    
    def register_check(
        self,
        name: str,
        check_fn: Callable,
    ) -> None:
        """Register a health check function.
        
        Args:
            name: Check name
            check_fn: Async function returning ComponentHealth
        """
        self._checks[name] = check_fn
        logger.debug("Registered health check: %s", name)
    
    async def is_alive(self) -> bool:
        """Quick liveness check."""
        return True
    
    async def is_ready(self) -> bool:
        """Check if system is ready to serve requests."""
        try:
            health = await self.check_health()
            return health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        except Exception:
            return False
    
    async def check_health(self) -> SystemHealth:
        """Run all health checks and return overall status."""
        components: List[ComponentHealth] = []
        
        # Run all checks concurrently
        tasks = [
            self._run_check(name, check_fn)
            for name, check_fn in self._checks.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, ComponentHealth):
                components.append(result)
            elif isinstance(result, Exception):
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                ))
        
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        for comp in components:
            if comp.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif comp.status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            version=self.version,
            uptime_seconds=time.time() - self._start_time,
            components=components,
            system_metrics=self._get_system_metrics(),
        )
    
    async def _run_check(
        self,
        name: str,
        check_fn: Callable,
    ) -> ComponentHealth:
        """Run a single health check with timing."""
        start = time.time()
        
        try:
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = await asyncio.to_thread(check_fn)
            
            if isinstance(result, ComponentHealth):
                result.latency_ms = (time.time() - start) * 1000
                return result
            
            return ComponentHealth(
                name=name,
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
            )
            
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message=str(e),
            )
    
    async def _check_system(self) -> ComponentHealth:
        """Check system resources."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            status = HealthStatus.HEALTHY
            messages = []
            
            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                messages.append(f"High CPU: {cpu_percent}%")
            
            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                messages.append(f"High memory: {memory.percent}%")
            
            if disk.percent > 90:
                status = HealthStatus.DEGRADED
                messages.append(f"High disk: {disk.percent}%")
            
            return ComponentHealth(
                name="system",
                status=status,
                message="; ".join(messages) if messages else "System resources OK",
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available // (1024 * 1024),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free // (1024 * 1024 * 1024),
                },
            )
            
        except Exception as e:
            return ComponentHealth(
                name="system",
                status=HealthStatus.DEGRADED,
                message=f"Could not check system: {e}",
            )
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_total_mb": psutil.virtual_memory().total // (1024 * 1024),
                "memory_available_mb": psutil.virtual_memory().available // (1024 * 1024),
                "process_memory_mb": psutil.Process().memory_info().rss // (1024 * 1024),
            }
        except Exception:
            return {}


# ==============================================================================
# Pre-built Check Functions
# ==============================================================================

async def check_redis(redis_url: Optional[str] = None) -> ComponentHealth:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(url)
        
        start = time.time()
        await client.ping()
        latency = (time.time() - start) * 1000
        
        await client.close()
        
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Redis connected",
        )
        
    except ImportError:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,  # Not required
            message="Redis client not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis error: {e}",
        )


async def check_database(db_url: Optional[str] = None) -> ComponentHealth:
    """Check database connectivity."""
    try:
        # Placeholder - implement based on your DB
        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database check skipped (not configured)",
        )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database error: {e}",
        )


async def check_llm_provider(provider_name: str, test_fn: Callable) -> ComponentHealth:
    """Check LLM provider health."""
    try:
        start = time.time()
        await test_fn()
        latency = (time.time() - start) * 1000
        
        return ComponentHealth(
            name=f"llm_{provider_name}",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message=f"{provider_name} API responding",
        )
        
    except Exception as e:
        return ComponentHealth(
            name=f"llm_{provider_name}",
            status=HealthStatus.DEGRADED,
            message=f"{provider_name} error: {e}",
        )


# ==============================================================================
# Global Instance
# ==============================================================================

_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker."""
    global _health_checker
    if _health_checker is None:
        version = os.getenv("LLMHIVE_VERSION", "1.0.0")
        _health_checker = HealthChecker(version=version)
    return _health_checker


# ==============================================================================
# FastAPI Integration
# ==============================================================================

def setup_health_endpoints(app):
    """Setup health check endpoints."""
    from fastapi import Response
    
    @app.get("/healthz")
    async def liveness():
        """Kubernetes liveness probe."""
        checker = get_health_checker()
        if await checker.is_alive():
            return {"status": "ok"}
        return Response(status_code=503, content='{"status": "unhealthy"}')
    
    @app.get("/readyz")
    async def readiness():
        """Kubernetes readiness probe."""
        checker = get_health_checker()
        if await checker.is_ready():
            return {"status": "ok"}
        return Response(status_code=503, content='{"status": "not ready"}')
    
    @app.get("/health")
    async def full_health():
        """Full health check."""
        checker = get_health_checker()
        health = await checker.check_health()
        
        status_code = 200
        if health.status == HealthStatus.DEGRADED:
            status_code = 200  # Still serving
        elif health.status == HealthStatus.UNHEALTHY:
            status_code = 503
        
        return Response(
            status_code=status_code,
            content=__import__('json').dumps(health.to_dict()),
            media_type="application/json",
        )
    
    logger.info("Health endpoints registered: /healthz, /readyz, /health")

