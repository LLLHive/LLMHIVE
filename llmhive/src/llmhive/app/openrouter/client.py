"""OpenRouter API Client.

HTTP client for OpenRouter API with:
- Rate limiting and backoff
- Caching
- Error handling
- Streaming support

Allowed API Surfaces (Compliance):
==================================
GET  https://openrouter.ai/api/v1/models
GET  https://openrouter.ai/api/v1/models/:author/:slug/endpoints
POST https://openrouter.ai/api/v1/chat/completions
POST https://openrouter.ai/api/v1/completions (legacy)
GET  https://openrouter.ai/api/v1/generation?id=<GENERATION_ID>

Authentication:
- Authorization: Bearer <OPENROUTER_API_KEY>
- HTTP-Referer: <product URL>
- X-Title: <product name>
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, TypeVar

import httpx

logger = logging.getLogger(__name__)

# Type for retry callback
T = TypeVar("T")


@dataclass
class OpenRouterConfig:
    """OpenRouter client configuration."""
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    product_url: str = "https://llmhive.ai"
    product_name: str = "LLMHive"
    
    # Rate limiting
    max_requests_per_minute: int = 60
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    
    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 120.0
    
    # Caching
    cache_ttl_seconds: int = 3600  # 1 hour for model list
    
    @classmethod
    def from_env(cls) -> "OpenRouterConfig":
        """Load config from environment variables."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable required")
        
        return cls(
            api_key=api_key,
            product_url=os.getenv("OPENROUTER_PRODUCT_URL", "https://llmhive.ai"),
            product_name=os.getenv("OPENROUTER_PRODUCT_NAME", "LLMHive"),
        )


@dataclass
class RateLimiter:
    """Simple token bucket rate limiter."""
    tokens_per_minute: int
    _tokens: float = field(default=0, init=False)
    _last_update: float = field(default_factory=time.time, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            
            # Refill tokens
            self._tokens = min(
                self.tokens_per_minute,
                self._tokens + (elapsed * self.tokens_per_minute / 60)
            )
            self._last_update = now
            
            if self._tokens < 1:
                # Wait for token
                wait_time = (1 - self._tokens) * 60 / self.tokens_per_minute
                logger.debug("Rate limit: waiting %.2fs", wait_time)
                await asyncio.sleep(wait_time)
                self._tokens = 1
            
            self._tokens -= 1


@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    data: Any
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class OpenRouterClient:
    """OpenRouter API client with rate limiting and caching.
    
    Usage:
        config = OpenRouterConfig.from_env()
        async with OpenRouterClient(config) as client:
            models = await client.list_models()
            response = await client.chat_completion(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
            )
    """
    
    def __init__(self, config: Optional[OpenRouterConfig] = None):
        """Initialize client.
        
        Args:
            config: Client configuration. If None, loads from environment.
        """
        self.config = config or OpenRouterConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(tokens_per_minute=self.config.max_requests_per_minute)
        self._cache: Dict[str, CacheEntry] = {}
    
    async def __aenter__(self) -> "OpenRouterClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.read_timeout,
                    write=30.0,
                    pool=5.0,
                ),
                headers=self._default_headers(),
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "HTTP-Referer": self.config.product_url,
            "X-Title": self.config.product_name,
            "Content-Type": "application/json",
        }
    
    def _cache_key(self, method: str, path: str, params: Optional[Dict] = None) -> str:
        """Generate cache key."""
        key_data = f"{method}:{path}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry.data
        if entry:
            del self._cache[key]
        return None
    
    def _set_cached(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set cache value with TTL."""
        ttl = ttl_seconds or self.config.cache_ttl_seconds
        self._cache[key] = CacheEntry(
            data=data,
            expires_at=time.time() + ttl,
        )
    
    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_cache: bool = False,
        cache_ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make request with retry logic.
        
        Args:
            method: HTTP method
            path: API path
            json_data: JSON body
            params: Query parameters
            use_cache: Whether to use caching
            cache_ttl: Cache TTL override
            
        Returns:
            API response data
            
        Raises:
            httpx.HTTPError: On unrecoverable HTTP error
        """
        # Check cache first
        if use_cache and method.upper() == "GET":
            cache_key = self._cache_key(method, path, params)
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s %s", method, path)
                return cached
        
        client = await self._ensure_client()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Rate limiting
                await self._rate_limiter.acquire()
                
                # Make request
                response = await client.request(
                    method=method,
                    url=path,
                    json=json_data,
                    params=params,
                )
                
                # Handle response
                if response.status_code == 429:
                    # Rate limited - get retry-after header
                    retry_after = float(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limited, waiting %ss", retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                
                if response.status_code >= 500:
                    # Server error - retry with backoff
                    delay = min(
                        self.config.retry_base_delay * (2 ** attempt),
                        self.config.retry_max_delay,
                    )
                    logger.warning("Server error %d, retrying in %ss", response.status_code, delay)
                    await asyncio.sleep(delay)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Cache successful GET responses
                if use_cache and method.upper() == "GET":
                    self._set_cached(cache_key, data, cache_ttl)
                
                return data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 and e.response.status_code != 429:
                    # Client error (4xx except 429) - don't retry
                    logger.error("Client error: %s", e)
                    raise
                last_error = e
                
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                # Network error - retry with backoff
                last_error = e
                delay = min(
                    self.config.retry_base_delay * (2 ** attempt),
                    self.config.retry_max_delay,
                )
                logger.warning("Network error, retrying in %ss: %s", delay, e)
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_error or RuntimeError("Request failed after retries")
    
    # =========================================================================
    # Model Discovery API
    # =========================================================================
    
    async def list_models(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch full model catalog.
        
        API: GET https://openrouter.ai/api/v1/models
        
        Returns:
            List of model dictionaries from OpenRouter
        """
        logger.info("Fetching OpenRouter model catalog")
        response = await self._request_with_retry(
            "GET",
            "/models",
            use_cache=use_cache,
            cache_ttl=self.config.cache_ttl_seconds,
        )
        
        models = response.get("data", [])
        logger.info("Fetched %d models from OpenRouter", len(models))
        return models
    
    async def get_model_endpoints(
        self,
        model_id: str,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch endpoints for a specific model.
        
        API: GET https://openrouter.ai/api/v1/models/:author/:slug/endpoints
        
        Args:
            model_id: Model ID (e.g., "openai/gpt-4o")
            
        Returns:
            List of endpoint dictionaries
        """
        # Parse model ID into author/slug
        parts = model_id.split("/", 1)
        if len(parts) != 2:
            logger.warning("Invalid model ID format: %s", model_id)
            return []
        
        author, slug = parts
        path = f"/models/{author}/{slug}/endpoints"
        
        try:
            response = await self._request_with_retry(
                "GET",
                path,
                use_cache=use_cache,
                cache_ttl=self.config.cache_ttl_seconds,
            )
            
            endpoints = response.get("data", [])
            logger.debug("Fetched %d endpoints for %s", len(endpoints), model_id)
            return endpoints
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("No endpoints found for %s", model_id)
                return []
            raise
    
    # =========================================================================
    # Inference API
    # =========================================================================
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **params,
    ) -> Dict[str, Any]:
        """Run chat completion.
        
        API: POST https://openrouter.ai/api/v1/chat/completions
        
        Args:
            model: Model ID
            messages: Chat messages
            tools: Optional tool definitions
            response_format: Optional response format spec
            stream: Whether to stream response
            **params: Additional model parameters
            
        Returns:
            Completion response or stream
        """
        payload = {
            "model": model,
            "messages": messages,
            **params,
        }
        
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format
        if stream:
            payload["stream"] = True
        
        if stream:
            return await self._stream_completion(payload)
        
        logger.info("Chat completion: model=%s, messages=%d", model, len(messages))
        response = await self._request_with_retry(
            "POST",
            "/chat/completions",
            json_data=payload,
        )
        
        return response
    
    async def _stream_completion(self, payload: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat completion with SSE.
        
        Yields:
            Parsed SSE chunks
        """
        client = await self._ensure_client()
        await self._rate_limiter.acquire()
        
        async with client.stream(
            "POST",
            "/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning("Invalid SSE chunk: %s", data[:100])
    
    async def legacy_completion(
        self,
        model: str,
        prompt: str,
        **params,
    ) -> Dict[str, Any]:
        """Run legacy (non-chat) completion.
        
        API: POST https://openrouter.ai/api/v1/completions
        
        Args:
            model: Model ID
            prompt: Prompt string
            **params: Additional parameters
            
        Returns:
            Completion response
        """
        payload = {
            "model": model,
            "prompt": prompt,
            **params,
        }
        
        return await self._request_with_retry(
            "POST",
            "/completions",
            json_data=payload,
        )
    
    # =========================================================================
    # Usage/Cost API
    # =========================================================================
    
    async def get_generation(self, generation_id: str) -> Dict[str, Any]:
        """Retrieve generation metadata for cost accounting.
        
        API: GET https://openrouter.ai/api/v1/generation?id=<GENERATION_ID>
        
        Args:
            generation_id: Generation ID from completion response
            
        Returns:
            Generation metadata including tokens and cost
        """
        return await self._request_with_retry(
            "GET",
            "/generation",
            params={"id": generation_id},
        )
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    async def health_check(self) -> bool:
        """Check if OpenRouter API is reachable."""
        try:
            await self.list_models(use_cache=False)
            return True
        except Exception as e:
            logger.error("OpenRouter health check failed: %s", e)
            return False
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("OpenRouter client cache cleared")

