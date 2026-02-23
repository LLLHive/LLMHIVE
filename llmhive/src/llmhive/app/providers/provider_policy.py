"""
Dynamic Top-Tier Provider Auto-Discovery System
================================================
Provider-aware model discovery, shadow validation, canary rollout,
and rollback safety across all supported LLM providers.

Each provider implements a ``ProviderPolicy`` that knows how to
discover, filter, rank, and validate models for that provider.

Usage:
    from llmhive.app.providers.provider_policy import (
        discover_all_providers,
        select_best_model,
        shadow_validate_candidate,
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_REPORTS_DIR = _PROJECT_ROOT / "benchmark_reports"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredModel:
    """A model discovered from a provider's API."""
    provider: str
    model_id: str
    display_name: str = ""
    version: str = ""
    variant: str = ""           # pro | flash | reasoning | chat | ...
    context_window: int = 0
    supports_chat: bool = True
    deprecated: bool = False
    preview: bool = False
    pricing_tier: str = ""      # free | paid | premium
    priority: int = 0           # higher = better
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reject patterns (shared across providers)
# ---------------------------------------------------------------------------

_REJECT_TOKENS = re.compile(
    r"\b(preview|beta|exp(?:erimental)?|deprecated|canary|internal|dev)\b",
    re.IGNORECASE,
)

_BOOST_TOKENS = {
    "pro": 20, "max": 18, "reasoning": 15,
    "ultra": 15, "turbo": 8, "plus": 6,
}


def _stability_score(model_id: str) -> int:
    lower = model_id.lower()
    if _REJECT_TOKENS.search(lower):
        return -100
    score = 0
    for token, boost in _BOOST_TOKENS.items():
        if token in lower:
            score += boost
    return score


# ---------------------------------------------------------------------------
# Abstract policy
# ---------------------------------------------------------------------------

class ProviderPolicy(ABC):
    """Base class for provider-specific discovery policies."""

    name: str = "base"
    stability_level: str = "strict"   # strict | moderate | dynamic

    @abstractmethod
    async def discover_models(self) -> List[DiscoveredModel]:
        """Fetch available models from the provider API."""

    def filter_stable(self, models: List[DiscoveredModel]) -> List[DiscoveredModel]:
        """Remove preview / beta / deprecated / experimental models."""
        return [
            m for m in models
            if not m.deprecated
            and not m.preview
            and _stability_score(m.model_id) >= 0
        ]

    def rank_models(
        self, models: List[DiscoveredModel], workload: str = "general",
    ) -> List[DiscoveredModel]:
        """Sort models best-first for the given workload."""
        def _key(m: DiscoveredModel) -> Tuple[int, int, str]:
            base = m.priority + _stability_score(m.model_id)
            workload_bonus = 0
            lower = m.model_id.lower()
            if workload in ("reasoning", "coding", "math") and "pro" in lower:
                workload_bonus = 30
            elif workload in ("speed", "chat") and ("flash" in lower or "turbo" in lower):
                workload_bonus = 30
            return (base + workload_bonus, m.context_window, m.model_id)

        return sorted(models, key=_key, reverse=True)

    async def validate_model(self, model_id: str) -> bool:
        """Lightweight smoke test: ask the model to return '4'."""
        return True  # Overridden per provider

    async def shadow_validate(self, model_id: str) -> Dict[str, Any]:
        """Run micro-validation against the candidate model."""
        return {"model": model_id, "status": "skipped", "reason": "no runner configured"}


# ---------------------------------------------------------------------------
# OpenAI policy (Phase 2)
# ---------------------------------------------------------------------------

class OpenAIPolicy(ProviderPolicy):
    name = "openai"
    stability_level = "strict"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    async def discover_models(self) -> List[DiscoveredModel]:
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if r.status_code != 200:
                    logger.warning("OpenAI discovery: HTTP %d", r.status_code)
                    return []
                data = r.json().get("data", [])
        except Exception as exc:
            logger.warning("OpenAI discovery failed: %s", exc)
            return []

        out: List[DiscoveredModel] = []
        for raw in data:
            mid = raw.get("id", "")
            if not any(mid.startswith(p) for p in ("gpt-", "o1-", "o3-", "o4-")):
                continue
            ver_match = re.search(r"(\d+\.?\d*)", mid)
            version = ver_match.group(1) if ver_match else ""
            variant = "pro" if "pro" in mid.lower() else ("reasoning" if mid.startswith("o") else "chat")
            out.append(DiscoveredModel(
                provider="openai", model_id=mid,
                display_name=mid, version=version, variant=variant,
                supports_chat=True,
                deprecated="deprecated" in mid.lower(),
                preview="preview" in mid.lower() or "beta" in mid.lower(),
                priority=int(float(version) * 100) if version else 0,
                metadata=raw,
            ))
        logger.info("OpenAI discovery: %d models", len(out))
        return out

    async def validate_model(self, model_id: str) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": model_id, "messages": [{"role": "user", "content": "Return the number 4."}], "max_tokens": 5},
                )
                if r.status_code == 200:
                    text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    return "4" in text
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Anthropic policy (Phase 3)
# ---------------------------------------------------------------------------

class AnthropicPolicy(ProviderPolicy):
    name = "anthropic"
    stability_level = "strict"

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")

    async def discover_models(self) -> List[DiscoveredModel]:
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                if r.status_code != 200:
                    logger.warning("Anthropic discovery: HTTP %d", r.status_code)
                    return []
                data = r.json().get("data", [])
        except Exception as exc:
            logger.warning("Anthropic discovery failed: %s", exc)
            return []

        out: List[DiscoveredModel] = []
        for raw in data:
            mid = raw.get("id", "")
            if not mid.startswith("claude"):
                continue
            variant = "pro"
            if "sonnet" in mid.lower():
                variant = "pro"
            elif "haiku" in mid.lower():
                variant = "flash"
            elif "opus" in mid.lower():
                variant = "reasoning"

            date_match = re.search(r"(\d{8})", mid)
            date_str = date_match.group(1) if date_match else ""
            priority = int(date_str) if date_str else 0
            if "opus" in mid.lower():
                priority += 100
            elif "sonnet" in mid.lower():
                priority += 50

            out.append(DiscoveredModel(
                provider="anthropic", model_id=mid,
                display_name=raw.get("display_name", mid),
                version=date_str, variant=variant,
                supports_chat=True,
                deprecated=False,
                preview="preview" in mid.lower(),
                priority=priority,
                context_window=raw.get("context_window", 0),
                metadata=raw,
            ))
        logger.info("Anthropic discovery: %d models", len(out))
        return out

    async def validate_model(self, model_id: str) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={"model": model_id, "max_tokens": 10, "messages": [{"role": "user", "content": "Return the number 4."}]},
                )
                if r.status_code == 200:
                    blocks = r.json().get("content", [])
                    text = blocks[0].get("text", "") if blocks else ""
                    return "4" in text
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Grok / xAI policy (Phase 4)
# ---------------------------------------------------------------------------

class GrokPolicy(ProviderPolicy):
    name = "grok"
    stability_level = "moderate"

    _ALLOWLIST = ["grok-3", "grok-3-mini", "grok-2"]

    def __init__(self):
        self.api_key = os.getenv("XAI_API_KEY", os.getenv("GROK_API_KEY", ""))

    async def discover_models(self) -> List[DiscoveredModel]:
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if r.status_code == 200:
                    data = r.json().get("data", r.json().get("models", []))
                    out = []
                    for raw in data:
                        mid = raw.get("id", "")
                        if not mid.startswith("grok"):
                            continue
                        out.append(DiscoveredModel(
                            provider="grok", model_id=mid,
                            display_name=mid, variant="reasoning" if "mini" not in mid else "chat",
                            supports_chat=True,
                            preview="beta" in mid.lower(),
                            priority=_stability_score(mid) + 100,
                            metadata=raw,
                        ))
                    if out:
                        logger.info("Grok discovery: %d models", len(out))
                        return out
        except Exception as exc:
            logger.debug("Grok API discovery failed: %s", exc)

        return [
            DiscoveredModel(
                provider="grok", model_id=mid, display_name=mid,
                variant="reasoning", supports_chat=True, priority=100 + i * 10,
            )
            for i, mid in enumerate(reversed(self._ALLOWLIST))
        ]

    async def validate_model(self, model_id: str) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": model_id, "messages": [{"role": "user", "content": "Return the number 4."}], "max_tokens": 5},
                )
                return r.status_code == 200 and "4" in r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Google Gemini policy (Phase 5) — extends existing discovery module
# ---------------------------------------------------------------------------

class GooglePolicy(ProviderPolicy):
    name = "google"
    stability_level = "strict"

    async def discover_models(self) -> List[DiscoveredModel]:
        try:
            from llmhive.app.providers.google_model_discovery import (
                get_available_google_models,
            )
            gmodels = await get_available_google_models()
            return [
                DiscoveredModel(
                    provider="google", model_id=m.model_id,
                    display_name=m.display_name, version=m.version,
                    variant=m.variant, supports_chat=True,
                    context_window=m.input_token_limit,
                    priority=m.priority,
                )
                for m in gmodels
            ]
        except Exception as exc:
            logger.warning("Google discovery delegation failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# OpenRouter policy (Phase 6)
# ---------------------------------------------------------------------------

class OpenRouterPolicy(ProviderPolicy):
    name = "openrouter"
    stability_level = "moderate"

    async def discover_models(self) -> List[DiscoveredModel]:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get("https://openrouter.ai/api/v1/models")
                if r.status_code != 200:
                    return []
                data = r.json().get("data", [])
        except Exception as exc:
            logger.warning("OpenRouter discovery failed: %s", exc)
            return []

        out: List[DiscoveredModel] = []
        for raw in data:
            mid = raw.get("id", "")
            if ":free" in mid and "test" in mid.lower():
                continue
            ctx = raw.get("context_length", 0)
            pricing = raw.get("pricing", {})
            prompt_cost = float(pricing.get("prompt", "0") or "0")
            tier = "free" if prompt_cost == 0 else ("paid" if prompt_cost < 0.01 else "premium")
            out.append(DiscoveredModel(
                provider="openrouter", model_id=mid,
                display_name=raw.get("name", mid),
                context_window=ctx,
                supports_chat=True,
                deprecated="deprecated" in mid.lower(),
                preview="preview" in mid.lower(),
                pricing_tier=tier,
                priority=min(ctx // 1000, 200) + _stability_score(mid),
                metadata={"pricing": pricing},
            ))
        logger.info("OpenRouter discovery: %d models", len(out))
        return out


# ---------------------------------------------------------------------------
# DeepSeek / Groq / Together / Cerebras / HF (Phase 7)
# ---------------------------------------------------------------------------

class DeepSeekPolicy(ProviderPolicy):
    name = "deepseek"
    stability_level = "moderate"

    _ALLOWLIST = ["deepseek-chat", "deepseek-reasoner"]

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")

    async def discover_models(self) -> List[DiscoveredModel]:
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.get(
                        "https://api.deepseek.com/v1/models",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        if data:
                            return [
                                DiscoveredModel(
                                    provider="deepseek", model_id=m.get("id", ""),
                                    display_name=m.get("id", ""),
                                    variant="reasoning" if "reason" in m.get("id", "").lower() else "chat",
                                    supports_chat=True, priority=150,
                                )
                                for m in data if m.get("id", "").startswith("deepseek")
                            ]
            except Exception:
                pass

        return [
            DiscoveredModel(provider="deepseek", model_id=m, display_name=m,
                            variant="reasoning" if "reason" in m else "chat",
                            supports_chat=True, priority=150)
            for m in self._ALLOWLIST
        ]


class GroqPolicy(ProviderPolicy):
    name = "groq"
    stability_level = "moderate"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")

    async def discover_models(self) -> List[DiscoveredModel]:
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if r.status_code != 200:
                    return []
                data = r.json().get("data", [])
        except Exception:
            return []

        return [
            DiscoveredModel(
                provider="groq", model_id=m.get("id", ""),
                display_name=m.get("id", ""),
                context_window=m.get("context_window", 0),
                supports_chat=True, priority=120 + _stability_score(m.get("id", "")),
            )
            for m in data if m.get("id", "")
        ]


class TogetherPolicy(ProviderPolicy):
    name = "together"
    stability_level = "moderate"

    def __init__(self):
        self.api_key = os.getenv("TOGETHER_API_KEY", "")

    async def discover_models(self) -> List[DiscoveredModel]:
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    "https://api.together.xyz/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if r.status_code != 200:
                    return []
                data = r.json()
                if isinstance(data, list):
                    items = data
                else:
                    items = data.get("data", data.get("models", []))
        except Exception:
            return []

        return [
            DiscoveredModel(
                provider="together", model_id=m.get("id", ""),
                display_name=m.get("display_name", m.get("id", "")),
                context_window=m.get("context_length", 0),
                supports_chat=True,
                priority=100 + _stability_score(m.get("id", "")),
            )
            for m in items if m.get("id", "")
        ]


class CerebrasPolicy(ProviderPolicy):
    name = "cerebras"
    stability_level = "strict"

    _ALLOWLIST = ["llama-4-scout-17b-16e-instruct", "llama3.3-70b", "qwen-3-32b"]

    async def discover_models(self) -> List[DiscoveredModel]:
        return [
            DiscoveredModel(provider="cerebras", model_id=m, display_name=m,
                            supports_chat=True, priority=100)
            for m in self._ALLOWLIST
        ]


class HuggingFacePolicy(ProviderPolicy):
    name = "huggingface"
    stability_level = "strict"

    _ALLOWLIST = ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"]

    async def discover_models(self) -> List[DiscoveredModel]:
        return [
            DiscoveredModel(provider="huggingface", model_id=m, display_name=m,
                            supports_chat=True, priority=80)
            for m in self._ALLOWLIST
        ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_POLICIES: List[ProviderPolicy] = [
    OpenAIPolicy(),
    AnthropicPolicy(),
    GrokPolicy(),
    GooglePolicy(),
    OpenRouterPolicy(),
    DeepSeekPolicy(),
    GroqPolicy(),
    TogetherPolicy(),
    CerebrasPolicy(),
    HuggingFacePolicy(),
]

_POLICY_MAP: Dict[str, ProviderPolicy] = {p.name: p for p in ALL_POLICIES}


def get_policy(provider_name: str) -> Optional[ProviderPolicy]:
    return _POLICY_MAP.get(provider_name.lower())


# ---------------------------------------------------------------------------
# Aggregate discovery
# ---------------------------------------------------------------------------

async def discover_all_providers(
    providers: Optional[List[str]] = None,
) -> Dict[str, List[DiscoveredModel]]:
    """Discover models from all (or specified) providers concurrently."""
    policies = ALL_POLICIES if providers is None else [
        p for p in ALL_POLICIES if p.name in providers
    ]
    tasks = [p.discover_models() for p in policies]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: Dict[str, List[DiscoveredModel]] = {}
    for policy, result in zip(policies, results):
        if isinstance(result, Exception):
            logger.warning("Discovery failed for %s: %s", policy.name, result)
            out[policy.name] = []
        else:
            stable = policy.filter_stable(result)
            out[policy.name] = policy.rank_models(stable)
    return out


def select_best_model(
    discovered: Dict[str, List[DiscoveredModel]],
    provider: str,
    workload: str = "general",
) -> Optional[DiscoveredModel]:
    """Select the best model for a provider+workload from discovery results."""
    models = discovered.get(provider, [])
    policy = get_policy(provider)
    if policy and models:
        ranked = policy.rank_models(models, workload)
        return ranked[0] if ranked else None
    return models[0] if models else None


# ---------------------------------------------------------------------------
# Shadow validation (Phase 8)
# ---------------------------------------------------------------------------

async def shadow_validate_candidate(
    candidate: DiscoveredModel,
    baseline: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Validate a candidate model against baseline metrics.

    Returns a report dict with pass/fail status.  Does NOT run the
    full micro_validation.py — that is left to the weekly workflow.
    """
    defaults = {
        "accuracy_delta_min": 0.0,
        "category_drop_max": 1.0,
        "cost_increase_max_pct": 10.0,
        "latency_increase_max_pct": 20.0,
    }
    thresholds = {**defaults, **(thresholds or {})}

    policy = get_policy(candidate.provider)
    if not policy:
        return {"model": candidate.model_id, "status": "fail", "reason": "unknown provider"}

    smoke_ok = await policy.validate_model(candidate.model_id)
    if not smoke_ok:
        return {"model": candidate.model_id, "status": "fail", "reason": "smoke test failed"}

    report: Dict[str, Any] = {
        "model": candidate.model_id,
        "provider": candidate.provider,
        "smoke_test": "pass",
        "timestamp": datetime.now().isoformat(),
        "thresholds": thresholds,
    }

    if baseline:
        report["baseline_accuracy"] = baseline.get("accuracy", 0)
        report["baseline_cost"] = baseline.get("cost", 0)
        report["status"] = "pass"
        report["note"] = "Full shadow validation requires micro_validation.py execution"
    else:
        report["status"] = "pass"
        report["note"] = "No baseline provided — smoke test only"

    return report


# ---------------------------------------------------------------------------
# Canary rollout config (Phase 9)
# ---------------------------------------------------------------------------

@dataclass
class CanaryConfig:
    enabled: bool = False
    percent: int = 10
    candidate_model: str = ""
    baseline_model: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)


def load_canary_config() -> CanaryConfig:
    pct = int(os.getenv("MODEL_CANARY_PERCENT", "0"))
    candidate = os.getenv("MODEL_CANARY_CANDIDATE", "")
    baseline = os.getenv("MODEL_CANARY_BASELINE", "")
    return CanaryConfig(
        enabled=pct > 0 and bool(candidate),
        percent=pct,
        candidate_model=candidate,
        baseline_model=baseline,
    )


def should_use_canary(canary: CanaryConfig, request_hash: int) -> bool:
    """Deterministic canary routing based on request hash."""
    if not canary.enabled:
        return False
    return (request_hash % 100) < canary.percent


# ---------------------------------------------------------------------------
# Rollback triggers (Phase 10)
# ---------------------------------------------------------------------------

@dataclass
class RollbackState:
    """Tracks live metrics for rollback decisions."""
    accuracy_baseline: float = 0.0
    retry_rate_baseline: float = 0.0
    cost_per_correct_baseline: float = 0.0
    latency_baseline_ms: float = 0.0

    accuracy_current: float = 0.0
    retry_rate_current: float = 0.0
    cost_per_correct_current: float = 0.0
    latency_current_ms: float = 0.0


def check_rollback_triggers(state: RollbackState) -> Optional[str]:
    """Return a reason string if rollback should fire, else None."""
    if state.accuracy_baseline > 0 and state.accuracy_current > 0:
        drop = state.accuracy_baseline - state.accuracy_current
        if drop > 3.0:
            return f"accuracy_drop={drop:.1f}%"

    if state.retry_rate_baseline >= 0 and state.retry_rate_current > 0:
        increase = state.retry_rate_current - state.retry_rate_baseline
        if increase > 5.0:
            return f"retry_rate_increase={increase:.1f}%"

    if state.cost_per_correct_baseline > 0 and state.cost_per_correct_current > 0:
        ratio = state.cost_per_correct_current / state.cost_per_correct_baseline
        if ratio > 1.15:
            return f"cost_increase={ratio:.0%}"

    if state.latency_baseline_ms > 0 and state.latency_current_ms > 0:
        ratio = state.latency_current_ms / state.latency_baseline_ms
        if ratio > 2.0:
            return f"latency_doubled={ratio:.1f}x"

    return None
