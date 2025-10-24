"""
The Model Gateway Service for LLMHive.

This service provides a single, unified interface for interacting with any
configured LLM provider. It abstracts away the complexities of different
APIs and response formats, exposing a standardized `call` method.
"""

from typing import List, Dict, Any, AsyncGenerator
from pydantic import BaseModel
from ..models.llm_provider import get_provider_by_name, LLMProvider
from ..models.model_pool import model_pool

class StandardizedResponse(BaseModel):
    """A standardized response object returned by the gateway."""
    content: str
    tool_calls: List[Dict[str, Any]] = []
    usage: Dict[str, int] = {}

class ModelGateway:
    """A unified gateway to call any supported LLM provider."""

    async def call(
        self, model_id: str, messages: List[Dict[str, str]], stream: bool = False, **kwargs
    ) -> StandardizedResponse | AsyncGenerator[str, None]:
        """Calls the specified model via its provider."""
        profile = model_pool.get_model_profile(model_id)
        if not profile:
            error_msg = f"Model '{model_id}' not found in ModelPool."
            print(f"ERROR: {error_msg}")
            if stream:
                async def error_generator():
                    yield error_msg
                return error_generator()
            return StandardizedResponse(content=error_msg)

        try:
            provider = get_provider_by_name(profile.provider)
            if stream:
                return self._stream_call(provider, model_id, messages, **kwargs)
            else:
                return await self._sync_call(provider, model_id, messages, **kwargs)
        except Exception as e:
            error_msg = f"Gateway error calling model '{model_id}': {e}"
            print(f"ERROR: {error_msg}")
            if stream:
                async def error_generator():
                    yield error_msg
                return error_generator()
            return StandardizedResponse(content=error_msg)

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
