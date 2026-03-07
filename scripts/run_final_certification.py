#!/usr/bin/env python3
"""Final World-Class Launch Certification — Full Benchmark + Threshold Enforcement.

Runs the complete Elite+ benchmark suite with production sample sizes, then
evaluates results against marketing-grade certification thresholds.

Certification thresholds:
  - Any P0 category below floor → FAIL
  - Avg cost > $0.020 → FAIL
  - p95 cost > $0.025 → FAIL
  - Paid escalation rate > 35% → FAIL

Usage:
    python scripts/run_final_certification.py
    python scripts/run_final_certification.py --skip-bench   # use existing reports
    python scripts/run_final_certification.py --offline       # offline-only checks
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_REPORTS = _ROOT / "benchmark_reports"
_OUTPUT = _REPORTS / "final_launch_certification.json"
_MARKETING_JSON = _REPORTS / "marketing_benchmark.json"
_MARKETING_MD = _REPORTS / "marketing_benchmark.md"

CERTIFICATION_SAMPLE_SIZES = {
    "math": 100,
    "coding": 50,
    "reasoning": 100,
    "multilingual": 100,
    "long_context": 50,
    "tool_use": 50,
    "rag": 200,
    "dialogue": 30,
}

CERTIFICATION_THRESHOLDS = {
    "max_avg_cost_usd": 0.020,
    "max_p95_cost_usd": 0.025,
    "max_paid_escalation_pct": 35.0,
}

sys.path.insert(0, str(_ROOT / "llmhive" / "src"))


def _parse_args() -> Dict[str, Any]:
    return {
        "skip_bench": "--skip-bench" in sys.argv,
        "offline": "--offline" in sys.argv,
    }


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _find_latest(pattern: str) -> Path | None:
    candidates = []
    for d in [_REPORTS, _ROOT / "scripts" / "benchmark_reports"]:
        if d.exists():
            candidates.extend(d.glob(pattern))
    return max(candidates, key=lambda f: f.stat().st_mtime) if candidates else None


def _git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(_ROOT),
        )
        return r.stdout.strip()[:12] if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _run(cmd: list, env_extra: dict = None, check: bool = False) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(_ROOT), env=env, capture_output=False, check=check)


def _run_benchmarks() -> int:
    """Run full benchmark suite with certification sample sizes."""
    env_extra = {
        "ELITE_PLUS_EVAL": "1",
        "ALLOW_INTERNAL_BENCH_OUTPUT": "1",
        "CATEGORY_BENCH_TIER": "elite",
        "ELITE_PLUS_LAUNCH_MODE": "1",
        "ELITE_PLUS_MODE": "active",
        "CATEGORY_BENCH_MMLU_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["reasoning"]),
        "CATEGORY_BENCH_HUMANEVAL_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["coding"]),
        "CATEGORY_BENCH_GSM8K_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["math"]),
        "CATEGORY_BENCH_MMMLU_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["multilingual"]),
        "CATEGORY_BENCH_LONGBENCH_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["long_context"]),
        "CATEGORY_BENCH_TOOLBENCH_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["tool_use"]),
        "CATEGORY_BENCH_MSMARCO_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["rag"]),
        "CATEGORY_BENCH_MTBENCH_SAMPLES": str(CERTIFICATION_SAMPLE_SIZES["dialogue"]),
    }
    result = _run(
        [sys.executable, "scripts/run_category_benchmarks.py"],
        env_extra=env_extra,
    )
    return result.returncode


def _run_gate() -> int:
    gate_output = _REPORTS / "latest" / "gate_result.json"
    result = _run(
        [sys.executable, "scripts/run_launch_candidate_gate.py",
         "--output", str(gate_output)],
    )
    return result.returncode


def _regenerate_marketing():
    _run([sys.executable, "scripts/run_marketing_benchmark.py"])


def _evaluate_certification(gate_data: dict, eval_data: dict) -> Dict[str, Any]:
    """Evaluate results against certification thresholds."""
    failures: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {}

    category_results = gate_data.get("category_results", {})
    global_result = gate_data.get("global_result", {})

    # P0 category floor check
    p0_categories = {"tool_use", "rag", "dialogue", "math"}
    for cat, cr in category_results.items():
        if cr.get("priority") == "P0" or cat in p0_categories:
            if not cr.get("pass", False):
                failures.append(f"P0 category '{cat}' below floor")

    # Cost metrics
    cost_p50 = global_result.get("cost_p50_usd", 0)
    cost_p95 = global_result.get("cost_p95_usd", 0)
    if isinstance(cost_p50, dict):
        cost_p50 = cost_p50.get("actual", 0)
    if isinstance(cost_p95, dict):
        cost_p95 = cost_p95.get("actual", 0)

    total_samples = gate_data.get("total_samples", 0)
    all_costs = []
    all_paid_pcts = []
    for cat, cr in category_results.items():
        checks = cr.get("checks", {})
        cost_avg = checks.get("cost_usd_avg", {})
        if isinstance(cost_avg, dict):
            cost_avg = cost_avg.get("actual", 0)
        all_costs.append(cost_avg)

        paid_pct = checks.get("paid_call_pct", {})
        if isinstance(paid_pct, dict):
            paid_pct = paid_pct.get("actual", 0)
        all_paid_pcts.append(paid_pct)

    avg_cost = sum(all_costs) / max(len(all_costs), 1) if all_costs else 0
    avg_paid_pct = sum(all_paid_pcts) / max(len(all_paid_pcts), 1) if all_paid_pcts else 0

    metrics["cost_p50_usd"] = cost_p50
    metrics["cost_p95_usd"] = cost_p95
    metrics["avg_cost_usd"] = round(avg_cost, 6)
    metrics["paid_escalation_pct"] = round(avg_paid_pct, 2)
    metrics["total_samples"] = total_samples

    if avg_cost > CERTIFICATION_THRESHOLDS["max_avg_cost_usd"]:
        failures.append(
            f"avg_cost=${avg_cost:.4f} > ceiling=${CERTIFICATION_THRESHOLDS['max_avg_cost_usd']}"
        )

    if cost_p95 > CERTIFICATION_THRESHOLDS["max_p95_cost_usd"]:
        failures.append(
            f"p95_cost=${cost_p95:.4f} > ceiling=${CERTIFICATION_THRESHOLDS['max_p95_cost_usd']}"
        )

    if avg_paid_pct > CERTIFICATION_THRESHOLDS["max_paid_escalation_pct"]:
        failures.append(
            f"paid_escalation={avg_paid_pct:.1f}% > ceiling={CERTIFICATION_THRESHOLDS['max_paid_escalation_pct']}%"
        )

    # Latency
    lat_p50 = global_result.get("latency_p50_ms", 0)
    lat_p95 = global_result.get("latency_p95_ms", 0)
    if isinstance(lat_p50, dict):
        lat_p50 = lat_p50.get("actual", 0)
    if isinstance(lat_p95, dict):
        lat_p95 = lat_p95.get("actual", 0)
    metrics["latency_p50_ms"] = lat_p50
    metrics["latency_p95_ms"] = lat_p95

    # RAG grounding rate
    rag_cr = category_results.get("rag", {})
    rag_checks = rag_cr.get("checks", {})
    rag_ungrounded = rag_checks.get("rag_ungrounded_pct", {})
    if isinstance(rag_ungrounded, dict):
        rag_ungrounded = rag_ungrounded.get("actual", 0)
    metrics["rag_grounding_rate_pct"] = round(100.0 - float(rag_ungrounded or 0), 2)

    # Tool error rate
    tool_cr = category_results.get("tool_use", {})
    tool_checks = tool_cr.get("checks", {})
    tool_error = tool_checks.get("tool_error_rate_pct", {})
    if isinstance(tool_error, dict):
        tool_error = tool_error.get("actual", 0)
    metrics["tool_error_rate_pct"] = float(tool_error or 0)

    # Per-category summary
    category_summary = {}
    for cat, cr in category_results.items():
        checks = cr.get("checks", {})
        score = checks.get("score", {})
        if isinstance(score, dict):
            score = score.get("actual", 0)
        category_summary[cat] = {
            "priority": cr.get("priority", "P2"),
            "pass": cr.get("pass", False),
            "sample_count": cr.get("sample_count", 0),
            "score": score,
        }
    metrics["categories"] = category_summary

    return {
        "metrics": metrics,
        "failures": failures,
        "warnings": warnings,
        "certified": len(failures) == 0,
    }


def _build_offline_certification() -> Dict[str, Any]:
    """Offline certification using spend governor and config checks."""
    from llmhive.app.orchestration.tier_spend_governor import (
        TierSpendGovernor, InMemoryLedger, SpendDecision,
    )
    from llmhive.app.orchestration.internal_auth import (
        is_internal_request, sanitize_internal_flags,
    )

    failures = []
    checks = []

    gov = TierSpendGovernor(ledger=InMemoryLedger())

    # Free tier blocks paid
    dec = gov.evaluate("free", "cert_free_01", 0.01)
    ok = not dec.allowed_paid_escalation
    checks.append({"check": "free_tier_blocks_paid", "pass": ok})
    if not ok:
        failures.append("free_tier_blocks_paid: FAIL")

    # Elite+ allows within budget
    dec = gov.evaluate("elite+", "cert_elite_01", 0.01)
    ok = dec.allowed_paid_escalation
    checks.append({"check": "elite_plus_allows_within_budget", "pass": ok})
    if not ok:
        failures.append("elite_plus_allows_within_budget: FAIL")

    # Elite+ blocks over ceiling
    dec = gov.evaluate("elite+", "cert_elite_02", 0.10)
    ok = not dec.allowed_paid_escalation
    checks.append({"check": "elite_plus_blocks_over_ceiling", "pass": ok})
    if not ok:
        failures.append("elite_plus_blocks_over_ceiling: FAIL")

    # Config sanity
    elite_enabled = os.getenv("ELITE_PLUS_ENABLED", "1")
    ok = elite_enabled == "1"
    checks.append({"check": "elite_plus_enabled", "pass": ok})
    if not ok:
        failures.append("elite_plus_enabled: FAIL")

    mode = os.getenv("ELITE_PLUS_MODE", "active")
    ok = mode in ("active", "shadow")
    checks.append({"check": "elite_plus_mode_valid", "pass": ok, "detail": f"mode={mode}"})
    if not ok:
        failures.append(f"elite_plus_mode_valid: mode={mode} not in (active, shadow)")

    # Internal auth rejects fake key
    fake_headers = {"X-LLMHive-Internal-Key": "fake_key_123"}
    ok = not is_internal_request(fake_headers)
    checks.append({"check": "internal_auth_rejects_fake", "pass": ok})
    if not ok:
        failures.append("internal_auth_rejects_fake: FAIL")

    # Registry version matches
    try:
        from llmhive.app.orchestration.model_registry import MODEL_REGISTRY_VERSION
        models_json = _load_json(_ROOT / "public" / "models.json")
        ok = models_json.get("registryVersion") == MODEL_REGISTRY_VERSION
        checks.append({"check": "registry_version_sync", "pass": ok})
        if not ok:
            failures.append("registry_version_sync: FAIL")
    except Exception as e:
        checks.append({"check": "registry_version_sync", "pass": False, "error": str(e)})
        failures.append(f"registry_version_sync: {e}")

    return {
        "checks": checks,
        "failures": failures,
        "certified": len(failures) == 0,
    }


def main():
    args = _parse_args()
    t0 = time.time()
    now = datetime.now(timezone.utc).isoformat()

    print("=" * 70)
    print("FINAL WORLD-CLASS LAUNCH CERTIFICATION")
    print("=" * 70)
    print(f"  Time: {now}")
    print(f"  Sample sizes: {CERTIFICATION_SAMPLE_SIZES}")
    print(f"  Thresholds: {CERTIFICATION_THRESHOLDS}")
    print()

    _REPORTS.mkdir(exist_ok=True)
    (_REPORTS / "latest").mkdir(exist_ok=True)

    # Phase 1: Offline certification (always runs)
    print("[1/4] Running offline certification checks...")
    offline_result = _build_offline_certification()
    for c in offline_result["checks"]:
        status = "PASS" if c["pass"] else "FAIL"
        print(f"  {status}: {c['check']}")

    if args["offline"]:
        cert = {
            "title": "LLMHive Final Launch Certification",
            "generated_at": now,
            "mode": "offline",
            "git_sha": _git_sha(),
            "offline_certification": offline_result,
            "certified": offline_result["certified"],
            "failures": offline_result["failures"],
        }
        _OUTPUT.write_text(json.dumps(cert, indent=2, default=str) + "\n")
        print(f"\n  Offline certification: {'PASS' if cert['certified'] else 'FAIL'}")
        print(f"  Output: {_OUTPUT}")
        sys.exit(0 if cert["certified"] else 1)

    # Phase 2: Run benchmarks
    if not args["skip_bench"]:
        print("\n[2/4] Running full benchmark suite...")
        print(f"  Total samples: {sum(CERTIFICATION_SAMPLE_SIZES.values())}")
        bench_rc = _run_benchmarks()
        if bench_rc != 0:
            print(f"  WARNING: Benchmarks exited with code {bench_rc}")
    else:
        print("\n[2/4] Skipping benchmarks (--skip-bench)")

    # Phase 3: Run gate + marketing
    print("\n[3/4] Running launch gate + marketing pack...")
    gate_rc = _run_gate()
    _regenerate_marketing()

    # Phase 4: Evaluate certification thresholds
    print("\n[4/4] Evaluating certification thresholds...")
    gate_file = _find_latest("launch_candidate_gate_*.json")
    if not gate_file:
        gate_file = _REPORTS / "latest" / "gate_result.json"
    gate_data = _load_json(gate_file) if gate_file and gate_file.exists() else {}

    eval_file = _find_latest("elite_plus_eval_*.json")
    eval_data = _load_json(eval_file) if eval_file else {}

    bench_result = _evaluate_certification(gate_data, eval_data)

    # Registry info
    try:
        from llmhive.app.orchestration.model_registry import MODEL_REGISTRY_VERSION
    except ImportError:
        MODEL_REGISTRY_VERSION = "unknown"

    manifest = _load_json(_ROOT / "public" / "release_manifest.json")

    cert = {
        "title": "LLMHive Final Launch Certification",
        "generated_at": now,
        "mode": "full",
        "git_sha": _git_sha(),
        "version_manifest": {
            "model_registry_version": MODEL_REGISTRY_VERSION,
            "release_manifest_version": manifest.get("model_registry_version", "unknown"),
        },
        "sample_sizes": CERTIFICATION_SAMPLE_SIZES,
        "thresholds": CERTIFICATION_THRESHOLDS,
        "gate_passed": gate_rc == 0,
        "offline_certification": offline_result,
        "benchmark_certification": bench_result,
        "metrics": bench_result.get("metrics", {}),
        "failures": offline_result["failures"] + bench_result.get("failures", []),
        "certified": offline_result["certified"] and bench_result.get("certified", False),
    }

    _OUTPUT.write_text(json.dumps(cert, indent=2, default=str) + "\n")

    elapsed = round(time.time() - t0, 1)
    print(f"\n{'=' * 70}")
    print(f"FINAL CERTIFICATION: {'PASS' if cert['certified'] else 'FAIL'}")
    print(f"{'=' * 70}")
    print(f"  Elapsed: {elapsed}s")
    print(f"  Total samples: {cert['metrics'].get('total_samples', 'N/A')}")
    print(f"  Avg cost: ${cert['metrics'].get('avg_cost_usd', 0):.4f} (max: $0.020)")
    print(f"  p95 cost: ${cert['metrics'].get('cost_p95_usd', 0):.4f} (max: $0.025)")
    print(f"  Paid escalation: {cert['metrics'].get('paid_escalation_pct', 0):.1f}% (max: 35%)")
    print(f"  RAG grounding: {cert['metrics'].get('rag_grounding_rate_pct', 0):.1f}%")
    print(f"  Tool error rate: {cert['metrics'].get('tool_error_rate_pct', 0):.1f}%")
    print(f"  Output: {_OUTPUT}")

    if cert["failures"]:
        print(f"\n  Failures:")
        for f in cert["failures"]:
            print(f"    - {f}")

    sys.exit(0 if cert["certified"] else 1)


if __name__ == "__main__":
    main()
