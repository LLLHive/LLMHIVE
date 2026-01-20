"""Redis-Based Distributed Rate Limiter for LLMHive.

Provides production-grade rate limiting using Redis for multi-instance deployments.
Falls back to in-memory limiting when Redis is unavailable.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None
    logger.info("Redis not available. Install with: pip install redis")


class RateLimitBackend(str, Enum):
    """Rate limiting backend type."""
    MEMORY = "memory"
    REDIS = "redis"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    # Backend selection
    backend: RateLimitBackend = field(
        default_factory=lambda: RateLimitBackend(
            os.getenv("RATE_LIMIT_BACKEND", "memory")
        )
    )
    
    # Redis configuration
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    redis_prefix: str = "llmhive:ratelimit:"
    redis_socket_timeout: float = 1.0
    redis_connect_timeout: float = 2.0
    
    # Default limits (per minute)
    default_requests_per_minute: int = 60
    default_tokens_per_minute: int = 100000
    
    # Tier-based limits (per minute) - SIMPLIFIED 4-TIER STRUCTURE (January 2026)
    tier_limits: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "lite": {
            "requests_per_minute": 15,
            "tokens_per_minute": 50000,
            "requests_per_hour": 200,
        },
        "pro": {
            "requests_per_minute": 100,
            "tokens_per_minute": 500000,
            "requests_per_hour": 1000,
        },
        "enterprise": {
            "requests_per_minute": 500,
            "tokens_per_minute": 2000000,
            "requests_per_hour": 5000,
        },
        "maximum": {
            "requests_per_minute": 1000,
            "tokens_per_minute": 10000000,
            "requests_per_hour": 20000,
        },
        "free": {
            "requests_per_minute": 10,
            "tokens_per_minute": 10000,
            "requests_per_hour": 100,
        },
    })
    
    # Fallback behavior
    fail_open: bool = True  # Allow requests if rate limiter fails


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    retry_after_seconds: Optional[int] = None
    tier: str = "default"
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for the response."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at.timestamp())),
        }
        if self.retry_after_seconds and not self.allowed:
            headers["Retry-After"] = str(self.retry_after_seconds)
        return headers


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for single-instance deployments."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock_buckets: Dict[str, float] = {}
    
    def _get_bucket_key(self, identifier: str, window: str) -> str:
        """Generate bucket key."""
        return f"{identifier}:{window}"
    
    def _get_current_window(self, window_seconds: int) -> Tuple[int, datetime]:
        """Get current time window and reset time."""
        now = time.time()
        window_start = int(now // window_seconds) * window_seconds
        reset_at = datetime.fromtimestamp(window_start + window_seconds, tz=timezone.utc)
        return window_start, reset_at
    
    def check_rate_limit(
        self,
        identifier: str,
        tier: str = "default",
        cost: int = 1,
        limit_type: str = "requests_per_minute",
    ) -> RateLimitResult:
        """Check if request is within rate limits.
        
        Args:
            identifier: Unique identifier (user ID, IP, API key).
            tier: User tier (free, pro, enterprise).
            cost: Request cost (usually 1 for requests, token count for tokens).
            limit_type: Type of limit to check.
            
        Returns:
            RateLimitResult with allowed status and metadata.
        """
        # Get limit for tier
        tier_config = self.config.tier_limits.get(tier, {})
        limit = tier_config.get(limit_type, self.config.default_requests_per_minute)
        
        # Determine window size
        if "hour" in limit_type:
            window_seconds = 3600
        else:
            window_seconds = 60
        
        window_start, reset_at = self._get_current_window(window_seconds)
        bucket_key = self._get_bucket_key(identifier, f"{limit_type}:{window_start}")
        
        # Clean old buckets periodically
        self._cleanup_old_buckets(window_seconds)
        
        # Get or create bucket
        bucket = self._buckets.get(bucket_key)
        if bucket is None:
            bucket = {"count": 0, "window_start": window_start}
            self._buckets[bucket_key] = bucket
        
        current_count = bucket["count"]
        remaining = limit - current_count
        
        if current_count + cost > limit:
            # Rate limit exceeded
            retry_after = int(reset_at.timestamp() - time.time())
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
                tier=tier,
            )
        
        # Increment counter
        bucket["count"] += cost
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining - cost,
            reset_at=reset_at,
            tier=tier,
        )
    
    def _cleanup_old_buckets(self, window_seconds: int) -> None:
        """Remove expired buckets."""
        now = time.time()
        cutoff = now - (window_seconds * 2)
        
        keys_to_remove = []
        for key, bucket in self._buckets.items():
            if bucket.get("window_start", 0) < cutoff:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._buckets[key]


class RedisRateLimiter:
    """Redis-based distributed rate limiter.
    
    Uses sliding window algorithm with Redis for accurate distributed rate limiting.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize the rate limiter.
        
        Args:
            config: Rate limiting configuration.
        """
        self.config = config or RateLimitConfig()
        self._redis: Optional[Redis] = None
        self._fallback = InMemoryRateLimiter(self.config)
        self._redis_healthy = False
        
        # Try to connect to Redis if configured
        if self.config.backend == RateLimitBackend.REDIS and REDIS_AVAILABLE:
            self._connect_redis()
    
    def _connect_redis(self) -> bool:
        """Establish Redis connection.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self._redis = redis.from_url(
                self.config.redis_url,
                socket_timeout=self.config.redis_socket_timeout,
                socket_connect_timeout=self.config.redis_connect_timeout,
                decode_responses=True,
            )
            # Test connection
            self._redis.ping()
            self._redis_healthy = True
            logger.info(f"Connected to Redis at {self.config.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._redis = None
            self._redis_healthy = False
            return False
    
    def _get_redis(self) -> Optional[Redis]:
        """Get Redis connection, attempting reconnect if needed.
        
        Returns:
            Redis client or None if unavailable.
        """
        if self._redis is None:
            self._connect_redis()
        
        if self._redis:
            try:
                self._redis.ping()
                self._redis_healthy = True
                return self._redis
            except Exception:
                self._redis_healthy = False
                return None
        
        return None
    
    def check_rate_limit(
        self,
        identifier: str,
        tier: str = "default",
        cost: int = 1,
        limit_type: str = "requests_per_minute",
    ) -> RateLimitResult:
        """Check if request is within rate limits.
        
        Uses Redis if available, falls back to in-memory if not.
        
        Args:
            identifier: Unique identifier (user ID, IP, API key).
            tier: User tier (free, pro, enterprise).
            cost: Request cost (usually 1 for requests, token count for tokens).
            limit_type: Type of limit to check.
            
        Returns:
            RateLimitResult with allowed status and metadata.
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                return self._check_redis_rate_limit(
                    redis_client, identifier, tier, cost, limit_type
                )
            except Exception as e:
                logger.warning(f"Redis rate limit check failed: {e}")
                self._redis_healthy = False
                
                if self.config.fail_open:
                    return self._fallback.check_rate_limit(
                        identifier, tier, cost, limit_type
                    )
                else:
                    # Fail closed - deny request
                    return RateLimitResult(
                        allowed=False,
                        limit=0,
                        remaining=0,
                        reset_at=datetime.now(timezone.utc),
                        retry_after_seconds=60,
                        tier=tier,
                    )
        
        # Fallback to in-memory
        return self._fallback.check_rate_limit(identifier, tier, cost, limit_type)
    
    def _check_redis_rate_limit(
        self,
        redis_client: Redis,
        identifier: str,
        tier: str,
        cost: int,
        limit_type: str,
    ) -> RateLimitResult:
        """Check rate limit using Redis sliding window.
        
        Uses MULTI/EXEC for atomic operations.
        """
        # Get limit for tier
        tier_config = self.config.tier_limits.get(tier, {})
        limit = tier_config.get(limit_type, self.config.default_requests_per_minute)
        
        # Determine window size
        if "hour" in limit_type:
            window_seconds = 3600
        else:
            window_seconds = 60
        
        now = time.time()
        window_start = now - window_seconds
        reset_at = datetime.fromtimestamp(now + window_seconds, tz=timezone.utc)
        
        key = f"{self.config.redis_prefix}{identifier}:{limit_type}"
        
        # Use pipeline for atomic operations
        pipe = redis_client.pipeline()
        
        # Remove old entries (sliding window)
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Execute
        results = pipe.execute()
        current_count = results[1]
        
        remaining = limit - current_count
        
        if current_count + cost > limit:
            # Rate limit exceeded
            retry_after = int(window_seconds - (now % window_seconds))
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
                tier=tier,
            )
        
        # Add new entry and set expiry
        pipe = redis_client.pipeline()
        for i in range(cost):
            pipe.zadd(key, {f"{now}:{i}": now})
        pipe.expire(key, window_seconds + 10)  # Extra buffer for cleanup
        pipe.execute()
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining - cost,
            reset_at=reset_at,
            tier=tier,
        )
    
    def get_usage(
        self,
        identifier: str,
        limit_type: str = "requests_per_minute",
    ) -> Dict[str, Any]:
        """Get current usage for an identifier.
        
        Args:
            identifier: Unique identifier.
            limit_type: Type of limit to check.
            
        Returns:
            Dictionary with usage information.
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                key = f"{self.config.redis_prefix}{identifier}:{limit_type}"
                
                # Determine window
                if "hour" in limit_type:
                    window_seconds = 3600
                else:
                    window_seconds = 60
                
                now = time.time()
                window_start = now - window_seconds
                
                # Clean and count
                redis_client.zremrangebyscore(key, 0, window_start)
                count = redis_client.zcard(key)
                
                return {
                    "identifier": identifier,
                    "limit_type": limit_type,
                    "current_count": count,
                    "window_seconds": window_seconds,
                    "backend": "redis",
                }
            except Exception as e:
                logger.warning(f"Failed to get Redis usage: {e}")
        
        # Fallback info
        return {
            "identifier": identifier,
            "limit_type": limit_type,
            "current_count": 0,
            "window_seconds": 60,
            "backend": "memory",
            "note": "Redis unavailable, using in-memory fallback",
        }
    
    def reset_limit(self, identifier: str, limit_type: str = "requests_per_minute") -> bool:
        """Reset rate limit for an identifier.
        
        Args:
            identifier: Unique identifier.
            limit_type: Type of limit to reset.
            
        Returns:
            True if reset successful.
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                key = f"{self.config.redis_prefix}{identifier}:{limit_type}"
                redis_client.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Failed to reset Redis limit: {e}")
        
        return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of rate limiter.
        
        Returns:
            Health status dictionary.
        """
        redis_client = self._get_redis()
        
        return {
            "backend": self.config.backend.value,
            "redis_healthy": self._redis_healthy,
            "redis_url": self.config.redis_url if self.config.backend == RateLimitBackend.REDIS else None,
            "fallback_active": not self._redis_healthy and self.config.backend == RateLimitBackend.REDIS,
        }


# Global instance
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter() -> RedisRateLimiter:
    """Get the global rate limiter instance.
    
    Returns:
        The rate limiter instance.
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = create_rate_limiter()
    return _rate_limiter


def create_rate_limiter(config: Optional[RateLimitConfig] = None) -> RedisRateLimiter:
    """Create a new rate limiter with custom configuration.
    
    Args:
        config: Rate limiting configuration.
        
    Returns:
        A new rate limiter instance.
    """
    return RedisRateLimiter(config)
