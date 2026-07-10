"""Cloudflare Workers AI — account-scoped OpenAI-compatible chat."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "cloudflare-models.json"


def _load_catalog() -> Dict[str, Any]:
    raw = os.getenv("CLOUDFLARE_MODELS", "").strip()
    if raw:
        return json.loads(raw)
    if _DEFAULT_CATALOG.is_file():
        return json.loads(_DEFAULT_CATALOG.read_text())
    return {"chat": {}, "openrouter_map": {}, "default_chat": "llama_33_70b"}


def _account_id() -> Optional[str]:
    return (
        os.getenv("CLOUDFLARE_ACCOUNT_ID")
        or os.getenv("Cloudflare_Account_ID")
        or os.getenv("Cloudflare_Account_Id")
    )


def _api_key() -> Optional[str]:
    return os.getenv("CLOUDFLARE_API_KEY") or os.getenv("Cloudflare_Api_Key")


class CloudflareClient:
    def __init__(self, api_key: Optional[str] = None, account_id: Optional[str] = None):
        self.api_key = api_key or _api_key()
        self.account_id = account_id or _account_id()
        if not self.api_key:
            raise ValueError("CLOUDFLARE_API_KEY or Cloudflare_Api_Key not set")
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID or Cloudflare_Account_ID not set")
        self.catalog = _load_catalog()
        self.chat_models: Dict[str, str] = dict(self.catalog.get("chat") or {})
        self.openrouter_map: Dict[str, str] = dict(self.catalog.get("openrouter_map") or {})
        default_key = self.catalog.get("default_chat") or "llama_33_70b"
        self.default_model = self.chat_models.get(default_key, default_key)
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/v1"
        )
        logger.info("Cloudflare Workers AI client initialized")

    def resolve_model(self, model: str) -> str:
        if model in self.chat_models:
            return self.chat_models[model]
        logical = self.openrouter_map.get(model)
        if logical and logical in self.chat_models:
            return self.chat_models[logical]
        return self.default_model

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        native = self.resolve_model(model or self.default_model)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": native,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            if r.status_code == 200:
                data = r.json()
                choice = data["choices"][0]["message"]
                return (choice.get("content") or "").strip()
            if r.status_code == 429:
                raise Exception("Cloudflare rate limit")
            if r.status_code in (401, 403):
                raise Exception("Cloudflare auth failed")
            raise Exception(f"Cloudflare error {r.status_code}: {r.text[:200]}")

    async def generate_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 1,
    ) -> Optional[str]:
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(prompt, model)
            except Exception as e:
                err = str(e).lower()
                if "auth" in err:
                    return None
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
        return None


_cloudflare_client: Optional[CloudflareClient] = None


def get_cloudflare_client() -> Optional[CloudflareClient]:
    global _cloudflare_client
    if _cloudflare_client is not None:
        return _cloudflare_client
    try:
        _cloudflare_client = CloudflareClient()
        return _cloudflare_client
    except Exception as e:
        logger.warning("Cloudflare client unavailable: %s", e)
        return None
