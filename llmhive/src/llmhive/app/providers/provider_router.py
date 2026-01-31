"""
Multi-Provider Router
====================

Intelligently routes FREE tier model requests across multiple providers:
- OpenRouter (20 RPM, 20 free models)
- Google AI (15 RPM, Gemini models)
- Groq (generous limits, Llama models)

Benefits:
- 2-3x capacity increase (20 → 40+ RPM total)
- Ultra-fast Llama inference via Groq LPU
- Automatic fallback on rate limits
- Load distribution across providers
- Still $0/query cost (all FREE)

Strategy:
1. Route Gemini → Google AI (15 RPM independent)
2. Route Llama → Groq (ultra-fast LPU)
3. Route others → OpenRouter (fallback)
4. Track capacity per provider
5. Fallback to OpenRouter if primary exhausted

Last Updated: January 31, 2026
"""

import logging
from enum import Enum
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


class Provider(str, Enum):
    """Available LLM providers."""
    OPENROUTER = "openrouter"
    GOOGLE = "google"
    GROQ = "groq"


@dataclass
class ProviderCapacity:
    """Track rate limit capacity for a provider."""
    rpm_limit: int  # Requests per minute
    window_start: float  # Timestamp of current window start
    requests_in_window: int  # Requests made in current window
    
    def can_proceed(self) -> bool:
        """Check if provider has capacity."""
        now = time.time()
        
        # Reset window if 60s have passed
        if now - self.window_start >= 60:
            self.window_start = now
            self.requests_in_window = 0
        
        # Check if under limit
        return self.requests_in_window < self.rpm_limit
    
    def record_request(self):
        """Record a request to this provider."""
        now = time.time()
        
        # Reset window if needed
        if now - self.window_start >= 60:
            self.window_start = now
            self.requests_in_window = 0
        
        self.requests_in_window += 1


# Provider routing configuration
# Maps OpenRouter model IDs → (preferred_provider, native_model_id)
PROVIDER_ROUTING = {
    # Google Gemini models → Google AI (15 RPM, ultra-fast)
    "google/gemini-2.0-flash-exp:free": (Provider.GOOGLE, "gemini-2.0-flash-exp"),
    "google/gemini-2.5-flash:free": (Provider.GOOGLE, "gemini-2.5-flash-latest"),
    
    # Meta Llama models → Groq (ultra-fast LPU, generous limits)
    "meta-llama/llama-3.1-405b-instruct:free": (Provider.GROQ, "llama-3.1-405b-reasoning"),
    "meta-llama/llama-3.3-70b-instruct:free": (Provider.GROQ, "llama-3.3-70b-versatile"),
    "meta-llama/llama-3.2-3b-instruct:free": (Provider.GROQ, "llama-3.2-3b-preview"),
    
    # Everything else → OpenRouter (fallback, diverse models)
    # DeepSeek, Qwen, others remain on OpenRouter
}


class ProviderRouter:
    """
    Intelligent router for multi-provider FREE tier orchestration.
    
    Routes model requests to optimal provider based on:
    1. Model family (Gemini → Google, Llama → Groq)
    2. Provider capacity (rate limits)
    3. Automatic fallback to OpenRouter if primary exhausted
    """
    
    def __init__(self):
        """Initialize router with capacity tracking."""
        # Initialize provider clients
        from .google_ai_client import get_google_client
        from .groq_client import get_groq_client
        
        self.google_client = get_google_client()
        self.groq_client = get_groq_client()
        
        # Initialize capacity tracking
        self.capacity = {
            Provider.OPENROUTER: ProviderCapacity(
                rpm_limit=20,  # OpenRouter: 20 RPM for :free models
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.GOOGLE: ProviderCapacity(
                rpm_limit=15,  # Google: 15 RPM for Gemini 2.0 Flash
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.GROQ: ProviderCapacity(
                rpm_limit=50,  # Groq: Conservative estimate (actual may be higher)
                window_start=time.time(),
                requests_in_window=0
            ),
        }
        
        # Log availability
        providers_available = []
        if self.google_client:
            providers_available.append("Google AI (15 RPM)")
        if self.groq_client:
            providers_available.append("Groq (50+ RPM)")
        providers_available.append("OpenRouter (20 RPM)")
        
        logger.info(
            "🚀 Multi-provider router initialized: %s → Total ~%d RPM",
            ", ".join(providers_available),
            sum(c.rpm_limit for c in self.capacity.values() 
                if c.rpm_limit > 0)
        )
    
    def get_provider_for_model(
        self, 
        model_id: str
    ) -> Tuple[Provider, Optional[str]]:
        """
        Determine optimal provider for a model.
        
        Args:
            model_id: OpenRouter model ID (e.g., "google/gemini-2.0-flash-exp:free")
        
        Returns:
            (provider, native_model_id) tuple
            If native_model_id is None, use original model_id
        """
        # Check routing table
        if model_id in PROVIDER_ROUTING:
            provider, native_id = PROVIDER_ROUTING[model_id]
            
            # Check if provider is available and has capacity
            if provider == Provider.GOOGLE:
                if self.google_client and self.capacity[Provider.GOOGLE].can_proceed():
                    return (Provider.GOOGLE, native_id)
            
            elif provider == Provider.GROQ:
                if self.groq_client and self.capacity[Provider.GROQ].can_proceed():
                    return (Provider.GROQ, native_id)
        
        # Fallback to OpenRouter
        # Check OpenRouter capacity
        if self.capacity[Provider.OPENROUTER].can_proceed():
            return (Provider.OPENROUTER, None)
        
        # All providers exhausted - still return OpenRouter but log warning
        logger.warning(
            "All providers at capacity, routing to OpenRouter (may hit 429): %s",
            model_id
        )
        return (Provider.OPENROUTER, None)
    
    async def generate(
        self, 
        model_id: str, 
        prompt: str,
        orchestrator: Optional[any] = None
    ) -> Optional[str]:
        """
        Generate response using optimal provider.
        
        Args:
            model_id: OpenRouter model ID
            prompt: User prompt
            orchestrator: OpenRouter orchestrator instance (for fallback)
        
        Returns:
            Generated text or None if all providers fail
        """
        # Determine provider
        provider, native_model = self.get_provider_for_model(model_id)
        
        # Record request for capacity tracking
        self.capacity[provider].record_request()
        
        try:
            # Route to appropriate provider
            if provider == Provider.GOOGLE and self.google_client:
                logger.debug("Routing %s → Google AI (native: %s)", model_id, native_model)
                return await self.google_client.generate_with_retry(prompt, native_model)
            
            elif provider == Provider.GROQ and self.groq_client:
                logger.debug("Routing %s → Groq LPU (native: %s)", model_id, native_model)
                return await self.groq_client.generate_with_retry(prompt, native_model)
            
            else:
                # OpenRouter fallback
                logger.debug("Routing %s → OpenRouter (fallback)", model_id)
                if orchestrator:
                    # Use existing OpenRouter logic via orchestrator
                    # This will be implemented in elite_orchestration.py
                    return None  # Caller will handle OpenRouter
                else:
                    logger.warning("No orchestrator provided for OpenRouter fallback")
                    return None
        
        except Exception as e:
            logger.error("Provider %s failed for %s: %s", provider.value, model_id, e)
            
            # Try OpenRouter fallback if primary failed
            if provider != Provider.OPENROUTER and orchestrator:
                logger.info("Falling back to OpenRouter for %s", model_id)
                return None  # Caller will handle OpenRouter fallback
            
            return None
    
    def get_capacity_status(self) -> Dict[str, Dict]:
        """Get current capacity status for all providers."""
        status = {}
        for provider, capacity in self.capacity.items():
            status[provider.value] = {
                "rpm_limit": capacity.rpm_limit,
                "requests_in_window": capacity.requests_in_window,
                "available": capacity.can_proceed(),
                "utilization": f"{capacity.requests_in_window}/{capacity.rpm_limit}"
            }
        return status


# Singleton instance
_provider_router: Optional[ProviderRouter] = None


def get_provider_router() -> ProviderRouter:
    """
    Get singleton provider router instance.
    
    Creates instance on first call and reuses for subsequent calls.
    """
    global _provider_router
    
    if _provider_router is None:
        _provider_router = ProviderRouter()
    
    return _provider_router


def reset_provider_router():
    """Reset the singleton (useful for testing)."""
    global _provider_router
    _provider_router = None
