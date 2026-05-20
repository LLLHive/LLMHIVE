"""
Together.ai Direct API Client
=============================

Serverless chat on Together.ai (funded accounts use *-Turbo serverless IDs).

Legacy Meta-Llama-3.1-*-Turbo IDs return 400:
  "Unable to access non-serverless model" — use Llama-3.3-70B-Instruct-Turbo instead.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .catalog_client import CatalogClient, get_optional_catalog_client

logger = logging.getLogger(__name__)

_DEFAULT_CATALOG = Path(__file__).resolve().parents[5] / "scripts" / "together-models.json"

# Back-compat alias
TogetherClient = CatalogClient

_together_client: Optional[CatalogClient] = None


def get_together_client() -> Optional[CatalogClient]:
    global _together_client
    if _together_client is not None:
        return _together_client
    _together_client = get_optional_catalog_client(
        name="Together.ai",
        api_key_envs=("TOGETHERAI_API_KEY", "TOGETHER_API_KEY"),
        catalog_env="TOGETHER_MODELS",
        default_catalog_path=_DEFAULT_CATALOG,
        default_base_url="https://api.together.ai/v1",
    )
    return _together_client


def resolve_together_serverless(model: str) -> str:
    """Resolve OpenRouter slug to a serverless Together model id."""
    client = get_together_client()
    if not client:
        return "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    return client.resolve_model(model)
