"""
Multi-Provider Integration Package
==================================

Direct API integrations for FREE tier capacity distribution:
- Google AI (Gemini models): 15 RPM independent
- DeepSeek (R1/Chat models): 30 RPM, elite math/reasoning
- Together.ai (Llama/Qwen models): backup/complement
- OpenRouter (all others): Fallback, 20 RPM

Total capacity: ~65 RPM (3x increase over OpenRouter alone)

Usage:
    from llmhive.app.providers import get_provider_router
    
    router = get_provider_router()
    response = await router.generate("deepseek/deepseek-r1-0528:free", "Solve x^2 + 5x + 6 = 0")
"""

from .google_ai_client import GoogleAIClient, get_google_client
from .deepseek_client import DeepSeekClient, get_deepseek_client
from .together_client import TogetherClient, get_together_client
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
    "ProviderRouter",
    "Provider",
    "get_provider_router",
    "reset_provider_router",
]
