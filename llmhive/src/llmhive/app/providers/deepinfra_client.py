"""DeepInfra direct API — OpenAI-compatible inference."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "deepinfra-models.json"

_deepinfra_client: Optional[CatalogClient] = None


def get_deepinfra_client() -> Optional[CatalogClient]:
    global _deepinfra_client
    if _deepinfra_client is not None:
        return _deepinfra_client
    _deepinfra_client = get_optional_catalog_client(
        name="DeepInfra",
        api_key_envs=("DeepInfra_Api_Key", "DEEPINFRA_API_KEY"),
        catalog_env="DEEPINFRA_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://api.deepinfra.com/v1/openai",
    )
    return _deepinfra_client
