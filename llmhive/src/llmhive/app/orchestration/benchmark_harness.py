"""Benchmark Harness for LLMHive Elite Orchestrator.

Implements continuous evaluation and performance tracking to ensure
LLMHive consistently outperforms competitors across all key dimensions.

Key Features:
1. Automated benchmark testing on standard tasks
2. Performance regression detection
3. Competitive gap analysis
4. Self-improvement triggers
5. Quality trend monitoring
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BenchmarkCategory(str, Enum):
    """Benchmark categories aligned with key performance dimensions."""
    CODING = "coding"
    REASONING = "reasoning"
    FACTUAL = "factual"
    MATH = "math"
    CREATIVE = "creative"
    MULTI_HOP = "multi_hop"
    SPEED = "speed"
    OVERALL = "overall"


class BenchmarkDifficulty(str, Enum):
    """Benchmark difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass(slots=True)
class BenchmarkCase:
    """A single benchmark test case."""
    id: str
    category: BenchmarkCategory
    difficulty: BenchmarkDifficulty
    prompt: str
    expected_answer: Optional[str] = None
    evaluation_criteria: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass(slots=True)
class BenchmarkResult:
    """Result of a single benchmark execution."""
    case_id: str
    category: BenchmarkCategory
    passed: bool
    score: float  # 0-1
    actual_answer: str
    latency_ms: float
    tokens_used: int
    models_used: List[str]
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkReport:
    """Aggregated benchmark report."""
    timestamp: datetime
    total_cases: int
    passed_cases: int
    overall_score: float
    category_scores: Dict[BenchmarkCategory, float]
    latency_avg_ms: float
    latency_p95_ms: float
    total_tokens: int
    regression_detected: bool
    improvement_opportunities: List[str]
    results: List[BenchmarkResult]


# ==============================================================================
# Standard Benchmark Cases
# ==============================================================================

STANDARD_BENCHMARKS: List[BenchmarkCase] = [
    # Coding Benchmarks
    BenchmarkCase(
        id="code_001",
        category=BenchmarkCategory.CODING,
        difficulty=BenchmarkDifficulty.EASY,
        prompt="Write a Python function to reverse a string.",
        evaluation_criteria={"must_contain": ["def", "return"], "must_work": True},
        tags=["python", "strings"],
    ),
    BenchmarkCase(
        id="code_002",
        category=BenchmarkCategory.CODING,
        difficulty=BenchmarkDifficulty.MEDIUM,
        prompt="Implement a binary search function in Python that returns the index of the target element, or -1 if not found.",
        evaluation_criteria={"must_contain": ["def", "return"], "complexity": "O(log n)"},
        tags=["python", "algorithms"],
    ),
    BenchmarkCase(
        id="code_003",
        category=BenchmarkCategory.CODING,
        difficulty=BenchmarkDifficulty.HARD,
        prompt="Implement a LRU (Least Recently Used) cache in Python with O(1) get and put operations.",
        evaluation_criteria={"must_contain": ["class", "get", "put"], "complexity": "O(1)"},
        tags=["python", "data_structures"],
    ),
    
    # Reasoning Benchmarks
    BenchmarkCase(
        id="reason_001",
        category=BenchmarkCategory.REASONING,
        difficulty=BenchmarkDifficulty.EASY,
        prompt="If all roses are flowers and all flowers need water, what can we conclude about roses?",
        expected_answer="Roses need water",
        evaluation_criteria={"semantic_match": True},
        tags=["logic", "syllogism"],
    ),
    BenchmarkCase(
        id="reason_002",
        category=BenchmarkCategory.REASONING,
        difficulty=BenchmarkDifficulty.MEDIUM,
        prompt="A farmer has 17 sheep. All but 9 die. How many sheep does the farmer have left?",
        expected_answer="9",
        evaluation_criteria={"exact_number": 9},
        tags=["logic", "trick_question"],
    ),
    BenchmarkCase(
        id="reason_003",
        category=BenchmarkCategory.REASONING,
        difficulty=BenchmarkDifficulty.HARD,
        prompt="Three people check into a hotel room that costs $30. They each contribute $10. Later, the manager realizes the room was only $25 and gives $5 to the bellboy to return. The bellboy keeps $2 and gives $1 back to each person. Now each person has paid $9 (totaling $27), plus $2 the bellboy kept = $29. Where is the missing dollar?",
        expected_answer="There is no missing dollar. The $27 includes the bellboy's $2.",
        evaluation_criteria={"explains_fallacy": True},
        tags=["logic", "paradox"],
    ),
    
    # Math Benchmarks
    BenchmarkCase(
        id="math_001",
        category=BenchmarkCategory.MATH,
        difficulty=BenchmarkDifficulty.EASY,
        prompt="What is 15% of 80?",
        expected_answer="12",
        evaluation_criteria={"exact_number": 12},
        tags=["arithmetic", "percentages"],
    ),
    BenchmarkCase(
        id="math_002",
        category=BenchmarkCategory.MATH,
        difficulty=BenchmarkDifficulty.MEDIUM,
        prompt="A train travels 60 miles in 45 minutes. What is its average speed in miles per hour?",
        expected_answer="80 mph",
        evaluation_criteria={"exact_number": 80},
        tags=["arithmetic", "word_problem"],
    ),
    BenchmarkCase(
        id="math_003",
        category=BenchmarkCategory.MATH,
        difficulty=BenchmarkDifficulty.HARD,
        prompt="Solve for x: 2^(x+1) + 2^x = 24",
        expected_answer="x = 3",
        evaluation_criteria={"exact_number": 3},
        tags=["algebra", "exponents"],
    ),
    
    # Factual Benchmarks
    BenchmarkCase(
        id="fact_001",
        category=BenchmarkCategory.FACTUAL,
        difficulty=BenchmarkDifficulty.EASY,
        prompt="What is the capital of France?",
        expected_answer="Paris",
        evaluation_criteria={"exact_match": "Paris"},
        tags=["geography"],
    ),
    BenchmarkCase(
        id="fact_002",
        category=BenchmarkCategory.FACTUAL,
        difficulty=BenchmarkDifficulty.MEDIUM,
        prompt="Who wrote 'Pride and Prejudice' and in what year was it first published?",
        expected_answer="Jane Austen, 1813",
        evaluation_criteria={"must_contain": ["Jane Austen", "1813"]},
        tags=["literature", "history"],
    ),
    BenchmarkCase(
        id="fact_003",
        category=BenchmarkCategory.FACTUAL,
        difficulty=BenchmarkDifficulty.HARD,
        prompt="What is the half-life of Carbon-14 and why is it significant in archaeology?",
        expected_answer="~5,730 years; used for radiocarbon dating",
        evaluation_criteria={"must_contain": ["5730", "5,730", "dating"]},
        tags=["science", "archaeology"],
    ),
    
    # Multi-hop Benchmarks
    BenchmarkCase(
        id="multi_001",
        category=BenchmarkCategory.MULTI_HOP,
        difficulty=BenchmarkDifficulty.MEDIUM,
        prompt="If the Eiffel Tower is in France, and France uses the Euro, what currency would you need to visit the Eiffel Tower?",
        expected_answer="Euro",
        evaluation_criteria={"exact_match": "Euro"},
        tags=["reasoning_chain"],
    ),
    BenchmarkCase(
        id="multi_002",
        category=BenchmarkCategory.MULTI_HOP,
        difficulty=BenchmarkDifficulty.HARD,
        prompt="What is the GDP per capita of the country where the tallest building in the world is located? Provide the country name and approximate GDP per capita.",
        expected_answer="UAE (Dubai has Burj Khalifa), GDP per capita ~$45,000-50,000",
        evaluation_criteria={"must_contain": ["UAE", "United Arab Emirates"]},
        tags=["research", "multi_step"],
    ),
]


# ==============================================================================
# Evaluator Functions
# ==============================================================================

def evaluate_code_output(answer: str, criteria: Dict[str, Any]) -> Tuple[bool, float, str]:
    """Evaluate code-based benchmark results."""
    score = 0.0
    issues = []
    
    # Check required patterns
    must_contain = criteria.get("must_contain", [])
    for pattern in must_contain:
        if pattern.lower() in answer.lower():
            score += 0.3 / max(len(must_contain), 1)
        else:
            issues.append(f"Missing: {pattern}")
    
    # Check syntax (basic)
    if "def " in answer and "return" in answer:
        score += 0.3
    
    # Check for common issues
    if "error" in answer.lower() or "exception" in answer.lower():
        issues.append("Contains error mentions")
        score -= 0.2
    
    # Bonus for documentation
    if '"""' in answer or "'''" in answer or "#" in answer:
        score += 0.1
    
    score = max(0, min(1, score + 0.3))  # Base score + adjustments
    passed = score >= 0.6
    
    return passed, score, "; ".join(issues) if issues else "OK"


def evaluate_factual_output(
    answer: str, 
    expected: Optional[str], 
    criteria: Dict[str, Any]
) -> Tuple[bool, float, str]:
    """Evaluate factual benchmark results."""
    answer_lower = answer.lower()
    score = 0.0
    
    # Exact match check
    if criteria.get("exact_match"):
        expected_lower = criteria["exact_match"].lower()
        if expected_lower in answer_lower:
            return True, 1.0, "Exact match found"
        else:
            return False, 0.3, f"Expected: {criteria['exact_match']}"
    
    # Must contain check
    must_contain = criteria.get("must_contain", [])
    matches = 0
    for item in must_contain:
        if item.lower() in answer_lower:
            matches += 1
    
    if must_contain:
        score = matches / len(must_contain)
        passed = matches == len(must_contain)
        detail = f"Matched {matches}/{len(must_contain)} required terms"
    else:
        # Semantic comparison with expected
        if expected and expected.lower() in answer_lower:
            score = 1.0
            passed = True
            detail = "Expected answer found"
        else:
            score = 0.5  # Partial credit
            passed = False
            detail = "Expected answer not clearly present"
    
    return passed, score, detail


def evaluate_math_output(
    answer: str, 
    criteria: Dict[str, Any]
) -> Tuple[bool, float, str]:
    """Evaluate math benchmark results."""
    import re
    
    expected_number = criteria.get("exact_number")
    if expected_number is None:
        return True, 0.5, "No expected number to verify"
    
    # Extract numbers from answer
    numbers = re.findall(r'-?\d+\.?\d*', answer)
    
    for num_str in numbers:
        try:
            num = float(num_str)
            if abs(num - expected_number) < 0.01:  # Close enough
                return True, 1.0, "Correct numerical answer"
        except ValueError:
            continue
    
    return False, 0.0, f"Expected {expected_number}, found: {numbers}"


def evaluate_reasoning_output(
    answer: str,
    expected: Optional[str],
    criteria: Dict[str, Any]
) -> Tuple[bool, float, str]:
    """Evaluate reasoning benchmark results."""
    answer_lower = answer.lower()
    
    # Check for logical explanation
    if criteria.get("explains_fallacy"):
        explanation_indicators = [
            "fallacy", "misleading", "incorrect", "error in", 
            "doesn't make sense", "wrong assumption"
        ]
        has_explanation = any(ind in answer_lower for ind in explanation_indicators)
        if has_explanation:
            return True, 1.0, "Correctly explains the fallacy"
        else:
            return False, 0.3, "Missing explanation of fallacy"
    
    # Semantic match
    if criteria.get("semantic_match") and expected:
        # Simple check - does answer contain key concepts?
        expected_words = set(expected.lower().split())
        answer_words = set(answer_lower.split())
        overlap = len(expected_words & answer_words) / len(expected_words)
        
        if overlap > 0.5:
            return True, overlap, "Semantic match found"
        else:
            return False, overlap, f"Low semantic overlap: {overlap:.2f}"
    
    # Number match for numeric answers
    if criteria.get("exact_number"):
        return evaluate_math_output(answer, criteria)
    
    return True, 0.7, "No specific criteria to evaluate"


# ==============================================================================
# Benchmark Harness
# ==============================================================================

class BenchmarkHarness:
    """
    Automated benchmark harness for continuous evaluation.
    
    Features:
    1. Run standard benchmarks
    2. Track performance over time
    3. Detect regressions
    4. Identify improvement opportunities
    5. Compare against baseline
    """
    
    def __init__(
        self,
        orchestrator: Any,
        results_dir: Optional[Path] = None,
        baseline_score: float = 0.85,
    ):
        """Initialize the benchmark harness."""
        self.orchestrator = orchestrator
        self.results_dir = results_dir or Path.home() / ".llmhive" / "benchmarks"
        self.baseline_score = baseline_score
        self.historical_results: List[BenchmarkReport] = []
        
        # Load historical results
        self._load_historical_results()
    
    async def run_benchmarks(
        self,
        cases: Optional[List[BenchmarkCase]] = None,
        categories: Optional[List[BenchmarkCategory]] = None,
        max_concurrent: int = 3,
    ) -> BenchmarkReport:
        """
        Run benchmark tests.
        
        Args:
            cases: Specific cases to run (default: all standard)
            categories: Filter to specific categories
            max_concurrent: Max concurrent executions
            
        Returns:
            BenchmarkReport with results
        """
        cases = cases or STANDARD_BENCHMARKS
        
        # Filter by category if specified
        if categories:
            cases = [c for c in cases if c.category in categories]
        
        logger.info("Running %d benchmark cases", len(cases))
        
        results: List[BenchmarkResult] = []
        
        # Run benchmarks with limited concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_case(case: BenchmarkCase) -> BenchmarkResult:
            async with semaphore:
                return await self._run_single_benchmark(case)
        
        tasks = [run_case(case) for case in cases]
        results = await asyncio.gather(*tasks)
        
        # Generate report
        report = self._generate_report(results)
        
        # Save results
        self._save_report(report)
        
        # Check for regressions
        self._check_regressions(report)
        
        return report
    
    async def _run_single_benchmark(self, case: BenchmarkCase) -> BenchmarkResult:
        """Run a single benchmark case."""
        start_time = time.time()
        
        try:
            # Run through orchestrator
            if hasattr(self.orchestrator, 'orchestrate'):
                result = await self.orchestrator.orchestrate(case.prompt)
                answer = result.answer if hasattr(result, 'answer') else str(result)
                models_used = result.models_used if hasattr(result, 'models_used') else []
                tokens_used = result.total_tokens if hasattr(result, 'total_tokens') else 0
            else:
                # Fallback for simpler orchestrators
                answer = await self.orchestrator(case.prompt)
                models_used = []
                tokens_used = 0
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Evaluate result
            passed, score, details = self._evaluate_result(case, answer)
            
            return BenchmarkResult(
                case_id=case.id,
                category=case.category,
                passed=passed,
                score=score,
                actual_answer=answer[:500],  # Truncate long answers
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                models_used=models_used,
                details={"evaluation": details},
            )
            
        except Exception as e:
            logger.error("Benchmark %s failed: %s", case.id, e)
            return BenchmarkResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                score=0.0,
                actual_answer="",
                latency_ms=(time.time() - start_time) * 1000,
                tokens_used=0,
                models_used=[],
                error=str(e),
            )
    
    def _evaluate_result(
        self, 
        case: BenchmarkCase, 
        answer: str
    ) -> Tuple[bool, float, str]:
        """Evaluate a benchmark result."""
        if case.category == BenchmarkCategory.CODING:
            return evaluate_code_output(answer, case.evaluation_criteria)
        elif case.category == BenchmarkCategory.MATH:
            return evaluate_math_output(answer, case.evaluation_criteria)
        elif case.category == BenchmarkCategory.FACTUAL:
            return evaluate_factual_output(
                answer, case.expected_answer, case.evaluation_criteria
            )
        elif case.category in [BenchmarkCategory.REASONING, BenchmarkCategory.MULTI_HOP]:
            return evaluate_reasoning_output(
                answer, case.expected_answer, case.evaluation_criteria
            )
        else:
            # Default evaluation
            if case.expected_answer:
                return evaluate_factual_output(
                    answer, case.expected_answer, case.evaluation_criteria
                )
            return True, 0.7, "No specific evaluation criteria"
    
    def _generate_report(self, results: List[BenchmarkResult]) -> BenchmarkReport:
        """Generate a benchmark report from results."""
        passed = sum(1 for r in results if r.passed)
        scores = [r.score for r in results]
        latencies = [r.latency_ms for r in results]
        
        # Category scores
        category_scores: Dict[BenchmarkCategory, float] = {}
        for category in BenchmarkCategory:
            cat_results = [r for r in results if r.category == category]
            if cat_results:
                category_scores[category] = sum(r.score for r in cat_results) / len(cat_results)
        
        # Overall score
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        # Latency stats
        latency_avg = sum(latencies) / len(latencies) if latencies else 0.0
        latency_p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
        
        # Identify improvement opportunities
        opportunities = []
        for category, score in category_scores.items():
            if score < 0.8:
                opportunities.append(
                    f"Improve {category.value}: current score {score:.2f}, target 0.85+"
                )
        
        # Check for regression
        regression_detected = False
        if self.historical_results:
            last_score = self.historical_results[-1].overall_score
            if overall_score < last_score - 0.05:  # 5% threshold
                regression_detected = True
        
        return BenchmarkReport(
            timestamp=datetime.now(),
            total_cases=len(results),
            passed_cases=passed,
            overall_score=overall_score,
            category_scores=category_scores,
            latency_avg_ms=latency_avg,
            latency_p95_ms=latency_p95,
            total_tokens=sum(r.tokens_used for r in results),
            regression_detected=regression_detected,
            improvement_opportunities=opportunities,
            results=results,
        )
    
    def _save_report(self, report: BenchmarkReport) -> None:
        """Save benchmark report to disk."""
        try:
            self.results_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"benchmark_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.results_dir / filename
            
            # Convert to serializable format
            data = {
                "timestamp": report.timestamp.isoformat(),
                "total_cases": report.total_cases,
                "passed_cases": report.passed_cases,
                "overall_score": report.overall_score,
                "category_scores": {k.value: v for k, v in report.category_scores.items()},
                "latency_avg_ms": report.latency_avg_ms,
                "latency_p95_ms": report.latency_p95_ms,
                "total_tokens": report.total_tokens,
                "regression_detected": report.regression_detected,
                "improvement_opportunities": report.improvement_opportunities,
            }
            
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info("Benchmark report saved to %s", filepath)
            
        except Exception as e:
            logger.warning("Failed to save benchmark report: %s", e)
    
    def _load_historical_results(self) -> None:
        """Load historical benchmark results."""
        try:
            if not self.results_dir.exists():
                return
            
            for filepath in sorted(self.results_dir.glob("benchmark_*.json"))[-10:]:
                with open(filepath) as f:
                    data = json.load(f)
                
                # Convert back to BenchmarkReport (simplified)
                report = BenchmarkReport(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    total_cases=data["total_cases"],
                    passed_cases=data["passed_cases"],
                    overall_score=data["overall_score"],
                    category_scores={
                        BenchmarkCategory(k): v 
                        for k, v in data["category_scores"].items()
                    },
                    latency_avg_ms=data["latency_avg_ms"],
                    latency_p95_ms=data["latency_p95_ms"],
                    total_tokens=data["total_tokens"],
                    regression_detected=data["regression_detected"],
                    improvement_opportunities=data["improvement_opportunities"],
                    results=[],  # Not loaded for historical
                )
                self.historical_results.append(report)
                
        except Exception as e:
            logger.warning("Failed to load historical results: %s", e)
    
    def _check_regressions(self, report: BenchmarkReport) -> None:
        """Check for performance regressions and alert."""
        if report.regression_detected:
            logger.warning(
                "REGRESSION DETECTED: Overall score dropped from %.2f to %.2f",
                self.historical_results[-1].overall_score if self.historical_results else 0,
                report.overall_score
            )
        
        # Check category-specific regressions
        if self.historical_results:
            last_report = self.historical_results[-1]
            for category, score in report.category_scores.items():
                last_score = last_report.category_scores.get(category, 0)
                if score < last_score - 0.1:  # 10% category regression
                    logger.warning(
                        "Category regression in %s: %.2f -> %.2f",
                        category.value, last_score, score
                    )
    
    def get_performance_trend(self) -> Dict[str, List[float]]:
        """Get performance trend over time."""
        trend = {
            "timestamps": [],
            "overall_scores": [],
        }
        
        for category in BenchmarkCategory:
            trend[category.value] = []
        
        for report in self.historical_results:
            trend["timestamps"].append(report.timestamp.isoformat())
            trend["overall_scores"].append(report.overall_score)
            for category in BenchmarkCategory:
                trend[category.value].append(
                    report.category_scores.get(category, 0)
                )
        
        return trend


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def run_quick_benchmark(orchestrator: Any) -> BenchmarkReport:
    """Run a quick benchmark with minimal cases."""
    harness = BenchmarkHarness(orchestrator)
    
    # Select a few cases from each category
    quick_cases = [
        c for c in STANDARD_BENCHMARKS 
        if c.difficulty in [BenchmarkDifficulty.EASY, BenchmarkDifficulty.MEDIUM]
    ][:8]
    
    return await harness.run_benchmarks(cases=quick_cases)


async def run_full_benchmark(orchestrator: Any) -> BenchmarkReport:
    """Run the full benchmark suite."""
    harness = BenchmarkHarness(orchestrator)
    return await harness.run_benchmarks()


def create_benchmark_harness(orchestrator: Any) -> BenchmarkHarness:
    """Create a benchmark harness for an orchestrator."""
    return BenchmarkHarness(orchestrator)

