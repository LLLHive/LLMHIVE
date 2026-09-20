"""NVIDIA NIM / integrate.api.nvidia.com — Nemotron direct API."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "nvidia-models.json"

_nvidia_client: Optional[CatalogClient] = None


def get_nvidia_client() -> Optional[CatalogClient]:
    global _nvidia_client
    if _nvidia_client is not None:
        return _nvidia_client
    _nvidia_client = get_optional_catalog_client(
        name="NVIDIA",
        api_key_envs=("NVIDIA_API_KEY", "NGC_API_KEY", "NIM_API_KEY"),
        catalog_env="NVIDIA_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://integrate.api.nvidia.com/v1",
    )
    return _nvidia_client
