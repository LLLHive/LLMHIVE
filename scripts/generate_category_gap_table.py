#!/usr/bin/env python3
"""Generate category gap table with Elite+ vs Free vs Leader and deltas.

Inputs:
  - elite_plus_scores.json (or elite benchmark results)
  - free_scores.json (or free benchmark results)
  - industry_leaders_2026-02-27.json

Output:
  - Markdown table with columns: Category | Elite+ | Free | Leader score | Leader model |
    Elite+ − Leader | Elite+ − Free
  - Percent categories: delta in pp (percentage points)
  - MT-Bench: delta in pts
  - Rounds to 1 decimal

Usage:
  python scripts/generate_category_gap_table.py \\
    --elite-plus benchmark_reports/elite_plus_scores.json \\
    --free benchmark_reports/free_scores.json \\
    --leaders benchmark_configs/industry_leaders_2026-02-27.json \\
    --out artifacts/category_gap_table.md
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Map industry_leaders category key -> (benchmark category name, unit)
_INDUSTRY_TO_BENCH: dict[str, tuple[str, str]] = {
    "mmlu_reasoning": ("General Reasoning (MMLU)", "pp"),
    "coding_humaneval": ("Coding (HumanEval)", "pp"),
    "math_gsm8k": ("Math (GSM8K)", "pp"),
    "multilingual_mmmlu": ("Multilingual (MMMLU)", "pp"),
    "longbench": ("Long Context (LongBench)", "pp"),
    "toolbench": ("Tool Use (ToolBench)", "pp"),
    "rag_msmarco_mrr10": ("RAG (MS MARCO)", "pp"),
    "dialogue_mtbench": ("Dialogue (MT-Bench)", "pts"),
}


def _parse_args() -> dict:
    args = {
        "elite": "",
        "free": "",
        "leaders": str(_ROOT / "benchmark_configs" / "industry_leaders_2026-02-27.json"),
        "output": str(_ROOT / "artifacts" / "category_gap_table.md"),
    }
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("--elite-plus", "--elite") and i + 1 < len(sys.argv):
            args["elite"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--free" and i + 1 < len(sys.argv):
            args["free"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--leaders" and i + 1 < len(sys.argv):
            args["leaders"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] in ("--out", "--output") and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def _load_results(path: Path) -> dict[str, dict]:
    """Return dict mapping benchmark category -> {score, format}."""
    data = json.loads(path.read_text())
    results = data.get("results", data.get("scores", []))
    if isinstance(results, dict):
        # Flatten {category: score}
        out: dict[str, dict] = {}
        for cat, val in results.items():
            if isinstance(val, (int, float)) and not (isinstance(val, float) and math.isnan(val)):
                out[cat] = {"score": float(val), "format": "x/10" if "Dialogue" in cat or "MT" in cat else "%"}
            elif isinstance(val, dict):
                s = val.get("score", val.get("accuracy"))
                fmt = val.get("format", "%")
                out[cat] = {"score": s, "format": fmt}
        return out
    out = {}
    for r in results:
        cat = r.get("category", "")
        if not cat:
            continue
        acc = r.get("accuracy", r.get("score"))
        extra = r.get("extra") or {}
        if "Dialogue" in cat and "raw_score_out_of_10" in extra:
            out[cat] = {"score": extra["raw_score_out_of_10"], "format": "x/10"}
        elif "RAG" in cat and "mrr_at_10" in extra:
            out[cat] = {"score": extra["mrr_at_10"] * 100, "format": "%"}
        elif acc is not None and not (isinstance(acc, float) and math.isnan(acc)):
            out[cat] = {"score": float(acc), "format": "%"}
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


def _compute_delta(a: float | None, b: float | None) -> float | None:
    """Compute a - b. Returns None if either is None/NaN."""
    if a is None or b is None:
        return None
    if isinstance(a, float) and math.isnan(a):
        return None
    if isinstance(b, float) and math.isnan(b):
        return None
    return round(a - b, 1)


def _format_delta(delta: float | None, unit: str) -> str:
    if delta is None:
        return "—"
    return f"{delta:+.1f} {unit}"


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

    ind_data = json.loads(leaders_path.read_text())
    ind_cats = ind_data.get("categories", {})
    if not ind_cats:
        print("FAIL: Industry leaders JSON has no categories.")
        return 1

    elite_results = _load_results(elite_path)
    free_results = _load_results(free_path)

    lines = [
        "# Category Gap Table",
        "",
        f"*Generated from: Elite+={elite_path.name}, Free={free_path.name}, Leaders={ind_data.get('updated_at', '?')}*",
        "",
        "| Category | Elite+ | Free | Leader score | Leader model | Elite+ − Leader | Elite+ − Free |",
        "|----------|--------|------|--------------|--------------|-----------------|---------------|",
    ]

    for ind_key, (bench_cat, unit) in _INDUSTRY_TO_BENCH.items():
        leader_info = ind_cats.get(ind_key)
        if not leader_info:
            print(f"FAIL: Industry key {ind_key} missing in leaders")
            return 1

        leader_score_raw = leader_info.get("leader_score")
        leader_model = leader_info.get("leader_model_label", "—")

        if bench_cat not in elite_results:
            print(f"FAIL: Category {bench_cat} missing in elite results")
            return 1
        if bench_cat not in free_results:
            print(f"FAIL: Category {bench_cat} missing in free results")
            return 1

        elite_entry = elite_results[bench_cat]
        free_entry = free_results[bench_cat]
        elite_score = elite_entry.get("score")
        free_score = free_entry.get("score")
        leader_score = float(leader_score_raw) if leader_score_raw is not None else None

        if elite_score is None and free_score is None:
            print(f"FAIL: Category {bench_cat} has no score in either tier")
            return 1

        # Format leader score for display
        if unit == "pts":
            leader_display = f"{leader_score:.1f}/10" if leader_score is not None else "—"
        else:
            leader_display = f"{leader_score:.1f}%" if leader_score is not None else "—"

        # Compute deltas (Elite+ − Leader, Elite+ − Free)
        delta_leader = _compute_delta(elite_score, leader_score)
        delta_free = _compute_delta(elite_score, free_score)

        elite_str = _format_score(elite_entry)
        free_str = _format_score(free_entry)
        delta_leader_str = _format_delta(delta_leader, unit)
        delta_free_str = _format_delta(delta_free, unit)

        display = bench_cat
        lines.append(
            f"| {display} | {elite_str} | {free_str} | {leader_display} | {leader_model} | "
            f"{delta_leader_str} | {delta_free_str} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
