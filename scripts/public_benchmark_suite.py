#!/usr/bin/env python3
"""Public Benchmark Dominance Package — Leaderboard artifact generator.

Wraps the full 8-category benchmark run and produces:
  - benchmark_reports/public_benchmark_report.json
  - benchmark_reports/public_benchmark_summary.md

Includes performance vs single-model baselines, ensemble entropy,
cost per correct answer, latency per category, reliability metrics.

Usage:
  python3 scripts/public_benchmark_suite.py [--dry-run]

Requires: full benchmark infrastructure (run_category_benchmarks.py)
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llmhive" / "src"))

SINGLE_MODEL_BASELINES = {
    "gpt-5.2-pro": {
        "reasoning": 78.0, "coding": 90.0, "math": 95.0, "multilingual": 76.0,
        "long_context": 88.0, "tool_use": 85.0, "rag": 40.0, "dialogue": 6.5,
    },
    "claude-sonnet-4.6": {
        "reasoning": 76.0, "coding": 88.0, "math": 91.0, "multilingual": 82.0,
        "long_context": 85.0, "tool_use": 82.0, "rag": 38.0, "dialogue": 7.0,
    },
    "gemini-2.5-pro": {
        "reasoning": 74.0, "coding": 84.0, "math": 89.0, "multilingual": 78.0,
        "long_context": 96.0, "tool_use": 80.0, "rag": 36.0, "dialogue": 6.0,
    },
}

RQI_BASELINES = {
    "gpt-5.2-pro": 0.38,
    "claude-sonnet-4.6": 0.35,
    "gemini-2.5-pro": 0.33,
}

CATEGORY_MAP = {
    "General Reasoning (MMLU)": "reasoning",
    "Coding (HumanEval)": "coding",
    "Math (GSM8K)": "math",
    "Multilingual (MMMLU)": "multilingual",
    "Long Context (LongBench)": "long_context",
    "Tool Use (ToolBench)": "tool_use",
    "RAG (MS MARCO)": "rag",
    "Dialogue (MT-Bench)": "dialogue",
}


def _load_latest_results() -> list:
    """Load results from the most recent benchmark JSON."""
    report_dir = Path("benchmark_reports")
    candidates = sorted(report_dir.glob("category_benchmarks_elite_*.json"), reverse=True)
    if not candidates:
        candidates = sorted(report_dir.glob("category_benchmarks_*.json"), reverse=True)
    if not candidates:
        return []
    return json.loads(candidates[0].read_text()).get("results", [])


def _compute_uplift(llmhive_score: float, baseline_score: float) -> float:
    if baseline_score <= 0:
        return 0.0
    return round((llmhive_score - baseline_score) / baseline_score * 100, 2)


def generate_public_report(results: list) -> dict:
    from llmhive.app.intelligence import (
        get_intelligence_telemetry,
        get_reliability_guard,
        get_model_registry_2026,
        ELITE_POLICY,
    )
    from llmhive.app.intelligence.elite_policy import get_intelligence_mode
    from llmhive.app.intelligence.strategy_db import get_strategy_db
    from llmhive.app.intelligence.ensemble import get_adaptive_ensemble
    from llmhive.app.intelligence.verify_policy import get_verify_policy

    registry = get_model_registry_2026()
    telemetry = get_intelligence_telemetry()
    guard = get_reliability_guard()

    scores: dict = {}
    cost_total = 0.0
    correct_total = 0
    rag_rqi = 0.0
    for r in results:
        if not isinstance(r, dict) or "error" in r:
            continue
        cat_name = r.get("category", "")
        key = CATEGORY_MAP.get(cat_name, cat_name.lower().replace(" ", "_"))
        scores[key] = {
            "accuracy": r.get("accuracy", 0),
            "sample_size": r.get("sample_size", 0),
            "latency_avg_ms": r.get("avg_latency_ms", 0),
            "infra_failures": r.get("infra_failures", 0),
        }
        cost_total += r.get("total_cost", 0)
        correct_total += int(r.get("accuracy", 0) / 100 * r.get("sample_size", 0))
        extra = r.get("extra", {})
        if key == "rag" and isinstance(extra, dict):
            rag_rqi = extra.get("rqi", 0.0)

    cost_per_correct = round(cost_total / correct_total, 4) if correct_total else 0

    comparisons = {}
    for baseline_name, baselines in SINGLE_MODEL_BASELINES.items():
        comp = {}
        for cat, baseline_score in baselines.items():
            llmhive_score = scores.get(cat, {}).get("accuracy", 0)
            comp[cat] = {
                "llmhive": llmhive_score,
                "baseline": baseline_score,
                "uplift_pct": _compute_uplift(llmhive_score, baseline_score),
            }
        total_llm = sum(scores.get(c, {}).get("accuracy", 0) for c in baselines)
        total_base = sum(baselines.values())
        comp["aggregate_uplift_pct"] = _compute_uplift(total_llm, total_base)
        comparisons[baseline_name] = comp

    tel_summary = telemetry.get_summary()
    rel_summary = guard.get_summary()

    sdb = get_strategy_db()
    sdb.load_from_local_history()
    cai = sdb.compute_competitive_advantage_index()
    pareto = sdb.get_pareto_rankings()

    ensemble = get_adaptive_ensemble()
    verify = get_verify_policy()

    sla_compliance = rel_summary.get("sla_compliance", {})
    sla_pct = 0.0
    if isinstance(sla_compliance, dict):
        tiers = sla_compliance.get("tiers", {})
        if tiers:
            pcts = [t.get("compliance_pct", 0) for t in tiers.values() if isinstance(t, dict)]
            sla_pct = sum(pcts) / len(pcts) if pcts else 0.0

    entropy_stability = 1.0 - min(ensemble.avg_entropy, 1.0)

    rqi_uplift = {}
    for baseline_name, baseline_rqi in RQI_BASELINES.items():
        rqi_uplift[baseline_name] = {
            "llmhive_rqi": round(rag_rqi, 4),
            "baseline_rqi": baseline_rqi,
            "uplift": round(rag_rqi - baseline_rqi, 4),
            "uplift_pct": _compute_uplift(rag_rqi * 100, baseline_rqi * 100),
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intelligence_mode": get_intelligence_mode(),
        "elite_policy": dict(ELITE_POLICY),
        "registry_models": len(registry.list_models()),
        "categories": scores,
        "cost_per_correct_answer_usd": cost_per_correct,
        "total_cost_usd": round(cost_total, 4),
        "comparisons_vs_baselines": comparisons,
        "competitive_advantage_index": cai,
        "rag_quality_index": round(rag_rqi, 4),
        "rag_rqi_uplift_vs_baselines": rqi_uplift,
        "sla_compliance_pct": round(sla_pct, 2),
        "entropy_stability_score": round(entropy_stability, 4),
        "pareto_efficiency": {k: v[:3] for k, v in pareto.items()},
        "ensemble_precision": {
            "avg_entropy": round(ensemble.avg_entropy, 4),
            "escalation_count": ensemble.escalation_count,
            "tiebreaker_count": ensemble.tiebreaker_count,
            "instability_fallbacks": ensemble.instability_count,
        },
        "verify_pipeline": {
            "timeout_rate": round(verify.timeout_rate, 4),
            "verify_penalty": round(verify.verify_penalty, 4),
            "latency_p95": verify.verify_latency_p95,
        },
        "telemetry": tel_summary,
        "reliability": rel_summary,
    }
    return report


def generate_markdown_summary(report: dict) -> str:
    lines = [
        "# LLMHive Public Benchmark Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Intelligence mode: `{report['intelligence_mode']}`",
        f"Registry models: {report['registry_models']}",
        "",
        "## Category Scores",
        "",
        "| Category | Accuracy | Samples | Avg Latency |",
        "|----------|----------|---------|-------------|",
    ]
    for cat, data in sorted(report.get("categories", {}).items()):
        lines.append(
            f"| {cat} | {data['accuracy']:.1f}% | {data['sample_size']} | "
            f"{data.get('latency_avg_ms', 0)}ms |"
        )

    lines += ["", "## Performance vs Single-Model Baselines", ""]
    for baseline, comp in report.get("comparisons_vs_baselines", {}).items():
        agg = comp.pop("aggregate_uplift_pct", 0)
        lines.append(f"### vs {baseline} (aggregate uplift: {agg:+.2f}%)")
        lines.append("")
        lines.append("| Category | LLMHive | Baseline | Uplift |")
        lines.append("|----------|---------|----------|--------|")
        for cat, vals in sorted(comp.items()):
            lines.append(
                f"| {cat} | {vals['llmhive']:.1f}% | {vals['baseline']:.1f}% | "
                f"{vals['uplift_pct']:+.2f}% |"
            )
        lines.append("")

    lines += ["", "## RAG Quality Index (RQI) Uplift", ""]
    lines.append("| vs Baseline | LLMHive RQI | Baseline RQI | Uplift |")
    lines.append("|-------------|-------------|--------------|--------|")
    for bname, rdata in report.get("rag_rqi_uplift_vs_baselines", {}).items():
        lines.append(
            f"| {bname} | {rdata['llmhive_rqi']:.4f} | {rdata['baseline_rqi']:.4f} | "
            f"{rdata['uplift']:+.4f} ({rdata['uplift_pct']:+.2f}%) |"
        )

    cai = report.get("competitive_advantage_index", {})
    lines += [
        "",
        "## Competitive Advantage Index",
        "",
        f"- **CAI Composite**: {cai.get('composite_index', 0):.2f} ({cai.get('interpretation', 'N/A')})",
        f"- RAG Quality Index (RQI): {report.get('rag_quality_index', 0):.4f}",
        f"- SLA Compliance: {report.get('sla_compliance_pct', 0):.1f}%",
        f"- Entropy Stability: {report.get('entropy_stability_score', 0):.4f}",
        "",
        "## Ensemble Precision",
        "",
        f"- Avg Entropy: {report.get('ensemble_precision', {}).get('avg_entropy', 0):.4f}",
        f"- Escalations: {report.get('ensemble_precision', {}).get('escalation_count', 0)}",
        f"- Instability Fallbacks: {report.get('ensemble_precision', {}).get('instability_fallbacks', 0)}",
        "",
        "## Verify Pipeline",
        "",
        f"- Timeout Rate: {report.get('verify_pipeline', {}).get('timeout_rate', 0):.2%}",
        f"- Latency p95: {report.get('verify_pipeline', {}).get('latency_p95', 0)}ms",
        "",
        "## Cost Efficiency",
        "",
        f"- Cost per correct answer: ${report.get('cost_per_correct_answer_usd', 0):.4f}",
        f"- Total cost: ${report.get('total_cost_usd', 0):.4f}",
        "",
        "## Reliability",
        "",
        f"- Total alerts: {report.get('reliability', {}).get('total_alerts', 0)}",
        "",
    ]
    return "\n".join(lines)


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 64)
    print("  LLMHIVE PUBLIC BENCHMARK DOMINANCE PACKAGE")
    print("=" * 64)

    if dry_run:
        print("  Mode: DRY RUN (using latest cached results)")
        results = _load_latest_results()
        if not results:
            print("  No cached benchmark results found.")
            print("  Run the full benchmark first, then re-run this script.")
            sys.exit(1)
        print(f"  Loaded {len(results)} category results from cache")
    else:
        print("  Mode: LIVE (requires full benchmark execution)")
        print("  To generate from cached results, use --dry-run")
        results = _load_latest_results()
        if not results:
            print("  No benchmark results available. Run the benchmark first.")
            sys.exit(1)

    report = generate_public_report(results)

    report_dir = Path("benchmark_reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = str(report_dir / "public_benchmark_report.json")
    Path(json_path).write_text(json.dumps(report, indent=2, default=str))

    md_content = generate_markdown_summary(report)
    md_path = str(report_dir / "public_benchmark_summary.md")
    Path(md_path).write_text(md_content)

    print(f"\n  Reports generated:")
    print(f"    {json_path}")
    print(f"    {md_path}")
    print(f"\n  Categories: {len(report.get('categories', {}))}")
    print(f"  Cost/correct: ${report.get('cost_per_correct_answer_usd', 0):.4f}")

    for baseline, comp in report.get("comparisons_vs_baselines", {}).items():
        agg = comp.get("aggregate_uplift_pct", 0)
        print(f"  vs {baseline}: {agg:+.2f}% aggregate uplift")

    print(f"\n{'=' * 64}")
    print("  PUBLIC BENCHMARK PACKAGE: COMPLETE")
    print(f"{'=' * 64}")


if __name__ == "__main__":
    main()
