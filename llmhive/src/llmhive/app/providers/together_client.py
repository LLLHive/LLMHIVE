"""
Together.ai Direct API Client
=============================

Direct integration with Together.ai for backup/complementary model access.

Docs:
- Chat completions: https://docs.together.ai/reference/chat-completions-1
"""

from __future__ import annotations

import os
import logging
import httpx
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class TogetherClient:
    """Client for Together.ai Chat Completions API."""

    BASE_URL = "https://api.together.ai/v1"
    DEFAULT_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

    # Optional mapping from OpenRouter or shorthand IDs to Together IDs
    MODEL_MAP = {
        "meta-llama/llama-3.1-405b-instruct": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        "meta-llama/llama-3.1-70b-instruct": DEFAULT_MODEL,
        "meta-llama/llama-3.1-8b-instruct": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "qwen/qwen2.5-72b-instruct": "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "qwen/qwen2.5-7b-instruct": "Qwen/Qwen2.5-7B-Instruct-Turbo",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Together.ai client.

        Args:
            api_key: Together.ai API key (defaults to TOGETHERAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("TOGETHERAI_API_KEY") or os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHERAI_API_KEY not set")
        logger.info("✅ Together.ai client initialized")

    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter or shorthand ID to Together native ID."""
        if model.startswith("together/"):
            model = model[len("together/"):]
        return self.MODEL_MAP.get(model, model)

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Generate completion using Together.ai.
        """
        native_model = self._get_native_model_id(model)

        payload = {
            "model": native_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return content

                if response.status_code == 429:
                    logger.warning("Together.ai rate limit (429)")
                    raise Exception("Together.ai rate limit - retry later")

                if response.status_code == 401:
                    logger.error("Together.ai 401: Invalid API key")
                    raise Exception("Invalid TOGETHERAI_API_KEY")

                logger.error(
                    "Together.ai API error %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                raise Exception(f"Together.ai API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Together.ai timeout for %s", native_model)
            raise Exception("Together.ai timeout")

    async def generate_with_retry(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_retries: int = 2,
        **kwargs,
    ) -> Optional[str]:
        """Generate with automatic retry on transient errors."""
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(prompt, model, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                if any(x in error_str for x in ["401", "invalid api key"]):
                    logger.warning("Together.ai non-retryable error: %s", e)
                    return None
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info("Together.ai retry %d/%d after %ds", attempt + 1, max_retries, wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Together.ai failed after %d retries", max_retries)
                    return None
        return None


_together_client: Optional[TogetherClient] = None


def get_together_client() -> Optional[TogetherClient]:
    """Get singleton Together.ai client instance."""
    global _together_client
    if _together_client is not None:
        return _together_client
    try:
        _together_client = TogetherClient()
        return _together_client
    except Exception as e:
        logger.warning("Together.ai client unavailable: %s", e)
        return None
