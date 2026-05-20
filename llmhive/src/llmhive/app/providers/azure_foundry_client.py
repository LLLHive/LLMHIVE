"""Microsoft Azure AI Foundry — deployment-scoped OpenAI-compatible chat."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "azure-foundry-models.json"
_DEFAULT_DEPLOYMENTS = Path(__file__).resolve().parents[5] / "scripts" / "foundry-deployments.json"


def _load_json_env_or_file(env_name: str, path: Path) -> Dict[str, Any]:
    raw = os.getenv(env_name, "").strip()
    if raw:
        return json.loads(raw)
    if path.is_file():
        return json.loads(path.read_text())
    return {}


class AzureFoundryClient:
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key or os.getenv("AZURE_FOUNDRY_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("AZURE_FOUNDRY_API_KEY not set")
        self.endpoint = (
            endpoint
            or os.getenv("AZURE_FOUNDRY_ENDPOINT", "https://llnhive.services.ai.azure.com")
        ).rstrip("/")
        self.catalog = _load_json_env_or_file("AZURE_FOUNDRY_MODELS", _DEFAULT_CATALOG)
        deployments = _load_json_env_or_file("AZURE_FOUNDRY_DEPLOYMENTS", _DEFAULT_DEPLOYMENTS)
        self.chat_models: Dict[str, str] = dict(self.catalog.get("chat") or deployments)
        self.openrouter_map: Dict[str, str] = dict(self.catalog.get("openrouter_map") or {})
        default_key = self.catalog.get("default_chat") or "deepseek_flash"
        self.default_deployment = self.chat_models.get(default_key, default_key)
        self.api_version = self.catalog.get("api_version", "2024-06-01")
        logger.info("Azure Foundry client initialized (%d deployments)", len(self.chat_models))

    def resolve_deployment(self, model: str) -> str:
        if model in self.chat_models:
            return self.chat_models[model]
        logical = self.openrouter_map.get(model)
        if logical and logical in self.chat_models:
            return self.chat_models[logical]
        return self.default_deployment

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        deployment = self.resolve_deployment(model or self.default_deployment)
        url = (
            f"{self.endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                data = r.json()
                choice = data["choices"][0]["message"]
                content = (choice.get("content") or "").strip()
                if not content and choice.get("reasoning_content"):
                    content = str(choice.get("reasoning_content", "")).strip()
                return content
            if r.status_code == 429:
                raise Exception("Azure Foundry rate limit")
            if r.status_code in (401, 403):
                raise Exception("Azure Foundry auth failed")
            raise Exception(f"Azure Foundry error {r.status_code}: {r.text[:200]}")

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


_azure_foundry_client: Optional[AzureFoundryClient] = None


def get_azure_foundry_client() -> Optional[AzureFoundryClient]:
    global _azure_foundry_client
    if _azure_foundry_client is not None:
        return _azure_foundry_client
    try:
        _azure_foundry_client = AzureFoundryClient()
        return _azure_foundry_client
    except Exception as e:
        logger.warning("Azure Foundry client unavailable: %s", e)
        return None
