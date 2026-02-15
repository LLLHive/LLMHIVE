"""
Groq Direct API Client
======================

Ultra-fast inference via Groq's LPU (Language Processing Unit) hardware.

Benefits:
- ~200ms latency (10-50x faster than GPU inference)
- 30 RPM FREE (no credit card required)
- OpenAI-compatible API format
- Ideal for: quick classification, answer extraction, MCQ, retries

Available Free Models:
- llama-3.3-70b-versatile: 30 RPM, 12K TPM, 100K TPD
- meta-llama/llama-4-maverick-17b-128e-instruct: 30 RPM, 6K TPM
- llama-3.1-8b-instant: 30 RPM, 6K TPM, 500K TPD

Rate Limits (Free Tier):
- 30 RPM per model
- Tokens per minute varies by model (6K-12K)
- Cached tokens don't count toward limits

Setup:
1. Get free API key from https://console.groq.com
2. Set GROQ_API_KEY environment variable (starts with gsk_)

Last Updated: February 14, 2026
"""

import os
import logging
import httpx
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class GroqClient:
    """Client for Groq API (ultra-fast LPU inference)."""

    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    # Model mappings (OpenRouter ID → Groq native ID)
    MODEL_MAP = {
        "meta-llama/llama-3.3-70b-instruct:free": "llama-3.3-70b-versatile",
        "meta-llama/llama-3.1-8b-instruct:free": "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant": "llama-3.1-8b-instant",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set. Get free key at https://console.groq.com")
        logger.info("✅ Groq client initialized (LPU ultra-fast inference)")

    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter or common ID to Groq native ID."""
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
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    logger.debug(
                        "Groq %s: %d in + %d out tokens (%.0fms)",
                        native_model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                        usage.get("total_time", 0) * 1000,
                    )
                    return content

                if response.status_code == 429:
                    logger.warning("Groq rate limit (429) for %s", native_model)
                    raise Exception("Groq rate limit - retry later")

                if response.status_code == 401:
                    logger.error("Groq 401: Invalid API key")
                    raise Exception("Invalid GROQ_API_KEY")

                logger.error("Groq API error %d: %s", response.status_code, response.text[:200])
                raise Exception(f"Groq API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Groq timeout for %s", native_model)
            raise Exception("Groq timeout")

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
                if any(x in error_str for x in ["401", "invalid"]):
                    logger.warning("Groq non-retryable error: %s", e)
                    return None
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info("Groq retry %d/%d after %ds", attempt + 1, max_retries, wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Groq failed after %d retries", max_retries)
                    return None
        return None


_groq_client: Optional[GroqClient] = None


def get_groq_client() -> Optional[GroqClient]:
    """Get singleton Groq client. Returns None if no API key."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    try:
        _groq_client = GroqClient()
        return _groq_client
    except Exception as e:
        logger.warning("Groq client unavailable: %s", e)
        return None
