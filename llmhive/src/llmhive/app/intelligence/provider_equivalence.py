"""Same-Model Multi-Provider Equivalence Matrix.

Maps elite model IDs to ordered lists of provider keys that can serve
the **exact same model** — no downgrade, no substitution.

Provider keys match ``Orchestrator.providers`` dict keys:
  "openrouter", "openai", "anthropic", "gemini", "grok", "deepseek"

The order within each list defines failover priority:
  index 0 = primary, index 1..N = same-model failover routes.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Same-Model Provider Matrix ──────────────────────────────────────────
# Only providers that serve the **identical** model are listed.
# NO weaker substitutes. Order = failover priority.

SAME_MODEL_PROVIDER_MATRIX: Dict[str, List[str]] = {
    "gpt-5.2-pro":       ["openrouter", "openai"],
    "gpt-5.2":           ["openrouter", "openai"],
    "claude-sonnet-4.6": ["openrouter", "anthropic"],
    "gemini-3.1-pro":    ["openrouter", "gemini"],
    "gemini-3-pro":      ["openrouter", "gemini"],
    "gemini-2.5-pro":    ["openrouter", "gemini"],
    "grok-4":            ["openrouter", "grok"],
    "grok-3-mini":       ["openrouter", "grok"],
    "deepseek-reasoner": ["openrouter", "deepseek"],
}

# Maps internal model_id → the model string each provider expects.
# "openrouter" entry uses the OpenRouter model slug;
# direct-API entry uses the provider's native model name.
_MODEL_ID_PER_PROVIDER: Dict[str, Dict[str, str]] = {
    "gpt-5.2-pro": {
        "openrouter": "openai/gpt-5.2-pro",
        "openai":     "gpt-5.2-pro",
    },
    "gpt-5.2": {
        "openrouter": "openai/gpt-5.2",
        "openai":     "gpt-5.2",
    },
    "claude-sonnet-4.6": {
        "openrouter": "anthropic/claude-sonnet-4.6",
        "anthropic":  "claude-sonnet-4.6",
    },
    "gemini-3.1-pro": {
        "openrouter": "google/gemini-3.1-pro-preview",
        "gemini":     "gemini-3.1-pro",
    },
    "gemini-3-pro": {
        "openrouter": "google/gemini-3-pro-preview",
        "gemini":     "gemini-3-pro",
    },
    "gemini-2.5-pro": {
        "openrouter": "google/gemini-2.5-pro-preview",
        "gemini":     "gemini-2.5-pro",
    },
    "grok-4": {
        "openrouter": "x-ai/grok-4",
        "grok":       "grok-4",
    },
    "grok-3-mini": {
        "openrouter": "x-ai/grok-3-mini",
        "grok":       "grok-3-mini",
    },
    "deepseek-reasoner": {
        "openrouter": "deepseek/deepseek-r1-0528",
        "deepseek":   "deepseek-reasoner",
    },
}

# ── Provider SLA thresholds ─────────────────────────────────────────────
# Used by the failover loop to *skip* a provider that is currently
# breaching SLA (cascading-failure prevention).

PROVIDER_SLA: Dict[str, Dict[str, int]] = {
    "openrouter":  {"p95_latency_ms": 2500, "error_threshold": 3},
    "openai":      {"p95_latency_ms": 1500, "error_threshold": 2},
    "anthropic":   {"p95_latency_ms": 1800, "error_threshold": 2},
    "gemini":      {"p95_latency_ms": 2000, "error_threshold": 2},
    "grok":        {"p95_latency_ms": 2000, "error_threshold": 2},
    "deepseek":    {"p95_latency_ms": 3000, "error_threshold": 3},
}

# Rolling window of recent provider errors (provider_key → list of timestamps)
_provider_error_window: Dict[str, List[float]] = {}
_ERROR_WINDOW_SECONDS = 120  # 2-minute sliding window


# ── Failure classification ──────────────────────────────────────────────

class ProviderFailureType:
    PAYMENT = "provider_payment_failure"
    RATE_LIMIT = "rate_limit"
    SERVER = "server_failure"
    TIMEOUT = "timeout"
    CLIENT = "client_error"


def classify_provider_failure(exc: BaseException) -> str:
    """Classify an exception into a structured failure type.

    402 → payment failure (provider-down equivalent)
    429 → rate limit
    5xx → server failure
    timeout / connection → timeout
    everything else → client error (not retryable across providers)
    """
    status_code = _extract_status_code(exc)

    if status_code == 402:
        return ProviderFailureType.PAYMENT
    if status_code == 429:
        return ProviderFailureType.RATE_LIMIT
    if status_code is not None and status_code >= 500:
        return ProviderFailureType.SERVER

    msg = str(exc).lower()
    if any(tok in msg for tok in (
        "timeout", "timed out", "connecttimeout", "readtimeout",
        "connection reset", "connection refused",
    )):
        return ProviderFailureType.TIMEOUT

    if isinstance(exc, (TimeoutError, ConnectionError, ConnectionResetError, OSError)):
        return ProviderFailureType.TIMEOUT

    return ProviderFailureType.CLIENT


_FAILOVER_TYPES = frozenset({
    ProviderFailureType.PAYMENT,
    ProviderFailureType.RATE_LIMIT,
    ProviderFailureType.SERVER,
    ProviderFailureType.TIMEOUT,
})


def is_failover_worthy(failure_type: str) -> bool:
    """Return True if the failure should trigger same-model provider rotation."""
    return failure_type in _FAILOVER_TYPES


# ── Public API ──────────────────────────────────────────────────────────

def get_equivalent_providers(model_id: str) -> List[str]:
    """Return ordered list of provider keys that can serve *model_id*.

    Falls back to ``["openrouter"]`` for models not in the matrix
    (non-elite models keep existing behaviour).
    """
    return list(SAME_MODEL_PROVIDER_MATRIX.get(model_id, ["openrouter"]))


def get_provider_model_name(model_id: str, provider_key: str) -> str:
    """Return the model name string that *provider_key* expects for *model_id*.

    Falls back to *model_id* unchanged if no explicit mapping exists.
    """
    return _MODEL_ID_PER_PROVIDER.get(model_id, {}).get(provider_key, model_id)


def is_provider_sla_healthy(
    provider_key: str,
    reliability_stats: Optional[Dict] = None,
) -> bool:
    """Check whether *provider_key* is within SLA thresholds.

    Uses the rolling error window maintained by ``record_provider_error``.
    Optionally cross-checks ``reliability_stats`` from ReliabilityGuard.
    """
    sla = PROVIDER_SLA.get(provider_key)
    if not sla:
        return True

    # Check rolling error count
    now = time.time()
    window = _provider_error_window.get(provider_key, [])
    window = [t for t in window if now - t < _ERROR_WINDOW_SECONDS]
    _provider_error_window[provider_key] = window

    if len(window) >= sla["error_threshold"]:
        logger.warning(
            "PROVIDER_SLA_BREACH: %s has %d errors in %ds window (threshold=%d) — skipping",
            provider_key, len(window), _ERROR_WINDOW_SECONDS, sla["error_threshold"],
        )
        return False

    # Optional: cross-check with ReliabilityGuard p95 latency
    if reliability_stats:
        p95 = reliability_stats.get("p95_latency_ms", 0)
        if p95 > sla["p95_latency_ms"]:
            logger.warning(
                "PROVIDER_SLA_BREACH: %s p95=%dms > threshold=%dms — skipping",
                provider_key, p95, sla["p95_latency_ms"],
            )
            return False

    return True


def record_provider_error(provider_key: str) -> None:
    """Record an error timestamp for *provider_key* (rolling window)."""
    _provider_error_window.setdefault(provider_key, []).append(time.time())


def _extract_status_code(exc: BaseException) -> Optional[int]:
    """Best-effort extraction of HTTP status code from various exception types."""
    # httpx.HTTPStatusError
    resp = getattr(exc, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        if code is not None:
            return int(code)

    # Generic .status / .status_code attributes
    for attr in ("status_code", "status", "code"):
        val = getattr(exc, attr, None)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass

    # Scan message for common HTTP codes
    msg = str(exc)
    import re
    m = re.search(r"\b(402|429|500|502|503|504)\b", msg)
    if m:
        return int(m.group(1))

    return None
