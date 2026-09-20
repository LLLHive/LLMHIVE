"""Z.ai (Zhipu) GLM direct API — OpenAI-compatible paas/v4."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "zai-models.json"

_zai_client: Optional[CatalogClient] = None


def get_zai_client() -> Optional[CatalogClient]:
    global _zai_client
    if _zai_client is not None:
        return _zai_client
    _zai_client = get_optional_catalog_client(
        name="Z.ai",
        api_key_envs=("ZAI_API_KEY", "ZHIPU_API_KEY", "GLM_API_KEY"),
        catalog_env="ZAI_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://api.z.ai/api/paas/v4",
    )
    return _zai_client
