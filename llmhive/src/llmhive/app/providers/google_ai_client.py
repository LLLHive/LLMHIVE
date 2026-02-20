"""
Google AI (Gemini) Direct API Client
====================================

Direct integration with Google AI Studio API for FREE access to Gemini models.
Model selection is handled dynamically via ``google_model_discovery`` — no
hardcoded model IDs.

Setup:
1. Get API key from https://aistudio.google.com
2. Set GOOGLE_AI_API_KEY environment variable
"""

import os
import logging
from typing import Optional
import httpx
import asyncio

from llmhive.app.providers.google_model_discovery import (
    get_google_model_cached,
    select_best_google_model,
    select_with_fallback,
    invalidate_cache,
)

logger = logging.getLogger(__name__)


class GoogleAIClient:
    """
    Direct Google AI (Gemini) API client.
    
    Uses Google AI Studio API for FREE access to Gemini models.
    Model IDs are discovered dynamically at runtime.
    """
    
    _resolved_default: Optional[str] = None
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key 
            or os.getenv("GOOGLE_AI_API_KEY") 
            or os.getenv("GEMINI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY or GEMINI_API_KEY not set. "
                "Get your free key at: https://aistudio.google.com"
            )
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        logger.info("Google AI client initialized")
    
    async def _resolve_model(self, model: Optional[str] = None) -> str:
        """Resolve a model ID through auto-discovery.
        
        If *model* is an OpenRouter-style ID (``google/...``) or an alias,
        strip it to the bare Gemini name.  Then validate it exists in the
        discovered list.  Falls back to the best available model.
        """
        bare = model or ""
        bare = bare.split(":")[0]               # remove :free suffix
        if bare.startswith("google/"):
            bare = bare[len("google/"):]

        if bare:
            models = await get_google_model_cached(self.api_key)
            known_ids = {m.model_id for m in models}
            if bare in known_ids:
                return bare

        try:
            models = await get_google_model_cached(self.api_key)
            selected = select_best_google_model(models, workload="speed")
            GoogleAIClient._resolved_default = selected
            return selected
        except ValueError:
            fallback = GoogleAIClient._resolved_default or "gemini-2.5-flash"
            logger.warning("google_ai_client: discovery failed, using fallback %s", fallback)
            return fallback
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0,
    ) -> str:
        """Generate a response from a Gemini model.

        *model* can be an OpenRouter-style ID, a bare Gemini name, or
        ``None`` (auto-selects the best available).  On a 404 the client
        automatically re-discovers models and retries once.
        """
        native_model = await self._resolve_model(model)
        logger.info("Google AI: using model %s", native_model)

        return await self._call(prompt, native_model, max_tokens, temperature)

    async def _call(
        self,
        prompt: str,
        native_model: str,
        max_tokens: int,
        temperature: float,
        _retried: bool = False,
    ) -> str:
        url = f"{self.base_url}/models/{native_model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            logger.debug("Google AI: %s returned %d chars", native_model, len(text))
                            return text
                    logger.warning("Google AI: Empty response from %s", native_model)
                    return ""

                if response.status_code == 404 and not _retried:
                    logger.warning("Google AI: 404 for %s — re-discovering models", native_model)
                    new_model = await select_with_fallback(
                        api_key=self.api_key, workload="speed", failed_model=native_model,
                    )
                    logger.info("Google AI: switching to %s", new_model)
                    return await self._call(prompt, new_model, max_tokens, temperature, _retried=True)

                if response.status_code == 429:
                    raise Exception(f"Google AI rate limit (429): {response.text[:200]}")
                if response.status_code == 400:
                    raise Exception(f"Google AI bad request (400): {response.text[:200]}")

                raise Exception(f"Google AI error ({response.status_code}): {response.text[:200]}")

        except httpx.TimeoutException:
            raise Exception(f"Google AI timeout for {native_model}")
        except Exception:
            raise
    
    async def generate_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 2,
        **kwargs
    ) -> Optional[str]:
        """
        Generate with automatic retry on transient errors.
        
        Args:
            prompt: User prompt
            model: Model ID
            max_retries: Max retry attempts
            **kwargs: Additional args for generate()
        
        Returns:
            Generated text or None if all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(prompt, model, **kwargs)
            
            except Exception as e:
                error_str = str(e)
                
                # Don't retry on rate limits or bad requests
                if "429" in error_str or "400" in error_str:
                    logger.warning(
                        "Google AI: Non-retryable error (attempt %d/%d): %s",
                        attempt + 1, max_retries + 1, error_str
                    )
                    return None
                
                # Retry on timeouts and server errors
                if attempt < max_retries:
                    backoff = 2 ** attempt  # 1s, 2s, 4s
                    logger.info(
                        "Google AI: Retrying in %ds (attempt %d/%d): %s",
                        backoff, attempt + 1, max_retries + 1, error_str
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Google AI: All retries failed: %s", error_str
                    )
                    return None
        
        return None


# Singleton instance
_google_client: Optional[GoogleAIClient] = None


def get_google_client() -> Optional[GoogleAIClient]:
    """
    Get singleton Google AI client instance.
    
    Returns None if GOOGLE_AI_API_KEY not set (graceful degradation).
    """
    global _google_client
    
    if _google_client is None:
        try:
            _google_client = GoogleAIClient()
        except ValueError as e:
            logger.warning("Google AI client not available: %s", e)
            return None
    
    return _google_client
