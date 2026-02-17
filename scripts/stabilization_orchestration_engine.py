#!/usr/bin/env python3
"""Post-recovery stabilization orchestration for 8-category benchmark hardening.

Implements the approved planning framework as executable, artifact-backed diagnostics
without mutating production benchmark logic.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


CATEGORIES: List[str] = [
    "mmlu",
    "humaneval",
    "gsm8k",
    "mmmlu",
    "long_context",
    "tool_use",
    "rag",
    "dialogue",
]

CATEGORY_LABELS: Dict[str, str] = {
    "mmlu": "MMLU",
    "humaneval": "HumanEval",
    "gsm8k": "GSM8K",
    "mmmlu": "MMMLU",
    "long_context": "Long Context",
    "tool_use": "Tool Use",
    "rag": "RAG (MRR@10)",
    "dialogue": "Dialogue (MT-Bench)",
}


@dataclass
class SmartRow:
    category: str
    current: float
    best: float
    leader: float

    @property
    def gap_best_vs_leader(self) -> float:
        return round(self.best - self.leader, 1)


LOCKED_BASELINE: List[SmartRow] = [
    SmartRow("mmlu", 60.0, 72.0, 89.0),
    SmartRow("humaneval", 90.0, 90.0, 92.0),
    SmartRow("gsm8k", 81.8, 94.9, 96.0),
    SmartRow("mmmlu", 75.0, 84.5, 86.0),
    SmartRow("long_context", 95.0, 95.0, 90.0),
    SmartRow("tool_use", 83.3, 83.3, 85.0),
    SmartRow("rag", 37.8, 51.5, 43.0),
    SmartRow("dialogue", 59.5, 67.0, 90.0),
]


def load_optional_json(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    payload_path = Path(path)
    if not payload_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {payload_path}")
    return json.loads(payload_path.read_text())


def env_snapshot() -> Dict[str, Any]:
    required = [
        "API_KEY",
        "LLMHIVE_API_KEY",
        "TOOLBENCH_EVAL_CMD",
        "LONGBENCH_EVAL_CMD",
        "MTBENCH_EVAL_CMD",
        "MSMARCO_EVAL_CMD",
    ]
    return {
        key: "set" if os.getenv(key) else "unset"
        for key in required
    }


def configuration_snapshot() -> Dict[str, Any]:
    return {
        "global_harness": {
            "entrypoint": "scripts/run_category_benchmarks.py",
            "tier_env": "CATEGORY_BENCH_TIER (default: elite)",
            "reasoning_mode_env": "CATEGORY_BENCH_REASONING_MODE (default: deep)",
            "sampling_params": {
                "temperature_env": "CATEGORY_BENCH_TEMPERATURE",
                "top_p_env": "CATEGORY_BENCH_TOP_P",
            },
            "seed_policy": "fixed deterministic seeds; baseline seed=42",
            "routing_api": {
                "endpoint": "/v1/chat",
                "retries": [429, 502, 503, 504],
                "max_retries": 3,
                "defaults": {
                    "accuracy_level": 5,
                    "use_deep_consensus": True,
                    "enable_verification": True,
                },
            },
            "infra_dependencies": env_snapshot(),
        },
        "categories": {
            "mmlu": {
                "models": [
                    "anthropic/claude-opus-4.6",
                    "google/gemini-3-pro",
                    "openai/gpt-5.2",
                    "deepseek/deepseek-v3.2-thinking",
                    "openai/gpt-5.3-codex",
                ],
                "fallback": "google/gemini-3-pro",
                "routing": "domain detection + negation handling + multi-path CoT + self-consistency + neighbor consistency",
                "seed": 42,
            },
            "humaneval": {
                "routing": "orchestrator tier routing",
                "prompt": "plan -> implement -> refine (3 attempts max)",
                "tool_usage": "human_eval.execution.check_correctness",
                "seed": "deterministic problem ordering",
            },
            "gsm8k": {
                "routing": "generate-then-verify math candidates",
                "extraction": "#### marker + fallback numeric parse",
                "seed": 42,
            },
            "mmmlu": {
                "routing": "orchestrator routing with verification",
                "prompt": "strict final line single letter A-D + robust schema parsing",
                "seed": 42,
            },
            "long_context": {
                "judge": "external LONGBENCH_EVAL_CMD",
                "seed": 42,
                "timeout_s": 1800,
            },
            "tool_use": {
                "judge": "external TOOLBENCH_EVAL_CMD",
                "seed": 42,
                "timeout_s": 3600,
            },
            "rag": {
                "retrieval": "MS MARCO + hybrid retrieval + BM25/keyword + intent-aware rerank + anti-position-bias shuffle + RRF",
                "reranker": "bge-reranker-v2-m3",
                "metric": "builtin MRR@10 unless external command supplied",
                "seed": 42,
            },
            "dialogue": {
                "judge": "external MTBENCH_EVAL_CMD",
                "seed": 42,
                "timeout_s": 1800,
            },
        },
    }


def smart_table_revalidation() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    protected: List[str] = []
    for row in LOCKED_BASELINE:
        gap = row.gap_best_vs_leader
        rows.append(
            {
                "category": CATEGORY_LABELS[row.category],
                "current": row.current,
                "best": row.best,
                "leader": row.leader,
                "gap": gap,
                "semantics": "ahead" if gap > 0 else "behind" if gap < 0 else "tied",
            }
        )
        if row.category in {"long_context", "rag"} and gap > 0:
            protected.append(CATEGORY_LABELS[row.category])

    return {
        "rows": rows,
        "gap_formula": "Gap = Our Best - Leader",
        "semantics": "positive gap means ahead; negative gap means behind",
        "protected_categories": protected,
    }


def _variance_from_runs(scores: List[float]) -> Dict[str, Any]:
    if not scores:
        return {
            "mean": None,
            "std_dev": None,
            "max_delta": None,
            "instability_flag": "unknown",
            "note": "missing artifact-backed replay data",
        }

    mean = statistics.fmean(scores)
    std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
    max_delta = max(scores) - min(scores)
    return {
        "mean": round(mean, 3),
        "std_dev": round(std_dev, 3),
        "max_delta": round(max_delta, 3),
        "instability_flag": bool(max_delta > 5.0),
    }


def variance_diagnostics(replays: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    by_cat: Dict[str, Any] = {}
    for category in CATEGORIES:
        scores = []
        if replays and category in replays:
            raw = replays[category]
            if isinstance(raw, list):
                scores = [float(x) for x in raw]
        by_cat[category] = _variance_from_runs(scores)

    by_cat["special_checks"] = {
        "humaneval": "pass@k sensitivity (k=1,5)",
        "gsm8k": "answer extraction stability",
        "dialogue": "judge variance",
        "tool_use": "API instability vs tool selection",
        "rag": "recall@k + rerank variance",
        "mmlu_mmmlu": "option-selection drift",
    }
    return by_cat


def infra_capability_table() -> List[Dict[str, Any]]:
    return [
        {"failure": "Tool API timeout/5xx", "count": "TBD", "infra_503": "TBD", "judge_bias": 0, "capability": 0},
        {"failure": "Tool schema/sequence violation", "count": "TBD", "infra_503": 0, "judge_bias": 0, "capability": "TBD"},
        {"failure": "MT-Bench judge unavailable/error", "count": "TBD", "infra_503": "TBD", "judge_bias": "TBD", "capability": 0},
        {"failure": "MT-Bench low score with valid output", "count": "TBD", "infra_503": 0, "judge_bias": "TBD", "capability": "TBD"},
    ]


def experiment_matrix() -> List[Dict[str, Any]]:
    return [
        {"id": "EXP-C1", "category": "MMLU", "single_variable": "negation preamble strictness", "expected_delta": "+3 to +5", "risk": "verbosity drift", "rollback": "any category <-1%"},
        {"id": "EXP-C2", "category": "Dialogue", "single_variable": "response scaffold template", "expected_delta": "+0.4 to +0.8", "risk": "style rigidity", "rollback": "MT variance >3%"},
        {"id": "EXP-C3", "category": "Dialogue", "single_variable": "judge-robust formatting constraints", "expected_delta": "+0.3", "risk": "response naturalness", "rollback": "writing/roleplay <-1%"},
        {"id": "EXP-B1", "category": "GSM8K", "single_variable": "final answer extraction rule", "expected_delta": "+1 to +2", "risk": "parser overfit", "rollback": "arithmetic cluster worsens"},
        {"id": "EXP-B2", "category": "MMMLU", "single_variable": "locale-specific answer-line instruction", "expected_delta": "+1 to +2", "risk": "token overhead", "rollback": "EN locale <-1%"},
        {"id": "EXP-B3", "category": "Tool Use", "single_variable": "retry/circuit-breaker shield", "expected_delta": "+1 to +2", "risk": "latency", "rollback": "latency +20%"},
        {"id": "EXP-B4", "category": "HumanEval", "single_variable": "completion sanitizer determinism", "expected_delta": "+1", "risk": "clip valid code", "rollback": "compile-fail +1%"},
        {"id": "EXP-A1", "category": "RAG", "single_variable": "rerank candidate depth", "expected_delta": "+5 to +10", "risk": "cost/latency", "rollback": "Long Context or Tool Use <-1%"},
    ]


def build_stabilization_artifact(replays: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration_snapshot": configuration_snapshot(),
        "smart_table_revalidation": smart_table_revalidation(),
        "variance_diagnostics": variance_diagnostics(replays),
        "infra_vs_capability": infra_capability_table(),
        "regression_shields": {
            "long_context": "needle test pre-merge mandatory",
            "rag": "recall floor + MRR floor",
            "humaneval": "format compliance suite",
            "tool_use": "mock API retry shield",
            "gsm8k": "extraction invariant enforcement",
            "mmmlu": "locale-format validation suite",
        },
        "cross_category_gate": {
            "sample": "20% fixed sample across all 8 categories",
            "rule": "no category regression worse than 1% absolute",
            "rollback": "mandatory if violated",
        },
        "anti_circularity": {
            "re_proposed_implemented_fix": "NO",
            "verified_artifact_before_change": "YES",
            "bundled_variables": "NO",
            "protected_categories_regressed": "NO_CHANGE_RUN",
            "infra_separated_from_capability": "YES",
        },
        "success_criteria": {
            "long_context": ">=95",
            "rag": ">=historical best",
            "gsm8k": ">=94",
            "mmmlu": ">=86",
            "tool_use": ">=85",
            "humaneval": ">=91",
            "mmlu": ">=80 trajectory",
            "dialogue": ">=7.0 average",
            "variance": "<3% all categories",
            "protected_regression": "none",
        },
        "experiment_matrix": experiment_matrix(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate stabilization orchestration artifact.")
    parser.add_argument(
        "--replays-json",
        help="Optional JSON file mapping category -> list of 3 replay scores.",
    )
    parser.add_argument(
        "--output",
        default="benchmark_reports/stabilization_orchestration_artifact.json",
        help="Output artifact path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    replays = load_optional_json(args.replays_json)
    artifact = build_stabilization_artifact(replays)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2))

    print(f"✅ Stabilization artifact written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
