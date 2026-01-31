"""
Google AI (Gemini) Direct API Client
====================================

Direct integration with Google AI Studio API for FREE access to Gemini models.

Benefits:
- 100% FREE (no credit card required)
- Independent rate limits from OpenRouter
- 15 RPM for Gemini 2.0 Flash
- Ultra-fast inference
- 1M token context window

Setup:
1. Get API key from https://aistudio.google.com
2. Set GOOGLE_AI_API_KEY environment variable

Rate Limits (Free Tier):
- Gemini 2.0 Flash: 15 RPM, 200 RPD, 1M TPM
- Gemini 2.5 Flash: 10 RPM, 250 RPD, 250K TPM
- Gemini 2.5 Flash-Lite: 15 RPM, 1,000 RPD, 250K TPM
- Gemini 2.5 Pro: 5 RPM, 100 RPD, 125K TPM

Last Updated: January 31, 2026
"""

import os
import logging
from typing import Optional
import httpx
import asyncio

logger = logging.getLogger(__name__)


class GoogleAIClient:
    """
    Direct Google AI (Gemini) API client.
    
    Uses Google AI Studio API for FREE access to Gemini models.
    No credit card required, just Gmail account.
    """
    
    # Default model for FREE tier (fastest, best limits)
    DEFAULT_MODEL = "gemini-2.0-flash-exp"
    
    # Model mapping from OpenRouter IDs to Google AI IDs
    MODEL_MAP = {
        "google/gemini-2.0-flash-exp:free": "gemini-2.0-flash-exp",
        "gemini-2.0-flash": "gemini-2.0-flash-exp",
        "gemini-2.5-flash": "gemini-2.5-flash-latest",
        "gemini-2.5-pro": "gemini-2.5-pro-latest",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google AI client.
        
        Args:
            api_key: Google AI API key (or will use GOOGLE_AI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY not set. "
                "Get your free key at: https://aistudio.google.com"
            )
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        logger.info("✅ Google AI client initialized (FREE tier)")
    
    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter model ID to Google AI native ID."""
        return self.MODEL_MAP.get(model, model)
    
    async def generate(
        self, 
        prompt: str, 
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2048,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate response from Gemini model.
        
        Args:
            prompt: User prompt/query
            model: Model ID (OpenRouter or native format)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature (0-2)
        
        Returns:
            Generated text response
        
        Raises:
            Exception: If API call fails
        """
        native_model = self._get_native_model_id(model)
        
        url = f"{self.base_url}/models/{native_model}:generateContent"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract text from response
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            logger.debug(
                                "Google AI: %s returned %d chars", 
                                native_model, len(text)
                            )
                            return text
                    
                    logger.warning("Google AI: Empty response from %s", native_model)
                    return ""
                
                elif response.status_code == 429:
                    # Rate limit hit
                    logger.warning(
                        "Google AI: Rate limit hit for %s (15 RPM limit)", 
                        native_model
                    )
                    raise Exception(f"Google AI rate limit (429): {response.text[:200]}")
                
                elif response.status_code == 400:
                    # Bad request (possibly invalid model)
                    logger.error(
                        "Google AI: Bad request for %s: %s", 
                        native_model, response.text[:200]
                    )
                    raise Exception(f"Google AI bad request (400): {response.text[:200]}")
                
                else:
                    # Other error
                    logger.error(
                        "Google AI: Error %d for %s: %s", 
                        response.status_code, native_model, response.text[:200]
                    )
                    raise Exception(
                        f"Google AI error ({response.status_code}): {response.text[:200]}"
                    )
        
        except httpx.TimeoutException:
            logger.warning("Google AI: Timeout for %s", native_model)
            raise Exception(f"Google AI timeout for {native_model}")
        
        except Exception as e:
            logger.error("Google AI: Failed for %s: %s", native_model, e)
            raise
    
    async def generate_with_retry(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
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
