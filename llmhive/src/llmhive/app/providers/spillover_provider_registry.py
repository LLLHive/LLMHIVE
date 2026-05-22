"""Register all ROUTING_V2 direct/spillover providers on Orchestrator.providers."""

from __future__ import annotations

import logging
from typing import Any, Dict, MutableMapping

from .direct_api_provider import build_provider

logger = logging.getLogger(__name__)

# (orchestrator.providers key, client getter, default OpenRouter slug, use CatalogClient)
_SPILLOVER_SPECS = (
    ("groq", "llmhive.app.providers.groq_client", "get_groq_client", "meta-llama/llama-3.3-70b-instruct:free", False),
    ("cerebras", "llmhive.app.providers.cerebras_client", "get_cerebras_client", "meta-llama/llama-3.3-70b-instruct:free", False),
    ("fireworks", "llmhive.app.providers.fireworks_client", "get_fireworks_client", "deepseek/deepseek-chat", True),
    ("hyperbolic", "llmhive.app.providers.hyperbolic_client", "get_hyperbolic_client", "meta-llama/llama-3.3-70b-instruct:free", True),
    ("dashscope", "llmhive.app.providers.dashscope_client", "get_dashscope_client", "qwen/qwen3-next-80b-a3b-instruct:free", True),
    ("deepinfra", "llmhive.app.providers.deepinfra_client", "get_deepinfra_client", "meta-llama/llama-3.3-70b-instruct:free", True),
    ("azure_foundry", "llmhive.app.providers.azure_foundry_client", "get_azure_foundry_client", "meta-llama/llama-3.3-70b-instruct:free", True),
    ("cloudflare", "llmhive.app.providers.cloudflare_client", "get_cloudflare_client", "meta-llama/llama-3.3-70b-instruct:free", True),
    ("kimi", "llmhive.app.providers.kimi_client", "get_kimi_client", "moonshotai/kimi-k2.6", True),
)


def _import_getter(module_path: str, func_name: str):
    import importlib

    mod = importlib.import_module(module_path)
    return getattr(mod, func_name)


def register_spillover_providers(providers: MutableMapping[str, Any]) -> list[str]:
    """Add direct API providers when env keys are present. Returns keys registered."""
    registered: list[str] = []
    for key, mod_path, getter_name, default_slug, is_catalog in _SPILLOVER_SPECS:
        if key in providers:
            registered.append(key)
            continue
        try:
            getter = _import_getter(mod_path, getter_name)
            provider = build_provider(key, getter, default_slug=default_slug, catalog=is_catalog)
            if provider:
                providers[key] = provider
                registered.append(key)
                logger.info("%s provider initialized (ROUTING_V2 direct)", key)
        except Exception as exc:
            logger.warning("Failed to initialize %s provider: %s", key, exc)
    return registered
