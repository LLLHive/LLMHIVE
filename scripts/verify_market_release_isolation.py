#!/usr/bin/env python3
"""Verify that the minimal market release surface does not overlap benchmark-critical files.

This is a static safety check for launch readiness. It does not modify code,
call production APIs, or run benchmarks.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Only the runtime files intended for the minimal launch release.
MINIMAL_RUNTIME_RELEASE = {
    "proxy.ts",
    "cloudbuild.yaml",
}

# Benchmark-critical implementation and validation files that must remain untouched
# by the minimal market release surface.
BENCHMARK_CRITICAL = {
    "scripts/run_category_benchmarks.py",
    "scripts/eval_mtbench.py",
    "scripts/eval_toolbench.py",
    "llmhive/src/llmhive/app/benchmarks/runner_llmhive.py",
    "llmhive/src/llmhive/app/orchestration/benchmark_config.py",
    "tests/benchmarks/test_runner_llmhive_contract.py",
    "tests/test_benchmark_prompt_guidance.py",
}


def main() -> int:
    overlap = sorted(MINIMAL_RUNTIME_RELEASE & BENCHMARK_CRITICAL)
    result = {
        "minimal_runtime_release": sorted(MINIMAL_RUNTIME_RELEASE),
        "benchmark_critical": sorted(BENCHMARK_CRITICAL),
        "overlap": overlap,
        "passed": len(overlap) == 0,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
