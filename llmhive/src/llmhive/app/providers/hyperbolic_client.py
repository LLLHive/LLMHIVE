"""
Hyperbolic AI Serverless Client
===============================

OpenAI-compatible inference for spillover when OpenRouter :free throttles.

Env:
  HYPERBOLIC_API_KEY or HYPERBOLIC_KEY — API key from app.hyperbolic.ai
  HYPERBOLIC_MODELS — JSON catalog (see scripts/hyperbolic-models.json)
  HYPERBOLIC_BASE_URL — optional override (default https://api.hyperbolic.xyz/v1)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[5] / "scripts" / "hyperbolic-models.json"
)


def _load_catalog() -> Dict[str, Any]:
    raw = os.getenv("HYPERBOLIC_MODELS", "").strip()
    if raw:
        return json.loads(raw)
    if _DEFAULT_CATALOG_PATH.is_file():
        return json.loads(_DEFAULT_CATALOG_PATH.read_text())
    return {"chat": {}, "openrouter_map": {}, "default_chat": "llama_33_70b"}


def _hyperbolic_api_key() -> Optional[str]:
    return os.getenv("HYPERBOLIC_API_KEY") or os.getenv("HYPERBOLIC_KEY") or None


class HyperbolicClient:
    """Hyperbolic serverless chat client."""

    def __init__(self, api_key: Optional[str] = None, catalog: Optional[Dict[str, Any]] = None):
        self.api_key = api_key or _hyperbolic_api_key()
        if not self.api_key:
            raise ValueError(
                "HYPERBOLIC_API_KEY or HYPERBOLIC_KEY not set. "
                "Create key at https://app.hyperbolic.ai/settings/api-keys"
            )
        self.catalog = catalog if catalog is not None else _load_catalog()
        self.base_url = (
            os.getenv("HYPERBOLIC_BASE_URL")
            or self.catalog.get("base_url")
            or "https://api.hyperbolic.xyz/v1"
        ).rstrip("/")
        self.chat_models: Dict[str, str] = dict(self.catalog.get("chat") or {})
        self.openrouter_map: Dict[str, str] = dict(self.catalog.get("openrouter_map") or {})
        default_key = self.catalog.get("default_chat") or "llama_33_70b"
        self.default_model = self.chat_models.get(default_key, default_key)
        logger.info(
            "Hyperbolic client initialized (%d chat models, %d OR mappings)",
            len(self.chat_models),
            len(self.openrouter_map),
        )

    def resolve_model(self, model: str) -> str:
        if model in self.chat_models:
            return self.chat_models[model]
        logical = self.openrouter_map.get(model)
        if logical and logical in self.chat_models:
            return self.chat_models[logical]
        if "/" in model:
            return model
        return self.default_model

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        native_model = self.resolve_model(model or self.default_model)
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
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    choice = data["choices"][0]["message"]
                    content = (choice.get("content") or "").strip()
                    if not content and choice.get("reasoning_content"):
                        content = str(choice.get("reasoning_content", "")).strip()
                    return content
                if response.status_code == 429:
                    raise Exception("Hyperbolic rate limit - retry later")
                if response.status_code in (401, 403):
                    raise Exception("Invalid HYPERBOLIC_API_KEY / HYPERBOLIC_KEY")
                if response.status_code == 402:
                    raise Exception("Hyperbolic payment required - add credits")
                raise Exception(
                    f"Hyperbolic API error {response.status_code}: {response.text[:200]}"
                )
        except httpx.TimeoutException as exc:
            raise Exception("Hyperbolic timeout") from exc

    async def generate_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 2,
        **kwargs: Any,
    ) -> Optional[str]:
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(prompt, model, **kwargs)
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in ["401", "403", "invalid", "payment"]):
                    logger.warning("Hyperbolic non-retryable: %s", e)
                    return None
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error("Hyperbolic failed after %d retries: %s", max_retries, e)
                    return None
        return None


_hyperbolic_client: Optional[HyperbolicClient] = None


def get_hyperbolic_client() -> Optional[HyperbolicClient]:
    global _hyperbolic_client
    if _hyperbolic_client is not None:
        return _hyperbolic_client
    try:
        _hyperbolic_client = HyperbolicClient()
        return _hyperbolic_client
    except Exception as e:
        logger.warning("Hyperbolic client unavailable: %s", e)
        return None
