#!/usr/bin/env python3
"""
LLMHive Internal Model Leaderboard Runner
==========================================
Runs a fixed-slice benchmark across a configurable roster of models,
producing per-category top-10 tables sorted by score, cost, and latency.

Usage:
    python scripts/model_leaderboard_runner.py
    python scripts/model_leaderboard_runner.py --roster benchmark_reports/model_roster.json
    python scripts/model_leaderboard_runner.py --categories mmlu,gsm8k

Env:
    CATEGORY_BENCH_FIXED_SLICE_FILE  (required — fixed slices for determinism)
    LLMHIVE_API_URL / API_KEY        (required)
    LEADERBOARD_SAMPLE_PCT           (default 33 — percent of fixed slice)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

API_URL = os.getenv(
    "LLMHIVE_API_URL",
    os.getenv("CATEGORY_BENCH_API_URL",
              "https://llmhive-orchestrator-792354158895.us-east1.run.app"),
)
API_KEY = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))

CATEGORY_MAP = {
    "mmlu": "reasoning",
    "humaneval": "coding",
    "gsm8k": "math",
    "mmmlu": "multilingual",
    "longbench": "long_context",
    "toolbench": "tool_use",
    "rag": "rag",
    "dialogue": "dialogue",
}

DEFAULT_ROSTER = [
    {"model_id": "gpt-5.2-pro", "provider": "openrouter"},
    {"model_id": "claude-sonnet-4.6", "provider": "openrouter"},
    {"model_id": "gemini-3.1-pro", "provider": "openrouter"},
    {"model_id": "gemini-2.5-pro", "provider": "openrouter"},
    {"model_id": "deepseek-reasoner", "provider": "openrouter"},
    {"model_id": "grok-4", "provider": "openrouter"},
]


async def _call_model(
    prompt: str,
    model_id: str,
    provider: str,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Single model call via LLMHive orchestrator."""
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": model_id,
        "api_key": API_KEY,
        "orchestration_config": {
            "accuracy_level": 5,
            "enable_verification": False,
            "use_deep_consensus": False,
        },
    }
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{API_URL}/v1/chat", json=payload)
            latency_ms = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                extra = data.get("extra", {})
                cost_info = extra.get("cost_tracking", {})
                return {
                    "success": True,
                    "response": data.get("message", ""),
                    "latency_ms": latency_ms,
                    "cost_usd": cost_info.get("total_cost_usd", 0.0),
                    "model_used": data.get("models_used", [model_id]),
                }
            return {"success": False, "error": f"status_{resp.status_code}",
                    "latency_ms": latency_ms, "cost_usd": 0.0}
    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        return {"success": False, "error": str(exc)[:120],
                "latency_ms": latency_ms, "cost_usd": 0.0}


def _load_roster(path: Optional[str]) -> List[Dict[str, str]]:
    if path and Path(path).exists():
        with open(path) as f:
            return json.load(f)
    return DEFAULT_ROSTER


def _build_leaderboard_tables(
    results: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group results by category and sort: score DESC, cost ASC, latency ASC."""
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        cat = r["category"]
        by_category.setdefault(cat, []).append(r)
    tables = {}
    for cat, rows in by_category.items():
        sorted_rows = sorted(
            rows,
            key=lambda x: (-x["score"], x["cost_per_item_usd"], x["avg_latency_ms"]),
        )
        tables[cat] = sorted_rows[:10]
    return tables


def _render_markdown(tables: Dict[str, List[Dict[str, Any]]], timestamp: str) -> str:
    lines = [f"# LLMHive Internal Model Leaderboard — {timestamp}\n"]
    for cat, rows in sorted(tables.items()):
        lines.append(f"\n## {cat}\n")
        lines.append("| Rank | Model | Provider | Score | Infra Fail% | Avg Latency (ms) | Cost/Item ($) | Total Cost ($) |")
        lines.append("|------|-------|----------|-------|-------------|-------------------|---------------|----------------|")
        for idx, r in enumerate(rows, 1):
            lines.append(
                f"| {idx} | {r['model_id']} | {r['provider']} | "
                f"{r['score']:.1f}% | {r['infra_failure_rate']:.1f}% | "
                f"{r['avg_latency_ms']} | {r['cost_per_item_usd']:.4f} | "
                f"{r['total_cost_usd']:.4f} |"
            )
    return "\n".join(lines) + "\n"


async def run_category_for_model(
    model_id: str,
    provider: str,
    category: str,
    samples: list,
    correct_answers: list,
) -> Dict[str, Any]:
    """Run a single category for a single model and return metrics."""
    import re
    correct = 0
    errors = 0
    total_latency = 0
    total_cost = 0.0
    n = len(samples)

    for idx, (prompt, expected) in enumerate(zip(samples, correct_answers)):
        result = await _call_model(prompt, model_id, provider)
        total_latency += result.get("latency_ms", 0)
        total_cost += result.get("cost_usd", 0.0)
        if not result.get("success"):
            errors += 1
            continue
        resp = result.get("response", "")
        answer = None
        m = re.search(r'(?:^|\n)\s*([A-D])\s*$', resp, re.MULTILINE)
        if m:
            answer = m.group(1)
        else:
            for ch in "ABCD":
                if ch in resp[:20]:
                    answer = ch
                    break
        if answer and answer == expected:
            correct += 1

    attempted = n - errors
    score = (correct / attempted * 100) if attempted > 0 else 0.0
    return {
        "model_id": model_id,
        "provider": provider,
        "category": category,
        "score": round(score, 1),
        "correct": correct,
        "attempted": attempted,
        "errors": errors,
        "infra_failure_rate": round(errors / n * 100, 1) if n > 0 else 0.0,
        "avg_latency_ms": int(total_latency / n) if n > 0 else 0,
        "total_cost_usd": round(total_cost, 4),
        "cost_per_item_usd": round(total_cost / n, 6) if n > 0 else 0.0,
        "timestamp": datetime.now().isoformat(),
    }


async def main_async(args):
    roster = _load_roster(args.roster)
    categories = [c.strip().lower() for c in args.categories.split(",")] if args.categories else ["mmlu"]

    slice_file = os.getenv("CATEGORY_BENCH_FIXED_SLICE_FILE",
                           "benchmark_reports/fixed_slice.json")
    if not Path(slice_file).exists():
        print(f"ERROR: Fixed slice file not found: {slice_file}", file=sys.stderr)
        print("Set CATEGORY_BENCH_FIXED_SLICE_FILE or generate fixed_slice.json first.", file=sys.stderr)
        sys.exit(1)

    with open(slice_file) as f:
        fixed_slices = json.load(f)

    print(f"\n{'='*60}")
    print(f"LLMHive Model Leaderboard Runner")
    print(f"{'='*60}")
    print(f"  Models: {len(roster)}")
    print(f"  Categories: {categories}")
    print(f"  API: {API_URL}")

    all_results: List[Dict[str, Any]] = []

    for cat_name in categories:
        cat_key = CATEGORY_MAP.get(cat_name, cat_name)
        print(f"\n--- Category: {cat_name} ({cat_key}) ---")

        if cat_key == "reasoning" and cat_key in fixed_slices:
            from datasets import load_dataset
            dataset = load_dataset("lighteval/mmlu", "all", split="test", trust_remote_code=True)
            indices = fixed_slices[cat_key]
            sample_pct = int(os.getenv("LEADERBOARD_SAMPLE_PCT", "33"))
            n_samples = max(1, len(indices) * sample_pct // 100)
            indices = indices[:n_samples]

            samples = []
            correct_answers = []
            for idx in indices:
                if idx < len(dataset):
                    item = dataset[idx]
                    q = item["question"]
                    choices = item["choices"]
                    answer_idx = item["answer"]
                    letters = "ABCD"
                    formatted = f"{q}\n" + "\n".join(
                        f"{letters[j]}. {choices[j]}" for j in range(len(choices))
                    ) + "\n\nReturn ONLY the letter (A, B, C, or D)."
                    samples.append(formatted)
                    correct_answers.append(letters[answer_idx] if isinstance(answer_idx, int) else str(answer_idx))

            for model_info in roster:
                mid = model_info["model_id"]
                prov = model_info["provider"]
                print(f"  Testing {mid} ({prov}) on {len(samples)} MMLU samples...", end="", flush=True)
                result = await run_category_for_model(mid, prov, cat_name, samples, correct_answers)
                all_results.append(result)
                print(f" {result['score']:.1f}% (latency={result['avg_latency_ms']}ms, cost=${result['total_cost_usd']:.4f})")
        else:
            print(f"  Skipping {cat_name}: dataset loader not implemented in leaderboard runner yet.")

    if not all_results:
        print("\nNo results collected. Exiting.")
        return

    tables = _build_leaderboard_tables(all_results)
    timestamp = datetime.now().strftime("%Y%m%d")

    json_path = f"benchmark_reports/model_leaderboard_{timestamp}.json"
    md_path = f"benchmark_reports/model_leaderboard_{timestamp}.md"

    Path("benchmark_reports").mkdir(exist_ok=True)
    with open(json_path, "w") as f:
        json.dump({"timestamp": timestamp, "results": all_results, "tables": tables}, f, indent=2)
    with open(md_path, "w") as f:
        f.write(_render_markdown(tables, timestamp))

    print(f"\n{'='*60}")
    print(f"LEADERBOARD COMPLETE")
    print(f"{'='*60}")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")

    for cat, rows in sorted(tables.items()):
        print(f"\n  Top models for {cat}:")
        for idx, r in enumerate(rows[:5], 1):
            print(f"    {idx}. {r['model_id']}: {r['score']:.1f}% "
                  f"(${r['cost_per_item_usd']:.4f}/item, {r['avg_latency_ms']}ms)")


def main():
    parser = argparse.ArgumentParser(description="LLMHive Model Leaderboard Runner")
    parser.add_argument("--roster", help="Path to model roster JSON file")
    parser.add_argument("--categories", default="mmlu", help="Comma-separated categories to test")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: API_KEY or LLMHIVE_API_KEY environment variable required", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
