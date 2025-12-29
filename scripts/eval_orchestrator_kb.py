#!/usr/bin/env python3
"""
LLMHive KB Orchestrator Evaluation Harness

Runs a suite of test queries to evaluate KB-integrated pipelines.
Compares baseline single-call vs orchestrated pipeline outputs.

Usage:
    python scripts/eval_orchestrator_kb.py
    python scripts/eval_orchestrator_kb.py --output eval_reports/
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "llmhive" / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """A single test case."""
    name: str
    query: str
    expected_pipeline: str
    category: str
    tools: List[str] = field(default_factory=list)
    expected_answer_contains: Optional[str] = None
    expected_citations: bool = False


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    category: str
    query: str
    
    # Baseline results
    baseline_answer: str = ""
    baseline_latency_ms: float = 0
    
    # Orchestrated results
    orchestrated_answer: str = ""
    orchestrated_pipeline: str = ""
    orchestrated_techniques: List[str] = field(default_factory=list)
    orchestrated_latency_ms: float = 0
    orchestrated_confidence: str = ""
    
    # Evaluation
    pipeline_matched: bool = False
    answer_valid: bool = False
    citations_present: bool = False
    tool_calls_bounded: bool = True
    no_cot_exposed: bool = True
    
    error: Optional[str] = None


# Test suite covering different reasoning types
# NOTE: Expected pipelines are based on current classifier behavior
# Some may route to baseline/simple when tools aren't available or patterns don't match
TEST_SUITE: List[TestCase] = [
    # Math reasoning - explicit math keywords
    TestCase(
        name="math_arithmetic",
        query="Calculate: what is 23 * 17 + 45?",
        expected_pipeline="PIPELINE_MATH_REASONING",
        category="math",
        expected_answer_contains="436",
    ),
    TestCase(
        name="math_word_problem",
        query="Solve this math problem: If a train travels at 60 mph for 2.5 hours, how far does it go?",
        expected_pipeline="PIPELINE_MATH_REASONING",
        category="math",
        expected_answer_contains="150",
    ),
    
    # Tool use - explicit search request
    TestCase(
        name="tool_search",
        query="Search for the current weather in San Francisco",
        expected_pipeline="PIPELINE_TOOL_USE_REACT",
        category="tool_use",
        tools=["web_search"],
    ),
    
    # Factual/research with RAG - with tools available
    TestCase(
        name="factual_with_search",
        query="Use the search tool to find: Who was the first president of the United States?",
        expected_pipeline="PIPELINE_TOOL_USE_REACT",
        category="factual",
        tools=["web_search"],
    ),
    TestCase(
        name="factual_with_citations",
        query="What are the main causes of climate change? Please cite sources and provide references.",
        expected_pipeline="PIPELINE_RAG",  # PIPELINE_RAG is the registered name
        category="factual",
        tools=["retrieval", "web_search"],
        expected_citations=True,
    ),
    
    # General writing (baseline)
    TestCase(
        name="writing_simple",
        query="Write a short poem about the ocean.",
        expected_pipeline="PIPELINE_BASELINE_SINGLECALL",  # No special routing for creative
        category="writing",
    ),
    TestCase(
        name="writing_detailed",
        query="Write a comprehensive analysis of the themes in Shakespeare's Hamlet.",
        expected_pipeline="PIPELINE_BASELINE_SINGLECALL",  # Complex but no specific trigger
        category="writing",
    ),
    
    # Coding - with sandbox available
    TestCase(
        name="coding_function",
        query="Write a Python function to calculate the factorial of a number.",
        expected_pipeline="PIPELINE_CODING_AGENT",
        category="coding",
        tools=["code_sandbox"],
        expected_answer_contains="def",
    ),
    
    # Medical query (will be baseline without high-risk detection trigger)
    TestCase(
        name="medical_question",
        query="What medication should I take for severe chest pain?",
        expected_pipeline="PIPELINE_BASELINE_SINGLECALL",  # Classifier may not detect high risk
        category="medical",
    ),
    
    # Logic - explicit logical keywords
    TestCase(
        name="logic_reasoning",
        query="Prove logically: If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?",
        expected_pipeline="PIPELINE_MATH_REASONING",  # "prove" triggers logical reasoning
        category="logic",
    ),
]


# CoT patterns that should NOT appear in output
COT_PATTERNS = [
    "let's think step by step",
    "let me think",
    "step 1:",
    "step 2:",
    "my reasoning:",
    "[thinking]",
    "[scratchpad]",
    "<thinking>",
]


def check_no_cot_exposed(text: str) -> bool:
    """Check that no chain-of-thought is exposed."""
    text_lower = text.lower()
    for pattern in COT_PATTERNS:
        if pattern in text_lower:
            return False
    return True


async def run_baseline(test: TestCase) -> tuple[str, float]:
    """Run baseline single-call."""
    from llmhive.pipelines.pipelines_impl import pipeline_baseline_singlecall
    from llmhive.pipelines.types import PipelineContext
    
    start = time.time()
    ctx = PipelineContext(
        query=test.query,
        tools_available=test.tools,
    )
    result = await pipeline_baseline_singlecall(ctx)
    latency = (time.time() - start) * 1000
    
    return result.final_answer, latency


async def run_orchestrated(test: TestCase) -> tuple[str, str, List[str], float, str]:
    """Run orchestrated pipeline."""
    from llmhive.pipelines.kb_orchestrator_bridge import process_with_kb_pipeline
    
    start = time.time()
    result = await process_with_kb_pipeline(
        query=test.query,
        tools_available=test.tools,
        enable_tracing=False,  # Don't trace during eval
    )
    latency = (time.time() - start) * 1000
    
    return (
        result.final_answer,
        result.pipeline_name,
        result.technique_ids,
        latency,
        result.confidence,
    )


async def run_test(test: TestCase) -> TestResult:
    """Run a single test case."""
    result = TestResult(
        name=test.name,
        category=test.category,
        query=test.query,
    )
    
    try:
        # Run baseline
        baseline_answer, baseline_latency = await run_baseline(test)
        result.baseline_answer = baseline_answer
        result.baseline_latency_ms = baseline_latency
        
        # Run orchestrated
        orch_answer, orch_pipeline, orch_techniques, orch_latency, orch_conf = await run_orchestrated(test)
        result.orchestrated_answer = orch_answer
        result.orchestrated_pipeline = orch_pipeline
        result.orchestrated_techniques = orch_techniques
        result.orchestrated_latency_ms = orch_latency
        result.orchestrated_confidence = orch_conf
        
        # Evaluate
        result.pipeline_matched = orch_pipeline == test.expected_pipeline
        
        if test.expected_answer_contains:
            result.answer_valid = test.expected_answer_contains.lower() in orch_answer.lower()
        else:
            result.answer_valid = len(orch_answer) > 10  # Basic validity
        
        result.citations_present = (
            not test.expected_citations or 
            any(word in orch_answer.lower() for word in ["source", "according to", "citation", "["])
        )
        
        result.no_cot_exposed = check_no_cot_exposed(orch_answer)
        
    except Exception as e:
        logger.error("Test %s failed: %s", test.name, e)
        result.error = str(e)
    
    return result


async def run_all_tests() -> List[TestResult]:
    """Run all tests."""
    results = []
    
    for test in TEST_SUITE:
        logger.info("Running test: %s", test.name)
        result = await run_test(test)
        results.append(result)
        
        status = "✅" if result.pipeline_matched and result.no_cot_exposed else "⚠️"
        logger.info("  %s Pipeline: %s (expected: %s)", status, result.orchestrated_pipeline, test.expected_pipeline)
    
    return results


def generate_report_json(results: List[TestResult]) -> Dict[str, Any]:
    """Generate JSON report."""
    total = len(results)
    passed = sum(1 for r in results if r.pipeline_matched and r.no_cot_exposed and r.error is None)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
        },
        "by_category": _group_by_category(results),
        "results": [asdict(r) for r in results],
    }


def generate_report_markdown(results: List[TestResult]) -> str:
    """Generate Markdown report."""
    total = len(results)
    passed = sum(1 for r in results if r.pipeline_matched and r.no_cot_exposed and r.error is None)
    
    lines = [
        "# LLMHive KB Orchestrator Evaluation Report",
        "",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Summary",
        "",
        f"- **Total Tests**: {total}",
        f"- **Passed**: {passed}",
        f"- **Failed**: {total - passed}",
        f"- **Pass Rate**: {passed/total*100:.1f}%" if total > 0 else "N/A",
        "",
        "## Results by Category",
        "",
    ]
    
    # Group by category
    by_cat = _group_by_category(results)
    for cat, stats in by_cat.items():
        lines.append(f"### {cat.title()}")
        lines.append(f"- Tests: {stats['total']}")
        lines.append(f"- Pipeline Match Rate: {stats['pipeline_match_rate']*100:.0f}%")
        lines.append(f"- Avg Latency: {stats['avg_latency_ms']:.0f}ms")
        lines.append("")
    
    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| Test | Category | Pipeline | Expected | Match | CoT Safe |")
    lines.append("|------|----------|----------|----------|-------|----------|")
    
    for r in results:
        match_emoji = "✅" if r.pipeline_matched else "❌"
        cot_emoji = "✅" if r.no_cot_exposed else "❌"
        lines.append(f"| {r.name} | {r.category} | {r.orchestrated_pipeline} | {TEST_SUITE[results.index(r)].expected_pipeline if r in results else 'N/A'} | {match_emoji} | {cot_emoji} |")
    
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- **Pipeline Match**: Whether the selected pipeline matches expected")
    lines.append("- **CoT Safe**: No chain-of-thought exposed in final answer")
    lines.append("- This is an internal evaluation harness, not external benchmark claims")
    
    return "\n".join(lines)


def _group_by_category(results: List[TestResult]) -> Dict[str, Dict[str, Any]]:
    """Group results by category."""
    categories: Dict[str, List[TestResult]] = {}
    
    for r in results:
        if r.category not in categories:
            categories[r.category] = []
        categories[r.category].append(r)
    
    stats = {}
    for cat, cat_results in categories.items():
        total = len(cat_results)
        matched = sum(1 for r in cat_results if r.pipeline_matched)
        avg_latency = sum(r.orchestrated_latency_ms for r in cat_results) / total if total > 0 else 0
        
        stats[cat] = {
            "total": total,
            "pipeline_match_rate": matched / total if total > 0 else 0,
            "avg_latency_ms": avg_latency,
        }
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Evaluate KB orchestrator pipelines")
    parser.add_argument("--output", "-o", default="eval_reports", help="Output directory")
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting KB Orchestrator Evaluation")
    logger.info("=" * 60)
    
    # Run tests
    results = asyncio.run(run_all_tests())
    
    # Generate reports
    json_report = generate_report_json(results)
    md_report = generate_report_markdown(results)
    
    # Write reports
    json_path = output_dir / "kb_eval.json"
    md_path = output_dir / "kb_eval.md"
    
    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2)
    
    with open(md_path, "w") as f:
        f.write(md_report)
    
    logger.info("=" * 60)
    logger.info("Reports written to:")
    logger.info("  - %s", json_path)
    logger.info("  - %s", md_path)
    
    # Print summary
    summary = json_report["summary"]
    logger.info("")
    logger.info("SUMMARY: %d/%d tests passed (%.1f%%)",
                summary["passed"], summary["total_tests"], summary["pass_rate"] * 100)
    
    # Exit with error if tests failed
    if summary["passed"] < summary["total_tests"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

