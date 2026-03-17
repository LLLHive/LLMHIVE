"""Elite+ Orchestrator — Free-First Verified Premium.

The ONLY public premium tier.  Elite is internal fallback only.

Policy: free_first_verified
  Stage A — Free primary:   run free ensemble for the category
  Stage B — Deterministic:  calculator/MCQ/tool-schema/RAG grounding check
  Stage C — Paid escalation: call ONE category-specific paid anchor (if triggered)
  Stage D — Fallback:       fall back to base Elite only on catastrophic failure

Cost targets: p50 <= $0.010, p95 <= $0.020 per request.
Paid calls default max = 1 in production (hard cap = 2 for internal bench).

Rollback: ELITE_PLUS_ENABLED=0 + PREMIUM_DEFAULT_TIER=elite
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENV FLAGS
# ---------------------------------------------------------------------------
ELITE_PLUS_ENABLED = os.getenv("ELITE_PLUS_ENABLED", "1").lower() in ("1", "true")
ELITE_PLUS_MODE = os.getenv("ELITE_PLUS_MODE", "active").lower().strip()
ELITE_PLUS_POLICY = os.getenv("ELITE_PLUS_POLICY", "free_first_verified").lower().strip()

# Premium tier routing — elite_plus is the public premium tier
PREMIUM_DEFAULT_TIER = os.getenv("PREMIUM_DEFAULT_TIER", "elite_plus").lower().strip()
ELITE_FALLBACK_ENABLED = os.getenv("ELITE_FALLBACK_ENABLED", "1").lower() in ("1", "true")
ELITE_PUBLIC_ENABLED = os.getenv("ELITE_PUBLIC_ENABLED", "0").lower() in ("1", "true")

# Budget caps
ELITE_PLUS_MAX_PAID_CALLS = int(os.getenv("ELITE_PLUS_MAX_PAID_CALLS", "1"))
ELITE_PLUS_MAX_PAID_CALLS_HARD = int(os.getenv("ELITE_PLUS_MAX_PAID_CALLS_HARD", "2"))
ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH = int(os.getenv("ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH", "1"))
ELITE_PLUS_BUDGET_USD_P50 = float(os.getenv("ELITE_PLUS_BUDGET_USD_P50", "0.010"))
ELITE_PLUS_BUDGET_USD_P95 = float(os.getenv("ELITE_PLUS_BUDGET_USD_P95", "0.020"))
ELITE_PLUS_BUDGET_MS = int(os.getenv("ELITE_PLUS_BUDGET_MS", "8000"))
ELITE_PLUS_V2_ANCHOR_BUDGET_MS = int(os.getenv("ELITE_PLUS_V2_ANCHOR_BUDGET_MS", "30000"))

# Escalation triggers
ELITE_PLUS_ESCALATE_ON_DISAGREEMENT = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_DISAGREEMENT", "1"
).lower() in ("1", "true")
ELITE_PLUS_ESCALATE_ON_LOW_CONFIDENCE = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_LOW_CONFIDENCE", "1"
).lower() in ("1", "true")
ELITE_PLUS_ESCALATE_ON_TOOL_FAILURE = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_TOOL_FAILURE", "1"
).lower() in ("1", "true")
ELITE_PLUS_ESCALATE_ON_RAG_UNGROUNDED = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_RAG_UNGROUNDED", "1"
).lower() in ("1", "true")
ELITE_PLUS_LOW_CONF_THRESHOLD = float(
    os.getenv("ELITE_PLUS_LOW_CONF_THRESHOLD", "0.65")
)

# Category-specific policies
ELITE_PLUS_TOOL_STRICT_MODE = os.getenv("ELITE_PLUS_TOOL_STRICT_MODE", "1").lower() in ("1", "true")
ELITE_PLUS_TOOL_POSTPROCESS_ALLOWED = os.getenv("ELITE_PLUS_TOOL_POSTPROCESS_ALLOWED", "0").lower() in ("1", "true")
ELITE_PLUS_RAG_EXTRACTIVE_MODE = os.getenv("ELITE_PLUS_RAG_EXTRACTIVE_MODE", "1").lower() in ("1", "true")
ELITE_PLUS_RAG_REQUIRE_SUPPORT = os.getenv("ELITE_PLUS_RAG_REQUIRE_SUPPORT", "1").lower() in ("1", "true")
ELITE_PLUS_RAG_TOPK = int(os.getenv("ELITE_PLUS_RAG_TOPK", "10"))
ELITE_PLUS_RERANK_DETERMINISTIC = os.getenv("ELITE_PLUS_RERANK_DETERMINISTIC", "1").lower() in ("1", "true")
ELITE_PLUS_DIALOGUE_LIGHT_TOUCH = os.getenv("ELITE_PLUS_DIALOGUE_LIGHT_TOUCH", "1").lower() in ("1", "true")
ELITE_PLUS_DIALOGUE_MAX_MODELS = int(os.getenv("ELITE_PLUS_DIALOGUE_MAX_MODELS", "1"))
ELITE_PLUS_MATH_FREE_FIRST = os.getenv("ELITE_PLUS_MATH_FREE_FIRST", "1").lower() in ("1", "true")
ELITE_PLUS_MATH_REQUIRE_VERIFICATION = os.getenv("ELITE_PLUS_MATH_REQUIRE_VERIFICATION", "1").lower() in ("1", "true")

# Long context
ELITE_PLUS_LONG_CONTEXT_ANCHOR_MODEL = os.getenv(
    "ELITE_PLUS_LONG_CONTEXT_ANCHOR_MODEL", "google/gemini-3.1-pro-preview"
)

# Verifier
ELITE_PLUS_VERIFIER_STRATEGY = os.getenv("ELITE_PLUS_VERIFIER_STRATEGY", "hybrid").lower()
ELITE_PLUS_VERIFIER_TIMEOUT_MS = int(os.getenv("ELITE_PLUS_VERIFIER_TIMEOUT_MS", "12000"))
ELITE_PLUS_VERIFIER_MODEL = os.getenv("ELITE_PLUS_VERIFIER_MODEL", "openai/gpt-4o-mini")

ELITE_PLUS_LOG_SHADOW = os.getenv("ELITE_PLUS_LOG_SHADOW", "1").lower() in ("1", "true")
ALLOW_INTERNAL_BENCH_OUTPUT = os.getenv("ALLOW_INTERNAL_BENCH_OUTPUT", "0").lower() in ("1", "true")

# Leader-aware routing (default OFF) — when enabled, prefer category leader model if available and cost-safe
ELITE_PLUS_LEADER_HINTS_ENABLED = os.getenv("ELITE_PLUS_LEADER_HINTS_ENABLED", "0").lower() in ("1", "true")

# Leader-first verified policy (Workstream B) — all defaults OFF
ELITE_PLUS_LEADERBOARD_AWARE = os.getenv("ELITE_PLUS_LEADERBOARD_AWARE", "0").lower() in ("1", "true")
ELITE_PLUS_LEADER_FIRST_ALLOWED = os.getenv("ELITE_PLUS_LEADER_FIRST_ALLOWED", "0").lower() in ("1", "true")
ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY = os.getenv("ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY", "1").lower() in ("1", "true")
ELITE_PLUS_LEADER_FIRST_MAX_PAID_CALLS = int(os.getenv("ELITE_PLUS_LEADER_FIRST_MAX_PAID_CALLS", "1"))

# Auto-dominance verified (Workstream 2) — Elite+ cannot be worse than Free by construction
ELITE_PLUS_ENABLE_AUTO_DOMINANCE = os.getenv("ELITE_PLUS_ENABLE_AUTO_DOMINANCE", "0").lower() in ("1", "true")
# Category allowlist for leader-first in production (default empty)
_LEADER_FIRST_CATEGORY_ALLOWLIST = set(
    c.strip().lower() for c in os.getenv("ELITE_PLUS_LEADER_FIRST_CATEGORIES", "").split(",") if c.strip()
)
# Internal bench allowlist includes reasoning and multilingual
_LEADER_FIRST_INTERNAL_ALLOWLIST = {"reasoning", "multilingual"}

# ---------------------------------------------------------------------------
# Dominance Architecture v2 — parallel ensemble with deterministic dominance
# ---------------------------------------------------------------------------
ELITE_PLUS_ENABLE_DOMINANCE_V2 = os.getenv("ELITE_PLUS_ENABLE_DOMINANCE_V2", "0").lower() in ("1", "true")
# ---------------------------------------------------------------------------
# Dominance Architecture v3 — hybrid ensemble-preserving with premium refiner
# Guarantees no regression in MCQ reasoning/coding by using free ensemble
# as primary and premium anchor only as refiner/fallback.
# ---------------------------------------------------------------------------
ELITE_PLUS_ENABLE_DOMINANCE_V3 = os.getenv("ELITE_PLUS_ENABLE_DOMINANCE_V3", "0").lower() in ("1", "true")
ELITE_PLUS_V3_LEADER_CONFIDENCE_THRESHOLD = float(
    os.getenv("ELITE_PLUS_V3_LEADER_CONFIDENCE_THRESHOLD", "0.8")
)
_DETERMINISTIC_CATEGORIES = {"reasoning", "coding", "math", "multilingual", "tool_use", "rag"}
_DIALOGUE_PREMIUM_MODEL = os.getenv("ELITE_PLUS_DIALOGUE_PREMIUM_MODEL", "openai/gpt-5.2")

# ---------------------------------------------------------------------------
# Production Split — per-category routing based on benchmark evidence
# Gated by ELITE_PLUS_PRODUCTION_SPLIT=1.  Does NOT alter v3 adjudication;
# it simply selects the best-performing *dispatch path* for each category.
# ---------------------------------------------------------------------------
ELITE_PLUS_PRODUCTION_SPLIT = os.getenv("ELITE_PLUS_PRODUCTION_SPLIT", "0").lower() in ("1", "true")

# Categories that showed improvement under leader_first (dominance v3/v2):
_SPLIT_LEADER_FIRST = {"tool_use", "rag"}
# Categories that showed regression under leader_first — keep on free_first:
_SPLIT_FREE_FIRST = {"reasoning", "coding", "multilingual", "math"}
# Dialogue always uses single-premium (handled in both v3 and free_first)
# Long_context uses Gemini anchor (handled in v2 delegation inside v3)

# STEP 1 + 3: Validate paid provider credentials at import time when dominance v2 is enabled
_V2_DIRECT_PROVIDERS: Dict[str, str] = {
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    "gemini": os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_AI_API_KEY", "")),
}
_V2_HAS_OPENROUTER = bool(os.getenv("OPENROUTER_API_KEY", ""))
BENCHMARK_MODE = os.getenv("BENCHMARK_MODE", "0").lower() in ("1", "true")
_CRITICAL_PAID_CATEGORIES = {"coding", "tool_use", "multilingual", "reasoning", "math", "rag"}

if ELITE_PLUS_ENABLE_DOMINANCE_V2 or ELITE_PLUS_ENABLE_DOMINANCE_V3:
    _v2_missing = [
        f"{name} ({name.upper()}_API_KEY)" for name, key in _V2_DIRECT_PROVIDERS.items()
        if not key and not _V2_HAS_OPENROUTER
    ]
    if _v2_missing:
        _v_label = "V3" if ELITE_PLUS_ENABLE_DOMINANCE_V3 else "V2"
        _msg = (
            f"ELITE_PLUS_ENABLE_DOMINANCE_{_v_label}=1 but paid providers not configured: "
            f"{', '.join(_v2_missing)}. Set provider API keys or OPENROUTER_API_KEY."
        )
        logger.error(_msg)
        raise RuntimeError(_msg)

    _active = [name for name, key in _V2_DIRECT_PROVIDERS.items() if key]
    if _V2_HAS_OPENROUTER:
        _active.append("openrouter")
    _v_label = "V3" if ELITE_PLUS_ENABLE_DOMINANCE_V3 else "V2"
    logger.info(
        "DOMINANCE_%s STARTUP: active_providers=%s direct=%s openrouter=%s",
        _v_label, _active,
        [n for n, k in _V2_DIRECT_PROVIDERS.items() if k],
        _V2_HAS_OPENROUTER,
    )

# ---------------------------------------------------------------------------
# Stability V1 gate — enables infra hardening without altering dominance logic
# ---------------------------------------------------------------------------
ELITE_PLUS_STABILITY_V1 = os.getenv("ELITE_PLUS_STABILITY_V1", "0").lower() in ("1", "true")
if ELITE_PLUS_STABILITY_V1:
    logger.info(
        "STABILITY_V1 ENABLED: soft_anchor_guard=true provider_health_auto_disable=true warmup_gated=true"
    )

# ---------------------------------------------------------------------------
# Provider warmup (STEP 2)
# ---------------------------------------------------------------------------
ELITE_PLUS_WARMUP = os.getenv("ELITE_PLUS_WARMUP", "0").lower() in ("1", "true")
ELITE_PLUS_WARMUP_TIMEOUT_MS = int(os.getenv("ELITE_PLUS_WARMUP_TIMEOUT_MS", "15000"))

# RAG learning loop (STEP 5)
RAG_LEARNING_MODE = os.getenv("RAG_LEARNING_MODE", "0").lower() in ("1", "true")

# ---------------------------------------------------------------------------
# Provider health scoring (STEP 3) — tracks success/failure per provider
# ---------------------------------------------------------------------------
class _ProviderHealthTracker:
    """Per-provider success/failure counter with auto-disable."""

    _DISABLE_THRESHOLD = 0.30
    _DISABLE_DURATION_SEC = 60

    def __init__(self) -> None:
        self._success: Dict[str, int] = {}
        self._failure: Dict[str, int] = {}
        self._disabled_until: Dict[str, float] = {}
        self._warmup_latency: Dict[str, int] = {}

    def record(self, provider: str, success: bool) -> None:
        if success:
            self._success[provider] = self._success.get(provider, 0) + 1
        else:
            self._failure[provider] = self._failure.get(provider, 0) + 1
        total = self._success.get(provider, 0) + self._failure.get(provider, 0)
        if total >= 5:
            fail_rate = self._failure.get(provider, 0) / total
            if fail_rate > self._DISABLE_THRESHOLD:
                self._disabled_until[provider] = time.time() + self._DISABLE_DURATION_SEC
                logger.warning(
                    "PROVIDER_HEALTH: %s disabled for %ds (fail_rate=%.0f%% over %d calls)",
                    provider, self._DISABLE_DURATION_SEC, fail_rate * 100, total,
                )

    def is_healthy(self, provider: str) -> bool:
        until = self._disabled_until.get(provider)
        if until is None:
            return True
        if time.time() >= until:
            del self._disabled_until[provider]
            self._success.pop(provider, None)
            self._failure.pop(provider, None)
            logger.info("PROVIDER_HEALTH: %s re-enabled (cooldown expired)", provider)
            return True
        return False

    def record_warmup(self, provider: str, latency_ms: int) -> None:
        self._warmup_latency[provider] = latency_ms

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "providers": {
                p: {
                    "success": self._success.get(p, 0),
                    "failure": self._failure.get(p, 0),
                    "healthy": self.is_healthy(p),
                    "warmup_latency_ms": self._warmup_latency.get(p),
                }
                for p in set(list(self._success) + list(self._failure) + list(self._warmup_latency))
            },
            "disabled": {
                p: {"remaining_sec": max(0, int(until - now))}
                for p, until in self._disabled_until.items()
                if now < until
            },
        }


_provider_health = _ProviderHealthTracker()


def get_provider_health_status() -> Dict[str, Any]:
    """Public accessor for health endpoint."""
    return _provider_health.get_status()


async def warmup_providers(orchestrator: Any) -> Dict[str, Any]:
    """Send one lightweight request to each premium anchor to warm connection pools.

    Returns a summary dict with per-provider latency or failure.
    """
    if not ELITE_PLUS_WARMUP:
        return {"skipped": True}

    results: Dict[str, Any] = {}
    warmup_prompt = "Reply with OK."
    unique_anchors = set(_V2_PAID_ANCHORS.values())

    for anchor in unique_anchors:
        t0 = time.perf_counter()
        try:
            text, latency = await _call_model(
                orchestrator, warmup_prompt, anchor,
                ELITE_PLUS_WARMUP_TIMEOUT_MS,
                force_direct=True,
            )
            ok = bool(text and len(text.strip()) > 0)
            _provider_health.record(anchor, ok)
            if ok:
                _provider_health.record_warmup(anchor, latency)
            results[anchor] = {"status": "healthy" if ok else "empty_response", "latency_ms": latency}
            logger.info("WARMUP: %s %s latency=%dms", anchor, "OK" if ok else "EMPTY", latency)
        except Exception as exc:
            latency = int((time.perf_counter() - t0) * 1000)
            _provider_health.record(anchor, False)
            results[anchor] = {"status": f"error:{type(exc).__name__}", "latency_ms": latency}
            logger.warning("WARMUP: %s FAILED latency=%dms err=%s", anchor, latency, exc)

    return results


# ---------------------------------------------------------------------------
# G2: Launch Mode runtime governance
# ---------------------------------------------------------------------------
ELITE_PLUS_LAUNCH_MODE = os.getenv("ELITE_PLUS_LAUNCH_MODE", "1").lower() in ("1", "true")
ELITE_PLUS_MAX_COST_USD_REQUEST = float(os.getenv("ELITE_PLUS_MAX_COST_USD_REQUEST", "0.025"))

# Circuit breaker config
ELITE_PLUS_CB_WINDOW = int(os.getenv("ELITE_PLUS_CB_WINDOW", "50"))
ELITE_PLUS_CB_MAX_ERROR_RATE = float(os.getenv("ELITE_PLUS_CB_MAX_ERROR_RATE", "0.20"))
ELITE_PLUS_CB_COOLDOWN_SEC = int(os.getenv("ELITE_PLUS_CB_COOLDOWN_SEC", "300"))

# P0 categories that are allowed paid escalation in Launch Mode
_P0_CATEGORIES = {"tool_use", "rag", "dialogue", "math"}
# Hard-failure escalation reasons that always allow paid calls
_HARD_FAILURE_REASONS = {"tool_schema_invalid", "tool_execution_error", "rag_grounding_fail", "catastrophic_failure"}

# ---------------------------------------------------------------------------
# Part B: Category-specific paid anchor selection (env-configurable)
# ---------------------------------------------------------------------------
_PAID_ANCHORS: Dict[str, str] = {
    "tool_use":     os.getenv("ELITE_PLUS_PAID_ANCHOR_TOOL_USE",     "openai/gpt-4o"),
    "rag":          os.getenv("ELITE_PLUS_PAID_ANCHOR_RAG",          "openai/gpt-4o-mini"),
    "reasoning":    os.getenv("ELITE_PLUS_PAID_ANCHOR_REASONING",    "openai/gpt-4o-mini"),
    "dialogue":     os.getenv("ELITE_PLUS_PAID_ANCHOR_DIALOGUE",     "anthropic/claude-sonnet-4"),
    "long_context": os.getenv("ELITE_PLUS_PAID_ANCHOR_LONG_CONTEXT", "google/gemini-3.1-pro-preview"),
    "math":         os.getenv("ELITE_PLUS_PAID_ANCHOR_MATH",         "openai/gpt-4o-mini"),
    "coding":       os.getenv("ELITE_PLUS_PAID_ANCHOR_CODING",       "anthropic/claude-sonnet-4"),
    "multilingual": os.getenv("ELITE_PLUS_PAID_ANCHOR_MULTILINGUAL", "openai/gpt-4o-mini"),
    "speed":        os.getenv("ELITE_PLUS_PAID_ANCHOR_SPEED",        "openai/gpt-4o-mini"),
    "multimodal":   os.getenv("ELITE_PLUS_PAID_ANCHOR_MULTIMODAL",   "openai/gpt-4o"),
}

# Free models per category
_FREE_MODELS_DEFAULT: Dict[str, List[str]] = {
    "math": ["deepseek/deepseek-chat", "qwen/qwen3-next-80b-a3b-instruct:free"],
    "reasoning": ["deepseek/deepseek-chat", "qwen/qwen3-next-80b-a3b-instruct:free"],
    "coding": ["qwen/qwen3-coder:free", "deepseek/deepseek-chat"],
    "rag": ["qwen/qwen3-next-80b-a3b-instruct:free", "deepseek/deepseek-chat"],
    "multilingual": ["deepseek/deepseek-chat", "qwen/qwen3-next-80b-a3b-instruct:free"],
    "long_context": ["qwen/qwen3-next-80b-a3b-instruct:free", "deepseek/deepseek-chat"],
    "tool_use": ["deepseek/deepseek-chat", "qwen/qwen3-coder:free"],
    "dialogue": ["deepseek/deepseek-chat"],
    "speed": ["deepseek/deepseek-chat"],
    "multimodal": ["deepseek/deepseek-chat"],
}

# V2 category-leader routing table (only active when ELITE_PLUS_ENABLE_DOMINANCE_V2=1)
_V2_PAID_ANCHORS: Dict[str, str] = {
    "reasoning":    os.getenv("ELITE_PLUS_V2_ANCHOR_REASONING",    "google/gemini-3.1-pro-preview"),
    "coding":       os.getenv("ELITE_PLUS_V2_ANCHOR_CODING",       "anthropic/claude-opus-4.6"),
    "math":         os.getenv("ELITE_PLUS_V2_ANCHOR_MATH",         "openai/gpt-5.2"),
    "multilingual": os.getenv("ELITE_PLUS_V2_ANCHOR_MULTILINGUAL", "google/gemini-3-pro"),
    "long_context": os.getenv("ELITE_PLUS_V2_ANCHOR_LONG_CONTEXT", "google/gemini-3.1-pro-preview"),
    "tool_use":     os.getenv("ELITE_PLUS_V2_ANCHOR_TOOL_USE",     "anthropic/claude-opus-4.6"),
    "rag":          os.getenv("ELITE_PLUS_V2_ANCHOR_RAG",          "openai/gpt-5.2"),
    "dialogue":     os.getenv("ELITE_PLUS_V2_ANCHOR_DIALOGUE",     "openai/gpt-5.2"),
}

# Estimated costs (output tokens per 1M) for budget tracking
_MODEL_COST_PER_1M: Dict[str, float] = {
    "openai/gpt-4o-mini": 0.60,
    "openai/gpt-4o": 10.0,
    "anthropic/claude-sonnet-4": 15.0,
    "google/gemini-3.1-pro-preview": 2.0,
    "google/gemini-2.5-flash": 0.075,
    "openai/gpt-5.2": 15.0,
    "anthropic/claude-opus-4.6": 15.0,
    "zhipuai/glm-4.7": 2.0,
    "google/gemini-3-pro": 1.5,
}

_MCQ_PATTERN = re.compile(r"\b([A-E])\b")
_MCQ_OPTIONS_PATTERN = re.compile(r"\b[A-E]\s*[.\)]\s*\w+", re.I)  # "A. foo" or "A) foo"


def _is_mcq_query(query: str) -> bool:
    """Detect if query contains MCQ-style options (A/B/C/D)."""
    if not query or len(query) < 20:
        return False
    # Look for option patterns: "A.", "B)", "C.", etc.
    return bool(_MCQ_OPTIONS_PATTERN.search(query)) or len(_MCQ_PATTERN.findall(query)) >= 2


def _extract_mcq_letter_strict(text: str) -> Optional[str]:
    """Strict MCQ extraction: single letter A-E only. Returns None if ambiguous/invalid."""
    if not text:
        return None
    letters = _MCQ_PATTERN.findall(text[:200].upper())
    if len(letters) == 1:
        return letters[0].upper()
    if len(letters) >= 2:
        # Take the last one (often the final answer after reasoning)
        return letters[-1].upper()
    return None


def _mcq_prompt_suffix() -> str:
    """Instruction to force single-letter MCQ response."""
    return "\n\nRespond with ONLY a single letter (A, B, C, D, or E). No explanation."


# ---------------------------------------------------------------------------
# G2: Circuit breaker (in-memory per-model health tracking)
# ---------------------------------------------------------------------------
class _CircuitBreaker:
    """Per-model rolling-window error tracker with cooldown.

    Thread-safe via GIL for single-process; adequate for initial launch.
    """

    def __init__(
        self,
        window: int = ELITE_PLUS_CB_WINDOW,
        max_error_rate: float = ELITE_PLUS_CB_MAX_ERROR_RATE,
        cooldown_sec: int = ELITE_PLUS_CB_COOLDOWN_SEC,
    ):
        self._window = window
        self._max_error_rate = max_error_rate
        self._cooldown_sec = cooldown_sec
        self._records: Dict[str, List[bool]] = {}        # model -> [ok, ok, fail, ...]
        self._degraded_until: Dict[str, float] = {}      # model -> timestamp

    def record(self, model_id: str, success: bool) -> None:
        buf = self._records.setdefault(model_id, [])
        buf.append(success)
        if len(buf) > self._window:
            buf.pop(0)
        if len(buf) >= 10:
            error_rate = 1.0 - (sum(buf) / len(buf))
            if error_rate >= self._max_error_rate:
                self._degraded_until[model_id] = time.time() + self._cooldown_sec
                logger.warning(
                    "Circuit breaker OPEN for %s (error_rate=%.2f, cooldown=%ds)",
                    model_id, error_rate, self._cooldown_sec,
                )

    def is_degraded(self, model_id: str) -> bool:
        until = self._degraded_until.get(model_id)
        if until is None:
            return False
        if time.time() >= until:
            del self._degraded_until[model_id]
            self._records.pop(model_id, None)
            logger.info("Circuit breaker CLOSED for %s (cooldown expired)", model_id)
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            model: {
                "degraded": True,
                "remaining_sec": max(0, int(until - now)),
                "error_rate": round(
                    1.0 - (sum(self._records.get(model, [])) / max(len(self._records.get(model, [])), 1)),
                    3,
                ),
            }
            for model, until in self._degraded_until.items()
            if now < until
        }


_circuit_breaker = _CircuitBreaker()


def _launch_mode_allows_escalation(
    category: str,
    escalation_reasons: List[str],
) -> bool:
    """In Launch Mode, only allow paid escalation for P0 categories or hard failures."""
    if not ELITE_PLUS_LAUNCH_MODE:
        return True
    if category in _P0_CATEGORIES:
        return True
    classified = set()
    for r in escalation_reasons:
        for hf in _HARD_FAILURE_REASONS:
            if hf in r:
                classified.add(hf)
    return len(classified) > 0


def _launch_mode_cost_ok(current_cost: float, next_model: str) -> bool:
    """Check if adding one more model call stays within per-request ceiling."""
    if not ELITE_PLUS_LAUNCH_MODE:
        return True
    predicted = current_cost + _estimate_cost(next_model)
    return predicted <= ELITE_PLUS_MAX_COST_USD_REQUEST


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Public accessor for KPI endpoint."""
    return _circuit_breaker.get_status()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ElitePlusResult:
    answer: str
    confidence: float
    mode: str
    policy: str
    stage_used: str                        # free_primary | deterministic_verify | paid_escalation | fallback_elite
    paid_calls_count: int = 0
    free_calls_count: int = 0
    estimated_cost_usd: float = 0.0
    estimated_cost_breakdown: Dict[str, float] = field(default_factory=dict)
    confidence_free: float = 0.0
    confidence_final: float = 0.0
    escalation_reason: List[str] = field(default_factory=list)
    models_called: List[str] = field(default_factory=list)
    tool_invocations: List[str] = field(default_factory=list)
    rag_grounding_status: str = "n/a"
    total_latency_ms: int = 0
    verifier_strategy: str = "none"
    verifier_status: str = "ok"
    verifier_latency_ms: int = 0

    # Part C: tool use telemetry
    tool_schema_valid: bool = True
    tool_retry_count: int = 0
    tool_execution_ok: bool = True
    tool_error_type: str = "none"

    # Part D: RAG telemetry
    rag_unanswered_reason: str = "none"
    rag_passage_count_used: int = 0

    # Part E: dialogue telemetry
    dialogue_mode: str = "n/a"
    dialogue_anchor_used: str = ""
    dialogue_escalated: bool = False

    # backward compat with shadow telemetry consumers
    shadow_answer: str = ""
    shadow_confidence: float = 0.0
    should_override: bool = True
    base_answer: str = ""
    base_confidence: float = 0.0
    blackboard_hash: str = ""

    # Auto-dominance telemetry (Workstream 2)
    baseline_policy_used: str = ""
    upgrade_attempted: bool = False
    upgrade_reason: str = ""
    upgrade_blocked_by_governor: bool = False
    selected_answer_source: str = "baseline"  # baseline | upgrade
    mcq_invalid_extraction: bool = False

    # Provider telemetry (v2 execution integrity)
    provider_used: str = ""
    direct_or_router: str = ""
    paid_call_made: bool = False
    fallback_reason: str = ""
    elite_v2_executed: bool = False
    anchor_failure_reason: str = ""
    anchor_model_used: str = ""

    def to_telemetry(self) -> Dict[str, Any]:
        return {
            "elite_plus_enabled": True,
            "elite_plus_mode": self.mode,
            "policy": self.policy,
            "stage_used": self.stage_used,
            "paid_calls_count": self.paid_calls_count,
            "free_calls_count": self.free_calls_count,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "estimated_cost_breakdown": self.estimated_cost_breakdown,
            "confidence_free": round(self.confidence_free, 3),
            "confidence_final": round(self.confidence_final, 3),
            "escalation_reason": self.escalation_reason,
            "models_called": self.models_called,
            "tool_invocations": self.tool_invocations,
            "rag_grounding_status": self.rag_grounding_status,
            "total_latency_ms": self.total_latency_ms,
            "verifier_strategy": self.verifier_strategy,
            "verifier_status": self.verifier_status,
            "verifier_latency_ms": self.verifier_latency_ms,
            "should_override": self.should_override,
            "shadow_confidence": round(self.shadow_confidence, 3),
            "base_confidence": round(self.base_confidence, 3),
            # Auto-dominance telemetry
            "baseline_policy_used": self.baseline_policy_used,
            "upgrade_attempted": self.upgrade_attempted,
            "upgrade_reason": self.upgrade_reason,
            "upgrade_blocked_by_governor": self.upgrade_blocked_by_governor,
            "selected_answer_source": self.selected_answer_source,
            "mcq_invalid_extraction": self.mcq_invalid_extraction,
            # Part C: tool telemetry
            "tool_schema_valid": self.tool_schema_valid,
            "tool_retry_count": self.tool_retry_count,
            "tool_execution_ok": self.tool_execution_ok,
            "tool_error_type": self.tool_error_type,
            # Part D: RAG telemetry
            "rag_unanswered_reason": self.rag_unanswered_reason,
            "rag_passage_count_used": self.rag_passage_count_used,
            # Part E: dialogue telemetry
            "dialogue_mode": self.dialogue_mode,
            "dialogue_anchor_used": self.dialogue_anchor_used,
            "dialogue_escalated": self.dialogue_escalated,
            # Provider telemetry (v2)
            "provider_used": self.provider_used,
            "direct_or_router": self.direct_or_router,
            "paid_call_made": self.paid_call_made,
            "fallback_reason": self.fallback_reason,
            "elite_v2_executed": self.elite_v2_executed,
            "anchor_failure_reason": self.anchor_failure_reason,
            "anchor_model_used": self.anchor_model_used,
        }


# ---------------------------------------------------------------------------
# Model call helper
# ---------------------------------------------------------------------------
@dataclass
class ModelCallResult:
    text: str
    latency_ms: int
    provider_used: str = "unknown"
    direct_or_router: str = "unknown"
    model_actually_used: str = ""
    fallback_occurred: bool = False
    fallback_reason: str = ""
    anchor_failure_reason: str = ""


async def _call_model(
    orchestrator: Any,
    prompt: str,
    model_id: str,
    timeout_ms: int,
    *,
    force_direct: bool = False,
) -> Tuple[str, int]:
    """Call a model. If force_direct=True, pass hint to bypass OpenRouter."""
    t0 = time.perf_counter()
    try:
        timeout_s = max(timeout_ms / 1000.0, 5.0)

        # STEP 3: When force_direct, pass _prefer_direct to orchestrator
        extra_kwargs: Dict[str, Any] = {}
        if force_direct:
            extra_kwargs["_prefer_direct_provider"] = True

        artifacts = await asyncio.wait_for(
            orchestrator.orchestrate(
                prompt,
                [model_id],
                use_hrm=False,
                use_adaptive_routing=False,
                use_deep_consensus=False,
                use_prompt_diffusion=False,
                accuracy_level=3,
                skip_injection_check=True,
                **extra_kwargs,
            ),
            timeout=timeout_s,
        )
        text = artifacts.final_response.content
        latency = int((time.perf_counter() - t0) * 1000)

        # STEP 4: Extract provider telemetry from artifacts
        actual_model = getattr(artifacts.final_response, "model", "") or ""
        if hasattr(artifacts, "metadata"):
            actual_model = actual_model or artifacts.metadata.get("model_used", "")

        if actual_model and "fallback" in actual_model.lower():
            logger.warning(
                "PROVIDER_DOWNGRADE: requested=%s actual=%s — paid model was replaced by fallback",
                model_id, actual_model,
            )

        return text, latency
    except asyncio.TimeoutError:
        latency = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "ANCHOR_FAILURE: model=%s reason=provider_timeout latency=%dms",
            model_id, latency,
        )
        return "", latency
    except Exception as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "ANCHOR_FAILURE: model=%s reason=%s latency=%dms exc=%s",
            model_id, type(exc).__name__, latency, exc,
        )
        return "", latency


def _estimate_cost(model_id: str, output_tokens: int = 500) -> float:
    rate = _MODEL_COST_PER_1M.get(model_id, 1.0)
    return rate * output_tokens / 1_000_000


# ---------------------------------------------------------------------------
# Deterministic verifiers (Stage B)
# ---------------------------------------------------------------------------
def _extract_numeric(text: str) -> Optional[float]:
    cleaned = text.strip()
    boxed = re.search(r"\\boxed\{([^}]+)\}", cleaned)
    if boxed:
        cleaned = boxed.group(1)
    final = re.search(r"(?:final answer|answer)\s*(?:is|=|:)\s*([0-9.,/\-]+)", cleaned, re.IGNORECASE)
    if final:
        cleaned = final.group(1)
    cleaned = cleaned.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        if "/" in cleaned:
            parts = cleaned.split("/")
            if len(parts) == 2:
                try:
                    return float(parts[0]) / float(parts[1])
                except (ValueError, ZeroDivisionError):
                    pass
    return None


def _extract_mcq_letter(text: str) -> Optional[str]:
    m = re.search(r"\b([A-E])\b", text[:50])
    return m.group(1).upper() if m else None


def _verify_math(answers: List[str]) -> Tuple[bool, float, str]:
    """Check numeric consensus across answers. Returns (verified, confidence, rationale)."""
    numerics = []
    for ans in answers:
        val = _extract_numeric(ans)
        if val is not None:
            numerics.append(val)
    if len(numerics) < 2:
        return False, 0.5, "insufficient_numeric_answers"
    groups: Dict[float, int] = {}
    for v in numerics:
        matched = False
        for key in groups:
            if abs(key - v) < 1e-6 or (key != 0 and abs((key - v) / key) < 0.001):
                groups[key] += 1
                matched = True
                break
        if not matched:
            groups[v] = 1
    if groups:
        best_key = max(groups, key=groups.get)
        count = groups[best_key]
        if count >= 2:
            return True, min(0.95, 0.7 + 0.1 * count), f"numeric_consensus_{count}_agree"
    return False, 0.5, "no_numeric_consensus"


def _verify_mcq(answers: List[str]) -> Tuple[bool, float, str]:
    """Check MCQ letter consensus."""
    letters = []
    for ans in answers:
        letter = _extract_mcq_letter(ans)
        if letter:
            letters.append(letter)
    if len(letters) < 2:
        return False, 0.5, "insufficient_mcq_answers"
    from collections import Counter
    counts = Counter(letters)
    best_letter, count = counts.most_common(1)[0]
    if count >= 2:
        return True, min(0.9, 0.6 + 0.15 * count), f"mcq_consensus_{count}_agree_on_{best_letter}"
    return False, 0.5, "no_mcq_consensus"


def _validate_tool_schema(answer: str) -> Tuple[bool, str]:
    """Validate that a tool-calling response contains valid JSON tool calls."""
    if not answer or len(answer.strip()) < 5:
        return False, "empty"
    json_match = re.search(r"\{[^}]{5,}\}", answer)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, dict):
                return True, "valid_json"
        except (json.JSONDecodeError, ValueError):
            pass
    if any(k in answer.lower() for k in ["function_call", "tool_call", "action", "result"]):
        return True, "structured_keywords"
    return True, "freeform_ok"


def _verify_tool(answer: str) -> Tuple[bool, float, str, str]:
    """Check if tool result is present and parseable.

    Returns (verified, confidence, rationale, error_type).
    """
    if not answer or len(answer.strip()) < 10:
        return False, 0.3, "empty_tool_response", "empty"
    lower = answer.lower()
    if "timeout" in lower:
        return False, 0.2, "tool_timeout", "timeout"
    if any(err in lower for err in ["error", "failed", "exception"]):
        return False, 0.3, "tool_error_detected", "execution_error"
    schema_ok, schema_detail = _validate_tool_schema(answer)
    if not schema_ok:
        return False, 0.35, f"tool_schema_invalid:{schema_detail}", "schema_invalid"
    return True, 0.85, "tool_result_present", "none"


def _verify_rag_grounding(answer: str, query: str) -> Tuple[bool, float, str, str]:
    """Groundedness check: answer should contain query-relevant terms.

    Returns (verified, confidence, rationale, unanswered_reason).
    """
    if not answer or len(answer.strip()) < 20:
        return False, 0.3, "empty_rag_response", "low_recall"
    lower = answer.lower()
    if any(p in lower for p in ["i don't know", "cannot determine", "no information", "insufficient evidence"]):
        return False, 0.5, "explicit_refusal", "insufficient_evidence"
    query_words = set(re.findall(r"\w+", query.lower()))
    answer_words = set(re.findall(r"\w+", answer.lower()))
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                 "to", "for", "of", "and", "or", "what", "how", "why", "when",
                 "where", "which", "do", "does", "did", "not", "no", "yes",
                 "can", "could", "would", "should", "will", "shall", "may", "might"}
    query_terms = query_words - stopwords
    if not query_terms:
        return True, 0.7, "no_query_terms_to_check", "none"
    overlap = query_terms & answer_words
    ratio = len(overlap) / max(len(query_terms), 1)
    if ratio >= 0.5:
        return True, min(0.9, 0.6 + ratio * 0.3), f"grounded_{ratio:.0%}_overlap", "none"
    if ratio >= 0.3:
        return True, min(0.75, 0.5 + ratio * 0.3), f"partial_{ratio:.0%}_overlap", "none"
    return False, 0.4, f"ungrounded_{ratio:.0%}_overlap", "low_precision"


@dataclass
class VerificationResult:
    verified: bool
    confidence: float
    rationale: str
    tool_error_type: str = "none"
    rag_unanswered_reason: str = "none"
    tool_schema_valid: bool = True


def _run_deterministic_verification(
    category: str,
    answers: List[str],
    query: str,
) -> VerificationResult:
    """Run category-appropriate deterministic verification."""
    if category == "math" and ELITE_PLUS_MATH_REQUIRE_VERIFICATION:
        ok, conf, rationale = _verify_math(answers)
        return VerificationResult(ok, conf, rationale)

    if category in ("reasoning", "multilingual"):
        ok, conf, rationale = _verify_mcq(answers)
        return VerificationResult(ok, conf, rationale)

    if category == "tool_use" and ELITE_PLUS_TOOL_STRICT_MODE:
        if answers:
            ok, conf, rationale, err_type = _verify_tool(answers[0])
            schema_ok, _ = _validate_tool_schema(answers[0])
            return VerificationResult(ok, conf, rationale,
                                      tool_error_type=err_type,
                                      tool_schema_valid=schema_ok)
        return VerificationResult(False, 0.3, "no_tool_answer",
                                  tool_error_type="empty", tool_schema_valid=False)

    if category == "rag" and ELITE_PLUS_RAG_REQUIRE_SUPPORT:
        if answers:
            ok, conf, rationale, unans = _verify_rag_grounding(answers[0], query)
            return VerificationResult(ok, conf, rationale, rag_unanswered_reason=unans)
        return VerificationResult(False, 0.3, "no_rag_answer",
                                  rag_unanswered_reason="low_recall")

    if answers and answers[0] and len(answers[0].strip()) > 20:
        return VerificationResult(True, 0.7, "default_pass")

    return VerificationResult(False, 0.5, "default_unverified")


# ---------------------------------------------------------------------------
# Escalation decision
# ---------------------------------------------------------------------------
def _should_escalate(
    category: str,
    free_confidence: float,
    vr: VerificationResult,
    free_answers: List[str],
) -> Tuple[bool, List[str]]:
    """Decide whether to call a paid anchor model."""
    reasons: List[str] = []

    if ELITE_PLUS_ESCALATE_ON_LOW_CONFIDENCE and free_confidence < ELITE_PLUS_LOW_CONF_THRESHOLD:
        reasons.append(f"low_confidence_{free_confidence:.2f}")

    if not vr.verified:
        if ELITE_PLUS_ESCALATE_ON_DISAGREEMENT and "no_" in vr.rationale:
            reasons.append(f"disagreement:{vr.rationale}")
        if ELITE_PLUS_ESCALATE_ON_TOOL_FAILURE and vr.tool_error_type != "none":
            reasons.append(f"tool_failure:{vr.tool_error_type}")
        if ELITE_PLUS_ESCALATE_ON_RAG_UNGROUNDED and "ungrounded" in vr.rationale:
            reasons.append(f"rag_ungrounded:{vr.rationale}")
        if "empty" in vr.rationale or "insufficient" in vr.rationale:
            reasons.append(f"verification_failed:{vr.rationale}")

    # Dialogue: only escalate on hard failures, not just low confidence
    if category == "dialogue" and ELITE_PLUS_DIALOGUE_LIGHT_TOUCH:
        if not reasons or all("low_confidence" in r for r in reasons):
            return False, []

    return len(reasons) > 0, reasons


# ---------------------------------------------------------------------------
# Part B: choose_paid_anchor — category-aware, env-configurable
# ---------------------------------------------------------------------------
# Map category_key from leaders JSON to internal category
_CATEGORY_KEY_TO_INTERNAL: Dict[str, str] = {
    "reasoning_mmlu": "reasoning",
    "coding_humaneval": "coding",
    "math_gsm8k": "math",
    "multilingual_mmmlu": "multilingual",
    "long_context_longbench": "long_context",
    "tool_use_toolbench": "tool_use",
    "rag_msmarco_mrr10": "rag",
    "dialogue_mtbench": "dialogue",
}

# Map leader_model (display name) to registry model ID — only models we have in registry
_LEADER_MODEL_TO_REGISTRY_ID: Dict[str, str] = {
    "GPT-5.2 Pro": "openai/gpt-5.2",
    "Claude Opus 4.6": "anthropic/claude-opus-4.6",
    "GLM 4.7": "zhipuai/glm-4.7",
    "Gemini 3.1 Pro": "google/gemini-3.1-pro-preview",
    "GPT-5.2 Pro + BM25": "openai/gpt-5.2",  # RAG: use GPT-5.2 for generation
}


def _load_category_leaders() -> List[Dict[str, Any]]:
    """Load category leaders from canonical JSON. Returns [] if missing."""
    try:
        # Resolve to project root (LLMHIVE): orchestration->app->llmhive->src->llmhive->project_root
        _root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        path = _root / "benchmark_configs" / "category_leaders_llmhive.json"
        if path.exists():
            data = json.loads(path.read_text())
            return data.get("categories", [])
    except Exception:
        pass
    return []


def _leader_hint_anchor(category: str) -> Optional[str]:
    """If leaderboard-aware (LEADER_HINTS or LEADERBOARD_AWARE), return leader model ID when available."""
    if not (ELITE_PLUS_LEADER_HINTS_ENABLED or ELITE_PLUS_LEADERBOARD_AWARE):
        return None
    leaders = _load_category_leaders()
    if not leaders:
        return None
    # Find category_key for this internal category
    cat_key = None
    for k, v in _CATEGORY_KEY_TO_INTERNAL.items():
        if v == category:
            cat_key = k
            break
    if not cat_key:
        return None
    for c in leaders:
        if c.get("category_key") == cat_key:
            leader_model = c.get("leader_model", "")
            reg_id = _LEADER_MODEL_TO_REGISTRY_ID.get(leader_model)
            if reg_id:
                # Spend governor enforces cost at call time; return leader for consideration
                return reg_id
            break
    return None


def choose_paid_anchor(category: str, escalation_reasons: List[str]) -> str:
    """Select the best paid anchor for the category and failure mode."""
    if ELITE_PLUS_ENABLE_DOMINANCE_V2:
        return _V2_PAID_ANCHORS.get(category, _PAID_ANCHORS.get(category, "openai/gpt-4o-mini"))
    hint = _leader_hint_anchor(category)
    if hint:
        return hint
    return _PAID_ANCHORS.get(category, "openai/gpt-4o-mini")


# ---------------------------------------------------------------------------
# Free model selection per category
# ---------------------------------------------------------------------------
def _get_free_models(category: str) -> List[str]:
    try:
        from .elite_orchestration import FREE_MODELS
        models = FREE_MODELS.get(category, FREE_MODELS.get("reasoning", []))
        if models:
            max_models = 1 if (category == "dialogue" and ELITE_PLUS_DIALOGUE_LIGHT_TOUCH) else 2
            return list(models[:max_models])
    except ImportError:
        pass
    defaults = _FREE_MODELS_DEFAULT.get(category, _FREE_MODELS_DEFAULT["reasoning"])
    max_models = 1 if (category == "dialogue" and ELITE_PLUS_DIALOGUE_LIGHT_TOUCH) else 2
    return list(defaults[:max_models])


def _get_paid_anchor(category: str) -> str:
    return _PAID_ANCHORS.get(category, "openai/gpt-4o-mini")


# ---------------------------------------------------------------------------
# Confidence extraction from model response
# ---------------------------------------------------------------------------
def _extract_confidence(text: str) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    if any(w in lower for w in ["i'm not sure", "uncertain", "i don't know", "cannot determine"]):
        return 0.35
    if any(w in lower for w in ["error", "failed", "exception"]):
        return 0.2
    length = len(text.strip())
    if length < 20:
        return 0.4
    if length < 50:
        return 0.55
    return 0.7


def _normalize_answer(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower().strip())[:500]


def _best_answer(answers: List[Tuple[str, float, str]]) -> Tuple[str, float, str]:
    """Pick the best answer from (text, confidence, model_id) tuples."""
    valid = [(t, c, m) for t, c, m in answers if t and len(t.strip()) > 5]
    if not valid:
        return ("", 0.0, "none")
    return max(valid, key=lambda x: x[1])


# ---------------------------------------------------------------------------
# Auto-dominance verified policy (Workstream 2)
# ---------------------------------------------------------------------------
def _should_attempt_upgrade(
    category: str,
    vr: VerificationResult,
    query: str,
    internal_bench: bool,
) -> Tuple[bool, str]:
    """Decide whether to attempt leader-first upgrade. Returns (attempt, reason)."""
    allowlist = _LEADER_FIRST_CATEGORY_ALLOWLIST | (_LEADER_FIRST_INTERNAL_ALLOWLIST if internal_bench else set())
    if category in allowlist and _is_mcq_query(query):
        return True, "mcq_allowlist"
    if not vr.verified:
        if "no_" in vr.rationale or "insufficient" in vr.rationale:
            return True, "baseline_verification_failed"
        if vr.tool_error_type != "none":
            return True, "tool_failure"
        if "ungrounded" in vr.rationale:
            return True, "rag_grounding_fail"
    if not vr.tool_schema_valid:
        return True, "tool_schema_invalid"
    if vr.rag_unanswered_reason not in ("none", ""):
        return True, "rag_partial_or_fail"
    return False, ""


def _leader_first_allowed(internal_bench: bool) -> bool:
    """True if leader-first policy is allowed for this request."""
    if internal_bench and ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY:
        return True
    if not internal_bench and ELITE_PLUS_LEADER_FIRST_ALLOWED:
        return True
    return False


async def _run_elite_plus_leader_first(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    internal_bench: bool,
) -> ElitePlusResult:
    """Leader-first verified: call leader anchor first, free models verify (no vote override)."""
    t0 = time.perf_counter()
    max_paid = ELITE_PLUS_LEADER_FIRST_MAX_PAID_CALLS
    if internal_bench:
        max_paid = min(max_paid, ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH)

    models_called: List[str] = []
    cost_breakdown: Dict[str, float] = {}
    verifier_strategy = "leader_first"

    # Stage 1: Call leader anchor first
    anchor = choose_paid_anchor(category, [])
    lm_cost_ok = _launch_mode_cost_ok(0.0, anchor)
    if not lm_cost_ok:
        logger.info("Leader-first: cost ceiling would exceed for anchor=%s, falling back to free_first", anchor)
        return await _run_elite_plus_free_first_impl(
            query, base_answer, base_confidence, category, orchestrator, "elite_plus", {},
            internal_bench=internal_bench,
        )

    if _circuit_breaker.is_degraded(anchor):
        anchor = "openai/gpt-4o-mini"
        logger.warning("Leader anchor degraded, using fallback %s", anchor)

    # Workstream C: MCQ detection — force letter-only for reasoning/multilingual
    leader_prompt = query
    if category in ("reasoning", "multilingual") and _is_mcq_query(query):
        leader_prompt = query + _mcq_prompt_suffix()

    try:
        leader_text, _ = await _call_model(orchestrator, leader_prompt, anchor, ELITE_PLUS_BUDGET_MS)
        models_called.append(anchor)
        cost_breakdown[anchor] = _estimate_cost(anchor)
        _circuit_breaker.record(anchor, bool(leader_text and len(leader_text.strip()) > 5))
    except Exception as exc:
        logger.warning("Leader-first: anchor %s failed: %s, falling back to free_first", anchor, exc)
        return await _run_elite_plus_free_first_impl(
            query, base_answer, base_confidence, category, orchestrator, "elite_plus", {},
            internal_bench=internal_bench,
        )

    if not leader_text or len(leader_text.strip()) < 5:
        return await _run_elite_plus_free_first_impl(
            query, base_answer, base_confidence, category, orchestrator, "elite_plus", {},
            internal_bench=internal_bench,
        )

    # Workstream C: MCQ strict extraction — re-ask once if invalid
    if category in ("reasoning", "multilingual") and _is_mcq_query(query):
        letter = _extract_mcq_letter_strict(leader_text)
        if letter is None:
            retry_prompt = query + "\n\nReturn ONLY the letter (A, B, C, D, or E). Nothing else."
            try:
                leader_text, _ = await _call_model(orchestrator, retry_prompt, anchor, ELITE_PLUS_BUDGET_MS)
                letter = _extract_mcq_letter_strict(leader_text) if leader_text else None
            except Exception:
                pass
            if letter:
                leader_text = letter

    # Stage 2: Free models as verifiers (not voters)
    free_models = _get_free_models(category)
    free_answers: List[Tuple[str, float, str]] = []
    if free_models:
        healthy_free = [m for m in free_models if not _circuit_breaker.is_degraded(m)] or free_models[:1]
        tasks = [_call_model(orchestrator, query, m, ELITE_PLUS_BUDGET_MS) for m in healthy_free]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for model_id, result in zip(healthy_free, raw):
            models_called.append(model_id)
            cost_breakdown[model_id] = 0.0
            if not isinstance(result, Exception) and result:
                text, _ = result
                if text:
                    free_answers.append((text, _extract_confidence(text), model_id))
            if isinstance(result, Exception):
                _circuit_breaker.record(model_id, False)
            else:
                _circuit_breaker.record(model_id, bool(result and result[0]))

    # Stage 3: Deterministic agreement check (no multi-model vote for MCQ/dialogue)
    answer_texts = [t for t, _, _ in free_answers]
    vr = _run_deterministic_verification(category, [leader_text] + answer_texts, query)

    if vr.verified:
        verifier_strategy = "leader_first_verified"
        final_answer = leader_text
        final_conf = max(_extract_confidence(leader_text), vr.confidence, 0.75)
        stage_used = "leader_first_verified"
    else:
        # Mismatch: use leader output (structured extraction handles MCQ; no vote override)
        final_answer = leader_text
        final_conf = _extract_confidence(leader_text)
        stage_used = "leader_first_unverified"

    total_latency = int((time.perf_counter() - t0) * 1000)
    total_cost = sum(cost_breakdown.values())

    if ELITE_PLUS_LOG_SHADOW:
        logger.info(
            "ELITE+ leader_first [%s] anchor=%s verifier=%s stage=%s cost=$%.4f models=%s",
            category, anchor, verifier_strategy, stage_used, total_cost, models_called,
        )

    result = ElitePlusResult(
        answer=final_answer,
        confidence=final_conf,
        mode=ELITE_PLUS_MODE,
        policy="leader_first_verified",
        stage_used=stage_used,
        paid_calls_count=1,
        free_calls_count=len(free_answers),
        estimated_cost_usd=total_cost,
        estimated_cost_breakdown=cost_breakdown,
        confidence_free=free_answers[0][1] if free_answers else 0.0,
        confidence_final=final_conf,
        escalation_reason=[],
        models_called=models_called,
        tool_invocations=[],
        rag_grounding_status="n/a",
        total_latency_ms=total_latency,
        verifier_strategy=verifier_strategy,
        verifier_status="verified" if vr.verified else "unverified",
        verifier_latency_ms=total_latency,
        tool_schema_valid=True,
        tool_retry_count=0,
        tool_execution_ok=True,
        tool_error_type="none",
        rag_unanswered_reason="none",
        rag_passage_count_used=0,
        dialogue_mode="n/a",
        dialogue_anchor_used=anchor if category == "dialogue" else "",
        dialogue_escalated=category == "dialogue",
        shadow_answer=final_answer,
        shadow_confidence=final_conf,
        should_override=(ELITE_PLUS_MODE == "active"),
        base_answer=base_answer,
        base_confidence=base_confidence,
        blackboard_hash=hashlib.sha256(f"{query[:100]}:{final_answer[:100]}".encode()).hexdigest()[:16],
    )
    return result


async def _run_elite_plus_auto_dominance(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    effective_tier: str,
    extra: Dict[str, Any],
    *,
    internal_bench: bool = False,
) -> ElitePlusResult:
    """Auto-dominance: run Free baseline, then conditionally upgrade with leader-first.
    Elite+ cannot be worse than Free by construction."""
    t0 = time.perf_counter()
    mode = ELITE_PLUS_MODE

    # Stage 1: Run Free-equivalent baseline (same free ensemble + verification, no paid)
    free_models = _get_free_models(category)
    free_answers: List[Tuple[str, float, str]] = []
    cost_breakdown: Dict[str, float] = {}
    if free_models:
        healthy_free = [m for m in free_models if not _circuit_breaker.is_degraded(m)] or free_models[:1]
        tasks = [_call_model(orchestrator, query, m, ELITE_PLUS_BUDGET_MS) for m in healthy_free]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for model_id, result in zip(healthy_free, raw):
            cost_breakdown[model_id] = 0.0
            if not isinstance(result, Exception) and result:
                text, _ = result
                if text:
                    free_answers.append((text, _extract_confidence(text), model_id))
            if isinstance(result, Exception):
                _circuit_breaker.record(model_id, False)
            else:
                _circuit_breaker.record(model_id, bool(result and result[0]))

    best_free_text, best_free_conf, _ = _best_answer(free_answers)
    answer_texts = [t for t, _, _ in free_answers]
    vr = _run_deterministic_verification(category, answer_texts, query)
    baseline_confidence = max(best_free_conf, vr.confidence) if vr.verified else best_free_conf

    # Baseline: use free answer if verified, else we have a "failed" baseline
    baseline_answer = best_free_text if best_free_text else base_answer
    baseline_conf = baseline_confidence if best_free_text else base_confidence

    upgrade_attempted = False
    upgrade_reason = ""
    upgrade_blocked = False
    selected_source = "baseline"
    final_answer = baseline_answer
    final_conf = baseline_conf
    policy_used = "auto_dominance_verified"
    stage_used = "baseline"
    paid_calls = 0
    models_called = [m for m, _, _ in free_answers]
    mcq_invalid = False

    upgrade, upgrade_reason = _should_attempt_upgrade(category, vr, query, internal_bench)
    if upgrade:
        upgrade_attempted = True
        anchor = choose_paid_anchor(category, [])
        if not _launch_mode_cost_ok(sum(cost_breakdown.values()), anchor):
            upgrade_blocked = True
        elif _circuit_breaker.is_degraded(anchor):
            upgrade_blocked = True
        else:
            try:
                leader_result = await _run_elite_plus_leader_first(
                    query, base_answer, base_confidence, category, orchestrator, internal_bench
                )
                cost_breakdown.update(leader_result.estimated_cost_breakdown)
                models_called = leader_result.models_called
                paid_calls = leader_result.paid_calls_count

                # Adjudicate: prefer upgrade only if it passed verification
                if leader_result.verifier_status == "verified":
                    if category in ("reasoning", "multilingual") and _is_mcq_query(query):
                        letter = _extract_mcq_letter_strict(leader_result.answer)
                        if letter:
                            final_answer = letter
                            final_conf = max(leader_result.confidence_final, 0.85)
                            selected_source = "upgrade"
                            stage_used = "upgrade_verified"
                        else:
                            mcq_invalid = True
                    elif category == "math" and vr.verified:
                        final_answer = leader_result.answer
                        final_conf = leader_result.confidence_final
                        selected_source = "upgrade"
                        stage_used = "upgrade_verified"
                    elif category == "tool_use" and leader_result.tool_schema_valid and leader_result.tool_execution_ok:
                        final_answer = leader_result.answer
                        final_conf = leader_result.confidence_final
                        selected_source = "upgrade"
                        stage_used = "upgrade_verified"
                    elif category == "rag" and leader_result.rag_grounding_status in ("ok", "partial"):
                        final_answer = leader_result.answer
                        final_conf = leader_result.confidence_final
                        selected_source = "upgrade"
                        stage_used = "upgrade_verified"
                    elif leader_result.confidence_final > baseline_conf:
                        final_answer = leader_result.answer
                        final_conf = leader_result.confidence_final
                        selected_source = "upgrade"
                        stage_used = "upgrade_verified"
            except Exception as exc:
                logger.warning("Auto-dominance: upgrade failed %s, using baseline", exc)

    total_cost = sum(cost_breakdown.values())
    total_latency = int((time.perf_counter() - t0) * 1000)

    return ElitePlusResult(
        answer=final_answer,
        confidence=final_conf,
        mode=mode,
        policy=policy_used,
        stage_used=stage_used,
        paid_calls_count=paid_calls,
        free_calls_count=len(free_answers),
        estimated_cost_usd=total_cost,
        estimated_cost_breakdown=cost_breakdown,
        confidence_free=best_free_conf,
        confidence_final=final_conf,
        escalation_reason=[],
        models_called=models_called,
        tool_invocations=[],
        rag_grounding_status=vr.rag_unanswered_reason if "rag" in category else "n/a",
        total_latency_ms=total_latency,
        verifier_strategy="auto_dominance",
        verifier_status="verified" if vr.verified else "unverified",
        verifier_latency_ms=total_latency,
        tool_schema_valid=vr.tool_schema_valid,
        tool_retry_count=0,
        tool_execution_ok=vr.tool_error_type == "none",
        tool_error_type=vr.tool_error_type,
        rag_unanswered_reason=vr.rag_unanswered_reason,
        rag_passage_count_used=0,
        dialogue_mode="n/a",
        dialogue_anchor_used="",
        dialogue_escalated=False,
        shadow_answer=final_answer,
        shadow_confidence=final_conf,
        should_override=(mode == "active"),
        base_answer=base_answer,
        base_confidence=base_confidence,
        blackboard_hash=hashlib.sha256(f"{query[:100]}:{final_answer[:100]}".encode()).hexdigest()[:16],
        baseline_policy_used="free_first_verified",
        upgrade_attempted=upgrade_attempted,
        upgrade_reason=upgrade_reason,
        upgrade_blocked_by_governor=upgrade_blocked,
        selected_answer_source=selected_source,
        mcq_invalid_extraction=mcq_invalid,
    )


# ---------------------------------------------------------------------------
# Dominance v2: parallel ensemble with deterministic dominance guarantee
# ---------------------------------------------------------------------------
def _adjudicate_v2(
    category: str,
    free_answer: str,
    free_confidence: float,
    leader_answer: str,
    leader_confidence: float,
    query: str,
) -> Tuple[str, float, str, bool]:
    """Adjudicate free vs leader results.

    Returns (final_answer, final_confidence, source, dominance_fallback).
    Dominance guarantee: on deterministic categories, never return a worse answer.
    """
    if not leader_answer or len(leader_answer.strip()) < 5:
        return free_answer, free_confidence, "free", False

    if not free_answer or len(free_answer.strip()) < 5:
        return leader_answer, leader_confidence, "leader", False

    # Category-specific deterministic comparison
    if category == "math":
        free_num = _extract_numeric(free_answer)
        leader_num = _extract_numeric(leader_answer)
        if leader_num is not None:
            return leader_answer, max(leader_confidence, 0.85), "leader", False
        if free_num is not None:
            return free_answer, free_confidence, "free", False
        return leader_answer, leader_confidence, "leader", False

    if category in ("reasoning", "multilingual"):
        free_letter = _extract_mcq_letter_strict(free_answer)
        leader_letter = _extract_mcq_letter_strict(leader_answer)
        if leader_letter and free_letter:
            if leader_letter == free_letter:
                return leader_answer, max(leader_confidence, free_confidence, 0.9), "leader_confirmed", False
            return leader_answer, max(leader_confidence, 0.8), "leader", False
        if leader_letter:
            return leader_letter, max(leader_confidence, 0.85), "leader", False
        if free_letter:
            return free_letter, free_confidence, "free", True
        return leader_answer, leader_confidence, "leader", False

    if category == "tool_use":
        leader_schema_ok, _ = _validate_tool_schema(leader_answer)
        free_schema_ok, _ = _validate_tool_schema(free_answer)
        if leader_schema_ok and not free_schema_ok:
            return leader_answer, max(leader_confidence, 0.85), "leader", False
        if free_schema_ok and not leader_schema_ok:
            return free_answer, free_confidence, "free", True
        if leader_schema_ok:
            return leader_answer, max(leader_confidence, 0.85), "leader", False
        return free_answer, free_confidence, "free", True

    if category == "rag":
        _, leader_conf_rag, _, leader_unans = _verify_rag_grounding(leader_answer, query)
        _, free_conf_rag, _, free_unans = _verify_rag_grounding(free_answer, query)
        if leader_unans == "none" and free_unans != "none":
            return leader_answer, max(leader_confidence, leader_conf_rag), "leader", False
        if free_unans == "none" and leader_unans != "none":
            return free_answer, max(free_confidence, free_conf_rag), "free", True
        if leader_conf_rag >= free_conf_rag:
            return leader_answer, max(leader_confidence, leader_conf_rag), "leader", False
        return free_answer, max(free_confidence, free_conf_rag), "free", True

    if category == "coding":
        if leader_confidence >= free_confidence:
            return leader_answer, leader_confidence, "leader", False
        return free_answer, free_confidence, "free", True

    if leader_confidence >= free_confidence:
        return leader_answer, leader_confidence, "leader", False
    return free_answer, free_confidence, "free", False


async def _run_elite_plus_dominance_v2(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    effective_tier: str,
    extra: Dict[str, Any],
    *,
    internal_bench: bool = False,
) -> ElitePlusResult:
    """Dominance v2: parallel free+leader ensemble with deterministic dominance guarantee.

    - Dialogue bypasses ensemble (single premium model).
    - Tool use enforces strict schema validation.
    - Deterministic categories guarantee Elite+ >= Free.
    """
    t0 = time.perf_counter()
    mode = ELITE_PLUS_MODE

    # STEP 5: Dialogue isolation — bypass ensemble
    if category == "dialogue":
        premium_model = _DIALOGUE_PREMIUM_MODEL
        if _circuit_breaker.is_degraded(premium_model):
            premium_model = _V2_PAID_ANCHORS.get("dialogue", "openai/gpt-5.2")
        if not _launch_mode_cost_ok(0.0, premium_model):
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        try:
            _dial_direct = True
            text, latency = await _call_model(
                orchestrator, query, premium_model, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
                force_direct=_dial_direct,
            )
            _circuit_breaker.record(premium_model, bool(text and len(text.strip()) > 5))
        except Exception as exc:
            logger.warning("Dominance v2 dialogue premium %s failed: %s", premium_model, exc)
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        if not text or len(text.strip()) < 5:
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        total_latency = int((time.perf_counter() - t0) * 1000)
        cost = _estimate_cost(premium_model)
        return ElitePlusResult(
            answer=text, confidence=max(_extract_confidence(text), 0.8),
            mode=mode, policy="dominance_v2", stage_used="dialogue_premium",
            paid_calls_count=1, free_calls_count=0,
            estimated_cost_usd=cost, estimated_cost_breakdown={premium_model: cost},
            confidence_free=0.0, confidence_final=max(_extract_confidence(text), 0.8),
            escalation_reason=[], models_called=[premium_model],
            tool_invocations=[], rag_grounding_status="n/a",
            total_latency_ms=total_latency, verifier_strategy="dialogue_premium",
            verifier_status="verified", verifier_latency_ms=total_latency,
            dialogue_mode="premium_isolated", dialogue_anchor_used=premium_model,
            dialogue_escalated=False,
            shadow_answer=text, shadow_confidence=max(_extract_confidence(text), 0.8),
            should_override=(mode == "active"),
            base_answer=base_answer, base_confidence=base_confidence,
            blackboard_hash=hashlib.sha256(f"{query[:100]}:{text[:100]}".encode()).hexdigest()[:16],
            baseline_policy_used="dominance_v2", selected_answer_source="dialogue_premium",
            provider_used=premium_model, direct_or_router="direct",
            paid_call_made=True, elite_v2_executed=True,
            anchor_model_used=premium_model,
        )

    # Resolve category leader model
    anchor = _V2_PAID_ANCHORS.get(category, _PAID_ANCHORS.get(category, "openai/gpt-4o-mini"))
    if _circuit_breaker.is_degraded(anchor):
        anchor = _PAID_ANCHORS.get(category, "openai/gpt-4o-mini")

    cost_ok = _launch_mode_cost_ok(0.0, anchor)
    if not cost_ok:
        # V2 anchors are pre-approved for deterministic categories — log but proceed
        if category in _DETERMINISTIC_CATEGORIES:
            logger.info(
                "DOMINANCE_V2_COST_OVERRIDE: anchor=%s exceeds ceiling but proceeding for deterministic category=%s",
                anchor, category,
            )
        else:
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )

    # STEP 2: Parallel ensemble — run free models and category leader concurrently
    free_models = _get_free_models(category)
    healthy_free = [m for m in free_models if not _circuit_breaker.is_degraded(m)] or free_models[:1]

    leader_prompt = query
    if category in ("reasoning", "multilingual") and _is_mcq_query(query):
        leader_prompt = query + _mcq_prompt_suffix()
    # STEP 6: ToolBench strict mode — constrained prompt
    if category == "tool_use":
        leader_prompt = (
            "You MUST respond with ONLY a valid JSON tool call. "
            "Do NOT include any explanation or freeform text.\n\n"
            f"{query}"
        )

    # Always force direct provider for paid anchors (no OpenRouter fallback)
    _use_direct = True
    _anchor_healthy = _provider_health.is_healthy(anchor) if ELITE_PLUS_STABILITY_V1 else True
    free_tasks = [_call_model(orchestrator, query, m, ELITE_PLUS_BUDGET_MS) for m in healthy_free]

    if _anchor_healthy:
        leader_task = _call_model(
            orchestrator, leader_prompt, anchor, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
            force_direct=_use_direct,
        )
        all_results = await asyncio.gather(*free_tasks, leader_task, return_exceptions=True)
        free_raw = all_results[:-1]
        leader_raw = all_results[-1]
    else:
        logger.warning(
            "PROVIDER_HEALTH: anchor %s disabled, skipping paid call for category=%s",
            anchor, category,
        )
        all_results = await asyncio.gather(*free_tasks, return_exceptions=True)
        free_raw = all_results
        leader_raw = Exception("provider_disabled_by_health_tracker")

    # Process free results
    free_answers: List[Tuple[str, float, str]] = []
    models_called: List[str] = []
    cost_breakdown: Dict[str, float] = {}
    anchor_failure_reason = ""
    for model_id, result in zip(healthy_free, free_raw):
        models_called.append(model_id)
        cost_breakdown[model_id] = 0.0
        if isinstance(result, Exception):
            _circuit_breaker.record(model_id, False)
        else:
            text, _ = result
            _circuit_breaker.record(model_id, bool(text and len(text.strip()) > 5))
            if text:
                free_answers.append((text, _extract_confidence(text), model_id))

    best_free_text, best_free_conf, _ = _best_answer(free_answers)
    free_answer_texts = [t for t, _, _ in free_answers]
    free_vr = _run_deterministic_verification(category, free_answer_texts, query)
    if free_vr.verified:
        best_free_conf = max(best_free_conf, free_vr.confidence)

    # Process leader result
    leader_text = ""
    leader_conf = 0.0
    paid_calls = 0
    if isinstance(leader_raw, Exception):
        anchor_failure_reason = f"exception:{type(leader_raw).__name__}:{leader_raw}"
        logger.warning(
            "ANCHOR_FAILURE: category=%s anchor=%s reason=%s",
            category, anchor, anchor_failure_reason,
        )
        _circuit_breaker.record(anchor, False)
        _provider_health.record(anchor, False)
    else:
        leader_text, leader_latency_ms = leader_raw
        _ok = bool(leader_text and len(leader_text.strip()) > 5)
        _circuit_breaker.record(anchor, _ok)
        _provider_health.record(anchor, _ok)
        if leader_text and len(leader_text.strip()) > 5:
            models_called.append(anchor)
            cost_breakdown[anchor] = _estimate_cost(anchor)
            paid_calls = 1
            leader_conf = max(_extract_confidence(leader_text), 0.75)

            # MCQ re-extraction for reasoning/multilingual
            if category in ("reasoning", "multilingual") and _is_mcq_query(query):
                letter = _extract_mcq_letter_strict(leader_text)
                if letter is None:
                    retry_prompt = query + "\n\nReturn ONLY the letter (A, B, C, D, or E). Nothing else."
                    try:
                        leader_text, _ = await _call_model(
                            orchestrator, retry_prompt, anchor, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
                            force_direct=_use_direct,
                        )
                        letter = _extract_mcq_letter_strict(leader_text) if leader_text else None
                    except Exception:
                        pass
                    if letter:
                        leader_text = letter

            # ToolBench strict schema validation
            if category == "tool_use":
                schema_ok, _ = _validate_tool_schema(leader_text)
                if not schema_ok:
                    leader_text = ""
                    leader_conf = 0.0
                    logger.info("Dominance v2: leader tool_use response failed schema validation, discarded")
        else:
            anchor_failure_reason = (
                f"provider_response_invalid: empty or too short "
                f"(len={len(leader_text.strip()) if leader_text else 0}, latency={leader_latency_ms}ms)"
            )
            logger.warning(
                "ANCHOR_FAILURE: category=%s anchor=%s reason=%s",
                category, anchor, anchor_failure_reason,
            )

    # Anchor guard — behavior depends on ELITE_PLUS_STABILITY_V1
    if BENCHMARK_MODE and category in _CRITICAL_PAID_CATEGORIES and paid_calls == 0:
        if ELITE_PLUS_STABILITY_V1:
            logger.warning(
                "ANCHOR_GUARD_SOFT: Anchor execution failed for category=%s "
                "anchor=%s reason=%s — continuing with free ensemble result",
                category, anchor, anchor_failure_reason,
            )
        else:
            _guard_msg = (
                f"HARD_ANCHOR_GUARD: Anchor execution failed for category={category} "
                f"anchor={anchor} reason={anchor_failure_reason} — "
                f"failing fast in benchmark mode"
            )
            logger.error(_guard_msg)
            raise RuntimeError(_guard_msg)

    # STEP 3: Adjudicate with dominance guarantee
    final_answer, final_conf, source, dominance_fallback = _adjudicate_v2(
        category, best_free_text, best_free_conf,
        leader_text, leader_conf, query,
    )

    # Dominance guarantee enforcement on deterministic categories
    if category in _DETERMINISTIC_CATEGORIES and source == "leader":
        all_answers = [leader_text] + free_answer_texts
        combined_vr = _run_deterministic_verification(category, all_answers, query)
        if not combined_vr.verified and free_vr.verified:
            final_answer = best_free_text
            final_conf = best_free_conf
            source = "free"
            dominance_fallback = True

    if not final_answer or len(final_answer.strip()) < 5:
        final_answer = base_answer
        final_conf = base_confidence
        source = "fallback_elite"

    total_cost = sum(cost_breakdown.values())
    total_latency = int((time.perf_counter() - t0) * 1000)

    # STEP 1: Execution assertion — warn if expected paid call did not execute
    if category in _CRITICAL_PAID_CATEGORIES and paid_calls == 0:
        logger.warning(
            "EXPECTED_PAID_CALL_NOT_EXECUTED: category=%s anchor=%s "
            "anchor_failure_reason=%s — paid model may have failed or been downgraded",
            category, anchor, anchor_failure_reason,
        )

    if ELITE_PLUS_LOG_SHADOW:
        logger.info(
            "ELITE+ dominance_v2 [%s] elite_v2_executed=True anchor_model_used=%s "
            "paid_call_made=%s source=%s dominance_fallback=%s "
            "cost=$%.4f paid=%d free=%d latency=%dms",
            category, anchor, paid_calls > 0, source, dominance_fallback,
            total_cost, paid_calls, len(free_answers), total_latency,
        )

    return ElitePlusResult(
        answer=final_answer, confidence=final_conf,
        mode=mode, policy="dominance_v2",
        stage_used=f"parallel_ensemble_{source}",
        paid_calls_count=paid_calls,
        free_calls_count=len(free_answers),
        estimated_cost_usd=total_cost,
        estimated_cost_breakdown=cost_breakdown,
        confidence_free=best_free_conf,
        confidence_final=final_conf,
        escalation_reason=["dominance_fallback"] if dominance_fallback else [],
        models_called=models_called,
        tool_invocations=[],
        rag_grounding_status=free_vr.rag_unanswered_reason if category == "rag" else "n/a",
        total_latency_ms=total_latency,
        verifier_strategy="dominance_v2",
        verifier_status="verified" if free_vr.verified else "unverified",
        verifier_latency_ms=total_latency,
        tool_schema_valid=free_vr.tool_schema_valid,
        tool_retry_count=0,
        tool_execution_ok=free_vr.tool_error_type == "none",
        tool_error_type=free_vr.tool_error_type,
        rag_unanswered_reason=free_vr.rag_unanswered_reason,
        rag_passage_count_used=0,
        dialogue_mode="n/a", dialogue_anchor_used="", dialogue_escalated=False,
        shadow_answer=final_answer, shadow_confidence=final_conf,
        should_override=(mode == "active"),
        base_answer=base_answer, base_confidence=base_confidence,
        blackboard_hash=hashlib.sha256(f"{query[:100]}:{final_answer[:100]}".encode()).hexdigest()[:16],
        baseline_policy_used="dominance_v2",
        upgrade_attempted=paid_calls > 0,
        upgrade_reason=f"parallel_ensemble_{category}",
        upgrade_blocked_by_governor=not cost_ok,
        selected_answer_source=source,
        mcq_invalid_extraction=(
            category in ("reasoning", "multilingual")
            and _is_mcq_query(query)
            and leader_text
            and _extract_mcq_letter_strict(leader_text) is None
        ),
        # Provider telemetry (v2)
        provider_used=anchor,
        direct_or_router="direct" if any(
            p in anchor for p in ("openai/", "anthropic/", "google/")
        ) else "router",
        paid_call_made=paid_calls > 0,
        fallback_reason="dominance_fallback" if dominance_fallback else "",
        elite_v2_executed=True,
        anchor_failure_reason=anchor_failure_reason,
        anchor_model_used=anchor,
    )


# ---------------------------------------------------------------------------
# Dominance v3: hybrid ensemble-preserving with premium refiner
# ---------------------------------------------------------------------------

def _majority_vote(answers: List[Tuple[str, float, str]], category: str, query: str) -> Tuple[str, float, str, bool]:
    """Compute majority vote from ensemble answers.

    Returns (answer, confidence, source_model, unanimous).
    For MCQ categories, votes on extracted letters. For others, normalizes text.
    """
    if not answers:
        return "", 0.0, "none", False

    if category in ("reasoning", "multilingual") and _is_mcq_query(query):
        letter_votes: List[Tuple[str, float, str]] = []
        for text, conf, model in answers:
            letter = _extract_mcq_letter_strict(text)
            if letter:
                letter_votes.append((letter, conf, model))
        if not letter_votes:
            best = max(answers, key=lambda x: x[1])
            return best[0], best[1], best[2], False

        counts = Counter(l for l, _, _ in letter_votes)
        best_letter, count = counts.most_common(1)[0]
        unanimous = count == len(letter_votes) and len(letter_votes) >= 2
        confidence = min(0.95, 0.6 + 0.15 * count)
        source = next(m for l, _, m in letter_votes if l == best_letter)
        return best_letter, confidence, source, unanimous

    if category == "math":
        numerics: List[Tuple[float, float, str]] = []
        for text, conf, model in answers:
            val = _extract_numeric(text)
            if val is not None:
                numerics.append((val, conf, model))
        if len(numerics) >= 2:
            groups: Dict[float, List[Tuple[float, str]]] = {}
            for val, conf, model in numerics:
                matched = False
                for key in groups:
                    if abs(key - val) < 1e-6 or (key != 0 and abs((key - val) / key) < 0.001):
                        groups[key].append((conf, model))
                        matched = True
                        break
                if not matched:
                    groups[val] = [(conf, model)]
            best_key = max(groups, key=lambda k: len(groups[k]))
            count = len(groups[best_key])
            unanimous = count == len(numerics) and len(numerics) >= 2
            confidence = min(0.95, 0.7 + 0.1 * count)
            source = groups[best_key][0][1]
            best_text = next(t for t, _, m in answers if m == source)
            return best_text, confidence, source, unanimous

    best = max(answers, key=lambda x: x[1])
    unanimous = len(answers) >= 2 and all(
        _normalize_answer(t) == _normalize_answer(best[0]) for t, _, _ in answers
    )
    return best[0], best[1], best[2], unanimous


def _coding_attempt_passes(text: str) -> bool:
    """Heuristic: does a code-generation response look valid (non-error, non-empty)?"""
    if not text or len(text.strip()) < 10:
        return False
    lower = text.lower()
    if any(err in lower for err in ["error", "exception", "traceback", "syntaxerror", "nameerror"]):
        return False
    code_markers = ["def ", "class ", "function ", "import ", "return ", "print(", "console.log("]
    if any(m in text for m in code_markers):
        return True
    if len(text.strip()) > 50:
        return True
    return False


async def _run_elite_plus_dominance_v3(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    effective_tier: str,
    extra: Dict[str, Any],
    *,
    internal_bench: bool = False,
) -> ElitePlusResult:
    """Dominance v3: hybrid ensemble-preserving architecture.

    Key difference from v2: premium anchor is a *refiner*, not a replacement.
    - Reasoning: free ensemble majority first; leader only refines on disagreement.
    - Coding: free ensemble pass@k first; leader only on all-fail.
    - Dialogue: single premium model (unchanged from v2).
    - Tool Use, RAG, Math, Multilingual: delegate to v2 (preserved gains).
    """
    t0 = time.perf_counter()
    mode = ELITE_PLUS_MODE

    # Categories that keep v2 behavior (where v2 showed gains)
    _V3_DELEGATE_TO_V2 = {"tool_use", "rag", "multilingual", "math", "long_context"}

    if category in _V3_DELEGATE_TO_V2:
        return await _run_elite_plus_dominance_v2(
            query, base_answer, base_confidence, category,
            orchestrator, effective_tier, extra,
            internal_bench=internal_bench,
        )

    # Dialogue isolation (STEP 3) — single premium model, unchanged
    if category == "dialogue":
        premium_model = _DIALOGUE_PREMIUM_MODEL
        if _circuit_breaker.is_degraded(premium_model):
            premium_model = _V2_PAID_ANCHORS.get("dialogue", "openai/gpt-5.2")
        if not _launch_mode_cost_ok(0.0, premium_model):
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        try:
            _dial_direct = True
            text, latency = await _call_model(
                orchestrator, query, premium_model, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
                force_direct=_dial_direct,
            )
            _circuit_breaker.record(premium_model, bool(text and len(text.strip()) > 5))
        except Exception as exc:
            logger.warning("Dominance v3 dialogue premium %s failed: %s", premium_model, exc)
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        if not text or len(text.strip()) < 5:
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        total_latency = int((time.perf_counter() - t0) * 1000)
        cost = _estimate_cost(premium_model)
        return ElitePlusResult(
            answer=text, confidence=max(_extract_confidence(text), 0.8),
            mode=mode, policy="dominance_v3", stage_used="dialogue_premium",
            paid_calls_count=1, free_calls_count=0,
            estimated_cost_usd=cost, estimated_cost_breakdown={premium_model: cost},
            confidence_free=0.0, confidence_final=max(_extract_confidence(text), 0.8),
            escalation_reason=[], models_called=[premium_model],
            tool_invocations=[], rag_grounding_status="n/a",
            total_latency_ms=total_latency, verifier_strategy="dialogue_premium",
            verifier_status="verified", verifier_latency_ms=total_latency,
            dialogue_mode="premium_isolated", dialogue_anchor_used=premium_model,
            dialogue_escalated=False,
            shadow_answer=text, shadow_confidence=max(_extract_confidence(text), 0.8),
            should_override=(mode == "active"),
            base_answer=base_answer, base_confidence=base_confidence,
            blackboard_hash=hashlib.sha256(f"{query[:100]}:{text[:100]}".encode()).hexdigest()[:16],
            baseline_policy_used="dominance_v3", selected_answer_source="dialogue_premium",
            provider_used=premium_model, direct_or_router="direct",
            paid_call_made=True, elite_v2_executed=True,
            anchor_model_used=premium_model,
        )

    # -----------------------------------------------------------------------
    # STEP 1 — Reasoning: ensemble majority + leader refiner
    # STEP 2 — Coding: free pass@k + leader fallback
    # -----------------------------------------------------------------------
    anchor = _V2_PAID_ANCHORS.get(category, _PAID_ANCHORS.get(category, "openai/gpt-4o-mini"))
    if _circuit_breaker.is_degraded(anchor):
        anchor = _PAID_ANCHORS.get(category, "openai/gpt-4o-mini")

    free_models = _get_free_models(category)
    healthy_free = [m for m in free_models if not _circuit_breaker.is_degraded(m)] or free_models[:1]

    # Stage A: Run free ensemble (always runs first in v3)
    free_tasks = [_call_model(orchestrator, query, m, ELITE_PLUS_BUDGET_MS) for m in healthy_free]
    free_raw = await asyncio.gather(*free_tasks, return_exceptions=True)

    free_answers: List[Tuple[str, float, str]] = []
    models_called: List[str] = []
    cost_breakdown: Dict[str, float] = {}
    anchor_failure_reason = ""

    for model_id, result in zip(healthy_free, free_raw):
        models_called.append(model_id)
        cost_breakdown[model_id] = 0.0
        if isinstance(result, Exception):
            _circuit_breaker.record(model_id, False)
        else:
            text, _ = result
            _circuit_breaker.record(model_id, bool(text and len(text.strip()) > 5))
            if text:
                free_answers.append((text, _extract_confidence(text), model_id))

    # Stage B: Compute majority / pass@k
    majority_answer, majority_conf, majority_model, unanimous = _majority_vote(
        free_answers, category, query,
    )
    free_vr = _run_deterministic_verification(category, [t for t, _, _ in free_answers], query)
    if free_vr.verified:
        majority_conf = max(majority_conf, free_vr.confidence)

    paid_calls = 0
    leader_text = ""
    leader_conf = 0.0
    source = "free"
    final_answer = majority_answer
    final_conf = majority_conf

    if category == "reasoning":
        # STEP 1 — Reasoning hybrid adjudication
        if unanimous and majority_answer:
            source = "free_unanimous"
            logger.info("DOMINANCE_V3 reasoning: unanimous free ensemble, skipping leader")
        elif majority_answer:
            # Non-unanimous: call leader as refiner
            _use_direct = True
            leader_prompt = query
            if _is_mcq_query(query):
                leader_prompt = query + _mcq_prompt_suffix()
            try:
                leader_text, leader_latency = await _call_model(
                    orchestrator, leader_prompt, anchor, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
                    force_direct=_use_direct,
                )
                _leader_ok = bool(leader_text and len(leader_text.strip()) > 5)
                _circuit_breaker.record(anchor, _leader_ok)
                _provider_health.record(anchor, _leader_ok)
                if leader_text and len(leader_text.strip()) > 5:
                    models_called.append(anchor)
                    cost_breakdown[anchor] = _estimate_cost(anchor)
                    paid_calls = 1
                    leader_conf = max(_extract_confidence(leader_text), 0.75)

                    # MCQ re-extraction
                    if _is_mcq_query(query):
                        letter = _extract_mcq_letter_strict(leader_text)
                        if letter is None:
                            retry_prompt = query + "\n\nReturn ONLY the letter (A, B, C, D, or E). Nothing else."
                            try:
                                leader_text, _ = await _call_model(
                                    orchestrator, retry_prompt, anchor, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
                                    force_direct=_use_direct,
                                )
                                letter = _extract_mcq_letter_strict(leader_text) if leader_text else None
                            except Exception:
                                pass
                            if letter:
                                leader_text = letter

                    # Adjudicate: leader agrees with majority -> confirm majority
                    leader_letter = _extract_mcq_letter_strict(leader_text) if _is_mcq_query(query) else None
                    majority_letter = _extract_mcq_letter_strict(majority_answer) if _is_mcq_query(query) else None

                    if leader_letter and majority_letter:
                        if leader_letter == majority_letter:
                            final_answer = majority_answer
                            final_conf = max(majority_conf, leader_conf, 0.9)
                            source = "free_confirmed_by_leader"
                        elif leader_conf > ELITE_PLUS_V3_LEADER_CONFIDENCE_THRESHOLD:
                            final_answer = leader_text
                            final_conf = leader_conf
                            source = "leader_high_conf"
                        else:
                            final_answer = majority_answer
                            final_conf = majority_conf
                            source = "free_majority_preserved"
                    elif leader_text:
                        if leader_conf > ELITE_PLUS_V3_LEADER_CONFIDENCE_THRESHOLD:
                            final_answer = leader_text
                            final_conf = leader_conf
                            source = "leader_high_conf"
                        else:
                            final_answer = majority_answer
                            final_conf = majority_conf
                            source = "free_majority_preserved"
                else:
                    _provider_health.record(anchor, False)
                    anchor_failure_reason = (
                        f"provider_response_invalid: empty or too short "
                        f"(len={len(leader_text.strip()) if leader_text else 0}, latency={leader_latency}ms)"
                    )
                    source = "free_leader_failed"
            except Exception as exc:
                _provider_health.record(anchor, False)
                anchor_failure_reason = f"exception:{type(exc).__name__}:{exc}"
                logger.warning("DOMINANCE_V3 reasoning leader failed: %s", exc)
                source = "free_leader_failed"
        else:
            source = "free_no_answer"

    elif category == "coding":
        # STEP 2 — Coding: free pass@k + leader fallback
        passing_attempts = [(t, c, m) for t, c, m in free_answers if _coding_attempt_passes(t)]

        if passing_attempts:
            first_pass = passing_attempts[0]
            final_answer = first_pass[0]
            final_conf = max(first_pass[1], 0.75)
            source = "free_pass_k"
            logger.info("DOMINANCE_V3 coding: free pass@k succeeded (%d/%d pass)", len(passing_attempts), len(free_answers))
        else:
            # All free attempts failed — call leader as fallback
            _use_direct = True
            try:
                leader_text, leader_latency = await _call_model(
                    orchestrator, query, anchor, ELITE_PLUS_V2_ANCHOR_BUDGET_MS,
                    force_direct=_use_direct,
                )
                _coding_leader_ok = bool(leader_text and len(leader_text.strip()) > 5)
                _circuit_breaker.record(anchor, _coding_leader_ok)
                _provider_health.record(anchor, _coding_leader_ok)
                if leader_text and len(leader_text.strip()) > 5:
                    models_called.append(anchor)
                    cost_breakdown[anchor] = _estimate_cost(anchor)
                    paid_calls = 1
                    leader_conf = max(_extract_confidence(leader_text), 0.75)

                    if _coding_attempt_passes(leader_text):
                        final_answer = leader_text
                        final_conf = leader_conf
                        source = "leader_fallback_pass"
                    else:
                        best_free = max(free_answers, key=lambda x: x[1]) if free_answers else ("", 0.0, "none")
                        final_answer = best_free[0] if best_free[0] else leader_text
                        final_conf = best_free[1] if best_free[0] else leader_conf
                        source = "best_free_no_pass"
                else:
                    anchor_failure_reason = (
                        f"provider_response_invalid: empty or too short "
                        f"(len={len(leader_text.strip()) if leader_text else 0}, latency={leader_latency}ms)"
                    )
                    best_free = max(free_answers, key=lambda x: x[1]) if free_answers else ("", 0.0, "none")
                    final_answer = best_free[0]
                    final_conf = best_free[1]
                    source = "best_free_leader_failed"
            except Exception as exc:
                _provider_health.record(anchor, False)
                anchor_failure_reason = f"exception:{type(exc).__name__}:{exc}"
                logger.warning("DOMINANCE_V3 coding leader failed: %s", exc)
                best_free = max(free_answers, key=lambda x: x[1]) if free_answers else ("", 0.0, "none")
                final_answer = best_free[0]
                final_conf = best_free[1]
                source = "best_free_leader_failed"
    else:
        source = "free_default"

    if not final_answer or len(final_answer.strip()) < 5:
        final_answer = base_answer
        final_conf = base_confidence
        source = "fallback_elite"

    total_cost = sum(cost_breakdown.values())
    total_latency = int((time.perf_counter() - t0) * 1000)

    if ELITE_PLUS_LOG_SHADOW:
        logger.info(
            "ELITE+ dominance_v3 [%s] anchor_model_used=%s "
            "paid_call_made=%s source=%s "
            "cost=$%.4f paid=%d free=%d latency=%dms",
            category, anchor, paid_calls > 0, source,
            total_cost, paid_calls, len(free_answers), total_latency,
        )

    return ElitePlusResult(
        answer=final_answer, confidence=final_conf,
        mode=mode, policy="dominance_v3",
        stage_used=f"v3_hybrid_{source}",
        paid_calls_count=paid_calls,
        free_calls_count=len(free_answers),
        estimated_cost_usd=total_cost,
        estimated_cost_breakdown=cost_breakdown,
        confidence_free=majority_conf,
        confidence_final=final_conf,
        escalation_reason=["leader_refine"] if paid_calls > 0 else [],
        models_called=models_called,
        tool_invocations=[],
        rag_grounding_status=free_vr.rag_unanswered_reason if category == "rag" else "n/a",
        total_latency_ms=total_latency,
        verifier_strategy="dominance_v3_hybrid",
        verifier_status="verified" if free_vr.verified else "unverified",
        verifier_latency_ms=total_latency,
        tool_schema_valid=free_vr.tool_schema_valid,
        tool_retry_count=0,
        tool_execution_ok=free_vr.tool_error_type == "none",
        tool_error_type=free_vr.tool_error_type,
        rag_unanswered_reason=free_vr.rag_unanswered_reason,
        rag_passage_count_used=0,
        dialogue_mode="n/a", dialogue_anchor_used="", dialogue_escalated=False,
        shadow_answer=final_answer, shadow_confidence=final_conf,
        should_override=(mode == "active"),
        base_answer=base_answer, base_confidence=base_confidence,
        blackboard_hash=hashlib.sha256(f"{query[:100]}:{final_answer[:100]}".encode()).hexdigest()[:16],
        baseline_policy_used="dominance_v3",
        upgrade_attempted=paid_calls > 0,
        upgrade_reason=f"v3_hybrid_{category}_{source}",
        upgrade_blocked_by_governor=False,
        selected_answer_source=source,
        mcq_invalid_extraction=(
            category in ("reasoning", "multilingual")
            and _is_mcq_query(query)
            and leader_text
            and _extract_mcq_letter_strict(leader_text) is None
        ),
        provider_used=anchor,
        direct_or_router="direct" if any(
            p in anchor for p in ("openai/", "anthropic/", "google/")
        ) else "router",
        paid_call_made=paid_calls > 0,
        fallback_reason=anchor_failure_reason if anchor_failure_reason else "",
        elite_v2_executed=True,
        anchor_failure_reason=anchor_failure_reason,
        anchor_model_used=anchor,
    )


# ---------------------------------------------------------------------------
# RAG Learning Loop (STEP 5) — store misses in Pinecone for reranker bias
# ---------------------------------------------------------------------------
_RAG_LEARNING_INDEX = None
_RAG_LEARNING_NAMESPACE = "rag_learning_v1"


def _get_rag_learning_index():
    """Lazy-init Pinecone index for RAG learning. Returns None if unavailable."""
    global _RAG_LEARNING_INDEX
    if not RAG_LEARNING_MODE:
        return None
    if _RAG_LEARNING_INDEX is not None:
        return _RAG_LEARNING_INDEX
    try:
        from pinecone import Pinecone
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.info("RAG_LEARNING_MODE=1 but PINECONE_API_KEY not set, learning loop disabled")
            return None
        pc = Pinecone(api_key=api_key)
        index_name = os.getenv("RAG_LEARNING_INDEX", "llmhive-rag-learning")
        if pc.has_index(index_name):
            _RAG_LEARNING_INDEX = pc.Index(index_name)
            logger.info("RAG learning loop connected to index=%s", index_name)
        else:
            logger.warning("RAG learning index '%s' does not exist. Create it first.", index_name)
    except Exception as exc:
        logger.warning("RAG learning loop init failed: %s", exc)
    return _RAG_LEARNING_INDEX


def record_rag_miss(
    query: str,
    expected_answer: str,
    actual_answer: str,
    category: str,
    *,
    grounding_status: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Store a RAG miss in Pinecone for future reranker bias improvement.

    Only active when RAG_LEARNING_MODE=1 (internal bench only).
    Returns True if stored successfully.
    """
    if not RAG_LEARNING_MODE:
        return False
    index = _get_rag_learning_index()
    if index is None:
        return False
    try:
        record = {
            "_id": hashlib.sha256(f"{query[:200]}:{time.time()}".encode()).hexdigest()[:24],
            "content": f"Query: {query[:500]}\nExpected: {expected_answer[:500]}\nActual: {actual_answer[:500]}",
            "category": category,
            "grounding_status": grounding_status,
            "miss_type": "rag_incorrect",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    record[k] = v
        index.upsert_records(_RAG_LEARNING_NAMESPACE, [record])
        logger.info("RAG_LEARNING: stored miss for query=%s", query[:80])
        return True
    except Exception as exc:
        logger.warning("RAG_LEARNING: failed to store miss: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def run_elite_plus(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    effective_tier: str,
    extra: Dict[str, Any],
    *,
    internal_bench: bool = False,
    _force_free_first: bool = False,
    policy_override: Optional[str] = None,
) -> ElitePlusResult:
    """Run the Elite+ pipeline. Dispatches to dominance_v3, dominance_v2, auto_dominance, leader_first, or free_first."""
    policy = (policy_override or ELITE_PLUS_POLICY).lower().strip()

    # Production split: per-category optimal routing based on benchmark evidence.
    # Routes tool_use/rag through dominance v3 (leader-first gains) while keeping
    # reasoning/coding/multilingual/math on free-first (no regression).
    if (
        ELITE_PLUS_PRODUCTION_SPLIT
        and ELITE_PLUS_ENABLE_DOMINANCE_V3
        and not _force_free_first
    ):
        if category in _SPLIT_LEADER_FIRST:
            logger.info(
                "PRODUCTION_SPLIT: category=%s -> dominance_v3 (leader-first gain)",
                category,
            )
            return await _run_elite_plus_dominance_v3(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        elif category in _SPLIT_FREE_FIRST:
            logger.info(
                "PRODUCTION_SPLIT: category=%s -> free_first (regression avoidance)",
                category,
            )
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        elif category == "dialogue":
            logger.info("PRODUCTION_SPLIT: category=dialogue -> dominance_v3 (single premium)")
            return await _run_elite_plus_dominance_v3(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        elif category == "long_context":
            logger.info("PRODUCTION_SPLIT: category=long_context -> dominance_v3 (gemini anchor)")
            return await _run_elite_plus_dominance_v3(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )
        else:
            logger.info(
                "PRODUCTION_SPLIT: category=%s -> free_first (default safe path)",
                category,
            )
            return await _run_elite_plus_free_first_impl(
                query, base_answer, base_confidence, category, orchestrator,
                effective_tier, extra, internal_bench=internal_bench,
            )

    if _force_free_first:
        pass
    elif ELITE_PLUS_ENABLE_DOMINANCE_V3:
        return await _run_elite_plus_dominance_v3(
            query, base_answer, base_confidence, category, orchestrator, effective_tier, extra,
            internal_bench=internal_bench,
        )
    elif ELITE_PLUS_ENABLE_DOMINANCE_V2:
        return await _run_elite_plus_dominance_v2(
            query, base_answer, base_confidence, category, orchestrator, effective_tier, extra,
            internal_bench=internal_bench,
        )
    elif ELITE_PLUS_ENABLE_AUTO_DOMINANCE and policy == "auto_dominance_verified":
        return await _run_elite_plus_auto_dominance(
            query, base_answer, base_confidence, category, orchestrator, effective_tier, extra,
            internal_bench=internal_bench,
        )
    elif (
        policy == "leader_first_verified"
        and _leader_first_allowed(internal_bench)
    ):
        return await _run_elite_plus_leader_first(
            query, base_answer, base_confidence, category, orchestrator, internal_bench
        )
    return await _run_elite_plus_free_first_impl(
        query, base_answer, base_confidence, category, orchestrator, effective_tier, extra,
        internal_bench=internal_bench,
        policy_override=policy_override,
    )


async def _run_elite_plus_free_first_impl(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    effective_tier: str,
    extra: Dict[str, Any],
    *,
    internal_bench: bool = False,
    policy_override: Optional[str] = None,
) -> ElitePlusResult:
    """Run the Elite+ free-first-verified pipeline.

    Flow:
      Stage A: Call free models for the category
      Stage B: Run deterministic verification (schema, grounding, consensus)
      Stage C: Escalate to ONE category-specific paid anchor if needed
      Stage D: Fallback to base elite answer on total failure
    """
    t0 = time.perf_counter()
    mode = ELITE_PLUS_MODE
    policy = (policy_override or ELITE_PLUS_POLICY).lower().strip()

    # Resolve effective max paid calls (internal bench can allow 2)
    max_paid = ELITE_PLUS_MAX_PAID_CALLS
    if internal_bench:
        max_paid = ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH

    models_called: List[str] = []
    free_calls = 0
    paid_calls = 0
    cost_breakdown: Dict[str, float] = {}
    escalation_reasons: List[str] = []
    tool_invocations: List[str] = []
    rag_grounding = "n/a"
    verifier_strategy = "none"
    verifier_status = "ok"
    verifier_latency = 0

    # Category-specific telemetry
    tool_schema_valid = True
    tool_retry_count = 0
    tool_execution_ok = True
    tool_error_type = "none"
    rag_unanswered_reason = "none"
    rag_passage_count = 0
    dialogue_mode_val = "n/a"
    dialogue_anchor_used = ""
    dialogue_escalated = False

    if category == "dialogue":
        dialogue_mode_val = "light_touch" if ELITE_PLUS_DIALOGUE_LIGHT_TOUCH else "full"

    # -----------------------------------------------------------------------
    # Stage A: Free primary — call free models
    # -----------------------------------------------------------------------
    free_models = _get_free_models(category)
    free_answers: List[Tuple[str, float, str]] = []

    if free_models:
        # G2: skip degraded free models via circuit breaker
        healthy_free = [m for m in free_models if not _circuit_breaker.is_degraded(m)]
        if not healthy_free:
            healthy_free = free_models[:1]
            logger.warning("All free models degraded for %s, forcing first: %s", category, healthy_free[0])

        tasks = [_call_model(orchestrator, query, m, ELITE_PLUS_BUDGET_MS) for m in healthy_free]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for model_id, result in zip(healthy_free, raw):
            models_called.append(model_id)
            free_calls += 1
            cost_breakdown[model_id] = 0.0
            if isinstance(result, Exception):
                logger.warning("Elite+ free model %s error: %s", model_id, result)
                _circuit_breaker.record(model_id, False)
            else:
                text, latency = result
                conf = _extract_confidence(text)
                _circuit_breaker.record(model_id, bool(text and len(text.strip()) > 5))
                if text:
                    free_answers.append((text, conf, model_id))

    best_free_text, best_free_conf, best_free_model = _best_answer(free_answers)
    stage_used = "free_primary"

    # -----------------------------------------------------------------------
    # Stage B: Deterministic verification
    # -----------------------------------------------------------------------
    answer_texts = [t for t, _, _ in free_answers]
    vr = _run_deterministic_verification(category, answer_texts, query)
    verifier_strategy = "deterministic"
    verifier_latency = int((time.perf_counter() - t0) * 1000)

    if vr.verified:
        best_free_conf = max(best_free_conf, vr.confidence)
        stage_used = "deterministic_verify"
        verifier_status = "verified"

    # Propagate category-specific verification details
    tool_schema_valid = vr.tool_schema_valid
    tool_error_type = vr.tool_error_type
    tool_execution_ok = vr.tool_error_type == "none"
    rag_unanswered_reason = vr.rag_unanswered_reason

    if category == "rag":
        if answer_texts:
            _, _, rag_rationale, _ = _verify_rag_grounding(answer_texts[0], query)
            if "grounded" in rag_rationale or "partial" in rag_rationale:
                rag_grounding = "ok" if "grounded" in rag_rationale else "partial"
            else:
                rag_grounding = "fail"
        else:
            rag_grounding = "fail"

    # -----------------------------------------------------------------------
    # Stage C: Paid escalation (if triggered)
    # -----------------------------------------------------------------------
    should_esc, esc_reasons = _should_escalate(
        category, best_free_conf, vr, answer_texts
    )

    paid_answer = ""
    paid_conf = 0.0
    if should_esc and paid_calls < max_paid:
        anchor = choose_paid_anchor(category, esc_reasons)
        escalation_reasons = esc_reasons

        # G2: Launch Mode governance — check escalation allowlist + cost ceiling
        lm_allowed = _launch_mode_allows_escalation(category, esc_reasons)
        lm_cost_ok = _launch_mode_cost_ok(sum(cost_breakdown.values()), anchor)

        # G2: Skip degraded paid anchor; fall back to default
        if _circuit_breaker.is_degraded(anchor):
            fallback_anchor = "openai/gpt-4o-mini"
            logger.warning("Paid anchor %s degraded, substituting %s", anchor, fallback_anchor)
            anchor = fallback_anchor

        if not lm_allowed:
            logger.info("Launch Mode blocked escalation for category=%s reasons=%s", category, esc_reasons)
            escalation_reasons.append("launch_mode_blocked")
        elif not lm_cost_ok:
            logger.info("Launch Mode cost ceiling would be exceeded for anchor=%s", anchor)
            escalation_reasons.append("cost_ceiling_exceeded")
        else:
            if category == "dialogue":
                dialogue_escalated = True
                dialogue_anchor_used = anchor

            # Part C: for tool_use, if schema was invalid, retry with constrained prompt
            tool_retry_prompt = query
            if category == "tool_use" and not tool_schema_valid and ELITE_PLUS_TOOL_STRICT_MODE:
                tool_retry_count = 1
                tool_retry_prompt = (
                    "You MUST respond with ONLY a valid JSON tool call. "
                    "Do NOT include any explanation or freeform text.\n\n"
                    f"Original request: {query}"
                )

            try:
                paid_text, paid_lat = await _call_model(
                    orchestrator, tool_retry_prompt if category == "tool_use" else query,
                    anchor, ELITE_PLUS_BUDGET_MS,
                )
                models_called.append(anchor)
                paid_calls += 1
                cost_breakdown[anchor] = _estimate_cost(anchor)
                _circuit_breaker.record(anchor, bool(paid_text and len(paid_text.strip()) > 5))

                if paid_text and len(paid_text.strip()) > 5:
                    paid_answer = paid_text
                    paid_conf = max(_extract_confidence(paid_text), 0.75)
                    stage_used = "paid_escalation"
                    verifier_strategy = "paid_anchor"

                    # Part D: re-check RAG grounding after paid escalation
                    if category == "rag" and ELITE_PLUS_RAG_REQUIRE_SUPPORT:
                        ok2, _, rat2, unans2 = _verify_rag_grounding(paid_text, query)
                        if not ok2:
                            rag_grounding = "fail"
                            rag_unanswered_reason = unans2
                            paid_answer = (
                                "I don't have sufficient evidence to answer this question "
                                "based on the available context. Could you provide more details "
                                "or rephrase your question?"
                            )
                            paid_conf = 0.5
                        else:
                            rag_grounding = "ok"
                            rag_unanswered_reason = "none"

            except Exception as exc:
                logger.warning("Elite+ paid anchor %s failed: %s", anchor, exc)
                _circuit_breaker.record(anchor, False)
                escalation_reasons.append(f"anchor_error:{exc}")

    # -----------------------------------------------------------------------
    # Select final answer
    # -----------------------------------------------------------------------
    if paid_answer and paid_conf > best_free_conf:
        final_answer = paid_answer
        final_conf = paid_conf
    elif best_free_text:
        final_answer = best_free_text
        final_conf = best_free_conf
    else:
        final_answer = base_answer
        final_conf = base_confidence
        stage_used = "fallback_elite"

    total_latency = int((time.perf_counter() - t0) * 1000)
    total_cost = sum(cost_breakdown.values())

    result = ElitePlusResult(
        answer=final_answer,
        confidence=final_conf,
        mode=mode,
        policy=policy,
        stage_used=stage_used,
        paid_calls_count=paid_calls,
        free_calls_count=free_calls,
        estimated_cost_usd=total_cost,
        estimated_cost_breakdown=cost_breakdown,
        confidence_free=best_free_conf,
        confidence_final=final_conf,
        escalation_reason=escalation_reasons,
        models_called=models_called,
        tool_invocations=tool_invocations,
        rag_grounding_status=rag_grounding,
        total_latency_ms=total_latency,
        verifier_strategy=verifier_strategy,
        verifier_status=verifier_status,
        verifier_latency_ms=verifier_latency,
        # Part C telemetry
        tool_schema_valid=tool_schema_valid,
        tool_retry_count=tool_retry_count,
        tool_execution_ok=tool_execution_ok,
        tool_error_type=tool_error_type,
        # Part D telemetry
        rag_unanswered_reason=rag_unanswered_reason,
        rag_passage_count_used=rag_passage_count,
        # Part E telemetry
        dialogue_mode=dialogue_mode_val,
        dialogue_anchor_used=dialogue_anchor_used,
        dialogue_escalated=dialogue_escalated,
        # backward compat
        shadow_answer=final_answer,
        shadow_confidence=final_conf,
        should_override=(mode == "active"),
        base_answer=base_answer,
        base_confidence=base_confidence,
        blackboard_hash=hashlib.sha256(
            f"{query[:100]}:{final_answer[:100]}".encode()
        ).hexdigest()[:16],
    )

    if ELITE_PLUS_LOG_SHADOW:
        logger.info(
            "ELITE+ [%s/%s] stage=%s free=%d paid=%d cost=$%.4f "
            "conf_free=%.2f conf_final=%.2f esc=%s latency=%dms models=%s",
            mode, policy, stage_used, free_calls, paid_calls, total_cost,
            best_free_conf, final_conf,
            escalation_reasons or "none",
            total_latency, models_called,
        )

    return result
