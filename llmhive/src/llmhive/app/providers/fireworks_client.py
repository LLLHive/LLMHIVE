"""
Fireworks AI Serverless Client
==============================

OpenAI-compatible serverless inference for spillover when OpenRouter :free throttles.

Env:
  FIREWORKS_API_KEY or FIREWORKS_KEY — API key from app.fireworks.ai
  FIREWORKS_MODELS — JSON catalog (see scripts/fireworks-models.json)
  FIREWORKS_BASE_URL — optional override (default https://api.fireworks.ai/inference/v1)
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
    Path(__file__).resolve().parents[5] / "scripts" / "fireworks-models.json"
)


def _load_catalog() -> Dict[str, Any]:
    raw = os.getenv("FIREWORKS_MODELS", "").strip()
    if raw:
        return json.loads(raw)
    if _DEFAULT_CATALOG_PATH.is_file():
        return json.loads(_DEFAULT_CATALOG_PATH.read_text())
    return {"chat": {}, "openrouter_map": {}, "default_chat": "deepseek_v4_flash"}


def _fireworks_api_key() -> Optional[str]:
    return os.getenv("FIREWORKS_API_KEY") or os.getenv("FIREWORKS_KEY") or None


class FireworksClient:
    """Fireworks serverless chat client."""

    def __init__(self, api_key: Optional[str] = None, catalog: Optional[Dict[str, Any]] = None):
        self.api_key = api_key or _fireworks_api_key()
        if not self.api_key:
            raise ValueError(
                "FIREWORKS_API_KEY or FIREWORKS_KEY not set. "
                "Create key at https://app.fireworks.ai/settings/users/api-keys"
            )
        self.catalog = catalog if catalog is not None else _load_catalog()
        self.base_url = (
            os.getenv("FIREWORKS_BASE_URL")
            or self.catalog.get("base_url")
            or "https://api.fireworks.ai/inference/v1"
        ).rstrip("/")
        self.chat_models: Dict[str, str] = dict(self.catalog.get("chat") or {})
        self.utility_models: Dict[str, str] = dict(self.catalog.get("utility") or {})
        self.openrouter_map: Dict[str, str] = dict(self.catalog.get("openrouter_map") or {})
        default_key = self.catalog.get("default_chat") or "deepseek_v4_flash"
        self.default_model = self.chat_models.get(default_key, default_key)
        logger.info(
            "Fireworks client initialized (%d chat models, %d OR mappings)",
            len(self.chat_models),
            len(self.openrouter_map),
        )

    def resolve_model(self, model: str) -> str:
        """Map OpenRouter slug or logical key to Fireworks accounts/... model id."""
        if model in self.chat_models:
            return self.chat_models[model]
        if model in self.utility_models:
            return self.utility_models[model]
        logical = self.openrouter_map.get(model)
        if logical and logical in self.chat_models:
            return self.chat_models[logical]
        if model.startswith("accounts/fireworks/"):
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
            async with httpx.AsyncClient(timeout=90.0) as client:
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
                    raise Exception("Fireworks rate limit - retry later")
                if response.status_code == 401:
                    raise Exception("Invalid FIREWORKS_API_KEY / FIREWORKS_KEY")
                raise Exception(
                    f"Fireworks API error {response.status_code}: {response.text[:200]}"
                )
        except httpx.TimeoutException as exc:
            raise Exception("Fireworks timeout") from exc

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
                if any(x in err for x in ["401", "invalid"]):
                    logger.warning("Fireworks non-retryable: %s", e)
                    return None
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error("Fireworks failed after %d retries: %s", max_retries, e)
                    return None
        return None


_fireworks_client: Optional[FireworksClient] = None


def get_fireworks_client() -> Optional[FireworksClient]:
    global _fireworks_client
    if _fireworks_client is not None:
        return _fireworks_client
    try:
        _fireworks_client = FireworksClient()
        return _fireworks_client
    except Exception as e:
        logger.warning("Fireworks client unavailable: %s", e)
        return None
