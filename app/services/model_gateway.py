from typing import List, Dict, Any, AsyncGenerator
from pydantic import BaseModel
from ..models.llm_provider import get_provider_by_name, LLMProvider
from ..models.model_pool import model_pool

class StandardizedResponse(BaseModel):
    content: str

class ModelGateway:
    async def call(self, model_id: str, messages: List[Dict[str, str]], stream: bool = False, **kwargs):
        """
        Call a model through the gateway.
        Returns StandardizedResponse for sync calls or AsyncGenerator for stream calls.
        """
        profile = model_pool.get_model_profile(model_id)
        if not profile:
            error_msg = f"Model '{model_id}' not found in ModelPool."
            if stream:
                return self._error_stream(error_msg)
            return StandardizedResponse(content=error_msg)

        try:
            provider = get_provider_by_name(profile.provider)
            if stream:
                return self._stream_call(provider, model_id, messages, **kwargs)
            else:
                return await self._sync_call(provider, model_id, messages, **kwargs)
        except Exception as e:
            error_msg = f"Gateway error calling model '{model_id}': {e}"
            if stream:
                return self._error_stream(error_msg)
            return StandardizedResponse(content=error_msg)

    async def _sync_call(self, provider: LLMProvider, model: str, messages: List[Dict[str, str]], **kwargs) -> StandardizedResponse:
        content = await provider.generate(messages=messages, model=model, **kwargs)
        return StandardizedResponse(content=content)

    async def _stream_call(self, provider: LLMProvider, model: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        async for token in provider.generate_stream(messages=messages, model=model, **kwargs):
            yield token

    async def _error_stream(self, error_msg: str) -> AsyncGenerator[str, None]:
        """Helper to return error messages as a stream."""
        yield error_msg

model_gateway = ModelGateway()