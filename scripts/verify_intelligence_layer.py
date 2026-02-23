#!/usr/bin/env python3
"""Verify 2026 Intelligence Layer is correctly installed and configured.

Usage:
  python3 scripts/verify_intelligence_layer.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llmhive" / "src"))


def main():
    print("=" * 60)
    print("  2026 INTELLIGENCE LAYER VERIFICATION")
    print("=" * 60)

    errors = []

    # 1. Import verification
    print("\n  [1] Importing intelligence package...")
    try:
        from llmhive.app.intelligence import (
            get_model_registry_2026,
            ELITE_POLICY,
            get_routing_engine,
            get_verify_policy,
            get_intelligence_telemetry,
            get_adaptive_ensemble,
            get_strategy_db,
            assert_startup_invariants,
            print_elite_config,
            print_drift_status,
            print_performance_summary,
            CANONICAL_MODELS,
            Vote,
        )
        print("       PASS — all modules imported")
    except ImportError as e:
        print(f"       FAIL — {e}")
        errors.append(str(e))
        sys.exit(1)

    # 2. Registry validation
    print("\n  [2] Validating model registry...")
    registry = get_model_registry_2026()
    models = registry.list_models()
    print(f"       Models registered: {len(models)}")
    for m in models:
        print(f"         {m.model_id:<25} {m.provider:<12} ctx={m.context_window:>10,}")
    required_elite = list(set(ELITE_POLICY.values()))
    validation_errors = registry.validate(required_elite_ids=required_elite)
    if validation_errors:
        for e in validation_errors:
            print(f"       ERROR: {e}")
            errors.append(e)
    else:
        print("       PASS — all elite models present, no duplicates")

    # 3. Elite policy
    print("\n  [3] Elite policy mapping...")
    print_elite_config()

    # 4. Routing engine
    print("\n  [4] Routing engine scoring...")
    engine = get_routing_engine()
    for cat in ["reasoning", "coding", "math", "multilingual", "long_context"]:
        scored = engine.select(cat, top_n=3)
        top = scored[0] if scored else None
        if top:
            print(f"       {cat:<15} -> {top.model_id:<20} (score={top.total_score:.4f})")
        else:
            errors.append(f"No model scored for {cat}")

    # 5. Verify policy
    print("\n  [5] Verify pipeline policy...")
    vp = get_verify_policy()
    print(f"       Verify model: {vp.verify_model_id}")
    print(f"       Circuit open: {vp.is_circuit_open}")

    # 6. Ensemble
    print("\n  [6] Adaptive ensemble test...")
    ensemble = get_adaptive_ensemble()
    votes = [
        Vote(model_id="gpt-5.2-pro", answer="42", confidence=0.95),
        Vote(model_id="claude-sonnet-4.6", answer="42", confidence=0.90),
        Vote(model_id="deepseek-reasoner", answer="41", confidence=0.60),
    ]
    result = ensemble.resolve(votes, "math")
    print(f"       Selected: {result.selected_answer} (winner={result.winning_model})")
    print(f"       Entropy:  {result.disagreement_entropy:.4f}")
    print(f"       Escalated: {result.escalated}")

    # 7. Drift guard
    print("\n  [7] Drift prevention guards...")
    print_drift_status()

    # 8. Strategy DB
    print("\n  [8] Strategy DB backends...")
    sdb = get_strategy_db()
    print(f"       Pinecone: {'available' if sdb._pinecone_available else 'unavailable'}")
    print(f"       Firestore: {'available' if sdb._firestore_available else 'unavailable'}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    else:
        print("  RESULT: PASS — Intelligence layer fully operational")
    print("=" * 60)


if __name__ == "__main__":
    main()
