#!/usr/bin/env python3
"""Reproducibility Bundle — Freeze all system state for exact result reproduction.

Produces: benchmark_reports/reproducibility_manifest.json

Captures:
  - Model registry version + full model list
  - Elite policy version
  - Routing engine weights
  - Strategy DB snapshot
  - Benchmark seed
  - Git commit hash + branch
  - Python version + key dependency versions

Usage:
  python3 scripts/reproducibility_bundle.py
"""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llmhive" / "src"))


def _git_info() -> dict:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], stderr=subprocess.DEVNULL
        ).decode().strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL
        ).decode().strip())
        return {"commit": commit, "branch": branch, "dirty": dirty}
    except Exception:
        return {"commit": "unknown", "branch": "unknown", "dirty": None}


def _dependency_versions() -> dict:
    deps = {}
    for pkg in ["pinecone", "httpx", "datasets", "openai", "anthropic"]:
        try:
            mod = __import__(pkg)
            deps[pkg] = getattr(mod, "__version__", "installed")
        except ImportError:
            deps[pkg] = "not_installed"
    return deps


def main():
    from llmhive.app.intelligence import (
        get_model_registry_2026,
        ELITE_POLICY,
        CANONICAL_MODELS,
        get_routing_engine,
        get_strategy_db,
    )
    from llmhive.app.intelligence.model_registry_2026 import SCHEMA_VERSION
    from llmhive.app.intelligence.elite_policy import (
        VERIFY_MODEL, get_intelligence_mode, VALID_INTELLIGENCE_MODES,
    )
    from llmhive.app.intelligence.routing_engine import (
        LATENCY_REFERENCE_MS, COST_REFERENCE_PER_1K,
    )

    print("=" * 64)
    print("  REPRODUCIBILITY BUNDLE GENERATOR")
    print("=" * 64)

    registry = get_model_registry_2026()
    engine = get_routing_engine()
    sdb = get_strategy_db()

    model_snapshot = {}
    for m in registry.list_models(available_only=False):
        model_snapshot[m.model_id] = {
            "provider": m.provider,
            "context_window": m.context_window,
            "reasoning_strength": m.reasoning_strength,
            "coding_strength": m.coding_strength,
            "math_strength": m.math_strength,
            "capability_tags": m.capability_tags,
            "latency_p50": m.latency_profile.p50,
            "latency_p95": m.latency_profile.p95,
            "cost_input": m.cost_profile.input_per_1k,
            "cost_output": m.cost_profile.output_per_1k,
        }

    routing_weights = {
        "strength_weight": 0.50,
        "reasoning_weight": 0.20,
        "latency_weight": 0.15,
        "cost_weight": 0.15,
        "latency_reference_ms": LATENCY_REFERENCE_MS,
        "cost_reference_per_1k": COST_REFERENCE_PER_1K,
    }

    routing_results = {}
    for cat in ELITE_POLICY:
        scored = engine.select(cat, top_n=3)
        routing_results[cat] = [
            {"model_id": s.model_id, "total_score": s.total_score}
            for s in scored
        ]

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "git": _git_info(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": _dependency_versions(),
        "benchmark_seed": int(os.getenv("CATEGORY_BENCH_SEED", "42")),
        "intelligence_mode": get_intelligence_mode(),
        "valid_modes": list(VALID_INTELLIGENCE_MODES),
        "model_registry": {
            "version": SCHEMA_VERSION,
            "model_count": len(model_snapshot),
            "models": model_snapshot,
        },
        "elite_policy": {
            "category_bindings": dict(ELITE_POLICY),
            "verify_model": VERIFY_MODEL,
        },
        "routing_engine": {
            "weights": routing_weights,
            "results_per_category": routing_results,
        },
        "strategy_db": {
            "records_cached": len(sdb._performance_cache),
            "pinecone_available": sdb._pinecone_available,
            "firestore_available": sdb._firestore_available,
        },
    }

    report_dir = Path("benchmark_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    path = str(report_dir / "reproducibility_manifest.json")
    Path(path).write_text(json.dumps(manifest, indent=2, default=str))

    print(f"\n  Git:          {manifest['git']['commit'][:12]} ({manifest['git']['branch']})")
    print(f"  Schema:       {SCHEMA_VERSION}")
    print(f"  Models:       {len(model_snapshot)}")
    print(f"  Seed:         {manifest['benchmark_seed']}")
    print(f"  Intel mode:   {manifest['intelligence_mode']}")
    print(f"  Manifest:     {path}")
    print(f"\n{'=' * 64}")
    print("  REPRODUCIBILITY BUNDLE: COMPLETE")
    print(f"{'=' * 64}")


if __name__ == "__main__":
    main()
