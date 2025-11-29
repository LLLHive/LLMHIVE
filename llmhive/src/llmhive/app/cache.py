"""In-memory caching layer for expensive operations in LLMHive orchestration.

This module provides request-scoped caching for:
- Web search results
- Knowledge base queries
- Prompt optimization results

The cache is per-request (short-lived) to avoid stale data across different queries.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class RequestCache:
    """Request-scoped in-memory cache with LRU eviction.
    
    Thread-safe for async operations using asyncio locks.
    Cache is keyed by operation type and parameters.
    """
    
    def __init__(self, max_size: int = 100):
        """Initialize request cache.
        
        Args:
            max_size: Maximum number of entries to cache (LRU eviction)
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, operation: str, *args, **kwargs) -> str:
        """Generate cache key from operation and arguments.
        
        Args:
            operation: Operation type (e.g., 'web_search', 'knowledge_search')
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create a hash of the arguments
        key_parts = [operation]
        
        # Add positional args
        for arg in args:
            if isinstance(arg, str):
                key_parts.append(arg)
            elif isinstance(arg, (int, float, bool)):
                key_parts.append(str(arg))
            elif arg is None:
                key_parts.append("None")
            else:
                # For complex objects, use string representation
                key_parts.append(str(hash(str(arg))))
        
        # Add keyword args (sorted for consistency)
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                if isinstance(v, str):
                    key_parts.append(f"{k}:{v}")
                elif isinstance(v, (int, float, bool)):
                    key_parts.append(f"{k}:{str(v)}")
                elif v is None:
                    key_parts.append(f"{k}:None")
                else:
                    key_parts.append(f"{k}:{str(hash(str(v)))}")
        
        # Create hash of key parts
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def get(self, operation: str, *args, **kwargs) -> Optional[Any]:
        """Get cached value if available.
        
        Args:
            operation: Operation type
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cached value or None if not found
        """
        key = self._make_key(operation, *args, **kwargs)
        
        async with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                value = self._cache.pop(key)
                self._cache[key] = value
                self._hits += 1
                logger.debug("Cache hit: %s (key: %s)", operation, key[:16])
                return value
        
        self._misses += 1
        logger.debug("Cache miss: %s (key: %s)", operation, key[:16])
        return None
    
    async def set(self, operation: str, value: Any, *args, **kwargs) -> None:
        """Set cached value.
        
        Args:
            operation: Operation type
            value: Value to cache
            *args: Positional arguments (for key generation)
            **kwargs: Keyword arguments (for key generation)
        """
        key = self._make_key(operation, *args, **kwargs)
        
        async with self._lock:
            # Remove if already exists
            if key in self._cache:
                del self._cache[key]
            
            # Add to end
            self._cache[key] = value
            
            # Evict oldest if over limit
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # Remove oldest (first item)
                logger.debug("Cache eviction: %s entries", len(self._cache))
    
    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.debug("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self.max_size,
        }


# Global request cache instance (per-process)
_request_cache: Optional[RequestCache] = None


def get_request_cache(max_size: int = 100) -> RequestCache:
    """Get or create the global request cache instance.
    
    Args:
        max_size: Maximum cache size (only used on first call)
        
    Returns:
        RequestCache instance
    """
    global _request_cache
    if _request_cache is None:
        _request_cache = RequestCache(max_size=max_size)
    return _request_cache


def reset_request_cache() -> None:
    """Reset the global request cache (useful for testing)."""
    global _request_cache
    _request_cache = None


def cached_async(operation: str, cache_key_fn: Optional[Callable] = None):
    """Decorator for caching async function results.
    
    Args:
        operation: Operation type name for cache key
        cache_key_fn: Optional function to generate custom cache key from args/kwargs
        
    Example:
        @cached_async("web_search")
        async def search(query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_request_cache()
            
            # Generate cache key
            if cache_key_fn:
                key = cache_key_fn(*args, **kwargs)
                cache_key = (operation, key)
            else:
                cache_key = (operation, *args, tuple(sorted(kwargs.items())))
            
            # Check cache
            cached_value = await cache.get(*cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(*cache_key, result)
            
            return result
        
        return wrapper
    return decorator

