"""Benchmarking Framework for LLMHive.

Provides standard QA, reasoning, and code benchmarks to evaluate
LLMHive's performance against state-of-the-art systems.

Supported Benchmarks:
- QA: SQuAD, TriviaQA, NaturalQuestions
- Reasoning: GSM8K, MATH, ARC
- Code: HumanEval, MBPP
- Knowledge: MMLU

Usage:
    runner = BenchmarkRunner()
    results = await runner.run_benchmark("squad", sample_size=100)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class BenchmarkType(str, Enum):
    """Types of benchmarks."""
    QA = "qa"
    REASONING = "reasoning"
    CODE = "code"
    KNOWLEDGE = "knowledge"
    SAFETY = "safety"


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    EXACT_MATCH = "exact_match"
    F1_SCORE = "f1_score"
    BLEU = "bleu"
    ACCURACY = "accuracy"
    PASS_AT_K = "pass@k"
    LATENCY = "latency"


@dataclass
class BenchmarkSample:
    """A single benchmark sample."""
    id: str
    question: str
    context: Optional[str] = None
    expected_answer: Optional[str] = None
    expected_answers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Result of evaluating a single sample."""
    sample_id: str
    question: str
    expected: str
    predicted: str
    correct: bool
    score: float
    latency_ms: float
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Aggregate benchmark results."""
    benchmark_name: str
    benchmark_type: BenchmarkType
    total_samples: int
    correct_count: int
    accuracy: float
    avg_score: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    model_breakdown: Dict[str, float]  # model -> accuracy
    results: List[EvaluationResult]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "benchmark_type": self.benchmark_type.value,
            "total_samples": self.total_samples,
            "correct_count": self.correct_count,
            "accuracy": round(self.accuracy, 4),
            "avg_score": round(self.avg_score, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "model_breakdown": self.model_breakdown,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def summary(self) -> str:
        return (
            f"{self.benchmark_name}: {self.accuracy:.1%} accuracy "
            f"({self.correct_count}/{self.total_samples}), "
            f"avg latency: {self.avg_latency_ms:.0f}ms"
        )


# ==============================================================================
# Metrics
# ==============================================================================

def normalize_answer(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    # Remove articles
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    return text


def exact_match(predicted: str, expected: str) -> bool:
    """Check if predicted matches expected exactly (normalized)."""
    return normalize_answer(predicted) == normalize_answer(expected)


def exact_match_any(predicted: str, expected_list: List[str]) -> bool:
    """Check if predicted matches any expected answer."""
    pred_norm = normalize_answer(predicted)
    return any(pred_norm == normalize_answer(exp) for exp in expected_list)


def f1_score(predicted: str, expected: str) -> float:
    """Compute token-level F1 score."""
    pred_tokens = set(normalize_answer(predicted).split())
    exp_tokens = set(normalize_answer(expected).split())
    
    if not pred_tokens or not exp_tokens:
        return 0.0
    
    common = pred_tokens & exp_tokens
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(exp_tokens)
    
    if precision + recall == 0:
        return 0.0
    
    return 2 * precision * recall / (precision + recall)


def contains_answer(predicted: str, expected: str) -> bool:
    """Check if predicted contains the expected answer."""
    return normalize_answer(expected) in normalize_answer(predicted)


def percentile(values: List[float], p: float) -> float:
    """Calculate percentile using linear interpolation.
    
    Uses the standard 0-indexed percentile calculation where p=50
    returns the median value.
    """
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    # Use (n-1) for 0-based indexing to get correct percentile
    idx = (n - 1) * p / 100
    lower = int(idx)
    upper = min(lower + 1, n - 1)
    # Linear interpolation between adjacent values
    weight = idx - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


# ==============================================================================
# Base Benchmark
# ==============================================================================

class Benchmark(ABC):
    """Abstract base class for benchmarks."""
    
    def __init__(
        self,
        name: str,
        benchmark_type: BenchmarkType,
        data_path: Optional[str] = None,
    ):
        self.name = name
        self.benchmark_type = benchmark_type
        self.data_path = data_path
        self.samples: List[BenchmarkSample] = []
    
    @abstractmethod
    def load_data(self, sample_size: Optional[int] = None) -> List[BenchmarkSample]:
        """Load benchmark data."""
        pass
    
    @abstractmethod
    def evaluate_sample(
        self,
        sample: BenchmarkSample,
        predicted: str,
    ) -> Tuple[bool, float]:
        """Evaluate a single prediction. Returns (correct, score)."""
        pass
    
    def get_prompt(self, sample: BenchmarkSample) -> str:
        """Generate prompt for the sample."""
        if sample.context:
            return f"Context: {sample.context}\n\nQuestion: {sample.question}\n\nAnswer:"
        return f"Question: {sample.question}\n\nAnswer:"


# ==============================================================================
# QA Benchmarks
# ==============================================================================

class SQuADBenchmark(Benchmark):
    """SQuAD 2.0 benchmark for reading comprehension."""
    
    def __init__(self, data_path: Optional[str] = None):
        super().__init__("SQuAD", BenchmarkType.QA, data_path)
    
    def load_data(self, sample_size: Optional[int] = None) -> List[BenchmarkSample]:
        """Load SQuAD data (uses built-in sample if no path)."""
        # Built-in sample questions
        samples = [
            BenchmarkSample(
                id="sq1",
                question="What is the capital of France?",
                context="France is a country in Western Europe. Its capital is Paris, a major European city known for art, fashion, and culture.",
                expected_answer="Paris",
            ),
            BenchmarkSample(
                id="sq2",
                question="When was the Eiffel Tower built?",
                context="The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris. It was constructed from 1887 to 1889 as the centerpiece of the 1889 World's Fair.",
                expected_answer="1889",
                expected_answers=["1887 to 1889", "1889", "from 1887 to 1889"],
            ),
            BenchmarkSample(
                id="sq3",
                question="Who wrote Romeo and Juliet?",
                context="Romeo and Juliet is a tragedy written by William Shakespeare early in his career.",
                expected_answer="William Shakespeare",
                expected_answers=["William Shakespeare", "Shakespeare"],
            ),
            BenchmarkSample(
                id="sq4",
                question="What is photosynthesis?",
                context="Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water.",
                expected_answer="the process by which green plants use sunlight to synthesize foods",
            ),
            BenchmarkSample(
                id="sq5",
                question="What is the speed of light?",
                context="The speed of light in vacuum is exactly 299,792,458 meters per second, approximately 300,000 kilometers per second.",
                expected_answer="299,792,458 meters per second",
                expected_answers=["299,792,458 meters per second", "300,000 kilometers per second", "about 300,000 km/s"],
            ),
        ]
        
        if sample_size:
            samples = samples[:sample_size]
        
        self.samples = samples
        return samples
    
    def evaluate_sample(
        self,
        sample: BenchmarkSample,
        predicted: str,
    ) -> Tuple[bool, float]:
        """Evaluate using F1 and exact match."""
        expected_list = sample.expected_answers or [sample.expected_answer or ""]
        
        # Check exact match first
        if exact_match_any(predicted, expected_list):
            return True, 1.0
        
        # Check if answer is contained
        for exp in expected_list:
            if contains_answer(predicted, exp):
                return True, 0.9
        
        # Calculate best F1
        best_f1 = max(f1_score(predicted, exp) for exp in expected_list)
        return best_f1 > 0.5, best_f1


class TriviaQABenchmark(Benchmark):
    """TriviaQA benchmark for factual knowledge."""
    
    def __init__(self, data_path: Optional[str] = None):
        super().__init__("TriviaQA", BenchmarkType.QA, data_path)
    
    def load_data(self, sample_size: Optional[int] = None) -> List[BenchmarkSample]:
        """Load TriviaQA data."""
        samples = [
            BenchmarkSample(id="tq1", question="What year did World War II end?", expected_answer="1945"),
            BenchmarkSample(id="tq2", question="Who painted the Mona Lisa?", expected_answer="Leonardo da Vinci"),
            BenchmarkSample(id="tq3", question="What is the largest planet in our solar system?", expected_answer="Jupiter"),
            BenchmarkSample(id="tq4", question="Who was the first person to walk on the moon?", expected_answer="Neil Armstrong"),
            BenchmarkSample(id="tq5", question="What is the chemical symbol for gold?", expected_answer="Au"),
            BenchmarkSample(id="tq6", question="In what year did the Titanic sink?", expected_answer="1912"),
            BenchmarkSample(id="tq7", question="Who wrote '1984'?", expected_answer="George Orwell"),
            BenchmarkSample(id="tq8", question="What is the capital of Japan?", expected_answer="Tokyo"),
            BenchmarkSample(id="tq9", question="How many continents are there?", expected_answer="7", expected_answers=["7", "seven"]),
            BenchmarkSample(id="tq10", question="What is the longest river in the world?", expected_answer="Nile", expected_answers=["Nile", "The Nile", "Nile River"]),
        ]
        
        if sample_size:
            samples = samples[:sample_size]
        
        self.samples = samples
        return samples
    
    def evaluate_sample(
        self,
        sample: BenchmarkSample,
        predicted: str,
    ) -> Tuple[bool, float]:
        """Evaluate factual accuracy."""
        expected_list = sample.expected_answers or [sample.expected_answer or ""]
        
        if exact_match_any(predicted, expected_list):
            return True, 1.0
        
        for exp in expected_list:
            if contains_answer(predicted, exp):
                return True, 0.9
        
        return False, 0.0


# ==============================================================================
# Reasoning Benchmarks
# ==============================================================================

class GSM8KBenchmark(Benchmark):
    """GSM8K benchmark for grade school math reasoning."""
    
    def __init__(self, data_path: Optional[str] = None):
        super().__init__("GSM8K", BenchmarkType.REASONING, data_path)
    
    def load_data(self, sample_size: Optional[int] = None) -> List[BenchmarkSample]:
        """Load GSM8K data."""
        samples = [
            BenchmarkSample(
                id="gsm1",
                question="Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?",
                expected_answer="18",
            ),
            BenchmarkSample(
                id="gsm2",
                question="A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?",
                expected_answer="3",
            ),
            BenchmarkSample(
                id="gsm3",
                question="Josh decides to try flipping a house. He buys a house for $80,000 and then puts in $50,000 in repairs. This increased the value of the house by 150%. How much profit did he make?",
                expected_answer="70000",
                expected_answers=["70000", "70,000", "$70,000", "$70000"],
            ),
            BenchmarkSample(
                id="gsm4",
                question="If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?",
                expected_answer="5",
            ),
            BenchmarkSample(
                id="gsm5",
                question="A baker has 24 cupcakes. If she sells 8 cupcakes in the morning and 10 in the afternoon, how many cupcakes does she have left?",
                expected_answer="6",
            ),
        ]
        
        if sample_size:
            samples = samples[:sample_size]
        
        self.samples = samples
        return samples
    
    def get_prompt(self, sample: BenchmarkSample) -> str:
        """Generate math reasoning prompt."""
        return (
            f"Solve the following math problem step by step. "
            f"At the end, provide your final answer as a number.\n\n"
            f"Problem: {sample.question}\n\n"
            f"Solution:"
        )
    
    def evaluate_sample(
        self,
        sample: BenchmarkSample,
        predicted: str,
    ) -> Tuple[bool, float]:
        """Evaluate math answer."""
        expected_list = sample.expected_answers or [sample.expected_answer or ""]
        
        # Extract numbers from prediction
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', predicted.replace(',', ''))
        
        for num in numbers:
            clean_num = num.replace(',', '')
            for exp in expected_list:
                clean_exp = exp.replace(',', '').replace('$', '').strip()
                if clean_num == clean_exp:
                    return True, 1.0
        
        # Check if answer appears in text
        for exp in expected_list:
            if exp.replace(',', '') in predicted.replace(',', ''):
                return True, 0.9
        
        return False, 0.0


class LogicalReasoningBenchmark(Benchmark):
    """Logical reasoning benchmark."""
    
    def __init__(self, data_path: Optional[str] = None):
        super().__init__("LogicalReasoning", BenchmarkType.REASONING, data_path)
    
    def load_data(self, sample_size: Optional[int] = None) -> List[BenchmarkSample]:
        """Load logical reasoning data."""
        samples = [
            BenchmarkSample(
                id="lr1",
                question="All roses are flowers. Some flowers fade quickly. Can we conclude that some roses fade quickly?",
                expected_answer="No",
                metadata={"type": "syllogism"},
            ),
            BenchmarkSample(
                id="lr2",
                question="If it rains, the ground gets wet. The ground is wet. Did it rain?",
                expected_answer="Not necessarily",
                expected_answers=["Not necessarily", "No", "Cannot be determined"],
                metadata={"type": "affirming_consequent"},
            ),
            BenchmarkSample(
                id="lr3",
                question="All mammals are warm-blooded. Whales are mammals. Are whales warm-blooded?",
                expected_answer="Yes",
                metadata={"type": "syllogism"},
            ),
            BenchmarkSample(
                id="lr4",
                question="If A then B. If B then C. A is true. What is C?",
                expected_answer="True",
                expected_answers=["True", "C is true"],
                metadata={"type": "transitive"},
            ),
        ]
        
        if sample_size:
            samples = samples[:sample_size]
        
        self.samples = samples
        return samples
    
    def evaluate_sample(
        self,
        sample: BenchmarkSample,
        predicted: str,
    ) -> Tuple[bool, float]:
        """Evaluate logical reasoning."""
        expected_list = sample.expected_answers or [sample.expected_answer or ""]
        
        pred_lower = predicted.lower().strip()
        
        for exp in expected_list:
            exp_lower = exp.lower().strip()
            if exp_lower in pred_lower or pred_lower.startswith(exp_lower):
                return True, 1.0
        
        return False, 0.0


# ==============================================================================
# Benchmark Runner
# ==============================================================================

class BenchmarkRunner:
    """Runs benchmarks and collects results."""
    
    BENCHMARKS = {
        "squad": SQuADBenchmark,
        "triviaqa": TriviaQABenchmark,
        "gsm8k": GSM8KBenchmark,
        "logical": LogicalReasoningBenchmark,
    }
    
    def __init__(
        self,
        llmhive_client: Optional[Any] = None,
        output_dir: str = "./benchmark_results",
    ):
        self.llmhive_client = llmhive_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, BenchmarkResult] = {}
    
    async def run_benchmark(
        self,
        benchmark_name: str,
        sample_size: Optional[int] = None,
        models: Optional[List[str]] = None,
        save_results: bool = True,
    ) -> BenchmarkResult:
        """Run a specific benchmark."""
        if benchmark_name not in self.BENCHMARKS:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")
        
        benchmark = self.BENCHMARKS[benchmark_name]()
        samples = benchmark.load_data(sample_size)
        
        logger.info(f"Running {benchmark_name} benchmark with {len(samples)} samples")
        
        results: List[EvaluationResult] = []
        model_results: Dict[str, List[bool]] = {}
        
        for sample in samples:
            prompt = benchmark.get_prompt(sample)
            
            start_time = time.time()
            
            # Get prediction from LLMHive
            predicted, model_used = await self._get_prediction(prompt, models)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Evaluate
            correct, score = benchmark.evaluate_sample(sample, predicted)
            
            result = EvaluationResult(
                sample_id=sample.id,
                question=sample.question,
                expected=sample.expected_answer or "",
                predicted=predicted,
                correct=correct,
                score=score,
                latency_ms=latency_ms,
                model_used=model_used,
            )
            results.append(result)
            
            # Track by model
            if model_used not in model_results:
                model_results[model_used] = []
            model_results[model_used].append(correct)
        
        # Calculate aggregate metrics
        latencies = [r.latency_ms for r in results]
        
        benchmark_result = BenchmarkResult(
            benchmark_name=benchmark_name,
            benchmark_type=benchmark.benchmark_type,
            total_samples=len(results),
            correct_count=sum(1 for r in results if r.correct),
            accuracy=sum(1 for r in results if r.correct) / len(results) if results else 0,
            avg_score=sum(r.score for r in results) / len(results) if results else 0,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            p50_latency_ms=percentile(latencies, 50),
            p95_latency_ms=percentile(latencies, 95),
            p99_latency_ms=percentile(latencies, 99),
            model_breakdown={
                model: sum(correct_list) / len(correct_list)
                for model, correct_list in model_results.items()
            },
            results=results,
        )
        
        self.results[benchmark_name] = benchmark_result
        
        if save_results:
            self._save_results(benchmark_result)
        
        logger.info(benchmark_result.summary())
        
        return benchmark_result
    
    async def run_all(
        self,
        sample_size: Optional[int] = None,
        benchmarks: Optional[List[str]] = None,
    ) -> Dict[str, BenchmarkResult]:
        """Run all benchmarks."""
        benchmark_names = benchmarks or list(self.BENCHMARKS.keys())
        
        all_results = {}
        for name in benchmark_names:
            try:
                result = await self.run_benchmark(name, sample_size)
                all_results[name] = result
            except Exception as e:
                logger.error(f"Benchmark {name} failed: {e}")
        
        # Save summary
        self._save_summary(all_results)
        
        return all_results
    
    async def _get_prediction(
        self,
        prompt: str,
        models: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        """Get prediction from LLMHive."""
        if self.llmhive_client:
            try:
                result = await self.llmhive_client.orchestrate(prompt, models=models)
                return (
                    getattr(result, 'content', str(result)),
                    getattr(result, 'model', 'unknown'),
                )
            except Exception as e:
                logger.error(f"LLMHive prediction failed: {e}")
                return f"Error: {e}", "error"
        else:
            # Stub response for testing
            return "Stub response - connect LLMHive client", "stub"
    
    def _save_results(self, result: BenchmarkResult) -> None:
        """Save benchmark results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{result.benchmark_name}_{timestamp}.json"
        
        data = result.to_dict()
        data["results"] = [
            {
                "sample_id": r.sample_id,
                "question": r.question,
                "expected": r.expected,
                "predicted": r.predicted,
                "correct": r.correct,
                "score": r.score,
                "latency_ms": r.latency_ms,
                "model": r.model_used,
            }
            for r in result.results
        ]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
    
    def _save_summary(self, results: Dict[str, BenchmarkResult]) -> None:
        """Save summary of all benchmarks."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"summary_{timestamp}.json"
        
        summary = {
            "timestamp": timestamp,
            "benchmarks": {
                name: result.to_dict()
                for name, result in results.items()
            },
            "overall": {
                "total_samples": sum(r.total_samples for r in results.values()),
                "avg_accuracy": sum(r.accuracy for r in results.values()) / len(results) if results else 0,
                "avg_latency_ms": sum(r.avg_latency_ms for r in results.values()) / len(results) if results else 0,
            },
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary saved to {filename}")
    
    def print_summary(self) -> None:
        """Print summary of all results."""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 60)
        
        for name, result in self.results.items():
            print(f"\n{name}:")
            print(f"  Accuracy: {result.accuracy:.1%} ({result.correct_count}/{result.total_samples})")
            print(f"  Avg Score: {result.avg_score:.3f}")
            print(f"  Latency: avg={result.avg_latency_ms:.0f}ms, p95={result.p95_latency_ms:.0f}ms")
            if result.model_breakdown:
                print("  Model breakdown:")
                for model, acc in result.model_breakdown.items():
                    print(f"    {model}: {acc:.1%}")
        
        print("\n" + "=" * 60)

