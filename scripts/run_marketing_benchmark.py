#!/usr/bin/env python3
"""Marketing Benchmark Pack — produce public-facing benchmark artifacts.

Uses gate result + eval artifacts to generate:
  1. A public markdown summary (benchmark_reports/marketing_benchmark.md)
  2. A JSON artifact with methods, slices, version manifests, and distributions
     (benchmark_reports/marketing_benchmark.json)

Required (no silent UNKNOWN):
  - Gate result: via --gate-json <path> OR --require-gate-pass
  - Eval artifact: required when --require-eval (recommended for marketing-certified pack)

Usage:
    python scripts/run_marketing_benchmark.py --gate-json benchmark_reports/latest/gate_result.json --require-eval
    python scripts/run_marketing_benchmark.py --require-gate-pass --require-eval
    python scripts/run_marketing_benchmark.py --run-bench  # runs benchmarks first, then requires gate
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

_MISSING_ARTIFACTS_MSG = (
    "Missing elite_plus_eval artifacts; run scripts/run_marketing_certified_release.py "
    "or scripts/run_final_certification.py without --offline."
)


def _parse_args() -> Dict[str, Any]:
    args: Dict[str, Any] = {
        "run_bench": False,
        "gate_json": None,
        "require_gate_pass": False,
        "require_eval": False,
    }
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--run-bench":
            args["run_bench"] = True
            i += 1
        elif sys.argv[i] == "--gate-json" and i + 1 < len(sys.argv):
            args["gate_json"] = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--require-gate-pass":
            args["require_gate_pass"] = True
            i += 1
        elif sys.argv[i] == "--require-eval":
            args["require_eval"] = True
            i += 1
        else:
            i += 1
    return args


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


def main() -> None:
    args = _parse_args()
    t0 = time.time()

    print("=" * 70)
    print("MARKETING BENCHMARK PACK")
    print("=" * 70)

    if args["run_bench"]:
        print("\n[1/4] Running benchmarks...")
        subprocess.run(
            [sys.executable, "scripts/run_release_candidate.py"],
            cwd=str(_ROOT), check=False,
        )
    else:
        print("\n[1/4] Using existing benchmark data")

    # Resolve gate source
    gate_path: Path | None = None
    if args["gate_json"]:
        p = Path(args["gate_json"])
        gate_path = p if p.is_absolute() else (_ROOT / p)
        if not gate_path.exists():
            print(f"ERROR: Gate file not found: {args['gate_json']}")
            sys.exit(2)
    elif args["require_gate_pass"]:
        gate_latest = _find_latest("launch_candidate_gate_*.json")
        if not gate_latest:
            alt = _REPORTS / "latest" / "gate_result.json"
            if alt.exists():
                gate_path = alt
            else:
                print("ERROR: No gate result found in benchmark_reports/")
                print(f"  {_MISSING_ARTIFACTS_MSG}")
                sys.exit(2)
        else:
            gate_path = gate_latest
    else:
        print("ERROR: Gate result required. Use --gate-json <path> or --require-gate-pass")
        print(f"  {_MISSING_ARTIFACTS_MSG}")
        sys.exit(2)

    gate = _load_json(gate_path)
    if not gate:
        print(f"ERROR: Gate file empty or invalid: {gate_path}")
        sys.exit(2)

    # Resolve eval source
    eval_file = _find_latest("elite_plus_eval_*.json")
    if args["require_eval"] and not eval_file:
        print("ERROR: No elite_plus_eval_*.json report found.")
        print(f"  {_MISSING_ARTIFACTS_MSG}")
        sys.exit(2)
    try:
        eval_source = str(eval_file.relative_to(_ROOT)) if eval_file else ""
    except (ValueError, TypeError):
        eval_source = str(eval_file) if eval_file else ""

    print(f"  Gate:   {gate_path.relative_to(_ROOT) if gate_path.is_relative_to(_ROOT) else gate_path}")
    print(f"  Eval:   {eval_source or '(none)'}")

    print("[2/4] Building artifacts...")

    rc_summary = _load_json(_REPORTS / "rc_summary.json")
    git_sha_val = _git_sha()
    reg_ver = _registry_version()
    man_ver = _manifest_version()
    now = datetime.now().isoformat()

    # Category results from gate (primary source)
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
    gate_pass = gate.get("gate_pass", False)
    gate_status = "pass" if gate_pass else "fail"
    if isinstance(gate_status, bool):
        gate_status = "pass" if gate_status else "fail"
    # Never allow UNKNOWN
    if gate_status not in ("pass", "fail"):
        print("ERROR: Gate status cannot be determined (must be pass or fail)")
        sys.exit(2)

    try:
        gate_source_str = str(gate_path.relative_to(_ROOT))
    except ValueError:
        gate_source_str = str(gate_path)

    # Build JSON artifact
    artifact = {
        "title": "LLMHive Elite+ Benchmark Report",
        "generated_at": now,
        "gate_status": gate_status,
        "gate_source": gate_source_str,
        "eval_source": eval_source,
        "methods": {
            "orchestration": "Elite+ free-first verified premium pipeline",
            "policy": "free_first_verified (Stage A → B → C → D)",
            "evaluation": "Paired comparison against Elite baseline",
            "scoring": "Deterministic verification + paid escalation metrics",
        },
        "version_manifest": {
            "orchestrator_revision": git_sha_val,
            "model_registry_version": reg_ver,
            "release_manifest_version": man_ver,
        },
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
        f"**Orchestrator revision:** `{git_sha_val}`",
        f"**Registry version:** {reg_ver}",
        f"**Release manifest version:** {man_ver}",
        f"**Gate status:** {gate_status.upper()}",
        f"**Gate source:** {gate_source_str}",
        f"**Eval source:** {eval_source or 'N/A'}",
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
    print(f"\n[3/4] Artifacts written ({elapsed}s)")
    print(f"  JSON: {_OUTPUT_JSON}")
    print(f"  Markdown: {_OUTPUT_MD}")
    print(f"  Gate: {gate_status.upper()} (source: {gate_source_str})")
    print(f"  Eval: {eval_source or 'N/A'}")
    print(f"  Categories: {len(categories)}")
    print(f"  Samples: {total_samples}")


if __name__ == "__main__":
    main()
