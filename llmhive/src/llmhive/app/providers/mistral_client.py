"""Mistral AI direct API — OpenAI-compatible chat completions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "mistral-models.json"

_mistral_client: Optional[CatalogClient] = None


def get_mistral_client() -> Optional[CatalogClient]:
    global _mistral_client
    if _mistral_client is not None:
        return _mistral_client
    _mistral_client = get_optional_catalog_client(
        name="Mistral",
        api_key_envs=("MISTRAL_API_KEY",),
        catalog_env="MISTRAL_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://api.mistral.ai/v1",
    )
    return _mistral_client
