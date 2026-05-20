"""Moonshot Kimi direct API."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "kimi-models.json"

_kimi_client: Optional[CatalogClient] = None


def get_kimi_client() -> Optional[CatalogClient]:
    global _kimi_client
    if _kimi_client is not None:
        return _kimi_client
    _kimi_client = get_optional_catalog_client(
        name="Kimi",
        api_key_envs=("Kimi_K26_Api_Key", "KIMI_API_KEY", "MOONSHOT_API_KEY"),
        catalog_env="KIMI_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://api.moonshot.ai/v1",
    )
    return _kimi_client
