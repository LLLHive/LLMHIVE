"""
Multi-Provider Integration Package
==================================

Direct API integrations for multi-provider capacity distribution:
- Google AI (Gemini models): 15 RPM independent
- Groq LPU (Llama models): 30 RPM, ultra-fast ~200ms
- Cerebras WSE (Llama/Qwen): 30 RPM, 2000+ tok/s, free 1M tok/day
- DeepSeek (R1/Chat models): 30 RPM, elite math/reasoning
- Together.ai (Llama/Qwen): backup/complement
- HuggingFace (open models): last-resort fallback
- OpenRouter (all others): primary router, 20 RPM

Total capacity: ~155 RPM (7+ providers)

Usage:
    from llmhive.app.providers import get_provider_router
    
    router = get_provider_router()
    response = await router.generate("deepseek/deepseek-r1-0528:free", "Solve x^2 + 5x + 6 = 0")
"""

from .google_ai_client import GoogleAIClient, get_google_client
from .deepseek_client import DeepSeekClient, get_deepseek_client
from .together_client import TogetherClient, get_together_client
from .groq_client import GroqClient, get_groq_client
from .cerebras_client import CerebrasClient, get_cerebras_client
from .hf_client import HuggingFaceClient, get_hf_client
from .fireworks_client import FireworksClient, get_fireworks_client
from .hyperbolic_client import HyperbolicClient, get_hyperbolic_client
from .dashscope_client import get_dashscope_client
from .deepinfra_client import get_deepinfra_client
from .azure_foundry_client import AzureFoundryClient, get_azure_foundry_client
from .cloudflare_client import CloudflareClient, get_cloudflare_client
from .kimi_client import get_kimi_client
from .provider_chain import (
    build_provider_chain,
    primary_provider_name,
    routing_v2_enabled,
    is_free_tier_slug,
)
from .provider_router import (
    ProviderRouter,
    Provider,
    get_provider_router,
    reset_provider_router,
)

__all__ = [
    "GoogleAIClient",
    "get_google_client",
    "DeepSeekClient",
    "get_deepseek_client",
    "TogetherClient",
    "get_together_client",
    "GroqClient",
    "get_groq_client",
    "CerebrasClient",
    "get_cerebras_client",
    "HuggingFaceClient",
    "get_hf_client",
    "FireworksClient",
    "get_fireworks_client",
    "HyperbolicClient",
    "get_hyperbolic_client",
    "get_dashscope_client",
    "get_deepinfra_client",
    "AzureFoundryClient",
    "get_azure_foundry_client",
    "CloudflareClient",
    "get_cloudflare_client",
    "get_kimi_client",
    "build_provider_chain",
    "primary_provider_name",
    "routing_v2_enabled",
    "is_free_tier_slug",
    "ProviderRouter",
    "Provider",
    "get_provider_router",
    "reset_provider_router",
]
