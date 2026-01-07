"""Command-line interface for running benchmarks.

This module provides the main orchestration logic for:
- Loading benchmark suites
- Running cases across multiple systems
- Scoring results
- Generating reports
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .runner_base import (
    RunnerBase,
    RunConfig,
    BenchmarkCase,
    RunResult,
    RunnerStatus,
    get_git_commit_hash,
)
from .runner_llmhive import get_llmhive_runner
from .runner_openai import get_openai_runner
from .runner_anthropic import get_anthropic_runner
from .runner_perplexity import get_perplexity_runner
from .runner_openrouter import OpenRouterRunner
from .scoring import (
    CompositeScorer,
    ObjectiveScorer,
    RubricScorer,
    ScoringResult,
    calculate_aggregate_scores,
)
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging for benchmark runs."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_suite(suite_path: str) -> Dict[str, Any]:
    """Load a benchmark suite from YAML file.
    
    Args:
        suite_path: Path to the YAML suite file.
    
    Returns:
        Parsed suite data.
    
    Raises:
        FileNotFoundError: If suite file doesn't exist.
        yaml.YAMLError: If YAML is invalid.
    """
    path = Path(suite_path)
    if not path.exists():
        raise FileNotFoundError(f"Suite file not found: {suite_path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    logger.info(f"Loaded suite: {data.get('metadata', {}).get('suite_name', 'Unknown')}")
    logger.info(f"Total prompts: {len(data.get('prompts', []))}")
    
    return data


def create_cases(
    suite_data: Dict[str, Any],
    categories: Optional[List[str]] = None,
    prompt_ids: Optional[List[str]] = None,
    critical_only: bool = False,
) -> List[BenchmarkCase]:
    """Create BenchmarkCase objects from suite data with optional filtering.
    
    Args:
        suite_data: Parsed suite YAML data.
        categories: Optional list of categories to filter by.
        prompt_ids: Optional list of specific prompt IDs to run.
        critical_only: If True, only include critical prompts.
    
    Returns:
        List of BenchmarkCase objects.
    """
    cases = []
    for p in suite_data.get("prompts", []):
        # Filter by category
        if categories:
            if p.get("category") not in categories:
                continue
        
        # Filter by specific prompt IDs
        if prompt_ids:
            if p.get("id") not in prompt_ids:
                continue
        
        # Filter for critical only
        if critical_only:
            if not p.get("scoring", {}).get("critical", False):
                continue
        
        cases.append(BenchmarkCase.from_yaml(p))
    
    return cases


def get_runners(
    systems: List[str],
    config: RunConfig,
    mode: str = "local",
) -> Dict[str, RunnerBase]:
    """Create runner instances for requested systems.
    
    Args:
        systems: List of system names to run.
        config: Run configuration.
        mode: LLMHive mode ("local" or "http").
    
    Returns:
        Dictionary of system_name -> runner.
    """
    runners = {}
    
    # OpenRouter model shortcuts
    openrouter_models = {
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "claude-3-opus": "claude-3-opus",
        "claude-3.5-sonnet": "claude-3.5-sonnet",
        "claude-3-haiku": "claude-3-haiku",
        "gemini-pro": "gemini-pro",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "llama-3.1-70b": "llama-3.1-70b",
        "mistral-large": "mistral-large",
    }
    
    for system in systems:
        system_lower = system.lower()
        
        if system_lower == "llmhive":
            runner = get_llmhive_runner(mode=mode, config=config)
        elif system_lower == "openai":
            runner = get_openai_runner(config=config)
        elif system_lower == "anthropic":
            runner = get_anthropic_runner(config=config)
        elif system_lower == "perplexity":
            runner = get_perplexity_runner(config=config)
        elif system_lower in openrouter_models:
            # Use OpenRouter for external model baselines
            runner = OpenRouterRunner(model=openrouter_models[system_lower])
        elif system_lower.startswith("openrouter/"):
            # Allow direct OpenRouter model specification
            model = system_lower.replace("openrouter/", "")
            runner = OpenRouterRunner(model=model)
        else:
            logger.warning(f"Unknown system: {system}, skipping")
            continue
        
        if runner.is_available():
            runners[runner.system_name] = runner
            logger.info(f"Registered runner: {runner.system_name} ({runner.model_id})")
        else:
            logger.warning(f"Runner not available: {system} (missing keys or dependencies)")
    
    return runners


@dataclass
class BenchmarkRun:
    """Container for a complete benchmark run."""
    # Configuration
    suite_name: str
    suite_version: str
    git_commit: Optional[str]
    timestamp: str
    config: Dict[str, Any]
    
    # Results
    systems: List[str]
    results: List[Dict[str, Any]]  # Raw results per case per system
    scores: List[Dict[str, Any]]  # Scoring results
    
    # Aggregate stats
    aggregate: Dict[str, Any]
    
    # Flags
    critical_failures: List[str]
    passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "suite_version": self.suite_version,
            "git_commit": self.git_commit,
            "timestamp": self.timestamp,
            "config": self.config,
            "systems": self.systems,
            "results": self.results,
            "scores": self.scores,
            "aggregate": self.aggregate,
            "critical_failures": self.critical_failures,
            "passed": self.passed,
        }


async def run_benchmark(
    suite_path: str,
    systems: List[str],
    runs_per_case: int = 1,
    mode: str = "local",
    output_dir: Optional[str] = None,
    config: Optional[RunConfig] = None,
    enable_rubric: bool = False,
    judge_system: Optional[str] = None,
    categories: Optional[List[str]] = None,
    prompt_ids: Optional[List[str]] = None,
    critical_only: bool = False,
) -> BenchmarkRun:
    """Run a complete benchmark session.
    
    Args:
        suite_path: Path to benchmark suite YAML.
        systems: List of systems to benchmark.
        runs_per_case: Number of runs per case (for variance).
        mode: LLMHive mode.
        output_dir: Directory for output artifacts.
        config: Run configuration.
        enable_rubric: Enable rubric-based scoring.
        judge_system: System to use as judge for rubric scoring.
    
    Returns:
        BenchmarkRun with all results.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Set up output directory
    if output_dir is None:
        output_dir = f"artifacts/benchmarks/{timestamp}"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    cases_path = output_path / "cases"
    cases_path.mkdir(exist_ok=True)
    
    logger.info(f"Output directory: {output_path}")
    
    # Load suite
    suite_data = load_suite(suite_path)
    suite_metadata = suite_data.get("metadata", {})
    cases = create_cases(
        suite_data,
        categories=categories,
        prompt_ids=prompt_ids,
        critical_only=critical_only,
    )
    
    if not cases:
        raise RuntimeError("No benchmark cases match the specified filters")
    
    # Create config
    config = config or RunConfig()
    
    # Get runners
    runners = get_runners(systems, config, mode)
    
    if not runners:
        raise RuntimeError("No runners available - check API keys and dependencies")
    
    # Set up scorer
    judge_runner = None
    if enable_rubric and judge_system:
        judge_runners = get_runners([judge_system], config, mode)
        judge_runner = judge_runners.get(judge_system)
    
    rubric_scorer = RubricScorer(judge_runner) if enable_rubric else None
    scorer = CompositeScorer(
        objective_scorer=ObjectiveScorer(),
        rubric_scorer=rubric_scorer,
    )
    
    # Run benchmarks
    all_results: List[Dict[str, Any]] = []
    all_scores: List[ScoringResult] = []
    
    total_cases = len(cases)
    for case_idx, case in enumerate(cases):
        logger.info(f"[{case_idx + 1}/{total_cases}] Running case: {case.id}")
        
        for run_num in range(runs_per_case):
            for system_name, runner in runners.items():
                logger.debug(f"  Running {system_name} (run {run_num + 1})")
                
                try:
                    result = await runner.run_case(case, config)
                    
                    # Score the result
                    score = await scorer.score(
                        prompt_id=case.id,
                        system_name=system_name,
                        prompt=case.prompt,
                        answer=result.answer_text,
                        expected=case.expected,
                        requirements=case.requirements,
                        scoring_config=case.scoring,
                        case_notes=case.notes,
                    )
                    
                    # Store results
                    result_dict = {
                        "case_id": case.id,
                        "system": system_name,
                        "run_num": run_num,
                        "result": result.to_dict(),
                        "score": score.to_dict(),
                    }
                    all_results.append(result_dict)
                    all_scores.append(score)
                    
                    # Save per-case result
                    case_file = cases_path / f"{case.id}_{system_name}_{run_num}.json"
                    with open(case_file, 'w') as f:
                        json.dump(result_dict, f, indent=2)
                    
                    # Log progress
                    status_str = "✓" if score.objective_score and score.objective_score.passed else "✗"
                    logger.info(
                        f"  {system_name}: {status_str} "
                        f"(score={score.composite_score:.2f}, latency={result.latency_ms:.0f}ms)"
                    )
                    
                except Exception as e:
                    logger.error(f"  {system_name}: Error - {e}")
                    # Record error result
                    error_result = runner.error_result(case.id, str(e))
                    all_results.append({
                        "case_id": case.id,
                        "system": system_name,
                        "run_num": run_num,
                        "result": error_result.to_dict(),
                        "score": None,
                    })
    
    # Calculate aggregate statistics
    aggregate = calculate_aggregate_scores(all_scores)
    
    # Find critical failures
    critical_failures = [
        s.prompt_id for s in all_scores
        if s.critical_failed and s.system_name.lower() == "llmhive"
    ]
    
    # Determine overall pass/fail
    passed = len(critical_failures) == 0
    
    # Create benchmark run object
    benchmark_run = BenchmarkRun(
        suite_name=suite_metadata.get("suite_name", "Unknown"),
        suite_version=suite_metadata.get("version", "Unknown"),
        git_commit=get_git_commit_hash(),
        timestamp=timestamp,
        config=config.to_dict(),
        systems=list(runners.keys()),
        results=all_results,
        scores=[s.to_dict() for s in all_scores],
        aggregate=aggregate,
        critical_failures=critical_failures,
        passed=passed,
    )
    
    # Save report.json
    report_path = output_path / "report.json"
    with open(report_path, 'w') as f:
        json.dump(benchmark_run.to_dict(), f, indent=2)
    logger.info(f"Saved JSON report: {report_path}")
    
    # Generate and save report.md
    markdown = generate_markdown_report(benchmark_run, all_scores)
    md_path = output_path / "report.md"
    with open(md_path, 'w') as f:
        f.write(markdown)
    logger.info(f"Saved Markdown report: {md_path}")
    
    return benchmark_run


def generate_markdown_report(
    run: BenchmarkRun,
    scores: List[ScoringResult],
) -> str:
    """Generate a Markdown report from benchmark results.
    
    Args:
        run: The BenchmarkRun object.
        scores: List of ScoringResult objects.
    
    Returns:
        Markdown string.
    """
    lines = [
        f"# Benchmark Report: {run.suite_name}",
        "",
        f"**Version:** {run.suite_version}",
        f"**Date:** {run.timestamp}",
        f"**Git Commit:** {run.git_commit or 'N/A'}",
        f"**Status:** {'✅ PASSED' if run.passed else '❌ FAILED'}",
        "",
        "## Summary",
        "",
    ]
    
    # Leaderboard table
    lines.append("### Leaderboard")
    lines.append("")
    lines.append("| System | Mean Score | Passed | Failed | Critical Failures |")
    lines.append("|--------|------------|--------|--------|-------------------|")
    
    for system_name, stats in run.aggregate.get("systems", {}).items():
        mean_score = stats.get("composite_mean", 0)
        passed_count = stats.get("passed_count", 0)
        failed_count = stats.get("failed_count", 0)
        critical = stats.get("critical_failures", 0)
        
        lines.append(
            f"| {system_name} | {mean_score:.3f} | {passed_count} | {failed_count} | {critical} |"
        )
    
    lines.append("")
    
    # Category breakdown
    lines.append("### Category Breakdown")
    lines.append("")
    
    # Group scores by category
    by_category: Dict[str, Dict[str, List[ScoringResult]]] = {}
    for s in scores:
        # Get category from prompt_id (assumes format like "mhr_001")
        category = s.prompt_id.split("_")[0]
        if category not in by_category:
            by_category[category] = {}
        if s.system_name not in by_category[category]:
            by_category[category][s.system_name] = []
        by_category[category][s.system_name].append(s)
    
    for category, systems in sorted(by_category.items()):
        lines.append(f"#### {category.upper()}")
        lines.append("")
        lines.append("| System | Mean Score | Cases |")
        lines.append("|--------|------------|-------|")
        
        for system_name, system_scores in systems.items():
            mean = sum(s.composite_score for s in system_scores) / len(system_scores)
            lines.append(f"| {system_name} | {mean:.3f} | {len(system_scores)} |")
        
        lines.append("")
    
    # Critical failures
    if run.critical_failures:
        lines.append("## ⚠️ Critical Failures")
        lines.append("")
        lines.append("The following critical cases failed:")
        lines.append("")
        for failure_id in run.critical_failures:
            lines.append(f"- `{failure_id}`")
        lines.append("")
    
    # Notable failures (top 5 lowest scores per system)
    lines.append("## Notable Failures")
    lines.append("")
    
    for system_name in run.systems:
        system_scores = [s for s in scores if s.system_name == system_name]
        system_scores.sort(key=lambda x: x.composite_score)
        
        lines.append(f"### {system_name}")
        lines.append("")
        
        if system_scores:
            for s in system_scores[:5]:
                if s.objective_score and not s.objective_score.passed:
                    details = ", ".join(
                        f"{k}: {v}" for k, v in s.objective_score.details.items()
                    )
                    lines.append(f"- **{s.prompt_id}** (score={s.composite_score:.2f}): {details or 'Failed'}")
        
        lines.append("")
    
    # Configuration
    lines.append("## Configuration")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(run.config, indent=2))
    lines.append("```")
    
    return "\n".join(lines)


def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run LLMHive benchmark comparisons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run LLMHive only (no API keys needed)
  python -m llmhive.app.benchmarks.cli --systems llmhive --mode local
  
  # Run with all available systems
  python -m llmhive.app.benchmarks.cli --systems llmhive,openai,anthropic
  
  # Multiple runs per case for variance
  python -m llmhive.app.benchmarks.cli --systems llmhive --runs-per-case 3
        """
    )
    
    parser.add_argument(
        "--suite",
        default="benchmarks/suites/complex_reasoning_v1.yaml",
        help="Path to benchmark suite YAML (default: benchmarks/suites/complex_reasoning_v1.yaml)",
    )
    parser.add_argument(
        "--systems",
        default="llmhive",
        help="Comma-separated list of systems to run (default: llmhive)",
    )
    parser.add_argument(
        "--runs-per-case",
        type=int,
        default=1,
        help="Number of runs per case (default: 1)",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "http"],
        default="local",
        help="LLMHive mode: local (in-process) or http (API calls)",
    )
    parser.add_argument(
        "--outdir",
        help="Output directory for artifacts (default: artifacts/benchmarks/TIMESTAMP)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature for inference (default: 0.0 for determinism)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="Max tokens for responses (default: 2048)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Timeout per case in seconds (default: 120)",
    )
    parser.add_argument(
        "--enable-rubric",
        action="store_true",
        help="Enable rubric-based scoring (requires judge model)",
    )
    parser.add_argument(
        "--judge-system",
        default="llmhive",
        help="System to use as judge for rubric scoring (default: llmhive)",
    )
    parser.add_argument(
        "--category",
        help="Filter by category (comma-separated, e.g. 'multi_hop_reasoning,factoid_ambiguity')",
    )
    parser.add_argument(
        "--prompts",
        help="Run specific prompts only (comma-separated IDs, e.g. 'mhr_001,tbr_002')",
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Only run critical prompts (useful for quick regression checks)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Parse systems
    systems = [s.strip() for s in args.systems.split(",")]
    
    # Parse categories if provided
    categories = None
    if args.category:
        categories = [c.strip() for c in args.category.split(",")]
    
    # Parse prompt IDs if provided
    prompt_ids = None
    if args.prompts:
        prompt_ids = [p.strip() for p in args.prompts.split(",")]
    
    # Create config
    config = RunConfig(
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
    )
    
    try:
        # Run benchmark
        result = asyncio.run(run_benchmark(
            suite_path=args.suite,
            systems=systems,
            runs_per_case=args.runs_per_case,
            mode=args.mode,
            output_dir=args.outdir,
            config=config,
            enable_rubric=args.enable_rubric,
            judge_system=args.judge_system if args.enable_rubric else None,
            categories=categories,
            prompt_ids=prompt_ids,
            critical_only=args.critical_only,
        ))
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"BENCHMARK COMPLETE: {'PASSED' if result.passed else 'FAILED'}")
        print("=" * 60)
        print(f"Suite: {result.suite_name} v{result.suite_version}")
        print(f"Systems: {', '.join(result.systems)}")
        print(f"Total cases: {result.aggregate.get('total_cases', 0)}")
        
        for system_name, stats in result.aggregate.get("systems", {}).items():
            print(f"\n{system_name}:")
            print(f"  Mean Score: {stats.get('composite_mean', 0):.3f}")
            print(f"  Passed: {stats.get('passed_count', 0)}")
            print(f"  Failed: {stats.get('failed_count', 0)}")
            print(f"  Critical Failures: {stats.get('critical_failures', 0)}")
        
        if result.critical_failures:
            print(f"\n⚠️ Critical failures: {result.critical_failures}")
        
        # Exit with appropriate code
        sys.exit(0 if result.passed else 1)
        
    except Exception as e:
        logger.exception("Benchmark failed")
        print(f"\n❌ Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

