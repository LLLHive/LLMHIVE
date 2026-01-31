"""
Groq Direct API Client
======================

Direct integration with Groq API for FREE, ultra-fast access to Llama models.

Benefits:
- 100% FREE tier (no credit card required)
- Ultra-low latency (LPU technology - 10x faster than GPU)
- Independent rate limits from OpenRouter
- Generous free tier limits
- Perfect for Llama 3.1 405B and Llama 3.3 70B

Setup:
1. Sign up at https://console.groq.com
2. Create API key in dashboard
3. Set GROQ_API_KEY environment variable

Rate Limits (Free Tier):
- Per-organization limits (check console.groq.com/settings/limits)
- Per-model limits
- "Generous free tier" per community reports

Last Updated: January 31, 2026
"""

import os
import logging
from typing import Optional
import httpx
import asyncio

logger = logging.getLogger(__name__)


class GroqClient:
    """
    Direct Groq API client for ultra-fast Llama inference.
    
    Uses Groq's LPU (Language Processing Unit) technology for
    10x faster inference than traditional GPU-based providers.
    """
    
    # Default model for FREE tier (best balance)
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    
    # Model mapping from OpenRouter IDs to Groq native IDs
    MODEL_MAP = {
        "meta-llama/llama-3.1-405b-instruct:free": "llama-3.1-405b-reasoning",
        "meta-llama/llama-3.3-70b-instruct:free": "llama-3.3-70b-versatile",
        "meta-llama/llama-3.2-3b-instruct:free": "llama-3.2-3b-preview",
        "llama-3.1-405b": "llama-3.1-405b-reasoning",
        "llama-3.3-70b": "llama-3.3-70b-versatile",
        "llama-3.2-3b": "llama-3.2-3b-preview",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key (or will use GROQ_API_KEY/GROK_API_KEY env var)
        """
        # Check both GROQ_API_KEY and GROK_API_KEY (common typo/confusion)
        self.api_key = (
            api_key 
            or os.getenv("GROQ_API_KEY") 
            or os.getenv("GROK_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY or GROK_API_KEY not set. "
                "Get your free key at: https://console.groq.com"
            )
        
        self.base_url = "https://api.groq.com/openai/v1"
        logger.info("✅ Groq client initialized (FREE tier, LPU-powered)")
    
    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter model ID to Groq native ID."""
        return self.MODEL_MAP.get(model, model)
    
    async def generate(
        self, 
        prompt: str, 
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2048,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate response from Groq-hosted Llama model.
        
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
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": native_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract text from OpenAI-format response
                    choices = data.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        text = message.get("content", "")
                        logger.debug(
                            "Groq LPU: %s returned %d chars (ultra-fast)", 
                            native_model, len(text)
                        )
                        return text
                    
                    logger.warning("Groq: Empty response from %s", native_model)
                    return ""
                
                elif response.status_code == 429:
                    # Rate limit hit
                    logger.warning(
                        "Groq: Rate limit hit for %s", 
                        native_model
                    )
                    raise Exception(f"Groq rate limit (429): {response.text[:200]}")
                
                elif response.status_code == 400:
                    # Bad request (possibly invalid model)
                    logger.error(
                        "Groq: Bad request for %s: %s", 
                        native_model, response.text[:200]
                    )
                    raise Exception(f"Groq bad request (400): {response.text[:200]}")
                
                elif response.status_code == 401:
                    # Invalid API key
                    logger.error("Groq: Invalid API key (401)")
                    raise Exception("Groq authentication failed (401) - check GROQ_API_KEY")
                
                else:
                    # Other error
                    logger.error(
                        "Groq: Error %d for %s: %s", 
                        response.status_code, native_model, response.text[:200]
                    )
                    raise Exception(
                        f"Groq error ({response.status_code}): {response.text[:200]}"
                    )
        
        except httpx.TimeoutException:
            logger.warning("Groq: Timeout for %s", native_model)
            raise Exception(f"Groq timeout for {native_model}")
        
        except Exception as e:
            logger.error("Groq: Failed for %s: %s", native_model, e)
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
                
                # Don't retry on rate limits, bad requests, or auth errors
                if any(code in error_str for code in ["429", "400", "401"]):
                    logger.warning(
                        "Groq: Non-retryable error (attempt %d/%d): %s",
                        attempt + 1, max_retries + 1, error_str
                    )
                    return None
                
                # Retry on timeouts and server errors
                if attempt < max_retries:
                    backoff = 2 ** attempt  # 1s, 2s, 4s
                    logger.info(
                        "Groq: Retrying in %ds (attempt %d/%d): %s",
                        backoff, attempt + 1, max_retries + 1, error_str
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Groq: All retries failed: %s", error_str
                    )
                    return None
        
        return None


# Singleton instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> Optional[GroqClient]:
    """
    Get singleton Groq client instance.
    
    Returns None if GROQ_API_KEY not set (graceful degradation).
    """
    global _groq_client
    
    if _groq_client is None:
        try:
            _groq_client = GroqClient()
        except ValueError as e:
            logger.warning("Groq client not available: %s", e)
            return None
    
    return _groq_client
