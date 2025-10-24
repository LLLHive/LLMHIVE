"""
LLM Provider Interface and Factory.

This module provides an abstraction for interacting with various LLM APIs
(e.g., OpenAI, Anthropic, Google) and includes a factory function to
instantiate the correct provider for a given model.
"""

from abc import ABC, abstractmethod
import asyncio
from ..config import settings

class LLMProvider(ABC):
    """Abstract base class for all LLM API providers."""
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        """Generates a response from the specified model."""
        pass

class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        # In a real app: from openai import AsyncOpenAI; self.client = AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        print(f"Calling OpenAI model '{model}'...")
        await asyncio.sleep(1) # Simulate network call
        # Real call would be:
        # response = await self.client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
        # return response.choices[0].message.content
        return f"Simulated response from OpenAI model {model} for prompt: '{prompt[:40]}...'"

class AnthropicProvider(LLMProvider):
    """Provider for Anthropic models."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        # In a real app: from anthropic import AsyncAnthropic; self.client = AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        print(f"Calling Anthropic model '{model}'...")
        await asyncio.sleep(1)
        return f"Simulated response from Anthropic model {model} for prompt: '{prompt[:40]}...'"

class GoogleProvider(LLMProvider):
    """Provider for Google models."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        # In a real app: import google.generativeai as genai; genai.configure(api_key=api_key)

    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        print(f"Calling Google model '{model}'...")
        await asyncio.sleep(1)
        return f"Simulated response from Google model {model} for prompt: '{prompt[:40]}...'"

# A mapping from provider names to their classes and required API keys
PROVIDER_MAP = {
    "openai": (OpenAIProvider, settings.OPENAI_API_KEY),
    "anthropic": (AnthropicProvider, settings.ANTHROPIC_API_KEY),
    "google": (GoogleProvider, settings.GOOGLE_API_KEY),
    "deepseek": (OpenAIProvider, "dummy_key_for_deepseek_if_openai_compatible"), # Example for compatible APIs
}

# A mapping from specific model IDs to their provider names
# In a real system, this would be part of the ModelPool's data
MODEL_PROVIDER_MAP = {
    "gpt-4": "openai",
    "claude-3-opus": "anthropic",
    "gemini-pro": "google",
    "deepseek-coder": "deepseek",
}

def get_provider_for_model(model_id: str) -> LLMProvider:
    """Factory function to get the correct provider for a given model ID."""
    provider_name = MODEL_PROVIDER_MAP.get(model_id)
    if not provider_name:
        raise ValueError(f"No provider found for model_id: {model_id}")

    provider_config = PROVIDER_MAP.get(provider_name)
    if not provider_config:
        raise ValueError(f"Provider '{provider_name}' is not configured.")
    
    provider_class, api_key = provider_config
    return provider_class(api_key=api_key)
