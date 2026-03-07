#!/usr/bin/env python3
"""Export the Python model registry to web/public/models.json.

This keeps the UI "Models" dropdown in sync with the authoritative
server-side registry.  Run after any change to model_registry.py.

Usage:
    python scripts/export_model_registry.py          # writes web/public/models.json
    python scripts/export_model_registry.py --check  # CI mode: exit 1 if stale
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llmhive" / "src"))

from llmhive.app.orchestration.model_registry import (
    MODEL_REGISTRY_VERSION,
    Tier,
    get_registry,
    compute_leaderboard_ranks,
    compute_best_for_categories,
    compute_registry_integrity_hash,
)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "public" / "models.json"


def _tier_display(tier: Tier) -> str:
    if tier == Tier.FREE:
        return "Free"
    if tier == Tier.BOTH:
        return "Elite+"
    return "Elite+"


def _build_json() -> dict:
    registry = get_registry()
    leaderboard = compute_leaderboard_ranks()
    best_for = compute_best_for_categories()

    models = []
    for m in sorted(registry.values(), key=lambda x: (-max(x.category_scores.values(), default=0), x.model_id)):
        best_cats = best_for.get(m.model_id, [])
        lb_ranks = leaderboard.get(m.model_id, {})
        models.append({
            "id": m.model_id,
            "tier": m.tier.value,
            "tierDisplay": _tier_display(m.tier),
            "capabilities": sorted(m.capabilities),
            "latencyTier": m.latency_tier.value,
            "reliability": m.reliability,
            "contextWindow": m.context_window,
            "categoryScores": m.category_scores,
            "recommended": m.reliability >= 0.90 and max(m.category_scores.values(), default=0) >= 90,
            "bestForCategories": sorted(best_cats),
            "leaderboardRank": lb_ranks,
            "notes": m.notes or None,
        })
    return {
        "registryVersion": MODEL_REGISTRY_VERSION,
        "registryIntegrityHash": compute_registry_integrity_hash(),
        "generatedBy": "scripts/export_model_registry.py",
        "models": models,
    }


def main() -> None:
    check_mode = "--check" in sys.argv
    payload = _build_json()

    if check_mode:
        if not OUTPUT_PATH.exists():
            print(f"FAIL: {OUTPUT_PATH} does not exist. Run export first.")
            sys.exit(1)
        existing = json.loads(OUTPUT_PATH.read_text())
        if existing.get("registryVersion") != payload["registryVersion"]:
            print(
                f"FAIL: models.json version ({existing.get('registryVersion')}) "
                f"!= registry version ({payload['registryVersion']}). Re-run export."
            )
            sys.exit(1)
        if len(existing.get("models", [])) != len(payload["models"]):
            print(
                f"FAIL: model count mismatch ({len(existing.get('models', []))} "
                f"vs {len(payload['models'])}). Re-run export."
            )
            sys.exit(1)
        existing_hash = existing.get("registryIntegrityHash", "")
        current_hash = payload.get("registryIntegrityHash", "")
        if existing_hash and current_hash and existing_hash != current_hash:
            print(
                f"FAIL: integrity hash mismatch "
                f"(models.json={existing_hash[:16]}… vs registry={current_hash[:16]}…). "
                f"Re-run export."
            )
            sys.exit(1)
        print(f"OK: models.json is in sync (version={payload['registryVersion']}, models={len(payload['models'])})")
        sys.exit(0)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"Exported {len(payload['models'])} models to {OUTPUT_PATH}")
    print(f"Registry version: {payload['registryVersion']}")


if __name__ == "__main__":
    main()
