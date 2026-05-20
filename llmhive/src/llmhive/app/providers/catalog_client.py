"""Shared OpenAI-compatible catalog client for spillover providers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class CatalogClient:
    """Thin HTTP client backed by a JSON model catalog (env or file)."""

    def __init__(
        self,
        *,
        name: str,
        api_key_envs: tuple[str, ...],
        catalog_env: str,
        default_catalog_path: Optional[Path] = None,
        default_base_url: str,
        timeout: float = 90.0,
    ):
        self.name = name
        self.api_key = self._first_key(api_key_envs)
        if not self.api_key:
            raise ValueError(f"{name}: no API key in {api_key_envs}")
        self.catalog = self._load_catalog(catalog_env, default_catalog_path)
        base_raw = (
            os.getenv(self.catalog.get("base_url_env", ""))
            if self.catalog.get("base_url_env")
            else None
        ) or os.getenv(catalog_env.replace("_MODELS", "_BASE_URL"), "").strip() or self.catalog.get(
            "base_url", default_base_url
        )
        if isinstance(base_raw, str) and base_raw.strip().startswith("{"):
            try:
                base_raw = json.loads(base_raw).get("base_url", default_base_url)
            except json.JSONDecodeError:
                base_raw = default_base_url
        self.base_url = str(base_raw).rstrip("/")
        self.chat_models: Dict[str, str] = dict(self.catalog.get("chat") or {})
        self.openrouter_map: Dict[str, str] = dict(self.catalog.get("openrouter_map") or {})
        default_key = self.catalog.get("default_chat") or next(iter(self.chat_models), "")
        self.default_model = self.chat_models.get(default_key, default_key)
        self.timeout = timeout

    @staticmethod
    def _first_key(envs: tuple[str, ...]) -> Optional[str]:
        for e in envs:
            v = os.getenv(e, "").strip()
            if v:
                return v
        return None

    @staticmethod
    def _load_catalog(catalog_env: str, path: Optional[Path]) -> Dict[str, Any]:
        raw = os.getenv(catalog_env, "").strip()
        if raw:
            return json.loads(raw)
        if path and path.is_file():
            return json.loads(path.read_text())
        return {"chat": {}, "openrouter_map": {}}

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
        extra_headers: Optional[Dict[str, str]] = None,
        url_suffix: str = "/chat/completions",
    ) -> str:
        native = self.resolve_model(model or self.default_model)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        payload = {
            "model": native,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}{url_suffix}", json=payload, headers=headers)
            if r.status_code == 200:
                data = r.json()
                choice = data["choices"][0]["message"]
                content = (choice.get("content") or "").strip()
                if not content and choice.get("reasoning_content"):
                    content = str(choice.get("reasoning_content", "")).strip()
                return content
            if r.status_code == 429:
                raise Exception(f"{self.name} rate limit")
            if r.status_code in (401, 403):
                raise Exception(f"{self.name} auth failed")
            if r.status_code == 402:
                raise Exception(f"{self.name} payment required")
            if r.status_code == 404:
                raise Exception(f"{self.name} model not found: {r.text[:200]}")
            raise Exception(f"{self.name} error {r.status_code}: {r.text[:200]}")

    async def generate_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 1,
        **kwargs: Any,
    ) -> Optional[str]:
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(prompt, model, **kwargs)
            except Exception as e:
                err = str(e).lower()
                if any(
                    x in err
                    for x in ("auth", "payment", "401", "403", "402", "model not found", "404")
                ):
                    return None
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
        return None


def catalog_client_from_env(
    *,
    name: str,
    api_key_envs: tuple[str, ...],
    catalog_env: str,
    default_catalog_path: Optional[Path] = None,
    default_base_url: str,
) -> CatalogClient:
    """Factory for spillover catalog clients (DeepInfra, DashScope, Kimi, etc.)."""
    return CatalogClient(
        name=name,
        api_key_envs=api_key_envs,
        catalog_env=catalog_env,
        default_catalog_path=default_catalog_path,
        default_base_url=default_base_url,
    )


def get_optional_catalog_client(
    *,
    name: str,
    api_key_envs: tuple[str, ...],
    catalog_env: str,
    default_catalog_path: Optional[Path] = None,
    default_base_url: str,
) -> Optional[CatalogClient]:
    try:
        return catalog_client_from_env(
            name=name,
            api_key_envs=api_key_envs,
            catalog_env=catalog_env,
            default_catalog_path=default_catalog_path,
            default_base_url=default_base_url,
        )
    except Exception as e:
        logger.warning("%s client unavailable: %s", name, e)
        return None
