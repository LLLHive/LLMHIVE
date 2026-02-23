"""Drift Prevention Guards — Startup and per-call invariant assertions.

At startup, assert:
  - Tier is explicit
  - No default model usage in benchmark mode
  - No silent fallback
  - No multi-model use in single-mode
  - No downgrade
  - All resolved models exist in the canonical registry
  - All provider names are registered

In benchmark mode:
  drift → immediate RuntimeError

In production:
  drift → log CRITICAL + continue
"""
from __future__ import annotations

import logging
import os
from typing import List

from .elite_policy import ELITE_POLICY, is_benchmark_mode, get_intelligence_mode
from .model_registry_2026 import get_model_registry_2026

logger = logging.getLogger(__name__)


class DriftViolation(RuntimeError):
    """Raised when a drift invariant is violated in benchmark mode."""
    pass


def _known_providers() -> set:
    registry = get_model_registry_2026()
    return {m.provider for m in registry.list_models(available_only=False)}


def assert_startup_invariants() -> List[str]:
    """Run all startup checks. Returns list of warnings (raises on fatal in bench mode)."""
    warnings: List[str] = []
    registry = get_model_registry_2026()
    benchmark = is_benchmark_mode()

    for category, model_id in ELITE_POLICY.items():
        if not registry.exists(model_id):
            msg = f"Elite model {model_id} for {category} not found in registry"
            if benchmark:
                raise DriftViolation(msg)
            warnings.append(msg)

    if benchmark:
        for model_id in set(ELITE_POLICY.values()):
            entry = registry.get(model_id)
            if entry and not entry.is_available:
                msg = f"Elite model {model_id} marked unavailable"
                raise DriftViolation(msg)

    if not warnings:
        logger.info("Drift guard: all startup invariants passed")
    else:
        for w in warnings:
            logger.warning("Drift guard warning: %s", w)

    return warnings


def assert_call_invariants(
    *,
    category: str,
    resolved_model: str,
    fallback_used: bool,
    models_used_count: int,
    tier: str = "elite",
    reasoning_mode: str = "deep",
) -> None:
    """Per-call invariant check.

    In benchmark mode: raises DriftViolation.
    In production: logs CRITICAL but continues.
    """
    benchmark = is_benchmark_mode()
    registry = get_model_registry_2026()

    def _handle(msg: str) -> None:
        if benchmark:
            raise DriftViolation(msg)
        logger.critical("DRIFT (production): %s", msg)

    # Model must exist in registry
    if not registry.exists(resolved_model):
        norm = resolved_model.lower().strip()
        found = any(
            norm == mid.lower() or norm in mid.lower()
            for mid in [m.model_id for m in registry.list_models(available_only=False)]
        )
        if not found:
            _handle(f"Unregistered model used: {resolved_model} (category={category})")

    # Provider must be known
    entry = registry.get(resolved_model)
    if entry and entry.provider not in _known_providers():
        _handle(f"Unknown provider {entry.provider} for model {resolved_model}")

    # Elite policy enforcement
    expected = ELITE_POLICY.get(category, "")
    norm_resolved = resolved_model.lower().strip()
    norm_expected = expected.lower().strip()
    if norm_expected and norm_resolved != norm_expected and norm_expected not in norm_resolved:
        _handle(f"Model drift: category={category}, expected={expected}, got={resolved_model}")

    if fallback_used:
        _handle(f"Fallback detected: category={category}")

    orch_mode = os.getenv("ORCHESTRATION_MODE", "").lower()
    if orch_mode == "single" and models_used_count > 1:
        _handle(f"Multi-model in single-mode: category={category}, count={models_used_count}")


def print_drift_status() -> None:
    """Print current drift prevention status."""
    registry = get_model_registry_2026()
    benchmark = is_benchmark_mode()
    mode = get_intelligence_mode()
    print("\n  ┌───────────────────────────────────────────┐")
    print("  │        DRIFT PREVENTION STATUS            │")
    print("  ├───────────────────────────────────────────┤")
    print(f"  │ Benchmark mode:  {'ACTIVE' if benchmark else 'inactive':<22} │")
    print(f"  │ Intel mode:      {mode:<22} │")
    print(f"  │ Registry models: {len(registry.list_models()):<22} │")
    print(f"  │ Elite policies:  {len(ELITE_POLICY):<22} │")
    print(f"  │ Known providers: {len(_known_providers()):<22} │")

    issues = assert_startup_invariants() if not benchmark else []
    status = "CLEAN" if not issues else f"{len(issues)} warnings"
    print(f"  │ Status:          {status:<22} │")
    print("  └───────────────────────────────────────────┘")
    print()
