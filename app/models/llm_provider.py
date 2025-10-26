"""
LLM Provider Interface and Factory.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict
from config import settings

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def generate_stream(self, messages: List[Dict[str, str]], model: str, **kwargs) -> AsyncGenerator[str, None]:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        if not AsyncOpenAI: raise ImportError("OpenAI client not found. Run 'pip install openai'.")
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        try:
            response = await self.client.chat.completions.create(model=model, messages=messages, **kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error: Could not get response from {model}."

    async def generate_stream(self, messages: List[Dict[str, str]], model: str, **kwargs) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(model=model, messages=messages, stream=True, **kwargs)
            async for chunk in stream:
                if content := chunk.choices[0].delta.content: yield content
        except Exception as e:
            yield f"Error: Could not stream from {model}."

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        if not AsyncAnthropic: raise ImportError("Anthropic client not found. Run 'pip install anthropic'.")
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        try:
            system_prompt = next((msg['content'] for msg in messages if msg['role'] == 'system'), None)
            user_messages = [msg for msg in messages if msg['role'] != 'system']
            response = await self.client.messages.create(model=model, max_tokens=4096, messages=user_messages, system=system_prompt, **kwargs)
            return response.content[0].text
        except Exception as e:
            return f"Error: Could not get response from {model}."

    async def generate_stream(self, messages: List[Dict[str, str]], model: str, **kwargs) -> AsyncGenerator[str, None]:
        try:
            system_prompt = next((msg['content'] for msg in messages if msg['role'] == 'system'), None)
            user_messages = [msg for msg in messages if msg['role'] != 'system']
            async with self.client.messages.stream(model=model, max_tokens=4096, messages=user_messages, system=system_prompt, **kwargs) as stream:
                async for text in stream.text_stream: yield text
        except Exception as e:
            yield f"Error: Could not stream from {model}."


# Import stub provider
from .stub_provider import StubProvider

PROVIDER_CLASS_MAP = {
    "openai": (OpenAIProvider, settings.OPENAI_API_KEY),
    "anthropic": (AnthropicProvider, settings.ANTHROPIC_API_KEY),
    "stub": (StubProvider, "stub")
}

def get_provider_by_name(provider_name: str) -> LLMProvider:
    """
    Initializes and returns a provider instance, checking for API key existence first.
    Falls back to stub provider if requested provider is not available.
    """
    # If provider not in map or is stub, use stub
    if provider_name not in PROVIDER_CLASS_MAP or provider_name == "stub":
        return StubProvider()
    
    provider_class, api_key = PROVIDER_CLASS_MAP[provider_name]
    
    # If no API key, fall back to stub
    if not api_key:
        return StubProvider()
        
    return provider_class(api_key=api_key)
