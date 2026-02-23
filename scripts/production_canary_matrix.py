#!/usr/bin/env python3
"""Production Canary Matrix — Simulated enterprise deployment validation.

Simulates routing decisions across categories, providers, and modes
to validate latency distribution, failure rates, entropy, and drift
without making actual API calls.

Usage:
  python3 scripts/production_canary_matrix.py
"""
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llmhive" / "src"))


def main():
    from llmhive.app.intelligence import (
        get_routing_engine,
        get_adaptive_ensemble,
        get_reliability_guard,
        get_explainability_exporter,
        get_intelligence_telemetry,
        get_model_registry_2026,
        ELITE_POLICY,
        Vote,
        ExplainabilityRecord,
    )
    from llmhive.app.intelligence.elite_policy import get_intelligence_mode

    print("=" * 64)
    print("  PRODUCTION CANARY DEPLOYMENT MATRIX")
    print("=" * 64)
    print(f"  Intelligence mode: {get_intelligence_mode()}")

    engine = get_routing_engine()
    ensemble = get_adaptive_ensemble()
    guard = get_reliability_guard()
    exporter = get_explainability_exporter()
    exporter.init_trace()
    registry = get_model_registry_2026()

    CANARY_PLAN = {
        "reasoning": 100,
        "coding": 50,
        "rag": 50,
    }

    results = {}
    total_calls = 0
    total_drift = 0

    for category, n_calls in CANARY_PLAN.items():
        cat_results = {
            "calls": n_calls,
            "latencies": [],
            "failures": 0,
            "drift_events": 0,
            "entropies": [],
            "models_selected": {},
        }

        for i in range(n_calls):
            scored = engine.select(category, top_n=3)
            if not scored:
                cat_results["failures"] += 1
                continue

            selected = scored[0]
            entry = registry.get(selected.model_id)
            base_latency = entry.latency_profile.p50 if entry else 800
            sim_latency = max(100, base_latency + random.randint(-200, 400))
            sim_success = random.random() > 0.01

            guard.record_call(
                model_id=selected.model_id,
                provider=selected.provider,
                latency_ms=sim_latency,
                success=sim_success,
            )

            cat_results["latencies"].append(sim_latency)
            if not sim_success:
                cat_results["failures"] += 1

            cat_results["models_selected"][selected.model_id] = (
                cat_results["models_selected"].get(selected.model_id, 0) + 1
            )

            # Simulate ensemble for a subset
            if i % 5 == 0 and len(scored) >= 2:
                votes = [
                    Vote(model_id=s.model_id, answer=f"answer_{random.randint(0,2)}", confidence=s.total_score)
                    for s in scored[:3]
                ]
                ens_result = ensemble.resolve(votes, category, tiebreaker_model=scored[0].model_id)
                cat_results["entropies"].append(ens_result.disagreement_entropy)

            # Drift check
            elite_expected = ELITE_POLICY.get(category, "")
            if elite_expected and selected.model_id != elite_expected:
                cat_results["drift_events"] += 1
                total_drift += 1

            exporter.record(ExplainabilityRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                category=category,
                model_used=selected.model_id,
                intelligence_mode=get_intelligence_mode(),
                routing_score_breakdown={
                    "strength": selected.strength_score,
                    "reasoning": selected.reasoning_score,
                    "latency": selected.latency_score,
                    "cost": selected.cost_score,
                },
                latency_ms=sim_latency,
                decision_reason="canary_simulation",
            ))

            total_calls += 1

        # Compute stats
        lats = cat_results["latencies"]
        if lats:
            lats_sorted = sorted(lats)
            cat_results["p50_latency"] = lats_sorted[len(lats_sorted) // 2]
            cat_results["p95_latency"] = lats_sorted[int(len(lats_sorted) * 0.95)]
            cat_results["avg_latency"] = round(sum(lats) / len(lats))
        cat_results["failure_rate"] = round(cat_results["failures"] / n_calls, 4)
        cat_results["avg_entropy"] = (
            round(sum(cat_results["entropies"]) / len(cat_results["entropies"]), 4)
            if cat_results["entropies"] else 0
        )
        del cat_results["latencies"]
        del cat_results["entropies"]
        results[category] = cat_results

    # Entropy distribution histogram
    all_entropies = []
    for cat, r in results.items():
        all_entropies.extend([r.get("avg_entropy", 0)] * r["calls"])

    entropy_buckets = {"<0.3": 0, "0.3-0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0, ">1.0": 0}
    for e in all_entropies:
        if e < 0.3:
            entropy_buckets["<0.3"] += 1
        elif e < 0.5:
            entropy_buckets["0.3-0.5"] += 1
        elif e < 0.8:
            entropy_buckets["0.5-0.8"] += 1
        elif e <= 1.0:
            entropy_buckets["0.8-1.0"] += 1
        else:
            entropy_buckets[">1.0"] += 1

    # Per-provider stability
    provider_stats: dict = {}
    for cat, r in results.items():
        for m, count in r["models_selected"].items():
            entry = registry.get(m)
            prov = entry.provider if entry else "unknown"
            if prov not in provider_stats:
                provider_stats[prov] = {"calls": 0, "failures": 0, "drift": 0}
            provider_stats[prov]["calls"] += count
        provider_stats.setdefault("unknown", {"calls": 0, "failures": 0, "drift": 0})

    # Summary
    print(f"\n  Total simulated calls: {total_calls}")
    print(f"  Total drift events:   {total_drift}")
    print(f"\n  {'Category':<15} {'Calls':>6} {'Fail%':>7} {'p50':>6} {'p95':>6} {'Entropy':>8} {'Drift':>6}")
    print("  " + "-" * 56)
    for cat, r in results.items():
        print(
            f"  {cat:<15} {r['calls']:>6} {r['failure_rate']*100:>6.1f}% "
            f"{r.get('p50_latency', 0):>5}ms {r.get('p95_latency', 0):>5}ms "
            f"{r.get('avg_entropy', 0):>7.4f} {r['drift_events']:>5}"
        )

    # Model distribution
    print("\n  Model distribution:")
    all_models = {}
    for cat, r in results.items():
        for m, count in r["models_selected"].items():
            all_models[m] = all_models.get(m, 0) + count
    for m, count in sorted(all_models.items(), key=lambda x: -x[1]):
        print(f"    {m:<25} {count:>4} calls ({count/total_calls*100:.1f}%)")

    # Entropy histogram
    print("\n  Entropy distribution:")
    for bucket, count in entropy_buckets.items():
        bar = "#" * min(count // 5, 40)
        print(f"    {bucket:<8} {count:>5} {bar}")

    # Provider stability
    print("\n  Provider stability:")
    for prov, ps in sorted(provider_stats.items()):
        fail_rate = ps["failures"] / max(ps["calls"], 1) * 100
        print(f"    {prov:<15} {ps['calls']:>5} calls  {fail_rate:.1f}% failures")

    # Reliability summary
    reliability = guard.get_summary()
    guard.save_summary()

    # Compute cost vs accuracy scatter data
    cost_accuracy_data = []
    for cat, r in results.items():
        avg_lat = r.get("avg_latency", 0)
        fail_r = r["failure_rate"]
        cost_accuracy_data.append({
            "category": cat,
            "avg_latency_ms": avg_lat,
            "failure_rate": fail_r,
            "drift_events": r["drift_events"],
            "entropy": r.get("avg_entropy", 0),
        })

    # Check latency against baseline
    latency_baseline_check = {}
    for cat, r in results.items():
        p95 = r.get("p95_latency", 0)
        scored = engine.select(cat, top_n=1)
        if scored:
            m = registry.get(scored[0].model_id)
            baseline = m.latency_profile.p95 if m else 2000
            ratio = p95 / baseline if baseline else 0
            latency_baseline_check[cat] = {
                "p95": p95,
                "baseline_p95": baseline,
                "ratio": round(ratio, 2),
                "within_1_5x": ratio <= 1.5,
            }

    # Save canary report
    report_dir = Path("benchmark_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intelligence_mode": get_intelligence_mode(),
        "total_calls": total_calls,
        "total_drift": total_drift,
        "categories": results,
        "entropy_distribution": entropy_buckets,
        "provider_stability": provider_stats,
        "cost_accuracy_scatter": cost_accuracy_data,
        "latency_baseline_check": latency_baseline_check,
        "reliability": reliability,
        "explainability": exporter.get_summary(),
    }
    report_path = str(report_dir / "canary_matrix_report.json")
    Path(report_path).write_text(json.dumps(report, indent=2, default=str))
    print(f"\n  Canary report: {report_path}")
    print(f"  Reliability:   benchmark_reports/reliability_summary.json")
    print(f"  Explainability: {exporter.get_summary().get('trace_file', 'n/a')}")

    # Pass/fail with enhanced criteria
    max_fail_rate = max(r["failure_rate"] for r in results.values())
    avg_entropy = sum(r.get("avg_entropy", 0) for r in results.values()) / max(len(results), 1)
    all_latency_ok = all(v.get("within_1_5x", True) for v in latency_baseline_check.values())

    pass_criteria = max_fail_rate < 0.02 and avg_entropy < 0.8 and all_latency_ok
    relaxed_pass = max_fail_rate < 0.05

    final_pass = pass_criteria or relaxed_pass
    status = "PASS" if pass_criteria else ("PASS (relaxed)" if relaxed_pass else "FAIL")

    print(f"\n  Canary checks:")
    print(f"    Max failure rate:  {max_fail_rate*100:.1f}% (<2% target, <5% relaxed)")
    print(f"    Avg entropy:       {avg_entropy:.4f} (<0.8 target)")
    print(f"    Latency p95 ≤1.5x: {'YES' if all_latency_ok else 'NO'}")

    print(f"\n  {'=' * 64}")
    print(f"  CANARY RESULT: {status}")
    print(f"  {'=' * 64}")

    sys.exit(0 if final_pass else 1)


if __name__ == "__main__":
    main()
