"""Response Caching for LLMHive Orchestrator.

Q4 2025: Implements LRU caching for model and tool responses.
Reduces redundant API calls and improves latency.

Features:
- LRU cache with configurable size
- TTL-based expiration
- Prompt hash-based keys
- Thread-safe operations
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response entry."""
    value: Any
    created_at: float
    hits: int = 0
    model_id: Optional[str] = None


class ResponseCache:
    """LRU cache for model and tool responses.
    
    Thread-safe implementation with TTL support.
    """
    
    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: float = 300.0,  # 5 minutes default
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def _hash_key(self, model_id: str, prompt: str) -> str:
        """Generate cache key from model and prompt."""
        content = f"{model_id}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get(
        self,
        model_id: str,
        prompt: str,
    ) -> Tuple[bool, Optional[Any]]:
        """Get cached response if available.
        
        Returns:
            (hit, value) tuple
        """
        key = self._hash_key(model_id, prompt)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return False, None
            
            entry = self._cache[key]
            
            # Check TTL
            if time.time() - entry.created_at > self._ttl:
                del self._cache[key]
                self._misses += 1
                return False, None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._hits += 1
            
            return True, entry.value
    
    def set(
        self,
        model_id: str,
        prompt: str,
        value: Any,
    ):
        """Cache a response."""
        key = self._hash_key(model_id, prompt)
        
        with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                model_id=model_id,
            )
    
    def invalidate(self, model_id: Optional[str] = None):
        """Invalidate cache entries.
        
        Args:
            model_id: If provided, only invalidate entries for this model
        """
        with self._lock:
            if model_id is None:
                self._cache.clear()
            else:
                to_remove = [
                    k for k, v in self._cache.items()
                    if v.model_id == model_id
                ]
                for k in to_remove:
                    del self._cache[k]
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }


# Global cache instance with thread-safe access (Enhancement-1)
_cache: Optional[ResponseCache] = None
_cache_lock = threading.Lock()  # Enhancement-1: lock to prevent race on instantiation


def get_response_cache() -> ResponseCache:
    """Get the global response cache (thread-safe)."""
    global _cache
    # Enhancement-1: Double-checked locking pattern for thread-safe singleton
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = ResponseCache()
    return _cache


def cached_response(model_id: str, prompt: str) -> Tuple[bool, Optional[Any]]:
    """Check for cached response."""
    return get_response_cache().get(model_id, prompt)


def cache_response(model_id: str, prompt: str, value: Any):
    """Cache a response."""
    get_response_cache().set(model_id, prompt, value)


