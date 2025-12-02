"""Benchmark-Optimized Strategies - Beat the Benchmarks.

This module implements strategies specifically optimized to excel at
major AI benchmarks. Each benchmark has unique characteristics and
we tune our approach accordingly.

Target Benchmarks:
- MMLU: Multi-task language understanding
- GSM8K: Grade school math
- HumanEval: Code generation
- TruthfulQA: Factual accuracy
- MATH: Advanced mathematics
- BBH: Big-Bench Hard reasoning
- ARC: Science reasoning

Strategy: Use the technique that BEST fits each benchmark type.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum, auto

from .advanced_reasoning import (
    AdvancedReasoningEngine,
    ReasoningStrategy,
    ReasoningResult,
)
from .smart_ensemble import SmartEnsemble, TaskCategory
from .tool_verification import VerificationPipeline

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks we optimize for."""
    MMLU = "mmlu"                    # Multiple choice knowledge
    GSM8K = "gsm8k"                  # Grade school math
    HUMANEVAL = "humaneval"          # Code generation
    TRUTHFULQA = "truthfulqa"        # Factual accuracy
    MATH = "math"                    # Competition math
    BBH = "bbh"                      # Big-Bench Hard
    ARC = "arc"                      # Science reasoning
    WINOGRANDE = "winogrande"        # Commonsense reasoning
    HELLASWAG = "hellaswag"          # Sentence completion
    DROP = "drop"                    # Reading comprehension
    GENERAL = "general"              # Default


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark-optimized execution."""
    benchmark_type: BenchmarkType
    reasoning_strategy: ReasoningStrategy
    num_samples: int = 1
    use_ensemble: bool = False
    ensemble_size: int = 3
    verify_with_tools: bool = False
    temperature: float = 0.0  # Lower = more deterministic
    max_tokens: int = 2048
    special_prompt: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Result from benchmark-optimized execution."""
    answer: str
    confidence: float
    benchmark_type: BenchmarkType
    strategy_used: str
    models_used: List[str]
    verified: bool = False
    execution_time_ms: int = 0


class BenchmarkOptimizer:
    """Optimizes execution strategy for benchmark performance.
    
    This is critical: different benchmarks need different approaches.
    We've studied what works best for each.
    """
    
    # Optimal configurations per benchmark (research-backed)
    OPTIMAL_CONFIGS = {
        BenchmarkType.MMLU: BenchmarkConfig(
            benchmark_type=BenchmarkType.MMLU,
            reasoning_strategy=ReasoningStrategy.SELF_CONSISTENCY,
            num_samples=5,
            use_ensemble=True,
            ensemble_size=2,
            temperature=0.0,
            special_prompt="Answer the following multiple choice question. Think step by step before selecting A, B, C, or D.",
        ),
        BenchmarkType.GSM8K: BenchmarkConfig(
            benchmark_type=BenchmarkType.GSM8K,
            reasoning_strategy=ReasoningStrategy.STEP_VERIFY,
            num_samples=5,
            use_ensemble=False,
            verify_with_tools=True,  # Use calculator!
            temperature=0.0,
            special_prompt="Solve this math word problem step by step. Show all calculations. End with 'Answer: [number]'",
        ),
        BenchmarkType.HUMANEVAL: BenchmarkConfig(
            benchmark_type=BenchmarkType.HUMANEVAL,
            reasoning_strategy=ReasoningStrategy.BEST_OF_N,
            num_samples=10,  # More samples = more likely correct
            use_ensemble=True,
            ensemble_size=2,
            verify_with_tools=True,  # Execute and test!
            temperature=0.2,  # Slight variation
            special_prompt="Complete the following Python function. Only output the function body, no explanation.",
        ),
        BenchmarkType.TRUTHFULQA: BenchmarkConfig(
            benchmark_type=BenchmarkType.TRUTHFULQA,
            reasoning_strategy=ReasoningStrategy.DEBATE,
            num_samples=3,
            use_ensemble=True,
            ensemble_size=3,
            verify_with_tools=False,
            temperature=0.0,
            special_prompt="Answer truthfully. If you're uncertain, say so. Avoid common misconceptions.",
        ),
        BenchmarkType.MATH: BenchmarkConfig(
            benchmark_type=BenchmarkType.MATH,
            reasoning_strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
            num_samples=5,
            use_ensemble=True,
            verify_with_tools=True,
            temperature=0.2,
            special_prompt="Solve this competition math problem. Consider multiple approaches. Verify your answer. Box the final answer.",
        ),
        BenchmarkType.BBH: BenchmarkConfig(
            benchmark_type=BenchmarkType.BBH,
            reasoning_strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            num_samples=3,
            use_ensemble=False,
            temperature=0.0,
            special_prompt="Let's think through this step by step:",
        ),
        BenchmarkType.ARC: BenchmarkConfig(
            benchmark_type=BenchmarkType.ARC,
            reasoning_strategy=ReasoningStrategy.SELF_CONSISTENCY,
            num_samples=5,
            use_ensemble=True,
            ensemble_size=2,
            temperature=0.0,
            special_prompt="This is a science question. Use scientific reasoning to select the best answer.",
        ),
        BenchmarkType.WINOGRANDE: BenchmarkConfig(
            benchmark_type=BenchmarkType.WINOGRANDE,
            reasoning_strategy=ReasoningStrategy.SELF_CONSISTENCY,
            num_samples=5,
            temperature=0.0,
            special_prompt="Complete the sentence with the most logical choice based on context.",
        ),
        BenchmarkType.HELLASWAG: BenchmarkConfig(
            benchmark_type=BenchmarkType.HELLASWAG,
            reasoning_strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            num_samples=1,
            temperature=0.0,
            special_prompt="Choose the most plausible continuation of the scenario.",
        ),
        BenchmarkType.DROP: BenchmarkConfig(
            benchmark_type=BenchmarkType.DROP,
            reasoning_strategy=ReasoningStrategy.STEP_VERIFY,
            num_samples=3,
            verify_with_tools=True,
            temperature=0.0,
            special_prompt="Read the passage carefully. Answer the question precisely. If the answer is a number, show your calculation.",
        ),
    }
    
    def __init__(
        self,
        model_caller: Callable,
        reasoning_engine: Optional[AdvancedReasoningEngine] = None,
        smart_ensemble: Optional[SmartEnsemble] = None,
        verification_pipeline: Optional[VerificationPipeline] = None,
    ):
        """Initialize benchmark optimizer.
        
        Args:
            model_caller: Function to call models
            reasoning_engine: Optional reasoning engine
            smart_ensemble: Optional ensemble system
            verification_pipeline: Optional verification system
        """
        self.model_caller = model_caller
        
        # Initialize components if not provided
        self.reasoning = reasoning_engine or AdvancedReasoningEngine(model_caller)
        self.ensemble = smart_ensemble or SmartEnsemble(model_caller)
        self.verifier = verification_pipeline or VerificationPipeline()
        
        logger.info("BenchmarkOptimizer initialized")
    
    def detect_benchmark_type(self, query: str) -> BenchmarkType:
        """Detect which benchmark type a query matches."""
        query_lower = query.lower()
        
        # Multiple choice pattern
        if re.match(r'.*(A\)|B\)|C\)|D\))', query) or "(A)" in query:
            # Check for science
            if any(w in query_lower for w in ["science", "biology", "physics", "chemistry"]):
                return BenchmarkType.ARC
            return BenchmarkType.MMLU
        
        # Math word problem
        if any(w in query_lower for w in ["apples", "oranges", "students", "dollars", "kilometers"]):
            if "step" in query_lower or len(query) > 200:
                return BenchmarkType.MATH
            return BenchmarkType.GSM8K
        
        # Code completion
        if "def " in query or "function" in query.lower() or "```" in query:
            return BenchmarkType.HUMANEVAL
        
        # Factual/truthfulness
        if any(w in query_lower for w in ["true that", "is it true", "fact"]):
            return BenchmarkType.TRUTHFULQA
        
        # Competition math indicators
        if any(w in query_lower for w in ["prove", "theorem", "for all", "integral", "polynomial"]):
            return BenchmarkType.MATH
        
        # Reasoning indicators
        if "therefore" in query_lower or "conclude" in query_lower:
            return BenchmarkType.BBH
        
        # Reading comprehension
        if "passage" in query_lower or "according to" in query_lower:
            return BenchmarkType.DROP
        
        return BenchmarkType.GENERAL
    
    async def solve(
        self,
        query: str,
        models: List[str],
        benchmark_type: Optional[BenchmarkType] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkResult:
        """Solve a query using benchmark-optimized strategy.
        
        Args:
            query: The query to solve
            models: Available models
            benchmark_type: Override detected type
            config_override: Override specific config settings
            
        Returns:
            BenchmarkResult with answer
        """
        import time
        start_time = time.time()
        
        # Detect benchmark type
        if benchmark_type is None:
            benchmark_type = self.detect_benchmark_type(query)
        
        # Get optimal config
        config = self.OPTIMAL_CONFIGS.get(
            benchmark_type,
            self.OPTIMAL_CONFIGS.get(BenchmarkType.GENERAL)
        )
        
        if config is None:
            # Default config
            config = BenchmarkConfig(
                benchmark_type=benchmark_type,
                reasoning_strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            )
        
        # Apply overrides
        if config_override:
            for key, value in config_override.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Build prompt
        if config.special_prompt:
            full_query = f"{config.special_prompt}\n\n{query}"
        else:
            full_query = query
        
        # Execute with strategy
        result = await self._execute_strategy(full_query, models, config)
        
        # Verify if configured
        if config.verify_with_tools:
            verified_answer, confidence, issues = await self.verifier.verify_answer(
                result.answer, query, fix_errors=True
            )
            result.answer = verified_answer
            result.confidence = min(result.confidence, confidence)
            result.verified = True
        
        # Extract final answer for benchmarks that expect specific format
        result.answer = self._format_for_benchmark(result.answer, benchmark_type)
        
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result
    
    async def _execute_strategy(
        self,
        query: str,
        models: List[str],
        config: BenchmarkConfig,
    ) -> BenchmarkResult:
        """Execute the configured strategy."""
        models_used = []
        
        # Select models if using ensemble
        if config.use_ensemble:
            selected_models = self.ensemble.select_ensemble(
                query, models, max_models=config.ensemble_size
            )
        else:
            # Use best single model for task
            task_cat = self._benchmark_to_task_category(config.benchmark_type)
            best_model = self.ensemble.select_best_model(
                query, models, task_category=task_cat
            )
            selected_models = [best_model]
        
        models_used = selected_models
        
        # Use reasoning engine with configured strategy
        reasoning_result = await self.reasoning.reason(
            query=query,
            task_type=config.benchmark_type.value,
            models=selected_models,
            strategy=config.reasoning_strategy,
        )
        
        return BenchmarkResult(
            answer=reasoning_result.answer,
            confidence=reasoning_result.confidence,
            benchmark_type=config.benchmark_type,
            strategy_used=config.reasoning_strategy.name,
            models_used=models_used,
        )
    
    def _benchmark_to_task_category(self, benchmark: BenchmarkType) -> TaskCategory:
        """Map benchmark type to task category."""
        mapping = {
            BenchmarkType.MMLU: TaskCategory.REASONING,
            BenchmarkType.GSM8K: TaskCategory.MATH,
            BenchmarkType.HUMANEVAL: TaskCategory.CODING,
            BenchmarkType.TRUTHFULQA: TaskCategory.FACTUAL,
            BenchmarkType.MATH: TaskCategory.MATH,
            BenchmarkType.BBH: TaskCategory.REASONING,
            BenchmarkType.ARC: TaskCategory.REASONING,
            BenchmarkType.WINOGRANDE: TaskCategory.REASONING,
            BenchmarkType.HELLASWAG: TaskCategory.REASONING,
            BenchmarkType.DROP: TaskCategory.ANALYSIS,
        }
        return mapping.get(benchmark, TaskCategory.REASONING)
    
    def _format_for_benchmark(self, answer: str, benchmark: BenchmarkType) -> str:
        """Format answer for benchmark-specific expectations."""
        if benchmark == BenchmarkType.MMLU or benchmark == BenchmarkType.ARC:
            # Extract letter answer
            import re
            match = re.search(r'\b([A-D])\b', answer.upper())
            if match:
                return match.group(1)
        
        elif benchmark == BenchmarkType.GSM8K:
            # Extract final number
            import re
            # Look for "Answer: X" pattern
            match = re.search(r'[Aa]nswer:?\s*(-?\d+(?:\.\d+)?)', answer)
            if match:
                return match.group(1)
            # Fallback: last number in text
            numbers = re.findall(r'-?\d+(?:\.\d+)?', answer)
            if numbers:
                return numbers[-1]
        
        elif benchmark == BenchmarkType.HUMANEVAL:
            # Extract just the code
            import re
            # Remove markdown code blocks
            code = re.sub(r'```python\s*', '', answer)
            code = re.sub(r'```\s*', '', code)
            return code.strip()
        
        return answer


# Import re for format function
import re


class BenchmarkRunner:
    """Run benchmarks and track performance."""
    
    def __init__(self, optimizer: BenchmarkOptimizer):
        self.optimizer = optimizer
        self._results: Dict[str, List[Tuple[bool, float]]] = {}
    
    async def run_benchmark(
        self,
        benchmark_type: BenchmarkType,
        test_cases: List[Dict[str, Any]],
        models: List[str],
    ) -> Dict[str, Any]:
        """Run a benchmark suite.
        
        Args:
            benchmark_type: Type of benchmark
            test_cases: List of {"query": str, "expected": str}
            models: Available models
            
        Returns:
            Benchmark results with accuracy
        """
        correct = 0
        total = len(test_cases)
        results = []
        
        for case in test_cases:
            query = case["query"]
            expected = case["expected"]
            
            result = await self.optimizer.solve(
                query, models, benchmark_type=benchmark_type
            )
            
            # Check correctness
            is_correct = self._check_answer(
                result.answer, expected, benchmark_type
            )
            correct += 1 if is_correct else 0
            
            results.append({
                "query": query[:100],
                "expected": expected,
                "answer": result.answer,
                "correct": is_correct,
                "confidence": result.confidence,
            })
        
        accuracy = correct / total if total > 0 else 0
        
        # Store for tracking
        key = benchmark_type.value
        if key not in self._results:
            self._results[key] = []
        self._results[key].append((accuracy, total))
        
        return {
            "benchmark": benchmark_type.value,
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "results": results[:10],  # First 10 for review
        }
    
    def _check_answer(
        self,
        answer: str,
        expected: str,
        benchmark_type: BenchmarkType
    ) -> bool:
        """Check if answer matches expected."""
        # Normalize
        answer_clean = answer.strip().lower()
        expected_clean = expected.strip().lower()
        
        # For multiple choice, just check letter
        if benchmark_type in [BenchmarkType.MMLU, BenchmarkType.ARC]:
            return answer_clean[:1] == expected_clean[:1]
        
        # For math, compare numbers
        if benchmark_type in [BenchmarkType.GSM8K, BenchmarkType.MATH]:
            try:
                ans_num = float(re.sub(r'[^\d.-]', '', answer_clean))
                exp_num = float(re.sub(r'[^\d.-]', '', expected_clean))
                return abs(ans_num - exp_num) < 0.01
            except:
                pass
        
        # Default: string match
        return answer_clean == expected_clean
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of benchmark performance."""
        summary = {}
        for benchmark, runs in self._results.items():
            accuracies = [r[0] for r in runs]
            summary[benchmark] = {
                "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
                "best_accuracy": max(accuracies) if accuracies else 0,
                "num_runs": len(runs),
            }
        return summary

