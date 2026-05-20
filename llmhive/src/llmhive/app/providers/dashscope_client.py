"""Alibaba DashScope (Qwen) direct API — OpenAI-compatible mode."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "dashscope-models.json"

_dashscope_client: Optional[CatalogClient] = None


def get_dashscope_client() -> Optional[CatalogClient]:
    global _dashscope_client
    if _dashscope_client is not None:
        return _dashscope_client
    _dashscope_client = get_optional_catalog_client(
        name="DashScope",
        api_key_envs=("DASHSCOPE_API_KEY",),
        catalog_env="DASHSCOPE_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    return _dashscope_client
