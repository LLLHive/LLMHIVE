"""
Cerebras Inference API Client
==============================

Ultra-fast inference via Cerebras Wafer-Scale Engine hardware.

Benefits:
- ~2000+ tokens/sec (fastest inference available)
- Free tier: 1M tokens/day, 30 RPM, 60K TPM
- OpenAI-compatible API format
- Ideal for: fast fallback, classification, extraction

Available Free Models:
- llama-3.3-70b: Llama 3.3 70B (best quality)
- llama3.1-8b: Llama 3.1 8B (ultra-fast)
- qwen-3-32b: Qwen 3 32B
- qwen-3-235b-a22b: Qwen 3 235B (MoE, high quality)

Rate Limits (Free Tier):
- 30 RPM per model
- 60K tokens per minute
- 1M tokens per day

Setup:
1. Get free API key from https://cloud.cerebras.ai
2. Set CEREBRAS_API_KEY environment variable

Last Updated: February 15, 2026
"""

import os
import logging
import httpx
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class CerebrasClient:
    """Client for Cerebras Inference API (ultra-fast wafer-scale inference)."""

    BASE_URL = "https://api.cerebras.ai/v1"
    DEFAULT_MODEL = "llama-3.3-70b"

    # Map OpenRouter model IDs to Cerebras native IDs
    MODEL_MAP = {
        "meta-llama/llama-3.3-70b-instruct:free": "llama-3.3-70b",
        "meta-llama/llama-3.3-70b-instruct": "llama-3.3-70b",
        "meta-llama/llama-3.1-8b-instruct:free": "llama3.1-8b",
        "meta-llama/llama-3.1-8b-instruct": "llama3.1-8b",
        "qwen/qwen3-next-80b-a3b-instruct:free": "qwen-3-32b",
        "qwen/qwen2.5-72b-instruct": "qwen-3-235b-a22b",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not set. Get free key at https://cloud.cerebras.ai")
        logger.info("Cerebras client initialized (wafer-scale ultra-fast inference)")

    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter or shorthand ID to Cerebras native ID."""
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
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                        usage = data.get("usage", {})
                        logger.debug(
                            "Cerebras %s: %d in + %d out tokens",
                            native_model,
                            usage.get("prompt_tokens", 0),
                            usage.get("completion_tokens", 0),
                        )
                        return content
                    raise Exception("Cerebras returned empty choices")

                if response.status_code == 429:
                    logger.warning("Cerebras rate limit (429)")
                    raise Exception("Cerebras rate limit - retry later")

                if response.status_code in (401, 403):
                    logger.error("Cerebras auth error %d", response.status_code)
                    raise Exception(f"Invalid CEREBRAS_API_KEY ({response.status_code})")

                logger.error(
                    "Cerebras API error %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                raise Exception(f"Cerebras API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Cerebras timeout for %s", native_model)
            raise Exception("Cerebras timeout")

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
                    logger.warning("Cerebras non-retryable error: %s", e)
                    return None
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info("Cerebras retry %d/%d after %ds", attempt + 1, max_retries, wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Cerebras failed after %d retries", max_retries)
                    return None
        return None


_cerebras_client: Optional[CerebrasClient] = None


def get_cerebras_client() -> Optional[CerebrasClient]:
    """Get singleton Cerebras client. Returns None if no API key."""
    global _cerebras_client
    if _cerebras_client is not None:
        return _cerebras_client
    try:
        _cerebras_client = CerebrasClient()
        return _cerebras_client
    except Exception as e:
        logger.warning("Cerebras client unavailable: %s", e)
        return None
