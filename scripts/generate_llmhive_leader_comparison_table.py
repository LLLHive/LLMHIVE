#!/usr/bin/env python3
"""Generate Elite+ vs Free vs Leader comparison table from benchmark artifacts.

Inputs:
  - Elite+ results JSON (from category_benchmarks_elite_*.json)
  - Free results JSON (from category_benchmarks_free_*.json)
  - category_leaders_llmhive.json

Output:
  - Markdown table: Category | Elite+ | Free | Leader score | Leader model

Usage:
  python scripts/generate_llmhive_leader_comparison_table.py \\
    --elite benchmark_reports/category_benchmarks_elite_20260304.json \\
    --free benchmark_reports/category_benchmarks_free_20260303.json \\
    --leaders benchmark_configs/category_leaders_llmhive.json \\
    --output docs/llmhive_leader_comparison.md
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Map category_key from leaders to benchmark result "category" string
_CATEGORY_KEY_TO_BENCHMARK: dict[str, str] = {
    "reasoning_mmlu": "General Reasoning (MMLU)",
    "coding_humaneval": "Coding (HumanEval)",
    "math_gsm8k": "Math (GSM8K)",
    "multilingual_mmmlu": "Multilingual (MMMLU)",
    "long_context_longbench": "Long Context (LongBench)",
    "tool_use_toolbench": "Tool Use (ToolBench)",
    "rag_msmarco_mrr10": "RAG (MS MARCO)",
    "dialogue_mtbench": "Dialogue (MT-Bench)",
}


def _parse_args() -> dict:
    args = {
        "elite": "",
        "free": "",
        "leaders": str(_ROOT / "benchmark_configs" / "category_leaders_llmhive.json"),
        "output": str(_ROOT / "docs" / "llmhive_leader_comparison.md"),
    }
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--elite" and i + 1 < len(sys.argv):
            args["elite"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--free" and i + 1 < len(sys.argv):
            args["free"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--leaders" and i + 1 < len(sys.argv):
            args["leaders"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def _load_results(path: Path) -> dict[str, dict]:
    """Return dict mapping benchmark category -> result (with score)."""
    data = json.loads(path.read_text())
    results = data.get("results", [])
    out: dict[str, dict] = {}
    for r in results:
        cat = r.get("category", "")
        if not cat:
            continue
        acc = r.get("accuracy")
        extra = r.get("extra") or {}
        # Dialogue: use raw_score_out_of_10 when present
        if "Dialogue" in cat and "raw_score_out_of_10" in extra:
            score = extra["raw_score_out_of_10"]
            out[cat] = {"score": score, "format": "x/10"}
        # RAG: use mrr_at_10 when present (convert to %)
        elif "RAG" in cat and "mrr_at_10" in extra:
            score = extra["mrr_at_10"] * 100
            out[cat] = {"score": score, "format": "%"}
        elif acc is not None and not (isinstance(acc, float) and math.isnan(acc)):
            out[cat] = {"score": acc, "format": "%"}
        else:
            out[cat] = {"score": None, "format": "%"}
    return out


def _format_score(entry: dict | None) -> str:
    if entry is None or entry.get("score") is None:
        return "—"
    s = entry["score"]
    fmt = entry.get("format", "%")
    if fmt == "x/10":
        return f"{s:.1f}/10"
    return f"{s:.1f}%"


def main() -> int:
    args = _parse_args()
    elite_path = Path(args["elite"])
    free_path = Path(args["free"])
    leaders_path = Path(args["leaders"])
    output_path = Path(args["output"])

    if not elite_path.exists():
        print(f"FAIL: Elite results not found: {elite_path}")
        return 1
    if not free_path.exists():
        print(f"FAIL: Free results not found: {free_path}")
        return 1
    if not leaders_path.exists():
        print(f"FAIL: Leaders config not found: {leaders_path}")
        return 1

    leaders_data = json.loads(leaders_path.read_text())
    categories = leaders_data.get("categories", [])
    if not categories:
        print("FAIL: Leaders JSON has no categories.")
        return 1

    elite_results = _load_results(elite_path)
    free_results = _load_results(free_path)

    lines = [
        "# LLMHive Orchestrator vs Category Leaders",
        "",
        f"*Generated from: Elite={elite_path.name}, Free={free_path.name}, Leaders={leaders_data.get('version', '?')}*",
        "",
        "| Category | Elite+ orchestrator | Free orchestrator | Leader score | Leader model |",
        "|----------|---------------------|-------------------|---------------|---------------|",
    ]

    for cat in categories:
        ck = cat.get("category_key", "")
        display = cat.get("display_name", "")
        leader_score = cat.get("leader_score", "—")
        leader_model = cat.get("leader_model", "—")

        bench_cat = _CATEGORY_KEY_TO_BENCHMARK.get(ck)
        if not bench_cat:
            print(f"FAIL: Unknown category_key {ck} (no benchmark mapping)")
            return 1

        if bench_cat not in elite_results:
            print(f"FAIL: Category {bench_cat} missing in elite results")
            return 1
        if bench_cat not in free_results:
            print(f"FAIL: Category {bench_cat} missing in free results")
            return 1

        elite_entry = elite_results[bench_cat]
        free_entry = free_results[bench_cat]
        if elite_entry.get("score") is None and free_entry.get("score") is None:
            print(f"FAIL: Category {bench_cat} has no score in either tier")
            return 1

        elite_str = _format_score(elite_entry)
        free_str = _format_score(free_entry)

        lines.append(f"| {display} | {elite_str} | {free_str} | {leader_score} | {leader_model} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
