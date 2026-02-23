"""Elite Tier Policy — Deterministic model binding for benchmark mode.

In BENCHMARK_MODE:
  - Every category is hard-locked to a specific model_id.
  - No fallback, no downgrade, no first-available selection.
  - Drift detection raises RuntimeError immediately.

Outside BENCHMARK_MODE:
  - This module provides advisory elite recommendations only.

INTELLIGENCE_MODE governs authority level:
  advisory            — routing engine scores but does not override (default for local dev)
  controlled          — routing engine selects model in production (default for production)
  production_hardened — controlled routing + reliability guard + explainability + strategy gating
  benchmark_locked    — only ELITE_POLICY allowed; intelligence layer logs and validates only
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from .model_registry_2026 import get_model_registry_2026

logger = logging.getLogger(__name__)


ELITE_POLICY: Dict[str, str] = {
    "reasoning":    "gpt-5.2-pro",
    "coding":       "gpt-5.2-pro",
    "math":         "gpt-5.2-pro",
    "multilingual": "claude-sonnet-4.6",
    "long_context": "gemini-2.5-pro",
    "tool_use":     "gpt-5.2-pro",
    "rag":          "gpt-5.2-pro",
    "dialogue":     "gpt-5.2-pro",
}

VERIFY_MODEL = "deepseek-reasoner"

VALID_INTELLIGENCE_MODES = (
    "advisory", "controlled", "benchmark_locked", "production_hardened",
)


def is_benchmark_mode() -> bool:
    return os.getenv("BENCHMARK_MODE", "").lower() in ("1", "true", "yes")


def get_intelligence_mode() -> str:
    """Return the current intelligence authority mode.

    Resolution order:
      1. Explicit INTELLIGENCE_MODE env var
      2. benchmark → benchmark_locked
      3. CLOUD_RUN / production → controlled
      4. default → advisory
    """
    explicit = os.getenv("INTELLIGENCE_MODE", "").lower().strip()
    if explicit in VALID_INTELLIGENCE_MODES:
        return explicit
    if is_benchmark_mode():
        return "benchmark_locked"
    if os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_EXECUTION"):
        return "controlled"
    return "advisory"


def get_elite_model(category: str) -> str:
    """Return the hard-locked elite model_id for a category."""
    model_id = ELITE_POLICY.get(category)
    if not model_id:
        raise ValueError(f"No elite model configured for category: {category}")
    return model_id


def get_verify_model() -> str:
    return VERIFY_MODEL


def assert_elite_locked(resolved_model: str, category: str) -> None:
    """In benchmark mode, raise if the resolved model doesn't match policy.

    Outside benchmark mode this is a no-op.
    """
    if not is_benchmark_mode():
        return
    expected = ELITE_POLICY.get(category)
    if not expected:
        return
    norm_resolved = resolved_model.lower().strip()
    norm_expected = expected.lower().strip()
    if norm_resolved != norm_expected and norm_expected not in norm_resolved:
        raise RuntimeError(
            f"Elite model drift detected: category={category}, "
            f"expected={expected}, resolved={resolved_model}"
        )


def validate_elite_registry() -> list[str]:
    """Verify all elite-policy models exist in the canonical registry."""
    registry = get_model_registry_2026()
    errors = []
    for category, model_id in ELITE_POLICY.items():
        if not registry.exists(model_id):
            errors.append(f"Elite model {model_id} (category={category}) not in registry")
    if VERIFY_MODEL and not registry.exists(VERIFY_MODEL):
        errors.append(f"Verify model {VERIFY_MODEL} not in registry")
    return errors


def print_elite_config() -> None:
    """Print the full elite configuration table (pre-benchmark diagnostic)."""
    registry = get_model_registry_2026()
    print("\n  ┌─────────────────────────────────────────────────────┐")
    print("  │           ELITE TIER CONFIGURATION (2026)           │")
    print("  ├──────────────┬──────────────────┬───────────────────┤")
    print("  │ Category     │ Model            │ Strength          │")
    print("  ├──────────────┼──────────────────┼───────────────────┤")
    for cat, mid in sorted(ELITE_POLICY.items()):
        entry = registry.get(mid)
        strength = f"{entry.strength_for_category(cat):.2f}" if entry else "?"
        print(f"  │ {cat:<12s} │ {mid:<16s} │ {strength:>17s} │")
    print("  ├──────────────┼──────────────────┼───────────────────┤")
    print(f"  │ {'verify':<12s} │ {VERIFY_MODEL:<16s} │ {'specialist':>17s} │")
    print("  └──────────────┴──────────────────┴───────────────────┘")
    mode = get_intelligence_mode()
    print(f"  Benchmark mode:    {'ACTIVE' if is_benchmark_mode() else 'inactive'}")
    print(f"  Intelligence mode: {mode}")
    print()
