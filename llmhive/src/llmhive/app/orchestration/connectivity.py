"""Connectivity & Resilience for LLMHive Stage 4.

This module implements Section 15 of Stage 4 upgrades:
- Backup search providers
- Logging failures & user notifications
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# PROVIDER STATUS
# ==============================================================================

class ProviderStatus(Enum):
    """Status of a provider."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Health information for a provider."""
    provider_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    avg_latency_ms: float = 0.0
    
    def record_success(self, latency_ms: float):
        """Record a successful call."""
        self.success_count += 1
        self.last_success = datetime.now(timezone.utc)
        self.failure_count = 0  # Reset consecutive failures
        
        # Update running average latency
        n = self.success_count
        self.avg_latency_ms = (self.avg_latency_ms * (n - 1) + latency_ms) / n
        
        self.status = ProviderStatus.HEALTHY
    
    def record_failure(self, error: str):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure = datetime.now(timezone.utc)
        
        # Update status based on failure count
        if self.failure_count >= 5:
            self.status = ProviderStatus.DOWN
        elif self.failure_count >= 2:
            self.status = ProviderStatus.DEGRADED
        
        logger.warning(
            "Provider %s failure #%d: %s",
            self.provider_name, self.failure_count, error
        )


# ==============================================================================
# SEARCH PROVIDER INTERFACE
# ==============================================================================

@dataclass
class SearchResult:
    """Result from a search provider."""
    title: str
    url: str
    snippet: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from a search operation."""
    results: List[SearchResult]
    provider: str
    latency_ms: float
    from_cache: bool = False
    error: Optional[str] = None


class SearchProvider(ABC):
    """Abstract base for search providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        """Execute a search."""
        pass


# ==============================================================================
# CONCRETE PROVIDERS
# ==============================================================================

class TavilyProvider(SearchProvider):
    """Tavily search provider (primary)."""
    
    @property
    def name(self) -> str:
        return "tavily"
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self._api_key = api_key or os.getenv("TAVILY_API_KEY")
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        if not self._api_key:
            return SearchResponse(
                results=[],
                provider=self.name,
                latency_ms=0,
                error="Tavily API key not configured",
            )
        
        start = time.time()
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self._api_key,
                        "query": query,
                        "max_results": max_results,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return SearchResponse(
                            results=[],
                            provider=self.name,
                            latency_ms=(time.time() - start) * 1000,
                            error=f"HTTP {resp.status}: {error_text[:100]}",
                        )
                    
                    data = await resp.json()
            
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", r.get("snippet", ""))[:500],
                    score=r.get("score", 0.0),
                )
                for r in data.get("results", [])
            ]
            
            return SearchResponse(
                results=results,
                provider=self.name,
                latency_ms=(time.time() - start) * 1000,
            )
            
        except Exception as e:
            return SearchResponse(
                results=[],
                provider=self.name,
                latency_ms=(time.time() - start) * 1000,
                error=str(e),
            )


class SerpAPIProvider(SearchProvider):
    """SerpAPI search provider (backup)."""
    
    @property
    def name(self) -> str:
        return "serpapi"
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self._api_key = api_key or os.getenv("SERPAPI_API_KEY")
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        if not self._api_key:
            return SearchResponse(
                results=[],
                provider=self.name,
                latency_ms=0,
                error="SerpAPI key not configured",
            )
        
        start = time.time()
        
        try:
            import aiohttp
            
            params = {
                "api_key": self._api_key,
                "q": query,
                "num": max_results,
                "engine": "google",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return SearchResponse(
                            results=[],
                            provider=self.name,
                            latency_ms=(time.time() - start) * 1000,
                            error=f"HTTP {resp.status}: {error_text[:100]}",
                        )
                    
                    data = await resp.json()
            
            results = []
            for r in data.get("organic_results", [])[:max_results]:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("link", ""),
                    snippet=r.get("snippet", "")[:500],
                ))
            
            return SearchResponse(
                results=results,
                provider=self.name,
                latency_ms=(time.time() - start) * 1000,
            )
            
        except Exception as e:
            return SearchResponse(
                results=[],
                provider=self.name,
                latency_ms=(time.time() - start) * 1000,
                error=str(e),
            )


class SerperProvider(SearchProvider):
    """Serper.dev search provider (backup)."""
    
    @property
    def name(self) -> str:
        return "serper"
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self._api_key = api_key or os.getenv("SERPER_API_KEY")
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        if not self._api_key:
            return SearchResponse(
                results=[],
                provider=self.name,
                latency_ms=0,
                error="Serper API key not configured",
            )
        
        start = time.time()
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": max_results},
                    headers={"X-API-KEY": self._api_key},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return SearchResponse(
                            results=[],
                            provider=self.name,
                            latency_ms=(time.time() - start) * 1000,
                            error=f"HTTP {resp.status}: {error_text[:100]}",
                        )
                    
                    data = await resp.json()
            
            results = []
            for r in data.get("organic", [])[:max_results]:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("link", ""),
                    snippet=r.get("snippet", "")[:500],
                ))
            
            return SearchResponse(
                results=results,
                provider=self.name,
                latency_ms=(time.time() - start) * 1000,
            )
            
        except Exception as e:
            return SearchResponse(
                results=[],
                provider=self.name,
                latency_ms=(time.time() - start) * 1000,
                error=str(e),
            )


# ==============================================================================
# RESILIENT SEARCH AGGREGATOR
# ==============================================================================

class ResilientSearchAggregator:
    """Aggregates multiple search providers with fallback.
    
    Implements Stage 4 Section 15: Backup providers and failure handling.
    """
    
    def __init__(
        self,
        providers: Optional[List[SearchProvider]] = None,
        cache_ttl_seconds: int = 300,
    ):
        self._providers = providers or [
            TavilyProvider(),
            SerperProvider(),
            SerpAPIProvider(),
        ]
        self._health: Dict[str, ProviderHealth] = {
            p.name: ProviderHealth(provider_name=p.name)
            for p in self._providers
        }
        self._cache: Dict[str, Tuple[SearchResponse, float]] = {}
        self._cache_ttl = cache_ttl_seconds
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        use_cache: bool = True,
    ) -> SearchResponse:
        """
        Search with automatic provider fallback.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            use_cache: Whether to use cached results
            
        Returns:
            SearchResponse with results or error
        """
        # Check cache
        cache_key = f"{query}:{max_results}"
        if use_cache and cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug("Cache hit for query: %s", query[:50])
                cached.from_cache = True
                return cached
        
        # Sort providers by health
        sorted_providers = self._get_sorted_providers()
        
        for provider in sorted_providers:
            health = self._health[provider.name]
            
            # Skip providers that are down
            if health.status == ProviderStatus.DOWN:
                # Check if enough time has passed to retry
                if health.last_failure:
                    seconds_since_failure = (
                        datetime.now(timezone.utc) - health.last_failure
                    ).total_seconds()
                    if seconds_since_failure < 60:  # Wait 60s before retry
                        continue
            
            logger.debug("Trying provider: %s", provider.name)
            
            response = await provider.search(query, max_results)
            
            if response.error:
                health.record_failure(response.error)
                logger.warning(
                    "Provider %s failed, trying next: %s",
                    provider.name, response.error
                )
                continue
            
            # Success!
            health.record_success(response.latency_ms)
            
            # Cache result
            self._cache[cache_key] = (response, time.time())
            
            logger.info(
                "Search completed via %s in %.1fms",
                provider.name, response.latency_ms
            )
            
            return response
        
        # All providers failed
        logger.error("All search providers failed for query: %s", query[:50])
        
        return SearchResponse(
            results=[],
            provider="none",
            latency_ms=0,
            error="Live search temporarily unavailable. Please try again later.",
        )
    
    def _get_sorted_providers(self) -> List[SearchProvider]:
        """Sort providers by health status."""
        def sort_key(p: SearchProvider) -> Tuple[int, float]:
            health = self._health[p.name]
            # Priority: HEALTHY (0) > UNKNOWN (1) > DEGRADED (2) > DOWN (3)
            status_priority = {
                ProviderStatus.HEALTHY: 0,
                ProviderStatus.UNKNOWN: 1,
                ProviderStatus.DEGRADED: 2,
                ProviderStatus.DOWN: 3,
            }
            return (status_priority[health.status], health.avg_latency_ms)
        
        return sorted(self._providers, key=sort_key)
    
    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers."""
        return {
            name: {
                "status": health.status.value,
                "failure_count": health.failure_count,
                "success_count": health.success_count,
                "avg_latency_ms": round(health.avg_latency_ms, 1),
                "last_success": health.last_success.isoformat() if health.last_success else None,
                "last_failure": health.last_failure.isoformat() if health.last_failure else None,
            }
            for name, health in self._health.items()
        }
    
    def reset_provider_health(self, provider_name: str):
        """Reset health status for a provider."""
        if provider_name in self._health:
            self._health[provider_name] = ProviderHealth(provider_name=provider_name)
            logger.info("Reset health for provider: %s", provider_name)


# ==============================================================================
# CONNECTIVITY MONITOR
# ==============================================================================

class ConnectivityMonitor:
    """Monitors connectivity and reports issues.
    
    Provides user notifications when services are degraded.
    """
    
    def __init__(
        self,
        search_aggregator: Optional[ResilientSearchAggregator] = None,
    ):
        self._search = search_aggregator or ResilientSearchAggregator()
        self._last_check: Optional[datetime] = None
        self._is_connected = True
    
    async def check_connectivity(self) -> Dict[str, Any]:
        """Check connectivity to all services."""
        results = {}
        
        # Test search providers
        search_health = self._search.get_health_status()
        healthy_providers = sum(
            1 for h in search_health.values()
            if h["status"] == "healthy"
        )
        
        results["search"] = {
            "healthy_providers": healthy_providers,
            "total_providers": len(search_health),
            "status": "healthy" if healthy_providers > 0 else "degraded",
            "details": search_health,
        }
        
        # Overall status
        all_healthy = all(
            r.get("status") == "healthy" for r in results.values()
        )
        
        self._is_connected = healthy_providers > 0
        self._last_check = datetime.now(timezone.utc)
        
        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "services": results,
            "checked_at": self._last_check.isoformat(),
        }
    
    def get_user_notification(self) -> Optional[str]:
        """Get notification message for user if connectivity issues exist."""
        if self._is_connected:
            return None
        
        return (
            "⚠️ Some live data services are temporarily unavailable. "
            "Results may be limited or delayed. We're working to restore full service."
        )


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================

def create_tavily_provider(api_key: Optional[str] = None) -> TavilyProvider:
    """Create a Tavily provider."""
    return TavilyProvider(api_key)


def create_serpapi_provider(api_key: Optional[str] = None) -> SerpAPIProvider:
    """Create a SerpAPI provider."""
    return SerpAPIProvider(api_key)


def create_serper_provider(api_key: Optional[str] = None) -> SerperProvider:
    """Create a Serper provider."""
    return SerperProvider(api_key)


def create_resilient_search() -> ResilientSearchAggregator:
    """Create a resilient search aggregator with all providers."""
    return ResilientSearchAggregator()


def create_connectivity_monitor() -> ConnectivityMonitor:
    """Create a connectivity monitor."""
    return ConnectivityMonitor()

