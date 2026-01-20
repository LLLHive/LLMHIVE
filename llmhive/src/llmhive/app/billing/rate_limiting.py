"""API rate limiting middleware for LLMHive billing system.

Rate limiting: Simple in-memory rate limiting per user/tier with rolling window.
Tracks requests per user in a 60-second rolling window and enforces tier-based limits.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import RLock
from typing import Dict, List, Optional, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from ..billing.pricing import get_pricing_manager
from ..billing.subscription import SubscriptionService

logger = logging.getLogger(__name__)

# Rate limiting: Per-tier rate limits (requests per 60 seconds)
# SIMPLIFIED 4-TIER STRUCTURE (January 2026)
RATE_LIMITS: Dict[str, int] = {
    "lite": 10,      # Lite tier: 10 req/min
    "pro": 30,       # Pro tier: 30 req/min
    "enterprise": 60, # Enterprise: 60 req/min (per seat limits also apply)
    "maximum": 120,   # Maximum: 120 req/min
    "free": 5,       # Free trial: 5 req/min (very limited)
}


class RateLimiter:
    """Rate limiting: In-memory rate limiter for API requests.
    
    Tracks requests per user in a rolling 60-second window.
    Uses per-tier limits defined in RATE_LIMITS.
    
    Note: For production with multiple instances, consider using Redis for distributed rate limiting.
    """

    def __init__(self) -> None:
        # Rate limiting: Thread-safe lock for concurrent requests
        self._lock = RLock()
        # Rate limiting: Track recent requests per user: {user_id: [timestamp1, timestamp2, ...]}
        self.recent_requests: Dict[str, List[float]] = defaultdict(list)
        self.pricing_manager = get_pricing_manager()

    def check_rate_limit(
        self,
        user_id: str,
        tier_name: str,
    ) -> Tuple[bool, Dict[str, int]]:
        """Rate limiting: Check if a request is within rate limits.
        
        Filters user's recent requests to only include events in the last 60 seconds,
        counts them, and compares to tier limit.

        Args:
            user_id: User identifier
            tier_name: User's tier name (free, pro, enterprise)

        Returns:
            Tuple of (allowed, limit_info)
            limit_info contains: limit, remaining, reset_time
        """
        # Rate limiting: Get limit for tier
        tier_name_lower = tier_name.lower()
        limit = RATE_LIMITS.get(tier_name_lower, RATE_LIMITS["free"])
        
        # Rate limiting: Get current time
        now = time.time()
        window_start = now - 60  # 60-second rolling window
        
        # Rate limiting: Thread-safe check and update
        with self._lock:
            # Rate limiting: Get user's recent requests
            user_requests = self.recent_requests[user_id]
            
            # Rate limiting: Filter to only include events in the last 60 seconds
            recent_in_window = [ts for ts in user_requests if ts > window_start]
            
            # Rate limiting: Count requests in window
            count = len(recent_in_window)
            
            # Rate limiting: Check if limit exceeded
            allowed = count < limit
            
            if allowed:
                # Rate limiting: Append current timestamp to user's list
                recent_in_window.append(now)
                self.recent_requests[user_id] = recent_in_window
                count += 1
            else:
                # Rate limiting: Update list to only include recent requests (cleanup)
                self.recent_requests[user_id] = recent_in_window
            
            remaining = max(0, limit - count)
            reset_time = now + 60  # Reset time is 60 seconds from now
            
            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset_time": int(reset_time),
            }

    def get_rate_limit_info(
        self,
        user_id: str,
        tier_name: str,
    ) -> Dict[str, int]:
        """Rate limiting: Get current rate limit information without incrementing counter."""
        tier_name_lower = tier_name.lower()
        limit = RATE_LIMITS.get(tier_name_lower, RATE_LIMITS["free"])
        
        now = time.time()
        window_start = now - 60
        
        with self._lock:
            user_requests = self.recent_requests[user_id]
            recent_in_window = [ts for ts in user_requests if ts > window_start]
            count = len(recent_in_window)
            remaining = max(0, limit - count)
            
            return {
                "limit": limit,
                "remaining": remaining,
                "reset_time": int(now + 60),
            }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def rate_limit_middleware(
    request: Request,
    call_next,
) -> Response:
    """Rate limiting: FastAPI middleware for rate limiting per user/tier.
    
    Identifies user from request, gets their subscription tier, and enforces
    rate limits based on tier. Uses rolling 60-second window.

    Usage:
        app.middleware("http")(rate_limit_middleware)
    """
    # Rate limiting: Skip rate limiting for health check endpoints
    skip_paths = ["/healthz", "/health", "/_ah/health", "/api/v1/system/healthz"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)

    # Rate limiting: Get user_id from request
    # Try multiple sources: query param, header, or request body (for POST requests)
    user_id = (
        request.query_params.get("user_id") 
        or request.headers.get("X-User-ID")
    )
    
    # Rate limiting: For POST requests, try to extract user_id from JSON body
    # Note: Reading body consumes it, so we restore it for downstream handlers
    if not user_id and request.method == "POST":
        try:
            # Read body to extract user_id
            body = await request.body()
            if body:
                import json
                try:
                    body_data = json.loads(body)
                    user_id = body_data.get("user_id") or body_data.get("userId")
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
                
                # Rate limiting: Restore body for downstream handlers
                # Starlette/FastAPI requires restoring the receive callable
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
        except Exception:
            # If body reading fails, continue without user_id
            pass
    
    if not user_id:
        # Rate limiting: If no user_id, allow request but don't track
        # In production, you might want to require authentication
        return await call_next(request)

    # Rate limiting: Get user's subscription tier
    tier_name = "free"  # Default to free tier
    try:
        from ..database import SessionLocal
        with SessionLocal() as db_session:
            service = SubscriptionService(db_session)
            subscription = service.get_user_subscription(user_id)
            if subscription and subscription.is_active():
                tier_name = subscription.tier_name.lower()
            else:
                tier_name = "free"
    except Exception as exc:
        logger.warning(
            "Rate limiting: Failed to get user subscription for user %s: %s",
            user_id,
            exc
        )
        # Default to free tier on error

    # Rate limiting: Check rate limit
    limiter = get_rate_limiter()
    allowed, limit_info = limiter.check_rate_limit(user_id, tier_name)

    if not allowed:
        # Rate limiting: Log rate limit hit
        logger.warning(
            "Rate limiting: Rate limit exceeded for user %s (tier: %s, limit: %d/min)",
            user_id,
            tier_name,
            limit_info["limit"]
        )
        
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests, please slow down.",
                "limit": limit_info["limit"],
                "remaining": limit_info["remaining"],
                "reset_time": limit_info["reset_time"],
                "tier": tier_name,
            },
        )
        # Rate limiting: Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset_time"])
        retry_after = max(1, int(limit_info["reset_time"] - time.time()))
        response.headers["Retry-After"] = str(retry_after)
        return response

    # Rate limiting: Call next middleware/handler
    response = await call_next(request)

    # Rate limiting: Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(limit_info["reset_time"])

    return response

