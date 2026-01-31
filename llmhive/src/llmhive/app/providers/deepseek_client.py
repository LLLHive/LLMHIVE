"""
DeepSeek Direct API Client
==========================

Direct integration with DeepSeek API for V3.2 models (Speciale & Thinking).

## Why Use DeepSeek Direct API?

**Performance Benefits:**
- 96.0% accuracy on AIME 2025 (beats GPT-5's 95.0%)
- 90.2% on HMMT 2025 (math competition)
- 2701 Codeforces rating (elite coding)
- 80.4% on τ² Bench (agentic capabilities)

**Cost Benefits:**
- $0.28/M tokens (cache miss) vs OpenAI's $1.75/M
- $0.14/M tokens for reasoning mode (vs $2.19/M output)
- Context caching reduces costs by 90% for similar prompts

**Best For:**
- ELITE tier math problems (where we need improvement)
- Complex reasoning tasks
- Agentic workflows
- Code generation and debugging

## Available Models

1. **deepseek-chat** (V3.2-Speciale)
   - General-purpose, fast
   - Best for: Quick reasoning, coding
   
2. **deepseek-reasoner** (V3.2-Thinking)
   - Extended reasoning with thinking mode
   - Best for: Hard math, complex logic

## Rate Limits (with credits)

- 30 RPM
- 5 concurrent requests
- $19.99 balance = ~70M tokens (at cache-miss rate)

## Setup

1. Get API key from: https://platform.deepseek.com
2. Set environment variable: `DEEPSEEK_API_KEY`
3. Client will auto-initialize when key is present

## Example Usage

```python
from llmhive.app.providers import get_deepseek_client

client = get_deepseek_client()
if client:
    # For math/reasoning tasks
    result = await client.generate(
        "Solve: ∫(x^2 + 2x + 1)dx",
        model="deepseek-reasoner",  # Uses thinking mode
        temperature=0.0
    )
```

Documentation: https://api-docs.deepseek.com/
"""

import os
import logging
import httpx
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Client for DeepSeek API (V3.2 models)."""
    
    BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"  # V3.2-Speciale
    
    # Model mappings (OpenRouter ID → DeepSeek native ID)
    MODEL_MAP = {
        "deepseek/deepseek-r1-0528:free": "deepseek-reasoner",
        "deepseek/deepseek-chat": "deepseek-chat",
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepSeek client.
        
        Args:
            api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not set - DeepSeek client unavailable")
        else:
            logger.info("✅ DeepSeek client initialized (V3.2 models)")
    
    def _get_native_model_id(self, model: str) -> str:
        """Convert OpenRouter or common ID to DeepSeek native ID."""
        return self.MODEL_MAP.get(model, model)
    
    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """
        Generate completion using DeepSeek API.
        
        Args:
            prompt: Input text
            model: Model ID (deepseek-chat or deepseek-reasoner)
            max_tokens: Max output tokens
            temperature: Sampling temperature (0-2)
            **kwargs: Additional API parameters
        
        Returns:
            Generated text
        
        Raises:
            Exception: On API errors (429, 401, etc.)
        """
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        
        native_model = self._get_native_model_id(model)
        
        # DeepSeek uses OpenAI-compatible API format
        payload = {
            "model": native_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Log token usage for cost tracking
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    
                    logger.info(
                        f"DeepSeek {native_model}: {prompt_tokens} in + "
                        f"{completion_tokens} out tokens"
                    )
                    
                    return content
                
                elif response.status_code == 429:
                    logger.warning(f"DeepSeek rate limit (429) for {native_model}")
                    raise Exception("DeepSeek rate limit - retry later")
                
                elif response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                    logger.error(f"DeepSeek 400 error: {error_msg}")
                    raise Exception(f"DeepSeek API error: {error_msg}")
                
                elif response.status_code == 401:
                    logger.error("DeepSeek 401: Invalid API key")
                    raise Exception("Invalid DEEPSEEK_API_KEY")
                
                else:
                    logger.error(
                        f"DeepSeek API error {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    raise Exception(f"DeepSeek API error: {response.status_code}")
        
        except httpx.TimeoutException:
            logger.error(f"DeepSeek timeout for {native_model}")
            raise Exception("DeepSeek API timeout")
        
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
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
            prompt: Input text
            model: Model ID
            max_retries: Number of retries for transient errors
            **kwargs: Additional parameters
        
        Returns:
            Generated text or None on failure
        """
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(prompt, model, **kwargs)
            
            except Exception as e:
                error_str = str(e)
                
                # Don't retry on rate limits, bad requests, or auth errors
                if any(x in error_str.lower() for x in ["rate limit", "400", "401"]):
                    logger.warning(f"DeepSeek non-retryable error: {e}")
                    return None
                
                # Retry transient errors
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(
                        f"DeepSeek retry {attempt + 1}/{max_retries} "
                        f"after {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"DeepSeek failed after {max_retries} retries")
                    return None
        
        return None


# Singleton pattern
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> Optional[DeepSeekClient]:
    """
    Get singleton DeepSeek client instance.
    
    Returns:
        DeepSeekClient if API key is set, None otherwise
    """
    global _deepseek_client
    
    if _deepseek_client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            _deepseek_client = DeepSeekClient(api_key)
        else:
            logger.info("DeepSeek client not initialized (no API key)")
            return None
    
    return _deepseek_client


def reset_deepseek_client():
    """Reset singleton (useful for testing)."""
    global _deepseek_client
    _deepseek_client = None
