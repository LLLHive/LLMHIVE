"""
Multi-Provider Router
====================

Intelligently routes model requests across multiple providers:
- OpenRouter (20 RPM, 20+ free models)
- Google AI (15 RPM, Gemini models - FREE)
- DeepSeek (30 RPM, V3.2 models - paid credits)

Benefits:
- 2x capacity increase (20 → 65+ RPM total)
- Elite math/reasoning via DeepSeek V3.2 (96% AIME)
- Automatic fallback on rate limits
- Load distribution across providers
- Cost-effective ($0.28/M tokens for DeepSeek vs $1.75/M for GPT)

Strategy:
1. Route Gemini → Google AI (15 RPM, FREE)
2. Route DeepSeek → DeepSeek Direct (30 RPM, for math/reasoning)
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
    DEEPSEEK = "deepseek"
    TOGETHER = "together"
    GROQ = "groq"
    GROK = "grok"  # xAI Grok (paid, high quality)
    CEREBRAS = "cerebras"
    HUGGINGFACE = "huggingface"


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
# Google models are resolved dynamically — the native_model_id here is
# passed to GoogleAIClient which re-resolves it through auto-discovery.
PROVIDER_ROUTING = {
    # Google Gemini models → Google AI (resolved dynamically)
    "google/gemini-2.0-flash-exp:free": (Provider.GOOGLE, "gemini-flash"),
    "google/gemini-2.5-flash:free": (Provider.GOOGLE, "gemini-flash"),
    
    # Groq models → Groq LPU (30 RPM, ~200ms latency, FREE)
    "meta-llama/llama-3.3-70b-instruct:free": (Provider.GROQ, "llama-3.3-70b-versatile"),

    # DeepSeek models → DeepSeek Direct (30 RPM, excellent for math/reasoning)
    "deepseek/deepseek-r1-0528:free": (Provider.DEEPSEEK, "deepseek-reasoner"),
    "deepseek/deepseek-chat": (Provider.DEEPSEEK, "deepseek-chat"),

    # Together.ai models → Together Direct (backup/complement)
    "together/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": (
        Provider.TOGETHER,
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    ),
    "together/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": (
        Provider.TOGETHER,
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
    ),
    "together/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": (
        Provider.TOGETHER,
        "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    ),
    "together/Qwen/Qwen2.5-72B-Instruct-Turbo": (
        Provider.TOGETHER,
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
    ),
    "together/Qwen/Qwen2.5-7B-Instruct-Turbo": (
        Provider.TOGETHER,
        "Qwen/Qwen2.5-7B-Instruct-Turbo",
    ),
    
    # Groq models → Groq LPU (30 RPM, ultra-fast ~200ms)
    "groq/llama-3.3-70b": (Provider.GROQ, "llama-3.3-70b-versatile"),
    "groq/llama-4-maverick": (Provider.GROQ, "meta-llama/llama-4-maverick-17b-128e-instruct"),

    # Everything else → OpenRouter (includes Llama, Qwen, and all other models)
}


class ProviderRouter:
    """
    Intelligent router for multi-provider FREE tier orchestration.
    
    Routes model requests to optimal provider based on:
    1. Model family (Gemini → Google, DeepSeek → DeepSeek)
    2. Provider capacity (rate limits)
    3. Automatic fallback to OpenRouter if primary exhausted
    """
    
    def __init__(self):
        """Initialize router with capacity tracking."""
        # Initialize provider clients
        from .google_ai_client import get_google_client
        from .deepseek_client import get_deepseek_client
        from .together_client import get_together_client
        from .groq_client import get_groq_client
        from .cerebras_client import get_cerebras_client
        from .hf_client import get_hf_client
        
        self.google_client = get_google_client()
        self.deepseek_client = get_deepseek_client()
        self.together_client = get_together_client()
        self.groq_client = get_groq_client()
        self.grok_client = None  # xAI Grok handled by orchestrator.py directly
        self.cerebras_client = get_cerebras_client()
        self.hf_client = get_hf_client()
        
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
            Provider.DEEPSEEK: ProviderCapacity(
                rpm_limit=30,  # DeepSeek: 30 RPM with credits
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.TOGETHER: ProviderCapacity(
                rpm_limit=20,  # Together.ai: conservative default
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.GROQ: ProviderCapacity(
                rpm_limit=30,  # Groq: 30 RPM free tier
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.GROK: ProviderCapacity(
                rpm_limit=60,  # xAI Grok: 60 RPM paid tier
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.CEREBRAS: ProviderCapacity(
                rpm_limit=30,  # Cerebras: 30 RPM free tier, 2000+ tok/s
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.HUGGINGFACE: ProviderCapacity(
                rpm_limit=10,  # HuggingFace: conservative (few hundred/hour)
                window_start=time.time(),
                requests_in_window=0
            ),
        }
        
        # Log availability
        providers_available = []
        if self.groq_client:
            providers_available.append("Groq LPU (30 RPM)")
        if self.grok_client:
            providers_available.append("xAI Grok (60 RPM)")
        if self.cerebras_client:
            providers_available.append("Cerebras WSE (30 RPM)")
        if self.google_client:
            providers_available.append("Google AI (15 RPM)")
        if self.deepseek_client:
            providers_available.append("DeepSeek (30 RPM)")
        if self.together_client:
            providers_available.append("Together.ai (20 RPM)")
        if self.hf_client:
            providers_available.append("HuggingFace (10 RPM)")
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
            if provider == Provider.GROQ:
                if self.groq_client and self.capacity[Provider.GROQ].can_proceed():
                    return (Provider.GROQ, native_id)

            elif provider == Provider.GOOGLE:
                if self.google_client and self.capacity[Provider.GOOGLE].can_proceed():
                    return (Provider.GOOGLE, native_id)
            
            elif provider == Provider.DEEPSEEK:
                if self.deepseek_client and self.capacity[Provider.DEEPSEEK].can_proceed():
                    return (Provider.DEEPSEEK, native_id)
            
            elif provider == Provider.TOGETHER:
                if self.together_client and self.capacity[Provider.TOGETHER].can_proceed():
                    return (Provider.TOGETHER, native_id)
        
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
    
    # Model mapping: OpenRouter model IDs → Together.ai equivalents for fallback
    OPENROUTER_TO_TOGETHER_MAP = {
        "openai/gpt-4o-mini": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "openai/gpt-4o": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "meta-llama/llama-3.3-70b-instruct:free": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "meta-llama/llama-3.1-8b-instruct:free": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "qwen/qwen-2.5-72b-instruct:free": "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "qwen/qwen-2.5-7b-instruct:free": "Qwen/Qwen2.5-7B-Instruct-Turbo",
        "google/gemini-2.0-flash-exp:free": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "mistralai/mistral-small-3.1-24b-instruct:free": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    }

    async def generate(
        self, 
        model_id: str, 
        prompt: str,
        orchestrator: Optional[any] = None
    ) -> Optional[str]:
        """
        Generate response using optimal provider.
        
        Fallback chain: Primary Provider → OpenRouter → Together.ai
        Together.ai acts as instant backup when OpenRouter fails (403/429/5xx).
        
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
            if provider == Provider.GROQ and self.groq_client:
                logger.debug("Routing %s → Groq LPU (native: %s)", model_id, native_model)
                return await self.groq_client.generate_with_retry(prompt, native_model)
            
            elif provider == Provider.GOOGLE and self.google_client:
                logger.debug("Routing %s → Google AI (native: %s)", model_id, native_model)
                return await self.google_client.generate_with_retry(prompt, native_model)
            
            elif provider == Provider.DEEPSEEK and self.deepseek_client:
                logger.debug("Routing %s → DeepSeek API (native: %s)", model_id, native_model)
                return await self.deepseek_client.generate_with_retry(prompt, native_model)
            
            elif provider == Provider.TOGETHER and self.together_client:
                logger.debug("Routing %s → Together.ai (native: %s)", model_id, native_model)
                return await self.together_client.generate_with_retry(prompt, native_model)
            
            else:
                # OpenRouter as default
                logger.debug("Routing %s → OpenRouter (default)", model_id)
                if orchestrator:
                    return None  # Caller will handle OpenRouter
                else:
                    logger.warning("No orchestrator provided for OpenRouter")
                    return None
        
        except Exception as e:
            logger.error("Provider %s failed for %s: %s", provider.value, model_id, e)
            
            # INSTANT FALLBACK: Together.ai when any provider fails
            together_result = await self._try_together_fallback(model_id, prompt)
            if together_result:
                return together_result
            
            # If Together.ai also failed and primary wasn't OpenRouter, signal caller to try OpenRouter
            if provider != Provider.OPENROUTER and orchestrator:
                logger.info("Falling back to OpenRouter for %s", model_id)
                return None  # Caller will handle OpenRouter fallback
            
            return None
    
    async def _try_together_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        """
        Instant Together.ai fallback when primary provider fails.
        Maps the requested model to a Together.ai equivalent and retries.
        """
        if not self.together_client:
            return None
        
        # Find Together.ai equivalent model
        together_model = self.OPENROUTER_TO_TOGETHER_MAP.get(model_id)
        if not together_model:
            # Default fallback: use Llama 3.1 70B as general-purpose replacement
            together_model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        
        try:
            logger.info("FALLBACK → Together.ai (%s) for failed %s", together_model, model_id)
            self.capacity[Provider.TOGETHER].record_request()
            result = await self.together_client.generate_with_retry(prompt, together_model)
            if result:
                logger.info("Together.ai fallback SUCCESS for %s", model_id)
            return result
        except Exception as fallback_error:
            logger.error("Together.ai fallback also failed for %s: %s", model_id, fallback_error)
            return None

    async def _try_cerebras_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        """
        Cerebras fallback -- ultra-fast wafer-scale inference (2000+ tok/s).
        Used when both primary provider and Together.ai fail.
        """
        if not self.cerebras_client:
            return None
        
        try:
            logger.info("FALLBACK → Cerebras (llama-3.3-70b) for failed %s", model_id)
            self.capacity[Provider.CEREBRAS].record_request()
            result = await self.cerebras_client.generate_with_retry(prompt, "llama-3.3-70b")
            if result:
                logger.info("Cerebras fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Cerebras fallback failed for %s: %s", model_id, e)
            return None

    async def _try_hf_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        """
        HuggingFace Inference fallback -- last resort using open models.
        Used when primary, Together.ai, and Cerebras all fail.
        """
        if not self.hf_client:
            return None
        
        try:
            logger.info("FALLBACK → HuggingFace (Llama-3.3-70B) for failed %s", model_id)
            self.capacity[Provider.HUGGINGFACE].record_request()
            result = await self.hf_client.generate_with_retry(
                prompt, "meta-llama/Llama-3.3-70B-Instruct"
            )
            if result:
                logger.info("HuggingFace fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("HuggingFace fallback failed for %s: %s", model_id, e)
            return None

    async def try_all_fallbacks(self, model_id: str, prompt: str) -> Optional[str]:
        """
        Try all fallback providers in order:
        Together.ai → Cerebras → HuggingFace
        Returns first successful result or None.
        """
        # 1. Together.ai (good model variety, paid)
        result = await self._try_together_fallback(model_id, prompt)
        if result:
            return result
        
        # 2. Cerebras (ultra-fast, free 1M tokens/day)
        result = await self._try_cerebras_fallback(model_id, prompt)
        if result:
            return result
        
        # 3. HuggingFace (free, slower, last resort)
        result = await self._try_hf_fallback(model_id, prompt)
        if result:
            return result
        
        logger.error("ALL fallback providers failed for %s", model_id)
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
