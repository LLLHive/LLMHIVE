"""Performance Controller - The Brain That Beats All Models.

This is the master controller that combines all advanced techniques to
ensure LLMHive consistently outperforms individual models on all tasks.

It coordinates:
1. Advanced Reasoning (ToT, Self-Consistency, Reflection)
2. Smart Ensemble (Model selection, weighted combination)
3. Tool Verification (Math, code, facts)
4. Benchmark Optimization (Task-specific strategies)
5. Error Recovery (Detect and fix problems)

Goal: ALWAYS beat the best single model through intelligent coordination.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto

from .advanced_reasoning import (
    AdvancedReasoningEngine,
    ReasoningStrategy,
    get_reasoning_engine,
)
from .smart_ensemble import SmartEnsemble, TaskCategory, get_smart_ensemble
from .tool_verification import VerificationPipeline, get_verification_pipeline
from .benchmark_strategies import BenchmarkOptimizer, BenchmarkType

logger = logging.getLogger(__name__)


class PerformanceMode(Enum):
    """Operating modes for the performance controller."""
    SPEED = auto()        # Fastest response, lower accuracy
    BALANCED = auto()     # Balance speed and accuracy
    ACCURACY = auto()     # Maximum accuracy, slower
    BENCHMARK = auto()    # Optimized for benchmark performance


@dataclass
class PerformanceConfig:
    """Configuration for performance controller."""
    mode: PerformanceMode = PerformanceMode.BALANCED
    max_parallel_calls: int = 5
    max_reasoning_rounds: int = 3
    enable_verification: bool = True
    enable_error_recovery: bool = True
    confidence_threshold: float = 0.85
    fallback_on_failure: bool = True


@dataclass
class PerformanceResult:
    """Result from performance-optimized execution."""
    answer: str
    confidence: float
    models_used: List[str]
    strategy: str
    reasoning_trace: List[str] = field(default_factory=list)
    verified: bool = False
    corrections_made: int = 0
    total_latency_ms: int = 0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceController:
    """Master controller for beating all models.
    
    This is the highest-level orchestration that combines everything
    to ensure maximum performance on any task.
    
    Key principles:
    1. Right model for right task
    2. Right strategy for right problem
    3. Verify everything that can be verified
    4. Fix errors before they reach the user
    5. Learn and adapt from outcomes
    """
    
    def __init__(
        self,
        model_caller: Callable,
        config: Optional[PerformanceConfig] = None,
    ):
        """Initialize the performance controller.
        
        Args:
            model_caller: Async function(model_id, prompt) -> response
            config: Optional configuration
        """
        self.model_caller = model_caller
        self.config = config or PerformanceConfig()
        
        # Initialize subsystems
        self.reasoning = AdvancedReasoningEngine(model_caller)
        self.ensemble = SmartEnsemble(model_caller)
        self.verifier = VerificationPipeline()
        self.benchmark_optimizer = BenchmarkOptimizer(
            model_caller, self.reasoning, self.ensemble, self.verifier
        )
        
        # Performance tracking
        self._performance_log: List[Dict[str, Any]] = []
        self._task_success_rates: Dict[str, List[bool]] = {}
        
        logger.info("PerformanceController initialized")
    
    async def process(
        self,
        query: str,
        available_models: List[str],
        context: Optional[str] = None,
        mode: Optional[PerformanceMode] = None,
    ) -> PerformanceResult:
        """Process a query with maximum performance.
        
        This is the main entry point. It analyzes the query, selects
        the optimal strategy, executes it, verifies results, and
        recovers from any errors.
        
        Args:
            query: The query to process
            available_models: List of available model IDs
            context: Optional additional context
            mode: Optional mode override
            
        Returns:
            PerformanceResult with optimized answer
        """
        start_time = time.time()
        mode = mode or self.config.mode
        
        # Step 1: Analyze the query
        analysis = self._analyze_query(query)
        
        # Step 2: Select strategy based on mode and analysis
        strategy = self._select_strategy(analysis, mode)
        
        # Step 3: Select models
        models = self._select_models(query, available_models, analysis, mode)
        
        # Step 4: Execute with selected strategy
        result = await self._execute(query, models, strategy, context, analysis)
        
        # Step 5: Verify if enabled
        if self.config.enable_verification and analysis["verifiable"]:
            result = await self._verify_and_correct(result, query)
        
        # Step 6: Error recovery if confidence too low
        if self.config.enable_error_recovery and result.confidence < self.config.confidence_threshold:
            result = await self._attempt_recovery(query, models, result, context)
        
        # Record performance
        result.total_latency_ms = int((time.time() - start_time) * 1000)
        self._log_performance(query, result, analysis)
        
        return result
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine optimal handling."""
        query_lower = query.lower()
        
        # Detect task type
        task_category = self.ensemble.detect_task_category(query)
        
        # Detect benchmark type
        benchmark_type = self.benchmark_optimizer.detect_benchmark_type(query)
        
        # Determine complexity
        complexity = self._estimate_complexity(query)
        
        # Determine if verifiable
        verifiable = any([
            task_category == TaskCategory.MATH,
            task_category == TaskCategory.CODING,
            "calculate" in query_lower,
            "code" in query_lower,
        ])
        
        # Detect multiple choice
        is_multiple_choice = any([
            "(A)" in query,
            "A)" in query,
            "a." in query_lower,
        ])
        
        return {
            "task_category": task_category,
            "benchmark_type": benchmark_type,
            "complexity": complexity,
            "verifiable": verifiable,
            "is_multiple_choice": is_multiple_choice,
            "query_length": len(query),
        }
    
    def _estimate_complexity(self, query: str) -> str:
        """Estimate query complexity."""
        # Simple heuristics
        length = len(query)
        question_marks = query.count("?")
        
        if length < 50 and question_marks <= 1:
            return "simple"
        elif length < 200 or question_marks <= 2:
            return "medium"
        else:
            return "complex"
    
    def _select_strategy(
        self,
        analysis: Dict[str, Any],
        mode: PerformanceMode
    ) -> ReasoningStrategy:
        """Select the optimal reasoning strategy."""
        task = analysis["task_category"]
        complexity = analysis["complexity"]
        
        # Mode-based selection
        if mode == PerformanceMode.SPEED:
            if complexity == "simple":
                return ReasoningStrategy.DIRECT
            return ReasoningStrategy.CHAIN_OF_THOUGHT
        
        elif mode == PerformanceMode.BENCHMARK:
            # Use benchmark-optimized strategies
            bt = analysis["benchmark_type"]
            return self.benchmark_optimizer.OPTIMAL_CONFIGS.get(
                bt, 
                self.benchmark_optimizer.OPTIMAL_CONFIGS[BenchmarkType.GENERAL]
            ).reasoning_strategy
        
        elif mode == PerformanceMode.ACCURACY:
            # Maximum accuracy strategies
            if task == TaskCategory.MATH:
                return ReasoningStrategy.STEP_VERIFY
            elif task == TaskCategory.CODING:
                return ReasoningStrategy.BEST_OF_N
            elif task == TaskCategory.REASONING:
                return ReasoningStrategy.SELF_CONSISTENCY
            elif task == TaskCategory.FACTUAL:
                return ReasoningStrategy.DEBATE
            elif complexity == "complex":
                return ReasoningStrategy.TREE_OF_THOUGHTS
            return ReasoningStrategy.MIXTURE
        
        else:  # BALANCED
            if task == TaskCategory.MATH:
                return ReasoningStrategy.STEP_VERIFY
            elif task == TaskCategory.CODING:
                return ReasoningStrategy.REFLECTION
            elif analysis["is_multiple_choice"]:
                return ReasoningStrategy.SELF_CONSISTENCY
            elif complexity == "complex":
                return ReasoningStrategy.TREE_OF_THOUGHTS
            return ReasoningStrategy.CHAIN_OF_THOUGHT
    
    def _select_models(
        self,
        query: str,
        available_models: List[str],
        analysis: Dict[str, Any],
        mode: PerformanceMode
    ) -> List[str]:
        """Select optimal models for the query."""
        task = analysis["task_category"]
        
        if mode == PerformanceMode.SPEED:
            # Single best model
            best = self.ensemble.select_best_model(
                query, available_models, task, optimize_for="speed"
            )
            return [best]
        
        elif mode == PerformanceMode.ACCURACY or mode == PerformanceMode.BENCHMARK:
            # Diverse ensemble
            return self.ensemble.select_ensemble(
                query, available_models, max_models=3, task_category=task
            )
        
        else:  # BALANCED
            # Top 2 models
            return self.ensemble.select_ensemble(
                query, available_models, max_models=2, task_category=task
            )
    
    async def _execute(
        self,
        query: str,
        models: List[str],
        strategy: ReasoningStrategy,
        context: Optional[str],
        analysis: Dict[str, Any],
    ) -> PerformanceResult:
        """Execute the query with selected strategy and models."""
        # Map task category to string for reasoning engine
        task_type = analysis["task_category"].value
        
        # Execute reasoning
        reasoning_result = await self.reasoning.reason(
            query=query,
            task_type=task_type,
            models=models,
            strategy=strategy,
            context=context,
        )
        
        return PerformanceResult(
            answer=reasoning_result.answer,
            confidence=reasoning_result.confidence,
            models_used=reasoning_result.models_used,
            strategy=strategy.name,
            reasoning_trace=reasoning_result.reasoning_trace,
            verified=False,
        )
    
    async def _verify_and_correct(
        self,
        result: PerformanceResult,
        query: str
    ) -> PerformanceResult:
        """Verify answer and correct if needed."""
        verified_answer, confidence, issues = await self.verifier.verify_answer(
            result.answer, query, fix_errors=True
        )
        
        # Track corrections
        corrections = 1 if verified_answer != result.answer else 0
        
        return PerformanceResult(
            answer=verified_answer,
            confidence=min(result.confidence, confidence),
            models_used=result.models_used,
            strategy=result.strategy,
            reasoning_trace=result.reasoning_trace + [f"Verification issues: {issues}"] if issues else result.reasoning_trace,
            verified=True,
            corrections_made=corrections,
        )
    
    async def _attempt_recovery(
        self,
        query: str,
        models: List[str],
        current_result: PerformanceResult,
        context: Optional[str],
    ) -> PerformanceResult:
        """Attempt to recover from low confidence result."""
        logger.info(
            f"Attempting recovery (confidence {current_result.confidence:.2f} "
            f"below threshold {self.config.confidence_threshold})"
        )
        
        # Strategy 1: Try different reasoning strategy
        alternate_strategies = [
            ReasoningStrategy.SELF_CONSISTENCY,
            ReasoningStrategy.REFLECTION,
            ReasoningStrategy.DEBATE,
        ]
        
        for strategy in alternate_strategies:
            if strategy.name == current_result.strategy:
                continue
            
            alt_result = await self.reasoning.reason(
                query=query,
                models=models,
                strategy=strategy,
                context=context,
            )
            
            if alt_result.confidence > current_result.confidence:
                return PerformanceResult(
                    answer=alt_result.answer,
                    confidence=alt_result.confidence,
                    models_used=alt_result.models_used,
                    strategy=f"RECOVERED_{strategy.name}",
                    reasoning_trace=current_result.reasoning_trace + [
                        f"Recovery attempt with {strategy.name}"
                    ],
                    corrections_made=current_result.corrections_made + 1,
                )
        
        # Strategy 2: Synthesize from multiple attempts
        if len(models) > 1:
            synthesis_prompt = f"""We have multiple answers to this question but aren't confident in any.

Question: {query}

Current best answer (confidence {current_result.confidence:.0%}):
{current_result.answer}

Please provide the most accurate answer, explaining your reasoning:"""
            
            synthesized = await self.model_caller(models[0], synthesis_prompt)
            
            return PerformanceResult(
                answer=synthesized,
                confidence=min(current_result.confidence + 0.1, 0.8),
                models_used=models,
                strategy=f"RECOVERED_SYNTHESIS",
                reasoning_trace=current_result.reasoning_trace + ["Recovery synthesis"],
                corrections_made=current_result.corrections_made + 1,
            )
        
        return current_result
    
    def _log_performance(
        self,
        query: str,
        result: PerformanceResult,
        analysis: Dict[str, Any]
    ) -> None:
        """Log performance for learning."""
        log_entry = {
            "query_preview": query[:100],
            "task_category": analysis["task_category"].value,
            "strategy": result.strategy,
            "confidence": result.confidence,
            "latency_ms": result.total_latency_ms,
            "models_used": result.models_used,
            "verified": result.verified,
            "corrections": result.corrections_made,
        }
        
        self._performance_log.append(log_entry)
        
        # Keep last 1000 entries
        if len(self._performance_log) > 1000:
            self._performance_log = self._performance_log[-1000:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self._performance_log:
            return {"message": "No performance data yet"}
        
        # Calculate stats
        avg_confidence = sum(
            e["confidence"] for e in self._performance_log
        ) / len(self._performance_log)
        
        avg_latency = sum(
            e["latency_ms"] for e in self._performance_log
        ) / len(self._performance_log)
        
        verification_rate = sum(
            1 for e in self._performance_log if e["verified"]
        ) / len(self._performance_log)
        
        correction_rate = sum(
            1 for e in self._performance_log if e["corrections"] > 0
        ) / len(self._performance_log)
        
        # Strategy distribution
        strategy_counts: Dict[str, int] = {}
        for entry in self._performance_log:
            strategy = entry["strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            "total_queries": len(self._performance_log),
            "avg_confidence": round(avg_confidence, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "verification_rate": round(verification_rate, 3),
            "correction_rate": round(correction_rate, 3),
            "strategy_distribution": strategy_counts,
        }


# ==================== Integration with Main Orchestrator ====================

async def create_performance_controller(
    model_caller: Callable,
    mode: str = "balanced"
) -> PerformanceController:
    """Factory function to create a configured performance controller.
    
    Args:
        model_caller: Function to call models
        mode: One of "speed", "balanced", "accuracy", "benchmark"
        
    Returns:
        Configured PerformanceController
    """
    mode_map = {
        "speed": PerformanceMode.SPEED,
        "balanced": PerformanceMode.BALANCED,
        "accuracy": PerformanceMode.ACCURACY,
        "benchmark": PerformanceMode.BENCHMARK,
    }
    
    config = PerformanceConfig(
        mode=mode_map.get(mode.lower(), PerformanceMode.BALANCED),
        enable_verification=True,
        enable_error_recovery=True,
    )
    
    return PerformanceController(model_caller, config)


# Singleton
_performance_controller: Optional[PerformanceController] = None


def get_performance_controller(
    model_caller: Optional[Callable] = None
) -> PerformanceController:
    """Get or create global performance controller."""
    global _performance_controller
    if _performance_controller is None:
        if model_caller is None:
            async def dummy(model, prompt):
                return f"Response from {model}"
            model_caller = dummy
        _performance_controller = PerformanceController(model_caller)
    return _performance_controller

