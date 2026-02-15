"""
HuggingFace Inference API Client
=================================

Direct integration with HuggingFace Serverless Inference for open model access.

Benefits:
- Access to thousands of open models
- Free tier with rate limits (~few hundred req/hour)
- OpenAI-compatible chat completions format
- Good fallback when OpenRouter/Together are down

Available Models (free):
- meta-llama/Llama-3.3-70B-Instruct
- Qwen/Qwen2.5-72B-Instruct
- mistralai/Mistral-Small-3.1-24B-Instruct-2503
- google/gemma-3-27b-it

Setup:
1. Get token from https://huggingface.co/settings/tokens
2. Set HF_TOKEN environment variable

Last Updated: February 15, 2026
"""

import os
import logging
import httpx
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class HuggingFaceClient:
    """Client for HuggingFace Serverless Inference API."""

    BASE_URL = "https://router.huggingface.co/hf-inference/v1"
    DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

    # Map OpenRouter model IDs to HuggingFace model IDs
    MODEL_MAP = {
        "meta-llama/llama-3.3-70b-instruct:free": "meta-llama/Llama-3.3-70B-Instruct",
        "meta-llama/llama-3.3-70b-instruct": "meta-llama/Llama-3.3-70B-Instruct",
        "meta-llama/llama-3.1-70b-instruct": "meta-llama/Llama-3.1-70B-Instruct",
        "meta-llama/llama-3.1-8b-instruct": "meta-llama/Llama-3.1-8B-Instruct",
        "meta-llama/llama-3.2-3b-instruct:free": "meta-llama/Llama-3.2-3B-Instruct",
        "qwen/qwen2.5-72b-instruct": "Qwen/Qwen2.5-72B-Instruct",
        "qwen/qwen3-coder:free": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "mistralai/mistral-small-3.1-24b-instruct:free": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        "google/gemma-3-27b-it:free": "google/gemma-3-27b-it",
        "google/gemma-3-12b-it:free": "google/gemma-3-12b-it",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if not self.api_key:
            raise ValueError("HF_TOKEN not set. Get token at https://huggingface.co/settings/tokens")
        logger.info("HuggingFace Inference client initialized")

    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter or shorthand ID to HuggingFace model ID."""
        return self.MODEL_MAP.get(model, model)

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        native_model = self._get_native_model_id(model)

        payload = {
            "model": native_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return content
                    raise Exception("HuggingFace returned empty choices")

                if response.status_code == 429:
                    logger.warning("HuggingFace rate limit (429)")
                    raise Exception("HuggingFace rate limit - retry later")

                if response.status_code in (401, 403):
                    logger.error("HuggingFace auth error %d", response.status_code)
                    raise Exception(f"Invalid HF_TOKEN ({response.status_code})")

                logger.error(
                    "HuggingFace API error %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                raise Exception(f"HuggingFace API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("HuggingFace timeout for %s", native_model)
            raise Exception("HuggingFace timeout")

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
                if any(x in error_str for x in ["401", "403", "invalid"]):
                    logger.warning("HuggingFace non-retryable error: %s", e)
                    return None
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info("HuggingFace retry %d/%d after %ds", attempt + 1, max_retries, wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("HuggingFace failed after %d retries", max_retries)
                    return None
        return None


_hf_client: Optional[HuggingFaceClient] = None


def get_hf_client() -> Optional[HuggingFaceClient]:
    """Get singleton HuggingFace client. Returns None if no token."""
    global _hf_client
    if _hf_client is not None:
        return _hf_client
    try:
        _hf_client = HuggingFaceClient()
        return _hf_client
    except Exception as e:
        logger.warning("HuggingFace client unavailable: %s", e)
        return None
