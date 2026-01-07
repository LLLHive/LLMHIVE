#!/usr/bin/env python3
"""Run category-specific benchmarks across multiple models.

This script benchmarks the top models from industry rankings across
12 domain categories: Programming, Science, Health, Legal, Marketing,
Technology, Finance, Academia, Roleplay, Creative Writing, Translation, and Reasoning.

Usage:
    # Run all categories on all models
    python scripts/run_category_benchmarks.py
    
    # Run specific category
    python scripts/run_category_benchmarks.py --category programming
    
    # Run specific models only
    python scripts/run_category_benchmarks.py --models gpt-4o,claude-3.5-sonnet
    
    # Run quick test (2 prompts per category)
    python scripts/run_category_benchmarks.py --quick
"""
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "llmhive" / "src"))


def load_env():
    """Load environment variables from .env files."""
    env_files = [
        PROJECT_ROOT / ".env.local",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "llmhive" / ".env",
    ]
    
    for env_file in env_files:
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = value


load_env()


# Available models mapped to runner types (2025 rankings)
MODELS_BY_TIER = {
    # Tier 1: TOP 10 Flagship Models (from screenshots)
    "tier1": [
        "claude-opus-4",       # #1-2 in most categories
        "claude-sonnet-4",     # #1-3 in most categories
        "gemini-2.5-pro",      # #3-5 in most categories
        "o1",                  # Top reasoning model
        "deepseek-r1",         # Top reasoning model
        "gpt-4o",              # Strong baseline
    ],
    # Tier 2: Strong Current Gen
    "tier2": [
        "claude-3.7-sonnet",
        "claude-3.5-sonnet",
        "gemini-2.5-flash",
        "deepseek-v3",
        "gpt-4-turbo",
        "mistral-large",
    ],
    # Tier 3: Open Source & Specialized
    "tier3": [
        "llama-3.1-70b",
        "llama-3.1-405b",
        "qwen-2.5-72b",
        "codestral",
        "command-r-plus",
        "grok-2",
    ],
    # Full top 10 models for comprehensive testing
    "top10": [
        "claude-opus-4",
        "claude-sonnet-4",
        "gemini-2.5-pro",
        "gemini-3-pro",
        "o1",
        "deepseek-r1",
        "gpt-4o",
        "claude-3.7-sonnet",
        "deepseek-v3",
        "mistral-large",
    ],
    # All available flagship models
    "all": [
        # Anthropic
        "claude-opus-4", "claude-sonnet-4", "claude-haiku-4.5",
        "claude-3.7-sonnet", "claude-3.5-sonnet", "claude-3.5-haiku",
        # Google
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-pro", "gemini-2.0-flash",
        # OpenAI
        "gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "o1", "o1-mini",
        # DeepSeek
        "deepseek-r1", "deepseek-v3", "deepseek-v3.2",
        # Open Source
        "llama-3.1-70b", "llama-3.1-405b",
        "mistral-large", "codestral",
        "qwen-2.5-72b", "command-r-plus", "grok-2",
    ],
}

CATEGORIES = [
    "programming",
    "science", 
    "health",
    "legal",
    "marketing",
    "technology",
    "finance",
    "academia",
    "roleplay",
    "creative_writing",
    "translation",
    "reasoning",
]


def load_benchmark_suite(suite_path: Path) -> Dict[str, Any]:
    """Load benchmark suite from YAML file."""
    with open(suite_path) as f:
        return yaml.safe_load(f)


def filter_cases_by_category(cases: List[Dict], category: str) -> List[Dict]:
    """Filter benchmark cases by category."""
    return [c for c in cases if c.get("category", "").lower() == category.lower()]


async def run_single_benchmark(
    model_name: str,
    case: Dict[str, Any],
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Run a single benchmark case on a model."""
    from llmhive.app.benchmarks.runner_openrouter import OpenRouterRunner
    from llmhive.app.benchmarks.runner_base import BenchmarkCase, RunConfig
    
    # Create runner
    runner = OpenRouterRunner(model=model_name)
    
    if not runner.is_available():
        return {
            "model": model_name,
            "case_id": case["id"],
            "status": "skipped",
            "reason": runner.skip_reason(),
        }
    
    # Create benchmark case
    benchmark_case = BenchmarkCase(
        id=case["id"],
        category=case.get("category", "general"),
        prompt=case["prompt"],
        expected=case.get("expected", {}),
        requirements=case.get("requirements", {}),
        scoring=case.get("scoring", {}),
    )
    
    config = RunConfig(
        temperature=0.3,
        max_tokens=2000,
        timeout_seconds=timeout,
    )
    
    try:
        start_time = time.perf_counter()
        result = await runner.run_case(benchmark_case, config)
        latency = time.perf_counter() - start_time
        
        return {
            "model": model_name,
            "case_id": case["id"],
            "category": case.get("category"),
            "status": result.status.value,
            "answer": result.answer_text[:500] if result.answer_text else "",
            "latency_ms": result.latency_ms or (latency * 1000),
            "tokens_in": result.metadata.tokens_in if result.metadata else None,
            "tokens_out": result.metadata.tokens_out if result.metadata else None,
            "cost_usd": result.metadata.cost_usd if result.metadata else None,
            "error": result.error_message,
        }
    except Exception as e:
        return {
            "model": model_name,
            "case_id": case["id"],
            "category": case.get("category"),
            "status": "error",
            "error": str(e),
        }


async def run_category_benchmark(
    category: str,
    models: List[str],
    cases: List[Dict],
    max_cases: Optional[int] = None,
) -> Dict[str, Any]:
    """Run benchmarks for a specific category across models."""
    filtered_cases = filter_cases_by_category(cases, category)
    
    if max_cases:
        filtered_cases = filtered_cases[:max_cases]
    
    if not filtered_cases:
        return {"category": category, "error": "No cases found", "results": []}
    
    print(f"\n{'='*60}")
    print(f"Category: {category.upper()}")
    print(f"Cases: {len(filtered_cases)}, Models: {len(models)}")
    print(f"{'='*60}")
    
    results = []
    
    for model in models:
        print(f"\n  Testing: {model}")
        model_results = []
        
        for i, case in enumerate(filtered_cases):
            print(f"    [{i+1}/{len(filtered_cases)}] {case['id']}", end="", flush=True)
            result = await run_single_benchmark(model, case)
            model_results.append(result)
            
            status_icon = "✓" if result["status"] == "success" else "✗" if result["status"] == "error" else "○"
            latency = result.get("latency_ms", 0)
            print(f" {status_icon} ({latency:.0f}ms)")
        
        # Calculate model stats
        successes = sum(1 for r in model_results if r["status"] == "success")
        errors = sum(1 for r in model_results if r["status"] == "error")
        avg_latency = sum(r.get("latency_ms", 0) for r in model_results) / len(model_results) if model_results else 0
        total_cost = sum(r.get("cost_usd", 0) or 0 for r in model_results)
        
        results.append({
            "model": model,
            "cases": model_results,
            "stats": {
                "total": len(model_results),
                "success": successes,
                "errors": errors,
                "success_rate": successes / len(model_results) if model_results else 0,
                "avg_latency_ms": avg_latency,
                "total_cost_usd": total_cost,
            }
        })
        
        print(f"    Summary: {successes}/{len(model_results)} success, avg {avg_latency:.0f}ms, ${total_cost:.4f}")
    
    return {
        "category": category,
        "total_cases": len(filtered_cases),
        "models_tested": len(models),
        "results": results,
    }


async def run_all_categories(
    models: List[str],
    categories: List[str],
    suite: Dict[str, Any],
    quick: bool = False,
    output_dir: Path = None,
) -> Dict[str, Any]:
    """Run benchmarks across all categories."""
    start_time = time.time()
    max_cases = 2 if quick else None
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "models": models,
        "categories": categories,
        "quick_mode": quick,
        "results": {},
    }
    
    for category in categories:
        result = await run_category_benchmark(
            category=category,
            models=models,
            cases=suite.get("cases", []),
            max_cases=max_cases,
        )
        all_results["results"][category] = result
    
    # Calculate overall statistics
    total_time = time.time() - start_time
    all_results["total_time_seconds"] = total_time
    
    # Aggregate by model
    model_aggregates = {}
    for category, cat_results in all_results["results"].items():
        for model_result in cat_results.get("results", []):
            model = model_result["model"]
            if model not in model_aggregates:
                model_aggregates[model] = {
                    "total_cases": 0,
                    "successes": 0,
                    "errors": 0,
                    "total_latency_ms": 0,
                    "total_cost_usd": 0,
                    "categories": {},
                }
            
            stats = model_result.get("stats", {})
            model_aggregates[model]["total_cases"] += stats.get("total", 0)
            model_aggregates[model]["successes"] += stats.get("success", 0)
            model_aggregates[model]["errors"] += stats.get("errors", 0)
            model_aggregates[model]["total_latency_ms"] += stats.get("avg_latency_ms", 0) * stats.get("total", 1)
            model_aggregates[model]["total_cost_usd"] += stats.get("total_cost_usd", 0)
            model_aggregates[model]["categories"][category] = stats.get("success_rate", 0)
    
    # Calculate final aggregates
    for model, agg in model_aggregates.items():
        if agg["total_cases"] > 0:
            agg["overall_success_rate"] = agg["successes"] / agg["total_cases"]
            agg["avg_latency_ms"] = agg["total_latency_ms"] / agg["total_cases"]
    
    all_results["model_aggregates"] = model_aggregates
    
    # Save results if output dir specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON
        json_path = output_dir / "category_benchmark_results.json"
        with open(json_path, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\n✓ Results saved to {json_path}")
        
        # Generate markdown report
        md_path = output_dir / "category_benchmark_report.md"
        generate_markdown_report(all_results, md_path)
        print(f"✓ Report saved to {md_path}")
    
    return all_results


def generate_markdown_report(results: Dict[str, Any], output_path: Path):
    """Generate a markdown report from benchmark results."""
    lines = [
        "# Category Benchmark Report",
        "",
        f"**Generated:** {results['timestamp']}",
        f"**Models:** {', '.join(results['models'])}",
        f"**Categories:** {len(results['categories'])}",
        f"**Quick Mode:** {results['quick_mode']}",
        f"**Total Time:** {results['total_time_seconds']:.1f}s",
        "",
        "## Overall Model Rankings",
        "",
        "| Rank | Model | Success Rate | Avg Latency | Total Cost |",
        "|------|-------|--------------|-------------|------------|",
    ]
    
    # Sort models by success rate
    aggregates = results.get("model_aggregates", {})
    sorted_models = sorted(
        aggregates.items(),
        key=lambda x: x[1].get("overall_success_rate", 0),
        reverse=True
    )
    
    for rank, (model, stats) in enumerate(sorted_models, 1):
        success_rate = stats.get("overall_success_rate", 0) * 100
        avg_latency = stats.get("avg_latency_ms", 0)
        total_cost = stats.get("total_cost_usd", 0)
        lines.append(f"| {rank} | {model} | {success_rate:.1f}% | {avg_latency:.0f}ms | ${total_cost:.4f} |")
    
    lines.extend(["", "## Results by Category", ""])
    
    for category, cat_results in results.get("results", {}).items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Model | Success Rate | Avg Latency |")
        lines.append("|-------|--------------|-------------|")
        
        for model_result in cat_results.get("results", []):
            model = model_result["model"]
            stats = model_result.get("stats", {})
            sr = stats.get("success_rate", 0) * 100
            lat = stats.get("avg_latency_ms", 0)
            lines.append(f"| {model} | {sr:.1f}% | {lat:.0f}ms |")
        
        lines.append("")
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Run category-specific benchmarks")
    parser.add_argument(
        "--models",
        type=str,
        help="Comma-separated list of models, or tier name (tier1, tier2, tier3, all)",
        default="tier1",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Specific category to test (or 'all')",
        default="all",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: only 2 prompts per category",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for results",
        default="artifacts/benchmarks/categories",
    )
    parser.add_argument(
        "--suite",
        type=str,
        help="Path to benchmark suite YAML",
        default="benchmarks/suites/category_benchmarks_v1.yaml",
    )
    
    args = parser.parse_args()
    
    # Determine models to test
    if args.models in MODELS_BY_TIER:
        models = MODELS_BY_TIER[args.models]
    else:
        models = [m.strip() for m in args.models.split(",")]
    
    # Determine categories
    if args.category.lower() == "all":
        categories = CATEGORIES
    else:
        categories = [c.strip().lower() for c in args.category.split(",")]
    
    # Load suite
    suite_path = PROJECT_ROOT / args.suite
    if not suite_path.exists():
        print(f"Error: Suite file not found: {suite_path}")
        sys.exit(1)
    
    suite = load_benchmark_suite(suite_path)
    
    print("=" * 60)
    print("Category Benchmarks")
    print("=" * 60)
    print(f"Models: {', '.join(models)}")
    print(f"Categories: {', '.join(categories)}")
    print(f"Quick Mode: {args.quick}")
    print(f"Suite: {suite_path.name}")
    
    # Check API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("\n⚠️  Warning: OPENROUTER_API_KEY not set. External model tests will be skipped.")
    
    # Run benchmarks
    output_dir = PROJECT_ROOT / args.output / datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = asyncio.run(run_all_categories(
        models=models,
        categories=categories,
        suite=suite,
        quick=args.quick,
        output_dir=output_dir,
    ))
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for model, stats in sorted(
        results.get("model_aggregates", {}).items(),
        key=lambda x: x[1].get("overall_success_rate", 0),
        reverse=True
    ):
        sr = stats.get("overall_success_rate", 0) * 100
        latency = stats.get("avg_latency_ms", 0)
        print(f"  {model}: {sr:.1f}% success, {latency:.0f}ms avg")
    
    print(f"\nTotal time: {results['total_time_seconds']:.1f}s")


if __name__ == "__main__":
    main()

