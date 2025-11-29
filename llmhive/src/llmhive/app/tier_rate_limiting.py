"""Tier-aware rate limiting middleware for LLMHive.

This module provides rate limiting based on user account tiers, with fallback
to IP-based limiting for unauthenticated users at Free tier level.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import RLock
from typing import Dict, List, Optional, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .tier_limits import TIER_LIMITS, get_tier_limits

logger = logging.getLogger(__name__)


class TierRateLimiter:
    """Tier-aware rate limiter with support for both authenticated and unauthenticated users.
    
    For authenticated users: Uses user_id and account tier from User model.
    For unauthenticated users: Uses IP address and applies Free tier limits.
    """

    def __init__(self) -> None:
        """Initialize the rate limiter."""
        # Thread-safe lock for concurrent requests
        self._lock = RLock()
        # Track recent requests per user/IP: {identifier: [timestamp1, timestamp2, ...]}
        self.recent_requests_minute: Dict[str, List[float]] = defaultdict(list)
        # Track daily requests: {identifier: {date: count}}
        self.daily_requests: Dict[str, Dict[str, int]] = defaultdict(dict)

    def _get_daily_key(self) -> str:
        """Get current date as string key for daily tracking."""
        return time.strftime("%Y-%m-%d")

    def check_rate_limit(
        self,
        identifier: str,  # user_id or IP address
        tier: str,  # Account tier (free, pro, enterprise)
        db_session: Optional[Session] = None,
    ) -> Tuple[bool, Dict[str, int | str]]:
        """Check if a request is within rate limits for the given tier.
        
        Args:
            identifier: User ID (for authenticated) or IP address (for unauthenticated)
            tier: Account tier (free, pro, enterprise)
            db_session: Optional database session to check User model
            
        Returns:
            Tuple of (allowed, limit_info)
            limit_info contains: limit, remaining, reset_time, tier, daily_limit, daily_remaining
        """
        # Get tier limits
        limits = get_tier_limits(tier)
        
        # Get current time
        now = time.time()
        window_start_minute = now - 60  # 60-second rolling window
        daily_key = self._get_daily_key()
        
        # Thread-safe check and update
        with self._lock:
            # Per-minute rate limiting
            user_requests_minute = self.recent_requests_minute[identifier]
            recent_in_window = [ts for ts in user_requests_minute if ts > window_start_minute]
            count_minute = len(recent_in_window)
            
            # Check per-minute limit
            allowed_minute = count_minute < limits.requests_per_minute
            
            # Per-day rate limiting (if configured)
            allowed_daily = True
            count_daily = 0
            if limits.requests_per_day is not None:
                daily_counts = self.daily_requests[identifier]
                count_daily = daily_counts.get(daily_key, 0)
                allowed_daily = count_daily < limits.requests_per_day
            
            # Overall allowed status
            allowed = allowed_minute and allowed_daily
            
            if allowed:
                # Record this request
                recent_in_window.append(now)
                self.recent_requests_minute[identifier] = recent_in_window
                count_minute += 1
                
                if limits.requests_per_day is not None:
                    daily_counts = self.daily_requests[identifier]
                    daily_counts[daily_key] = count_daily + 1
                    # Clean up old daily entries (keep only last 7 days)
                    keys_to_remove = [k for k in daily_counts.keys() if k < daily_key]
                    for k in keys_to_remove:
                        del daily_counts[k]
            
            # Calculate remaining and reset times
            remaining_minute = max(0, limits.requests_per_minute - count_minute)
            reset_time_minute = int(now + (60 - (now % 60)))  # Next minute boundary
            
            remaining_daily = None
            reset_time_daily = None
            if limits.requests_per_day is not None:
                remaining_daily = max(0, limits.requests_per_day - count_daily)
                # Reset time is end of current day
                reset_time_daily = int(time.mktime(time.strptime(f"{daily_key} 23:59:59", "%Y-%m-%d %H:%M:%S")))
            
            limit_info = {
                "limit": limits.requests_per_minute,
                "remaining": remaining_minute,
                "reset_time": reset_time_minute,
                "tier": tier,
                "daily_limit": limits.requests_per_day,
                "daily_remaining": remaining_daily,
                "daily_reset_time": reset_time_daily,
            }
            
            return allowed, limit_info

    def get_rate_limit_info(
        self,
        identifier: str,
        tier: str,
    ) -> Dict[str, int | str | None]:
        """Get current rate limit information without incrementing counter."""
        limits = get_tier_limits(tier)
        now = time.time()
        window_start_minute = now - 60
        daily_key = self._get_daily_key()
        
        with self._lock:
            user_requests_minute = self.recent_requests_minute[identifier]
            recent_in_window = [ts for ts in user_requests_minute if ts > window_start_minute]
            count_minute = len(recent_in_window)
            remaining_minute = max(0, limits.requests_per_minute - count_minute)
            
            count_daily = 0
            remaining_daily = None
            if limits.requests_per_day is not None:
                daily_counts = self.daily_requests[identifier]
                count_daily = daily_counts.get(daily_key, 0)
                remaining_daily = max(0, limits.requests_per_day - count_daily)
            
            return {
                "limit": limits.requests_per_minute,
                "remaining": remaining_minute,
                "tier": tier,
                "daily_limit": limits.requests_per_day,
                "daily_remaining": remaining_daily,
            }


# Global rate limiter instance
_rate_limiter: Optional[TierRateLimiter] = None


def get_tier_rate_limiter() -> TierRateLimiter:
    """Get the global tier rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TierRateLimiter()
    return _rate_limiter


async def tier_rate_limit_middleware(
    request: Request,
    call_next,
) -> Response:
    """Tier-aware rate limiting middleware.
    
    For authenticated users: Uses user_id and account tier from User model.
    For unauthenticated users: Uses IP address and applies Free tier limits.
    
    Usage:
        app.middleware("http")(tier_rate_limit_middleware)
    """
    # Skip rate limiting for health check endpoints
    skip_paths = ["/healthz", "/health", "/_ah/health", "/api/v1/system/healthz"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)
    
    # Get user identifier and tier
    user_id: Optional[str] = None
    tier = "free"  # Default to free tier
    identifier: str  # Will be user_id or IP
    
    # Try to get user_id from request
    user_id = (
        request.query_params.get("user_id")
        or request.headers.get("X-User-ID")
    )
    
    # For POST requests, try to extract user_id from JSON body
    if not user_id and request.method == "POST":
        try:
            body = await request.body()
            if body:
                import json
                try:
                    body_data = json.loads(body)
                    user_id = body_data.get("user_id") or body_data.get("userId")
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
                
                # Restore body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
        except Exception:
            pass
    
    # If user_id is available, try to get tier from User model
    if user_id:
        try:
            from ..database import SessionLocal
            from ..models import User, AccountTier
            
            with SessionLocal() as db_session:
                user = db_session.query(User).filter_by(user_id=user_id).first()
                if user:
                    # Backwards compatibility: If account_tier is None or missing, default to Free
                    try:
                        if user.account_tier is None:
                            tier = "free"
                            logger.debug("Tier Rate Limiting: User %s has no tier, defaulting to Free", user_id)
                        else:
                            tier = user.account_tier.value
                    except AttributeError:
                        # Backwards compatibility: If account_tier attribute doesn't exist (old schema)
                        tier = "free"
                        logger.debug("Tier Rate Limiting: User %s missing account_tier attribute, defaulting to Free", user_id)
                else:
                    # User doesn't exist yet - create as Free tier
                    # (This is a simple approach; in production you might want to create users differently)
                    try:
                        new_user = User(
                            user_id=user_id,
                            account_tier=AccountTier.FREE,
                        )
                        db_session.add(new_user)
                        db_session.commit()
                        tier = "free"
                        logger.debug("Tier Rate Limiting: Created new user %s with Free tier", user_id)
                    except Exception as exc:
                        logger.warning("Tier Rate Limiting: Failed to create user %s: %s", user_id, exc)
                        db_session.rollback()
                        # Fall back to Free tier
                        tier = "free"
        except Exception as exc:
            logger.warning(
                "Tier Rate Limiting: Failed to get user tier for %s: %s. Using Free tier.",
                user_id,
                exc
            )
            tier = "free"
        
        identifier = user_id
    else:
        # Unauthenticated user: use IP address and Free tier
        client_ip = request.client.host if request.client else "unknown"
        identifier = f"ip:{client_ip}"
        tier = "free"  # Always Free tier for unauthenticated users
        logger.debug("Tier Rate Limiting: Unauthenticated request from IP %s, applying Free tier limits", client_ip)
    
    # Check rate limit
    limiter = get_tier_rate_limiter()
    try:
        from ..database import SessionLocal
        with SessionLocal() as db_session:
            allowed, limit_info = limiter.check_rate_limit(identifier, tier, db_session=db_session)
    except Exception:
        # If database check fails, use in-memory only
        allowed, limit_info = limiter.check_rate_limit(identifier, tier, db_session=None)
    
    if not allowed:
        # Rate limit exceeded
        logger.warning(
            "Tier Rate Limiting: Rate limit exceeded for %s (tier: %s, limit: %d/min)",
            identifier,
            tier,
            limit_info["limit"]
        )
        
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests for {tier} tier. Please slow down or upgrade your account.",
                "limit": limit_info["limit"],
                "remaining": limit_info["remaining"],
                "reset_time": limit_info["reset_time"],
                "tier": tier,
                "daily_limit": limit_info.get("daily_limit"),
                "daily_remaining": limit_info.get("daily_remaining"),
            },
        )
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset_time"])
        if limit_info.get("daily_limit") is not None:
            response.headers["X-RateLimit-Daily-Limit"] = str(limit_info["daily_limit"])
            response.headers["X-RateLimit-Daily-Remaining"] = str(limit_info.get("daily_remaining", 0))
        retry_after = max(1, int(limit_info["reset_time"] - time.time()))
        response.headers["Retry-After"] = str(retry_after)
        return response
    
    # Call next middleware/handler
    response = await call_next(request)
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(limit_info["reset_time"])
    if limit_info.get("daily_limit") is not None:
        response.headers["X-RateLimit-Daily-Limit"] = str(limit_info["daily_limit"])
        response.headers["X-RateLimit-Daily-Remaining"] = str(limit_info.get("daily_remaining", 0))
    
    return response

