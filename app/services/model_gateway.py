"""
The Model Gateway Service for LLMHive.

This service provides a single, unified interface for interacting with any
configured LLM provider. It abstracts away the complexities of different
APIs and response formats, exposing a standardized `call` method.
"""

from typing import List, Dict, Any, AsyncGenerator
from pydantic import BaseModel
from ..models.llm_provider import get_provider_for_model, LLMProvider

class StandardizedResponse(BaseModel):
    """A standardized response object returned by the gateway."""
    content: str
    tool_calls: List[Dict[str, Any]] = []
    usage: Dict[str, int] = {}

class ModelGateway:
    """A unified gateway to call any supported LLM provider."""

    async def call(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> StandardizedResponse | AsyncGenerator[str, None]:
        """
        Calls the specified model via its provider and returns a standardized response or stream.

        Args:
            provider_name: The name of the provider (e.g., 'openai', 'anthropic').
            model: The specific model ID to use.
            messages: The list of messages for the prompt.
            stream: Whether to stream the response.
            **kwargs: Additional provider-specific parameters.
        """
        try:
            provider = get_provider_for_model(provider_name)
        except ValueError as e:
            # Fallback to a default provider if the requested one is not found
            print(f"Warning: {e}. Falling back to default provider.")
            provider = get_provider_for_model("openai") # Assumes OpenAI is always available

        if stream:
            return self._stream_call(provider, model, messages, **kwargs)
        else:
            return await self._sync_call(provider, model, messages, **kwargs)

    async def _sync_call(
        self, provider: LLMProvider, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> StandardizedResponse:
        """Handles a regular, non-streaming call."""
        print(f"Gateway calling model '{model}' via '{type(provider).__name__}'")
        # Here, we would normalize the response to our StandardizedResponse format.
        # For now, the provider's generate method returns a string, so we wrap it.
        content = await provider.generate(messages=messages, model=model, **kwargs)
        return StandardizedResponse(content=content)

    async def _stream_call(
        self, provider: LLMProvider, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Handles a streaming call."""
        print(f"Gateway streaming from model '{model}' via '{type(provider).__name__}'")
        async for token in provider.generate_stream(messages=messages, model=model, **kwargs):
            yield token

# Singleton instance of the gateway to be used across the application
model_gateway = ModelGateway()
