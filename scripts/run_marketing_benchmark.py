#!/usr/bin/env python3
"""Marketing Benchmark Pack — produce public-facing benchmark artifacts.

Uses existing benchmark runner + gate results to generate:
  1. A public markdown summary (benchmark_reports/marketing_benchmark.md)
  2. A JSON artifact with methods, slices, version manifests, and distributions
     (benchmark_reports/marketing_benchmark.json)

Required:
  - An existing elite_plus_eval_*.json report
  - An existing rc_summary.json or gate result

Usage:
    python scripts/run_marketing_benchmark.py
    python scripts/run_marketing_benchmark.py --run-bench  # also runs benchmarks first
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_REPORTS = _ROOT / "benchmark_reports"
_OUTPUT_JSON = _REPORTS / "marketing_benchmark.json"
_OUTPUT_MD = _REPORTS / "marketing_benchmark.md"


def _parse_args() -> Dict[str, bool]:
    return {"run_bench": "--run-bench" in sys.argv}


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _find_latest(pattern: str) -> Path | None:
    candidates = []
    for d in [_REPORTS, _ROOT / "scripts" / "benchmark_reports"]:
        if d.exists():
            candidates.extend(d.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_mtime)


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(_ROOT))
        return r.stdout.strip()[:12] if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _registry_version() -> str:
    try:
        sys.path.insert(0, str(_ROOT / "llmhive" / "src"))
        from llmhive.app.orchestration.model_registry import MODEL_REGISTRY_VERSION
        return MODEL_REGISTRY_VERSION
    except Exception:
        return "unknown"


def _manifest_version() -> str:
    manifest = _load_json(_ROOT / "public" / "release_manifest.json")
    return manifest.get("model_registry_version", "unknown")


def main():
    args = _parse_args()
    t0 = time.time()

    print("=" * 70)
    print("MARKETING BENCHMARK PACK")
    print("=" * 70)

    if args["run_bench"]:
        print("\n[1/3] Running benchmarks...")
        subprocess.run(
            [sys.executable, "scripts/run_release_candidate.py"],
            cwd=str(_ROOT), check=False,
        )
    else:
        print("\n[1/3] Using existing benchmark data")

    # Load data
    eval_file = _find_latest("elite_plus_eval_*.json")
    rc_summary = _load_json(_REPORTS / "rc_summary.json")
    gate_latest = _find_latest("launch_candidate_gate_*.json")
    gate = _load_json(gate_latest) if gate_latest else {}

    if not eval_file:
        print("  WARNING: No elite_plus_eval report found. Using gate data only.")
        eval_data = {}
    else:
        eval_data = _load_json(eval_file)
        print(f"  Eval report: {eval_file.name}")

    print("[2/3] Building artifacts...")

    git_sha = _git_sha()
    reg_ver = _registry_version()
    man_ver = _manifest_version()
    now = datetime.now().isoformat()

    # Category results
    category_results = gate.get("category_results", rc_summary.get("category_results", {}))
    categories: List[Dict[str, Any]] = []
    for cat, cr in sorted(category_results.items()):
        checks = cr.get("checks", {})
        categories.append({
            "category": cat,
            "priority": cr.get("priority", "P2"),
            "sample_count": cr.get("sample_count", 0),
            "score": checks.get("score", {}).get("actual", checks.get("score", 0)),
            "cost_usd_avg": checks.get("cost_usd_avg", {}).get("actual",
                             checks.get("avg_cost_usd", {}).get("value", 0)),
            "paid_call_pct": checks.get("paid_call_pct", {}).get("actual",
                              checks.get("paid_call_pct", {}).get("value", 0)),
            "pass": cr.get("pass", False),
            "stage_distribution": cr.get("stage_distribution", {}),
        })

    # Global metrics
    global_result = gate.get("global_result", rc_summary.get("global_result", {}))
    cost_p50 = global_result.get("cost_p50_usd", 0)
    cost_p95 = global_result.get("cost_p95_usd", 0)
    lat_p50 = global_result.get("latency_p50_ms", 0)
    lat_p95 = global_result.get("latency_p95_ms", 0)
    if isinstance(lat_p95, dict):
        lat_p95 = lat_p95.get("actual", 0)
    if isinstance(lat_p50, dict):
        lat_p50 = lat_p50.get("actual", 0)

    total_samples = gate.get("total_samples", rc_summary.get("total_samples", 0))
    gate_status = rc_summary.get("gate_status", gate.get("gate_pass", "unknown"))
    if isinstance(gate_status, bool):
        gate_status = "pass" if gate_status else "fail"

    # Build JSON artifact
    artifact = {
        "title": "LLMHive Elite+ Benchmark Report",
        "generated_at": now,
        "methods": {
            "orchestration": "Elite+ free-first verified premium pipeline",
            "policy": "free_first_verified (Stage A → B → C → D)",
            "evaluation": "Paired comparison against Elite baseline",
            "scoring": "Deterministic verification + paid escalation metrics",
        },
        "version_manifest": {
            "orchestrator_revision": git_sha,
            "model_registry_version": reg_ver,
            "release_manifest_version": man_ver,
        },
        "gate_status": gate_status,
        "total_samples": total_samples,
        "cost_distribution": {
            "p50_usd": cost_p50,
            "p95_usd": cost_p95,
            "budget_p50_target": 0.010,
            "budget_p95_target": 0.020,
        },
        "latency_distribution": {
            "p50_ms": lat_p50,
            "p95_ms": lat_p95,
        },
        "paid_escalation_rate": {
            "overall_pct": sum(c.get("paid_call_pct", 0) for c in categories) / max(len(categories), 1),
        },
        "categories": categories,
        "p0_failures": rc_summary.get("p0_failures", gate.get("p0_failures", [])),
    }

    _OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_JSON.write_text(json.dumps(artifact, indent=2, default=str) + "\n")

    # Build markdown summary
    md_lines = [
        "# LLMHive Elite+ Benchmark Report",
        "",
        f"**Generated:** {now}",
        f"**Orchestrator revision:** `{git_sha}`",
        f"**Registry version:** {reg_ver}",
        f"**Release manifest version:** {man_ver}",
        f"**Gate status:** {gate_status.upper()}",
        f"**Total samples:** {total_samples}",
        "",
        "## Cost & Latency",
        "",
        f"| Metric | Value | Target |",
        f"|--------|-------|--------|",
        f"| Cost p50 | ${cost_p50:.4f} | <= $0.010 |",
        f"| Cost p95 | ${cost_p95:.4f} | <= $0.020 |",
        f"| Latency p50 | {lat_p50}ms | — |",
        f"| Latency p95 | {lat_p95}ms | — |",
        "",
        "## Category Results",
        "",
        "| Category | Priority | Samples | Score | Cost Avg | Paid % | Pass |",
        "|----------|----------|---------|-------|----------|--------|------|",
    ]

    for c in categories:
        score = c["score"]
        score_str = f"{score:.3f}" if isinstance(score, float) else str(score)
        cost_str = f"${c['cost_usd_avg']:.4f}" if c["cost_usd_avg"] else "$0.00"
        pass_str = "Yes" if c["pass"] else "**NO**"
        md_lines.append(
            f"| {c['category']} | {c['priority']} | {c['sample_count']} | "
            f"{score_str} | {cost_str} | {c['paid_call_pct']:.1f}% | {pass_str} |"
        )

    md_lines.extend([
        "",
        "## Methodology",
        "",
        "- **Pipeline:** Elite+ free-first verified premium (Stage A: free ensemble → "
        "Stage B: deterministic verification → Stage C: paid escalation → Stage D: fallback)",
        "- **Policy:** `free_first_verified` — free models handle the query first; "
        "paid anchors invoked only on verification failure",
        "- **Cost governance:** Per-request ceiling ($0.025), per-account daily/monthly budgets, "
        "global emergency breaker",
        "- **Evaluation:** Paired comparison with Elite baseline using category-specific metrics",
        "",
        "---",
        f"*Report generated by `scripts/run_marketing_benchmark.py` at {now}*",
    ])

    _OUTPUT_MD.write_text("\n".join(md_lines) + "\n")

    elapsed = round(time.time() - t0, 1)
    print(f"\n[3/3] Artifacts written ({elapsed}s)")
    print(f"  JSON: {_OUTPUT_JSON}")
    print(f"  Markdown: {_OUTPUT_MD}")
    print(f"  Gate: {gate_status.upper()}")
    print(f"  Categories: {len(categories)}")
    print(f"  Samples: {total_samples}")


if __name__ == "__main__":
    main()
