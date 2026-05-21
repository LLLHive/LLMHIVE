"""
Provider chain selection for ROUTING_V2 (free-tier spillover).

Direct APIs are always tried before aggregators/gateways.
OpenRouter :free is the last resort when ROUTING_V2 is enabled.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Provider id strings (match Provider enum .value in provider_router)
P_GOOGLE = "google"
P_DEEPSEEK = "deepseek"
P_GROQ = "groq"
P_CEREBRAS = "cerebras"
P_GROK = "grok"
P_KIMI = "kimi"
P_MISTRAL = "mistral"
P_DASHSCOPE = "dashscope"
P_CLOUDFLARE = "cloudflare"
P_DEEPINFRA = "deepinfra"
P_FIREWORKS = "fireworks"
P_HYPERBOLIC = "hyperbolic"
P_AZURE_FOUNDRY = "azure_foundry"
P_TOGETHER = "together"
P_HUGGINGFACE = "huggingface"
P_OPENROUTER = "openrouter"

PROVIDER_COST_SCORE: Dict[str, float] = {
    P_GOOGLE: 0.0,
    P_DEEPSEEK: 0.1,
    P_GROQ: 0.2,
    P_CEREBRAS: 0.25,
    P_GROK: 0.5,
    P_MISTRAL: 0.45,
    P_KIMI: 0.55,
    P_DASHSCOPE: 0.6,
    P_CLOUDFLARE: 0.65,
    P_DEEPINFRA: 0.7,
    P_FIREWORKS: 0.75,
    P_HYPERBOLIC: 0.8,
    P_AZURE_FOUNDRY: 0.85,
    P_TOGETHER: 0.9,
    P_HUGGINGFACE: 0.95,
    P_OPENROUTER: 1.0,
}


def routing_v2_enabled() -> bool:
    return os.getenv("ROUTING_V2_ENABLED", "true").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def is_free_tier_slug(model_id: str) -> bool:
    if ":free" in model_id:
        return True
    try:
        from llmhive.app.orchestration.free_models_database import FREE_MODELS_DB

        return model_id in FREE_MODELS_DB
    except Exception:
        return False


def _env_present(*names: str) -> bool:
    return any(os.getenv(n, "").strip() for n in names)


def provider_available(provider: str) -> bool:
    checks = {
        P_GOOGLE: ("GOOGLE_AI_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_2"),
        P_DEEPSEEK: ("DEEPSEEK_API_KEY",),
        P_GROQ: ("GROQ_API_KEY",),
        P_CEREBRAS: ("CEREBRAS_API_KEY",),
        P_GROK: ("GROK_API_KEY",),
        P_KIMI: ("Kimi_K26_Api_Key", "KIMI_API_KEY", "MOONSHOT_API_KEY"),
        P_MISTRAL: ("MISTRAL_API_KEY",),
        P_DASHSCOPE: ("DASHSCOPE_API_KEY",),
        P_CLOUDFLARE: ("Cloudflare_Api_Key", "CLOUDFLARE_API_KEY"),
        P_DEEPINFRA: ("DeepInfra_Api_Key", "DEEPINFRA_API_KEY"),
        P_FIREWORKS: ("FIREWORKS_API_KEY", "FIREWORKS_KEY"),
        P_HYPERBOLIC: ("HYPERBOLIC_API_KEY", "HYPERBOLIC_KEY"),
        P_AZURE_FOUNDRY: ("AZURE_FOUNDRY_API_KEY",),
        P_TOGETHER: ("TOGETHERAI_API_KEY", "TOGETHER_API_KEY"),
        P_HUGGINGFACE: ("HF_TOKEN", "HUGGINGFACE_TOKEN"),
        P_OPENROUTER: ("OPENROUTER_API_KEY",),
    }
    return _env_present(*checks.get(provider, ()))


def _family_providers(model_id: str) -> List[str]:
    m = model_id.lower()
    if m.startswith("google/") or "gemini" in m or "gemma" in m:
        return [P_GOOGLE, P_HUGGINGFACE]
    if "deepseek" in m:
        return [P_DEEPSEEK]
    if "qwen" in m:
        return [P_DASHSCOPE, P_FIREWORKS, P_HYPERBOLIC, P_DEEPINFRA]
    if "llama" in m or "meta-llama" in m:
        return [P_GROQ, P_CEREBRAS, P_AZURE_FOUNDRY, P_HYPERBOLIC, P_FIREWORKS, P_DEEPINFRA]
    if "kimi" in m or "moonshot" in m:
        return [P_KIMI, P_AZURE_FOUNDRY, P_FIREWORKS, P_HYPERBOLIC]
    if "grok" in m or "x-ai" in m:
        return [P_GROK]
    if "mistral" in m:
        return [P_MISTRAL, P_AZURE_FOUNDRY, P_FIREWORKS, P_DEEPINFRA]
    return []


def get_explicit_routing() -> Dict[str, Tuple[str, Optional[str]]]:
    """Per-model direct routes from free_models_database + legacy PROVIDER_ROUTING."""
    routing: Dict[str, Tuple[str, Optional[str]]] = {}
    api_map = {
        "google": P_GOOGLE,
        "gemini": P_GOOGLE,
        "deepseek": P_DEEPSEEK,
        "groq": P_GROQ,
        "grok": P_GROK,
        "cerebras": P_CEREBRAS,
        "together": P_TOGETHER,
        "huggingface": P_HUGGINGFACE,
        "fireworks": P_FIREWORKS,
        "hyperbolic": P_HYPERBOLIC,
        "dashscope": P_DASHSCOPE,
        "deepinfra": P_DEEPINFRA,
        "azure_foundry": P_AZURE_FOUNDRY,
        "cloudflare": P_CLOUDFLARE,
        "kimi": P_KIMI,
        "mistral": P_MISTRAL,
        "openrouter": P_OPENROUTER,
    }
    try:
        from llmhive.app.orchestration.free_models_database import FREE_MODELS_DB

        for model_id, info in FREE_MODELS_DB.items():
            if info.preferred_api and info.preferred_api != "openrouter":
                p = api_map.get(info.preferred_api, info.preferred_api)
                routing[model_id] = (p, info.native_model_id)
    except Exception:
        pass
    try:
        from .provider_router import PROVIDER_ROUTING, Provider

        for model_id, (provider, native_id) in PROVIDER_ROUTING.items():
            routing.setdefault(model_id, (provider.value, native_id))
    except Exception:
        pass
    return routing


def build_provider_chain(
    model_id: str,
    explicit_routing: Optional[Dict[str, Tuple[str, Optional[str]]]] = None,
) -> List[Tuple[str, Optional[str]]]:
    """
    Ordered (provider, native_model_id) attempts.
    native_model_id None means client resolves from catalog / openrouter slug.
    """
    explicit_routing = explicit_routing or get_explicit_routing()
    if model_id in explicit_routing:
        p, native = explicit_routing[model_id]
        chain = [(p, native)]
    else:
        chain = []

    # Family-specific direct + spillover (dedupe)
    seen = {p for p, _ in chain}
    for p in _family_providers(model_id):
        if p not in seen and provider_available(p):
            chain.append((p, None))
            seen.add(p)

    # Cheap general spillover pool for :free
    if is_free_tier_slug(model_id):
        spill = [
            P_GROQ,
            P_CEREBRAS,
            P_CLOUDFLARE,
            P_DEEPINFRA,
            P_FIREWORKS,
            P_HYPERBOLIC,
            P_AZURE_FOUNDRY,
            P_TOGETHER,
            P_HUGGINGFACE,
        ]
        spill.sort(key=lambda x: PROVIDER_COST_SCORE.get(x, 1.0))
        for p in spill:
            if p not in seen and provider_available(p):
                chain.append((p, None))
                seen.add(p)

    # Paid / elite paths: Together + OpenRouter as primary routers (funded accounts)
    if not is_free_tier_slug(model_id):
        paid_primary: List[Tuple[str, Optional[str]]] = []
        if provider_available(P_TOGETHER):
            paid_primary.append((P_TOGETHER, None))
        if provider_available(P_OPENROUTER):
            paid_primary.append((P_OPENROUTER, None))
        # Prepend without duplicating providers already in chain
        for item in reversed(paid_primary):
            if item[0] not in seen:
                chain.insert(0, item)
                seen.add(item[0])

    if provider_available(P_OPENROUTER):
        if routing_v2_enabled() and is_free_tier_slug(model_id):
            if P_OPENROUTER not in seen:
                chain.append((P_OPENROUTER, None))
                seen.add(P_OPENROUTER)
        elif not routing_v2_enabled() and P_OPENROUTER not in seen:
            chain.insert(0, (P_OPENROUTER, None))

    return chain


def primary_provider_name(model_id: str) -> str:
    """Map to orchestrator.providers dict keys."""
    chain = build_provider_chain(model_id)
    if chain:
        return _provider_to_orchestrator_key(chain[0][0])
    return "openrouter"


def _provider_to_orchestrator_key(provider: str) -> str:
    mapping = {
        P_GOOGLE: "gemini",
        P_DEEPSEEK: "deepseek",
        P_GROQ: "groq",
        P_GROK: "grok",
        P_CEREBRAS: "cerebras",
        P_TOGETHER: "together",
        P_HUGGINGFACE: "huggingface",
        P_OPENROUTER: "openrouter",
        P_FIREWORKS: "fireworks",
        P_HYPERBOLIC: "hyperbolic",
        P_DASHSCOPE: "dashscope",
        P_DEEPINFRA: "deepinfra",
        P_AZURE_FOUNDRY: "azure_foundry",
        P_CLOUDFLARE: "cloudflare",
        P_KIMI: "kimi",
        P_MISTRAL: "mistral",
    }
    return mapping.get(provider, provider)
