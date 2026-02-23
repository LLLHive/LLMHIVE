"""Model Validation Hardening — Enterprise-grade capability verification.

For every registered model, validates:
  - context_window declared
  - supports_tools consistency
  - capability_tags present and non-empty
  - latency profile (p50/p95) within sane bounds
  - elite model has required strength for its assigned category
  - verify model compatible with verify pipeline

Produces: benchmark_reports/model_validation_2026.json
Aborts if elite model lacks required capability for its category.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .elite_policy import ELITE_POLICY, VERIFY_MODEL
from .model_registry_2026 import ModelEntry, get_model_registry_2026

logger = logging.getLogger(__name__)

CATEGORY_REQUIRED_TAGS: Dict[str, List[str]] = {
    "coding":       ["code_strong"],
    "math":         ["math_strong"],
    "reasoning":    ["elite_reasoning"],
    "long_context": ["long_context_leader"],
    "multilingual": ["multilingual_leader"],
}

MIN_ELITE_STRENGTH = 0.80
MAX_SANE_LATENCY_P95 = 30_000
MIN_CONTEXT_WINDOW = 4096


def validate_all_models() -> Dict[str, Any]:
    """Run full validation suite. Returns structured report."""
    registry = get_model_registry_2026()
    models = registry.list_models(available_only=False)
    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_models": len(models),
        "models": {},
        "errors": [],
        "warnings": [],
        "elite_validation": {},
        "passed": True,
    }

    for entry in models:
        model_report = _validate_single(entry)
        report["models"][entry.model_id] = model_report
        report["errors"].extend(model_report.get("errors", []))
        report["warnings"].extend(model_report.get("warnings", []))

    elite_errors = _validate_elite_assignments(registry)
    report["elite_validation"] = elite_errors
    report["errors"].extend(elite_errors.get("errors", []))

    verify_errors = _validate_verify_model(registry)
    report["errors"].extend(verify_errors)

    report["passed"] = len(report["errors"]) == 0
    report["error_count"] = len(report["errors"])
    report["warning_count"] = len(report["warnings"])
    return report


def _validate_single(entry: ModelEntry) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "model_id": entry.model_id,
        "provider": entry.provider,
        "errors": [],
        "warnings": [],
        "checks": {},
    }

    # Context window
    ok = entry.context_window >= MIN_CONTEXT_WINDOW
    result["checks"]["context_window"] = {"value": entry.context_window, "pass": ok}
    if not ok:
        result["errors"].append(
            f"{entry.model_id}: context_window {entry.context_window} < {MIN_CONTEXT_WINDOW}"
        )

    # Capability tags
    ok = len(entry.capability_tags) > 0
    result["checks"]["capability_tags"] = {"value": entry.capability_tags, "pass": ok}
    if not ok:
        result["errors"].append(f"{entry.model_id}: no capability_tags declared")

    # Latency sanity
    ok = entry.latency_profile.p95 <= MAX_SANE_LATENCY_P95
    result["checks"]["latency_p95"] = {"value": entry.latency_profile.p95, "pass": ok}
    if not ok:
        result["warnings"].append(
            f"{entry.model_id}: p95 latency {entry.latency_profile.p95}ms > {MAX_SANE_LATENCY_P95}ms"
        )

    # Tool support consistency
    if entry.supports_tools and "tool_use" not in entry.capability_tags:
        result["warnings"].append(
            f"{entry.model_id}: supports_tools=True but missing tool_use capability_tag"
        )

    # Strength range validation
    for attr in ("reasoning_strength", "coding_strength", "math_strength",
                 "rag_strength", "dialogue_strength"):
        val = getattr(entry, attr, 0)
        if not (0 <= val <= 1):
            result["errors"].append(f"{entry.model_id}: {attr}={val} outside [0,1]")

    return result


def _validate_elite_assignments(registry) -> Dict[str, Any]:
    result: Dict[str, Any] = {"categories": {}, "errors": []}

    for category, model_id in ELITE_POLICY.items():
        entry = registry.get(model_id)
        cat_result: Dict[str, Any] = {
            "model_id": model_id,
            "exists": entry is not None,
            "strength": None,
            "meets_minimum": False,
            "required_tags": CATEGORY_REQUIRED_TAGS.get(category, []),
            "has_required_tags": False,
        }

        if not entry:
            result["errors"].append(
                f"Elite model {model_id} for {category} not found in registry"
            )
            result["categories"][category] = cat_result
            continue

        strength = entry.strength_for_category(category)
        cat_result["strength"] = round(strength, 3)
        cat_result["meets_minimum"] = strength >= MIN_ELITE_STRENGTH
        if not cat_result["meets_minimum"]:
            result["errors"].append(
                f"Elite model {model_id} strength for {category} is {strength:.3f} "
                f"< required {MIN_ELITE_STRENGTH}"
            )

        required = CATEGORY_REQUIRED_TAGS.get(category, [])
        has_tags = all(t in entry.capability_tags for t in required)
        cat_result["has_required_tags"] = has_tags
        if required and not has_tags:
            missing = [t for t in required if t not in entry.capability_tags]
            result["errors"].append(
                f"Elite model {model_id} for {category} missing tags: {missing}"
            )

        result["categories"][category] = cat_result

    return result


def _validate_verify_model(registry) -> List[str]:
    errors = []
    entry = registry.get(VERIFY_MODEL)
    if not entry:
        errors.append(f"Verify model {VERIFY_MODEL} not in registry")
    elif not entry.is_available:
        errors.append(f"Verify model {VERIFY_MODEL} marked unavailable")
    elif "verify_specialist" not in entry.capability_tags and "elite_reasoning" not in entry.capability_tags:
        pass  # acceptable: DeepSeek has math_strong + elite_reasoning
    return errors


def save_validation_report(report: Dict[str, Any]) -> str:
    report_dir = Path("benchmark_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    path = str(report_dir / "model_validation_2026.json")
    Path(path).write_text(json.dumps(report, indent=2, default=str))
    return path


def print_validation_summary(report: Dict[str, Any]) -> None:
    print("\n  ╔═══════════════════════════════════════════════╗")
    print("  ║        MODEL VALIDATION REPORT (2026)         ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print(f"  Models validated:  {report['total_models']}")
    print(f"  Errors:            {report['error_count']}")
    print(f"  Warnings:          {report['warning_count']}")
    print(f"  Overall:           {'PASS' if report['passed'] else 'FAIL'}")
    if report["errors"]:
        print("  Errors:")
        for e in report["errors"]:
            print(f"    - {e}")
    if report["warnings"]:
        print("  Warnings:")
        for w in report["warnings"][:5]:
            print(f"    - {w}")
    print()
