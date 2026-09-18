"""Admin Router - System administration and optimization endpoints.

This router provides:
- Weekly optimization trigger
- System health checks
- Feature flag management
- Performance metrics
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel

from ..auto_improve import (
    gather_improvement_data,
    plan_improvements,
    run_auto_improve_cycle,
    ImprovementItem,
)
from ..feature_flags import (
    FeatureFlags,
    is_feature_enabled,
    get_all_feature_states,
    enable_feature,
    disable_feature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class WeeklyOptimizeRequest(BaseModel):
    lookback_days: int = 7
    apply_safe_changes: bool = False
    run_benchmarks: bool = False


class WeeklyOptimizeResponse(BaseModel):
    success: bool
    message: str
    improvements_found: int
    improvements_applied: int
    plan: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    timestamp: str


class FeatureFlagRequest(BaseModel):
    feature: str
    enabled: bool


class FeatureFlagResponse(BaseModel):
    feature: str
    enabled: bool
    success: bool


class SystemHealthResponse(BaseModel):
    status: str
    version: str
    features_enabled: List[str]
    features_disabled: List[str]
    uptime_seconds: float
    timestamp: str


# ==============================================================================
# Security
# ==============================================================================

def verify_admin_access(
    x_cron_secret: Optional[str] = Header(None),
    x_admin_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> bool:
    """Verify admin access via cron secret or admin key."""
    import os
    
    cron_secret = (os.getenv("CRON_SECRET") or "").strip()
    admin_key = (
        (os.getenv("ADMIN_API_KEY") or "").strip()
        or (os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY") or "").strip()
    )

    provided_cron = (x_cron_secret or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        provided_cron = provided_cron or authorization.split(" ", 1)[1].strip()
    provided_admin = (x_admin_key or "").strip()
    
    # Allow if no secrets configured (dev mode)
    if not cron_secret and not admin_key:
        logger.warning("Admin endpoints accessible without auth (no secrets configured)")
        return True
    
    # Check cron secret
    if cron_secret and provided_cron and provided_cron == cron_secret:
        return True
    
    # Check admin key
    if admin_key and provided_admin and provided_admin == admin_key:
        return True
    
    return False


# ==============================================================================
# Weekly Optimization Endpoint
# ==============================================================================

@router.post("/weekly-optimize", response_model=WeeklyOptimizeResponse)
async def weekly_optimize(
    request: WeeklyOptimizeRequest,
    background_tasks: BackgroundTasks,
    x_cron_secret: Optional[str] = Header(None),
    x_admin_key: Optional[str] = Header(None),
):
    """
    Trigger the weekly optimization cycle.
    
    This endpoint:
    1. Gathers feedback and performance data from the past N days
    2. Identifies patterns in failures and user complaints
    3. Creates an improvement plan with prioritized items
    4. Optionally applies safe configuration changes
    5. Optionally runs benchmarks to verify improvements
    
    Security: Requires CRON_SECRET or ADMIN_API_KEY header.
    """
    if not verify_admin_access(x_cron_secret, x_admin_key):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    logger.info(
        "Starting weekly optimization (lookback=%d days, apply_safe=%s)",
        request.lookback_days,
        request.apply_safe_changes,
    )
    
    try:
        # Gather improvement data
        data = gather_improvement_data(
            lookback_days=request.lookback_days,
            max_feedback=500,
        )
        
        logger.info(
            "Gathered data: %d failures, %d requests, %d metrics",
            len(data.common_failures),
            len(data.user_requests),
            len(data.metrics),
        )
        
        # Plan improvements
        plan = plan_improvements(data)
        
        # Count by status
        improvements_applied = sum(1 for p in plan if p.status == "done")
        improvements_pending = sum(1 for p in plan if p.status in ("planned", "applied_pending_test"))
        
        # Optionally apply safe changes
        config: Dict[str, Any] = {}
        if request.apply_safe_changes:
            plan = await run_auto_improve_cycle(
                config=config,
                apply_safe_changes=True,
                run_verifier=None,
            )
            improvements_applied = sum(1 for p in plan if p.status in ("done", "applied_pending_test"))
        
        # Build response
        plan_dicts = [
            {
                "id": p.id,
                "description": p.description,
                "status": p.status,
                "priority": p.priority,
                "created_at": p.created_at,
            }
            for p in plan
        ]
        
        metrics_summary = {
            "common_failures": data.common_failures[:10],
            "user_requests": data.user_requests[:10],
            "models_tracked": data.metrics.get("models_tracked", 0),
            "samples_collected": len(data.samples),
        }
        
        logger.info(
            "Weekly optimization complete: %d improvements found, %d applied",
            len(plan),
            improvements_applied,
        )
        
        return WeeklyOptimizeResponse(
            success=True,
            message=f"Optimization cycle complete: {len(plan)} items in plan",
            improvements_found=len(plan),
            improvements_applied=improvements_applied,
            plan=plan_dicts,
            metrics=metrics_summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
    except Exception as e:
        logger.error("Weekly optimization failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Feature Flags Management
# ==============================================================================

@router.get("/features")
async def get_features(
    x_admin_key: Optional[str] = Header(None),
):
    """Get all feature flag states."""
    states = get_all_feature_states()
    
    enabled = [k for k, v in states.items() if v]
    disabled = [k for k, v in states.items() if not v]
    
    return {
        "features": states,
        "enabled_count": len(enabled),
        "disabled_count": len(disabled),
        "enabled": enabled,
        "disabled": disabled,
    }


@router.post("/features", response_model=FeatureFlagResponse)
async def set_feature(
    request: FeatureFlagRequest,
    x_admin_key: Optional[str] = Header(None),
):
    """Enable or disable a feature flag (admin only)."""
    if not verify_admin_access(None, x_admin_key):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        feature = FeatureFlags(request.feature)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown feature: {request.feature}")
    
    if request.enabled:
        enable_feature(feature)
        logger.info("Feature %s enabled via admin API", request.feature)
    else:
        disable_feature(feature)
        logger.info("Feature %s disabled via admin API", request.feature)
    
    return FeatureFlagResponse(
        feature=request.feature,
        enabled=request.enabled,
        success=True,
    )


# ==============================================================================
# System Health
# ==============================================================================

_start_time = datetime.now(timezone.utc)


@router.get("/health", response_model=SystemHealthResponse)
async def admin_health():
    """Detailed system health check for admin dashboard."""
    states = get_all_feature_states()
    enabled = [k for k, v in states.items() if v]
    disabled = [k for k, v in states.items() if not v]
    
    now = datetime.now(timezone.utc)
    uptime = (now - _start_time).total_seconds()
    
    return SystemHealthResponse(
        status="healthy",
        version="0.2.0",
        features_enabled=enabled,
        features_disabled=disabled,
        uptime_seconds=uptime,
        timestamp=now.isoformat(),
    )


# ==============================================================================
# Performance Summary
# ==============================================================================

@router.get("/performance")
async def get_performance_summary(
    x_admin_key: Optional[str] = Header(None),
):
    """Get performance metrics summary."""
    try:
        from ..performance_tracker import performance_tracker
        
        if not performance_tracker:
            return {"available": False, "message": "Performance tracker not initialized"}
        
        snapshot = performance_tracker.snapshot()
        
        models_data = []
        for name, perf in snapshot.items():
            models_data.append({
                "model": name,
                "success_rate": getattr(perf, "success_rate", 0),
                "avg_latency_ms": getattr(perf, "avg_latency_ms", 0),
                "total_requests": getattr(perf, "total_requests", 0),
            })
        
        return {
            "available": True,
            "models_tracked": len(snapshot),
            "models": models_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.warning("Failed to get performance summary: %s", e)
        return {"available": False, "error": str(e)}


# ==============================================================================
# Prompt Diffusion Stats
# ==============================================================================

@router.get("/prompt-diffusion/stats")
async def get_prompt_diffusion_stats(
    x_admin_key: Optional[str] = Header(None),
):
    """Get prompt diffusion usage statistics."""
    # This would pull from actual usage data in production
    return {
        "enabled": is_feature_enabled(FeatureFlags.PROMPT_DIFFUSION),
        "total_refinements": 0,  # Would be pulled from metrics
        "avg_rounds": 0,
        "avg_improvement_score": 0,
        "most_used_roles": [],
        "note": "Stats collection requires production traffic",
    }


# ==============================================================================
# Pinecone Health & Smoke Tests
# ==============================================================================

@router.get("/pinecone/health")
async def pinecone_health(
    x_admin_key: Optional[str] = Header(None),
):
    """Get Pinecone connection health status (read-only).
    
    Returns per-index connection status without performing writes.
    """
    try:
        from ..knowledge.pinecone_registry import (
            get_pinecone_registry,
            IndexKind,
            INDEX_CONFIGS,
        )
        
        registry = get_pinecone_registry()
        health = registry.get_health_status()
        
        # Add friendly summary
        indexes_connected = sum(
            1 for idx_data in health.get("indexes", {}).values()
            if idx_data.get("connected")
        )
        indexes_configured = sum(
            1 for idx_data in health.get("indexes", {}).values()
            if idx_data.get("host_configured")
        )
        
        return {
            "status": "healthy" if indexes_connected > 0 else "degraded",
            "sdk_available": health.get("sdk_available", False),
            "api_key_set": health.get("api_key_set", False),
            "client_initialized": health.get("client_initialized", False),
            "require_hosts": health.get("require_hosts", False),
            "indexes_configured": indexes_configured,
            "indexes_connected": indexes_connected,
            "indexes": health.get("indexes", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error("Pinecone health check failed: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/pinecone/smoke")
async def pinecone_smoke_test(
    x_admin_key: Optional[str] = Header(None),
):
    """Run Pinecone smoke test (upsert/query/delete per index).
    
    Performs real write operations to verify full connectivity.
    Security: Requires admin access.
    """
    if not verify_admin_access(None, x_admin_key):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    import random
    import time
    
    SMOKE_NAMESPACE = "__llmhive_smoke__"
    
    try:
        from ..knowledge.pinecone_registry import (
            get_pinecone_registry,
            IndexKind,
        )
        
        registry = get_pinecone_registry()
        
        if not registry.is_available:
            return {
                "status": "failed",
                "error": "Pinecone registry not available",
                "results": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        results: Dict[str, Any] = {}
        
        for kind in IndexKind:
            index_key = kind.value
            test_id = f"smoke_{index_key}_{int(time.time())}_{random.randint(1000, 9999)}"
            
            try:
                idx = registry.get_index(kind)
                
                if not idx:
                    results[index_key] = {
                        "passed": False,
                        "error": "Index not connected",
                    }
                    continue
                
                # Get dimension from stats
                stats = idx.describe_index_stats()
                dimension = getattr(stats, 'dimension', 1024)  # Default for llama-embed
                vector_count = getattr(stats, 'total_vector_count', 0)
                
                # Generate test vector
                test_vector = [random.random() for _ in range(dimension)]
                
                # UPSERT
                try:
                    idx.upsert(
                        vectors=[(test_id, test_vector, {"test": True})],
                        namespace=SMOKE_NAMESPACE,
                    )
                except Exception as e:
                    # May fail for integrated embeddings indexes - still a connection success
                    if "integrated" in str(e).lower() or "records" in str(e).lower():
                        results[index_key] = {
                            "passed": True,
                            "note": "Connected (uses records API)",
                            "vector_count": vector_count,
                            "dimension": dimension,
                        }
                        continue
                    raise
                
                # Wait for consistency
                time.sleep(1)
                
                # QUERY
                found = False
                for _ in range(3):
                    try:
                        query_results = idx.query(
                            vector=test_vector,
                            top_k=1,
                            namespace=SMOKE_NAMESPACE,
                        )
                        if query_results.matches and query_results.matches[0].id == test_id:
                            found = True
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)
                
                # DELETE
                try:
                    idx.delete(ids=[test_id], namespace=SMOKE_NAMESPACE)
                except Exception:
                    pass
                
                results[index_key] = {
                    "passed": found,
                    "error": None if found else "Query did not return upserted vector",
                    "vector_count": vector_count,
                    "dimension": dimension,
                }
                
            except Exception as e:
                results[index_key] = {
                    "passed": False,
                    "error": str(e)[:200],
                }
        
        # Summary
        passed = sum(1 for r in results.values() if r.get("passed"))
        failed = sum(1 for r in results.values() if not r.get("passed"))
        
        return {
            "status": "passed" if failed == 0 else "failed",
            "passed": passed,
            "failed": failed,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error("Pinecone smoke test failed: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ==============================================================================
# Trial expiry reminder emails (1 day before)
# ==============================================================================

class TrialExpiryRemindersResponse(BaseModel):
    success: bool
    scanned: int = 0
    sent: int = 0
    skipped: int = 0
    errors: int = 0
    details: List[Dict[str, Any]] = []
    timestamp: str


def _as_utc_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            raw = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


@router.post("/trial-expiry-reminders", response_model=TrialExpiryRemindersResponse)
async def trial_expiry_reminders(
    x_cron_secret: Optional[str] = Header(None),
    x_admin_key: Optional[str] = Header(None),
    window_hours: float = 24.0,
    window_slack_hours: float = 6.0,
    dry_run: bool = False,
):
    """Email trialing users whose trial ends ~tomorrow, offering Standard at $10/mo.

    Selects Firestore ``status=trialing`` subscriptions with ``trial_end`` in
    ``[now + window_hours - slack, now + window_hours + slack]`` (default ~18–30h).
    Idempotent via ``trial_expiry_reminder_sent_at`` on the subscription doc.
    """
    if not verify_admin_access(x_cron_secret, x_admin_key, authorization=None):
        import os as _os
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Admin access required",
                "has_cron_header": bool((x_cron_secret or "").strip()),
                "has_admin_header": bool((x_admin_key or "").strip()),
                "has_cron_env": bool((_os.getenv("CRON_SECRET") or "").strip()),
                "has_admin_env": bool(
                    (_os.getenv("ADMIN_API_KEY") or _os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY") or "").strip()
                ),
            },
        )

    from ..firestore_db import FirestoreSubscriptionService, is_firestore_available
    from ..services.email import send_trial_expiring_email

    if not is_firestore_available():
        raise HTTPException(status_code=503, detail="Firestore unavailable")

    now = datetime.now(timezone.utc)
    center = now.timestamp() + (window_hours * 3600.0)
    slack = window_slack_hours * 3600.0
    window_start = datetime.fromtimestamp(center - slack, tz=timezone.utc)
    window_end = datetime.fromtimestamp(center + slack, tz=timezone.utc)

    service = FirestoreSubscriptionService()
    candidates = service.list_trialing_subscriptions(limit=1000)

    sent = skipped = errors = 0
    details: List[Dict[str, Any]] = []

    stripe_mod = None
    try:
        import stripe as _stripe
        import os as _os

        key = _os.getenv("STRIPE_SECRET_KEY") or _os.getenv("STRIPE_API_KEY")
        if key:
            _stripe.api_key = key
            stripe_mod = _stripe
    except Exception:
        stripe_mod = None

    for sub in candidates:
        sub_id = str(sub.get("id") or "")
        trial_end = _as_utc_dt(sub.get("trial_end"))
        if not trial_end or not (window_start <= trial_end <= window_end):
            continue

        if sub.get("trial_expiry_reminder_sent_at"):
            skipped += 1
            details.append({"id": sub_id, "status": "already_sent"})
            continue

        email = None
        name = None
        customer_id = sub.get("stripe_customer_id")
        if stripe_mod and customer_id:
            try:
                customer = stripe_mod.Customer.retrieve(str(customer_id))
                email = getattr(customer, "email", None) or (
                    customer.get("email") if hasattr(customer, "get") else None
                )
                name = getattr(customer, "name", None) or (
                    customer.get("name") if hasattr(customer, "get") else None
                )
            except Exception as exc:
                logger.warning(
                    "trial reminder: stripe lookup failed for %s: %s",
                    customer_id,
                    exc,
                )

        if not email:
            skipped += 1
            errors += 1
            details.append({"id": sub_id, "status": "no_email"})
            continue

        end_iso = trial_end.isoformat()
        if dry_run:
            sent += 1
            details.append(
                {
                    "id": sub_id,
                    "status": "dry_run",
                    "email": email,
                    "trial_end": end_iso,
                }
            )
            continue

        result = send_trial_expiring_email(
            to=str(email),
            customer_name=str(name) if name else None,
            trial_end_iso=end_iso,
            price_monthly_usd=10.0,
        )
        if result.get("sent"):
            if sub_id:
                service.update_subscription(
                    sub_id,
                    {"trial_expiry_reminder_sent_at": now},
                )
            sent += 1
            details.append(
                {
                    "id": sub_id,
                    "status": "sent",
                    "email": email,
                    "trial_end": end_iso,
                }
            )
        elif result.get("skipped"):
            skipped += 1
            details.append(
                {
                    "id": sub_id,
                    "status": "skipped_no_key",
                    "email": email,
                    "trial_end": end_iso,
                }
            )
        else:
            errors += 1
            details.append(
                {
                    "id": sub_id,
                    "status": "send_failed",
                    "error": result.get("error"),
                }
            )

    return TrialExpiryRemindersResponse(
        success=errors == 0,
        scanned=len(candidates),
        sent=sent,
        skipped=skipped,
        errors=errors,
        details=details[:50],
        timestamp=now.isoformat(),
    )

