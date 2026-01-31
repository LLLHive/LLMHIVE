"""
Multi-Provider Integration Package
==================================

Direct API integrations for FREE tier capacity distribution:
- Google AI (Gemini models): 15 RPM independent
- Groq (Llama models): Ultra-fast LPU, generous limits  
- OpenRouter (all others): Fallback, 20 RPM

Total capacity: ~40+ RPM (2-3x increase over OpenRouter alone)

Usage:
    from llmhive.app.providers import get_provider_router
    
    router = get_provider_router()
    response = await router.generate("meta-llama/llama-3.1-405b-instruct:free", "Hello")
"""

from .google_ai_client import GoogleAIClient, get_google_client
from .groq_client import GroqClient, get_groq_client
from .provider_router import (
    ProviderRouter,
    Provider,
    get_provider_router,
    reset_provider_router,
)

__all__ = [
    "GoogleAIClient",
    "get_google_client",
    "GroqClient",
    "get_groq_client",
    "ProviderRouter",
    "Provider",
    "get_provider_router",
    "reset_provider_router",
]
