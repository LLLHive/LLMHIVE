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
    FIREWORKS = "fireworks"
    HYPERBOLIC = "hyperbolic"
    DASHSCOPE = "dashscope"
    DEEPINFRA = "deepinfra"
    AZURE_FOUNDRY = "azure_foundry"
    CLOUDFLARE = "cloudflare"
    KIMI = "kimi"


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
        from .fireworks_client import get_fireworks_client
        from .hyperbolic_client import get_hyperbolic_client
        from .dashscope_client import get_dashscope_client
        from .deepinfra_client import get_deepinfra_client
        from .azure_foundry_client import get_azure_foundry_client
        from .cloudflare_client import get_cloudflare_client
        from .kimi_client import get_kimi_client

        self.google_client = get_google_client()
        self.deepseek_client = get_deepseek_client()
        self.together_client = get_together_client()
        self.groq_client = get_groq_client()
        self.grok_client = None  # xAI Grok handled by orchestrator.py directly
        self.cerebras_client = get_cerebras_client()
        self.hf_client = get_hf_client()
        self.fireworks_client = get_fireworks_client()
        self.hyperbolic_client = get_hyperbolic_client()
        self.dashscope_client = get_dashscope_client()
        self.deepinfra_client = get_deepinfra_client()
        self.azure_foundry_client = get_azure_foundry_client()
        self.cloudflare_client = get_cloudflare_client()
        self.kimi_client = get_kimi_client()

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
            Provider.FIREWORKS: ProviderCapacity(
                rpm_limit=60,  # Fireworks serverless: separate quota from OpenRouter
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.HYPERBOLIC: ProviderCapacity(
                rpm_limit=60,
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.DASHSCOPE: ProviderCapacity(
                rpm_limit=30,
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.DEEPINFRA: ProviderCapacity(
                rpm_limit=30,
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.AZURE_FOUNDRY: ProviderCapacity(
                rpm_limit=30,
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.CLOUDFLARE: ProviderCapacity(
                rpm_limit=20,
                window_start=time.time(),
                requests_in_window=0
            ),
            Provider.KIMI: ProviderCapacity(
                rpm_limit=20,
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
        if self.fireworks_client:
            providers_available.append("Fireworks serverless (60 RPM est.)")
        if self.hyperbolic_client:
            providers_available.append("Hyperbolic serverless (60 RPM est.)")
        if self.dashscope_client:
            providers_available.append("DashScope/Qwen (30 RPM est.)")
        if self.deepinfra_client:
            providers_available.append("DeepInfra (30 RPM est.)")
        if self.azure_foundry_client:
            providers_available.append("Azure Foundry (30 RPM est.)")
        if self.cloudflare_client:
            providers_available.append("Cloudflare Workers AI (20 RPM est.)")
        if self.kimi_client:
            providers_available.append("Kimi/Moonshot (20 RPM est.)")
        providers_available.append("OpenRouter (20 RPM)")
        
        logger.info(
            "🚀 Multi-provider router initialized: %s → Total ~%d RPM",
            ", ".join(providers_available),
            sum(c.rpm_limit for c in self.capacity.values() 
                if c.rpm_limit > 0)
        )
    
    def _provider_chain_for_model(self, model_id: str) -> list:
        from .provider_chain import build_provider_chain, routing_v2_enabled, is_free_tier_slug

        if routing_v2_enabled() and is_free_tier_slug(model_id):
            return build_provider_chain(model_id)
        if model_id in PROVIDER_ROUTING:
            p, native = PROVIDER_ROUTING[model_id]
            return [(p.value, native)]
        return [(Provider.OPENROUTER.value, None)]

    def _client_available(self, provider: Provider) -> bool:
        return {
            Provider.GROQ: self.groq_client,
            Provider.GOOGLE: self.google_client,
            Provider.DEEPSEEK: self.deepseek_client,
            Provider.TOGETHER: self.together_client,
            Provider.CEREBRAS: self.cerebras_client,
            Provider.HUGGINGFACE: self.hf_client,
            Provider.FIREWORKS: self.fireworks_client,
            Provider.HYPERBOLIC: self.hyperbolic_client,
            Provider.DASHSCOPE: self.dashscope_client,
            Provider.DEEPINFRA: self.deepinfra_client,
            Provider.AZURE_FOUNDRY: self.azure_foundry_client,
            Provider.CLOUDFLARE: self.cloudflare_client,
            Provider.KIMI: self.kimi_client,
            Provider.OPENROUTER: True,
            Provider.GROK: self.grok_client,
        }.get(provider)

    def _can_use_provider(self, provider: Provider) -> bool:
        if provider == Provider.OPENROUTER:
            return self.capacity[Provider.OPENROUTER].can_proceed()
        if not self._client_available(provider):
            return False
        cap = self.capacity.get(provider)
        return cap is None or cap.can_proceed()

    def get_provider_for_model(
        self, 
        model_id: str
    ) -> Tuple[Provider, Optional[str]]:
        """
        Determine optimal provider for a model.
        
        ROUTING_V2 (free slugs): first available direct provider from cost-ordered chain.
        Legacy: PROVIDER_ROUTING table, then OpenRouter.
        """
        for provider_str, native_id in self._provider_chain_for_model(model_id):
            try:
                provider = Provider(provider_str)
            except ValueError:
                continue
            if self._can_use_provider(provider):
                return provider, native_id

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

    async def _dispatch_provider(
        self,
        provider: Provider,
        model_id: str,
        native_model: Optional[str],
        prompt: str,
        orchestrator: Optional[any] = None,
    ) -> Optional[str]:
        """Single-provider generation attempt."""
        target = native_model or model_id
        if provider == Provider.GROQ and self.groq_client:
            return await self.groq_client.generate_with_retry(prompt, target)
        if provider == Provider.GOOGLE and self.google_client:
            return await self.google_client.generate_with_retry(prompt, target)
        if provider == Provider.DEEPSEEK and self.deepseek_client:
            return await self.deepseek_client.generate_with_retry(prompt, target)
        if provider == Provider.TOGETHER and self.together_client:
            return await self.together_client.generate_with_retry(prompt, target)
        if provider == Provider.CEREBRAS and self.cerebras_client:
            return await self.cerebras_client.generate_with_retry(prompt, target or "llama3.1-8b")
        if provider == Provider.FIREWORKS and self.fireworks_client:
            return await self.fireworks_client.generate_with_retry(prompt, model_id)
        if provider == Provider.HYPERBOLIC and self.hyperbolic_client:
            return await self.hyperbolic_client.generate_with_retry(prompt, model_id)
        if provider == Provider.DASHSCOPE and self.dashscope_client:
            return await self.dashscope_client.generate_with_retry(prompt, model_id)
        if provider == Provider.DEEPINFRA and self.deepinfra_client:
            return await self.deepinfra_client.generate_with_retry(prompt, model_id)
        if provider == Provider.AZURE_FOUNDRY and self.azure_foundry_client:
            return await self.azure_foundry_client.generate_with_retry(prompt, model_id)
        if provider == Provider.CLOUDFLARE and self.cloudflare_client:
            return await self.cloudflare_client.generate_with_retry(prompt, model_id)
        if provider == Provider.KIMI and self.kimi_client:
            return await self.kimi_client.generate_with_retry(prompt, model_id)
        if provider == Provider.HUGGINGFACE and self.hf_client:
            return await self.hf_client.generate_with_retry(
                prompt, target or "meta-llama/Llama-3.3-70B-Instruct"
            )
        if provider == Provider.OPENROUTER:
            if orchestrator:
                return None
            logger.warning("No orchestrator provided for OpenRouter")
        return None

    async def generate(
        self, 
        model_id: str, 
        prompt: str,
        orchestrator: Optional[any] = None
    ) -> Optional[str]:
        """
        Generate using ROUTING_V2 provider chain (direct first, OpenRouter last for :free).
        """
        chain = self._provider_chain_for_model(model_id)
        last_error: Optional[Exception] = None

        for provider_str, native_model in chain:
            try:
                provider = Provider(provider_str)
            except ValueError:
                continue
            if not self._can_use_provider(provider):
                continue
            self.capacity[provider].record_request()
            try:
                logger.debug(
                    "Routing %s → %s (native: %s)", model_id, provider.value, native_model
                )
                result = await self._dispatch_provider(
                    provider, model_id, native_model, prompt, orchestrator
                )
                if result:
                    return result
                if provider == Provider.OPENROUTER and orchestrator:
                    return None
            except Exception as e:
                last_error = e
                logger.warning(
                    "Provider %s failed for %s: %s", provider.value, model_id, e
                )

        if last_error:
            logger.error("Provider chain exhausted for %s: %s", model_id, last_error)
        from .provider_chain import routing_v2_enabled, is_free_tier_slug

        if routing_v2_enabled() and is_free_tier_slug(model_id):
            return None
        return await self.try_all_fallbacks(model_id, prompt)
    
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
            logger.info("FALLBACK → Cerebras (llama3.1-8b) for failed %s", model_id)
            self.capacity[Provider.CEREBRAS].record_request()
            result = await self.cerebras_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("Cerebras fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Cerebras fallback failed for %s: %s", model_id, e)
            return None

    async def _try_fireworks_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        """Fireworks serverless — spillover for :free slugs when OpenRouter throttles."""
        if not self.fireworks_client:
            return None
        try:
            fw_model = self.fireworks_client.resolve_model(model_id)
            logger.info("FALLBACK → Fireworks (%s) for failed %s", fw_model, model_id)
            self.capacity[Provider.FIREWORKS].record_request()
            result = await self.fireworks_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("Fireworks fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Fireworks fallback failed for %s: %s", model_id, e)
            return None

    async def _try_hyperbolic_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        """Hyperbolic serverless — spillover for :free slugs when OpenRouter throttles."""
        if not self.hyperbolic_client:
            return None
        try:
            hb_model = self.hyperbolic_client.resolve_model(model_id)
            logger.info("FALLBACK → Hyperbolic (%s) for failed %s", hb_model, model_id)
            self.capacity[Provider.HYPERBOLIC].record_request()
            result = await self.hyperbolic_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("Hyperbolic fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Hyperbolic fallback failed for %s: %s", model_id, e)
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
        Walk full provider chain (cost-ordered direct APIs, OpenRouter last for :free).
        """
        from .provider_chain import routing_v2_enabled, is_free_tier_slug

        chain = self._provider_chain_for_model(model_id)
        if not (routing_v2_enabled() and is_free_tier_slug(model_id)):
            fallbacks = [
                self._try_fireworks_fallback,
                self._try_hyperbolic_fallback,
                self._try_dashscope_fallback,
                self._try_deepinfra_fallback,
                self._try_azure_foundry_fallback,
                self._try_cloudflare_fallback,
                self._try_kimi_fallback,
                self._try_together_fallback,
                self._try_cerebras_fallback,
                self._try_hf_fallback,
            ]
            for fn in fallbacks:
                result = await fn(model_id, prompt)
                if result:
                    return result
            logger.error("ALL fallback providers failed for %s", model_id)
            return None

        for provider_str, native_model in chain:
            try:
                provider = Provider(provider_str)
            except ValueError:
                continue
            if not self._can_use_provider(provider):
                continue
            self.capacity[provider].record_request()
            try:
                result = await self._dispatch_provider(
                    provider, model_id, native_model, prompt, None
                )
                if result:
                    return result
            except Exception as e:
                logger.warning("Chain fallback %s failed: %s", provider.value, e)

        logger.error("ALL fallback providers failed for %s", model_id)
        return None

    async def _try_dashscope_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        if not self.dashscope_client:
            return None
        try:
            self.capacity[Provider.DASHSCOPE].record_request()
            result = await self.dashscope_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("DashScope fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("DashScope fallback failed for %s: %s", model_id, e)
            return None

    async def _try_deepinfra_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        if not self.deepinfra_client:
            return None
        try:
            self.capacity[Provider.DEEPINFRA].record_request()
            result = await self.deepinfra_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("DeepInfra fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("DeepInfra fallback failed for %s: %s", model_id, e)
            return None

    async def _try_azure_foundry_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        if not self.azure_foundry_client:
            return None
        try:
            self.capacity[Provider.AZURE_FOUNDRY].record_request()
            result = await self.azure_foundry_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("Azure Foundry fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Azure Foundry fallback failed for %s: %s", model_id, e)
            return None

    async def _try_cloudflare_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        if not self.cloudflare_client:
            return None
        try:
            self.capacity[Provider.CLOUDFLARE].record_request()
            result = await self.cloudflare_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("Cloudflare fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Cloudflare fallback failed for %s", model_id, e)
            return None

    async def _try_kimi_fallback(self, model_id: str, prompt: str) -> Optional[str]:
        if not self.kimi_client:
            return None
        try:
            self.capacity[Provider.KIMI].record_request()
            result = await self.kimi_client.generate_with_retry(prompt, model_id)
            if result:
                logger.info("Kimi fallback SUCCESS for %s", model_id)
            return result
        except Exception as e:
            logger.error("Kimi fallback failed for %s: %s", model_id, e)
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
