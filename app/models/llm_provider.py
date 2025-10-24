"""
LLM Provider Interface and Factory.
"""

from abc import ABC, abstractmethod
import asyncio
from typing import AsyncGenerator
from ..config import settings

# Attempt to import real clients, but fail gracefully if not installed.
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

class LLMProvider(ABC):
    """Abstract base class for all LLM API providers."""
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        """Generates a full response."""
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generates a response token by token."""
        pass

class OpenAIProvider(LLMProvider):
    """Provider for OpenAI and compatible models."""
    def __init__(self, api_key: str):
        if not AsyncOpenAI:
            raise ImportError("OpenAI client not found. Please install with 'pip install openai'.")
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        print(f"Calling OpenAI model '{model}'...")
        try:
            response = await self.client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}], **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return f"Error: Could not get response from {model}."

    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        print(f"Streaming from OpenAI model '{model}'...")
        try:
            stream = await self.client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}], stream=True, **kwargs
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            print(f"Error streaming from OpenAI: {e}")
            yield f"Error: Could not stream response from {model}."

class AnthropicProvider(LLMProvider):
    """Provider for Anthropic models."""
    def __init__(self, api_key: str):
        if not AsyncAnthropic:
            raise ImportError("Anthropic client not found. Please install with 'pip install anthropic'.")
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        print(f"Calling Anthropic model '{model}'...")
        try:
            response = await self.client.messages.create(
                model=model, max_tokens=2048, messages=[{"role": "user", "content": prompt}], **kwargs
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error calling Anthropic: {e}")
            return f"Error: Could not get response from {model}."

    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        print(f"Streaming from Anthropic model '{model}'...")
        try:
            async with self.client.messages.stream(
                model=model, max_tokens=2048, messages=[{"role": "user", "content": prompt}], **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            print(f"Error streaming from Anthropic: {e}")
            yield f"Error: Could not stream response from {model}."

PROVIDER_MAP = {
    "openai": (OpenAIProvider, settings.OPENAI_API_KEY),
    "anthropic": (AnthropicProvider, settings.ANTHROPIC_API_KEY),
}

MODEL_PROVIDER_MAP = {
    "gpt-4": "openai", "gpt-4-turbo": "openai",
    "claude-3-opus": "anthropic", "claude-3-sonnet": "anthropic",
    "gemini-pro": "google", # Google provider would be implemented similarly
    "deepseek-coder": "openai", # Assuming DeepSeek has an OpenAI-compatible API
}

def get_provider_for_model(model_id: str) -> LLMProvider:
    """Factory function to get the correct provider instance."""
    provider_name = MODEL_PROVIDER_MAP.get(model_id)
    if not provider_name or provider_name not in PROVIDER_MAP:
        raise ValueError(f"Provider for model '{model_id}' is not configured or supported.")
    
    provider_class, api_key = PROVIDER_MAP[provider_name]
    return provider_class(api_key=api_key)
