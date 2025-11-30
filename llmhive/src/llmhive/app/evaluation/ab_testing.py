"""A/B Testing Framework for LLMHive.

Compare LLMHive's responses against baseline models (GPT-4, Claude, etc.)
to identify strengths, weaknesses, and improvement opportunities.

Usage:
    tester = ABTester()
    results = await tester.compare(
        queries=["What is AI?", "Explain quantum computing"],
        baseline="gpt-4",
    )
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class ComparisonResult(str, Enum):
    """Result of A/B comparison."""
    LLMHIVE_BETTER = "llmhive_better"
    BASELINE_BETTER = "baseline_better"
    TIE = "tie"
    ERROR = "error"


@dataclass
class ResponseComparison:
    """Comparison of two responses."""
    query: str
    llmhive_response: str
    baseline_response: str
    llmhive_latency_ms: float
    baseline_latency_ms: float
    llmhive_model: str
    baseline_model: str
    winner: ComparisonResult
    scores: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """Aggregate A/B test results."""
    test_name: str
    total_queries: int
    llmhive_wins: int
    baseline_wins: int
    ties: int
    errors: int
    llmhive_win_rate: float
    avg_llmhive_latency_ms: float
    avg_baseline_latency_ms: float
    comparisons: List[ResponseComparison]
    baseline_model: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "total_queries": self.total_queries,
            "llmhive_wins": self.llmhive_wins,
            "baseline_wins": self.baseline_wins,
            "ties": self.ties,
            "llmhive_win_rate": round(self.llmhive_win_rate, 4),
            "avg_llmhive_latency_ms": round(self.avg_llmhive_latency_ms, 2),
            "avg_baseline_latency_ms": round(self.avg_baseline_latency_ms, 2),
            "baseline_model": self.baseline_model,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def summary(self) -> str:
        return (
            f"A/B Test vs {self.baseline_model}: "
            f"LLMHive wins {self.llmhive_win_rate:.1%} "
            f"({self.llmhive_wins}/{self.total_queries}), "
            f"Baseline wins {self.baseline_wins}/{self.total_queries}, "
            f"Ties {self.ties}"
        )


# ==============================================================================
# Evaluation Criteria
# ==============================================================================

class ResponseEvaluator:
    """Evaluates and compares responses based on multiple criteria."""
    
    CRITERIA = [
        "accuracy",      # Factual correctness
        "completeness",  # Covers all aspects of the question
        "clarity",       # Easy to understand
        "conciseness",   # Not unnecessarily verbose
        "helpfulness",   # Actually helps answer the question
    ]
    
    def __init__(self, judge_model: Optional[Any] = None):
        """
        Initialize evaluator.
        
        Args:
            judge_model: Optional LLM to use as judge for comparisons
        """
        self.judge_model = judge_model
    
    async def compare(
        self,
        query: str,
        response_a: str,
        response_b: str,
        use_llm_judge: bool = False,
    ) -> Tuple[ComparisonResult, Dict[str, float], str]:
        """
        Compare two responses.
        
        Returns:
            (winner, scores, reasoning)
        """
        if use_llm_judge and self.judge_model:
            return await self._llm_judge_compare(query, response_a, response_b)
        else:
            return self._heuristic_compare(query, response_a, response_b)
    
    def _heuristic_compare(
        self,
        query: str,
        response_a: str,
        response_b: str,
    ) -> Tuple[ComparisonResult, Dict[str, float], str]:
        """Compare using heuristics."""
        scores = {
            "response_a": 0.0,
            "response_b": 0.0,
        }
        reasoning_parts = []
        
        # Length comparison (prefer moderate length)
        len_a, len_b = len(response_a), len(response_b)
        optimal_length = len(query) * 5  # Rough heuristic
        
        len_score_a = 1.0 - min(abs(len_a - optimal_length) / optimal_length, 1.0)
        len_score_b = 1.0 - min(abs(len_b - optimal_length) / optimal_length, 1.0)
        
        scores["response_a"] += len_score_a * 0.2
        scores["response_b"] += len_score_b * 0.2
        
        # Structure (prefer responses with structure)
        has_structure_a = any(c in response_a for c in ['•', '-', '1.', '2.', '\n\n'])
        has_structure_b = any(c in response_b for c in ['•', '-', '1.', '2.', '\n\n'])
        
        if has_structure_a:
            scores["response_a"] += 0.15
            reasoning_parts.append("A has better structure")
        if has_structure_b:
            scores["response_b"] += 0.15
            reasoning_parts.append("B has better structure")
        
        # Keyword relevance
        query_words = set(query.lower().split())
        words_a = set(response_a.lower().split())
        words_b = set(response_b.lower().split())
        
        relevance_a = len(query_words & words_a) / len(query_words) if query_words else 0
        relevance_b = len(query_words & words_b) / len(query_words) if query_words else 0
        
        scores["response_a"] += relevance_a * 0.3
        scores["response_b"] += relevance_b * 0.3
        
        # Completeness (based on length if reasonable)
        if 100 < len_a < 2000:
            scores["response_a"] += 0.2
        if 100 < len_b < 2000:
            scores["response_b"] += 0.2
        
        # Determine winner
        diff = scores["response_a"] - scores["response_b"]
        if abs(diff) < 0.1:
            winner = ComparisonResult.TIE
            reasoning_parts.append("Scores too close")
        elif diff > 0:
            winner = ComparisonResult.LLMHIVE_BETTER
            reasoning_parts.append("A scored higher overall")
        else:
            winner = ComparisonResult.BASELINE_BETTER
            reasoning_parts.append("B scored higher overall")
        
        return winner, scores, "; ".join(reasoning_parts)
    
    async def _llm_judge_compare(
        self,
        query: str,
        response_a: str,
        response_b: str,
    ) -> Tuple[ComparisonResult, Dict[str, float], str]:
        """Use LLM as judge to compare responses."""
        judge_prompt = f"""You are an expert evaluator comparing two AI assistant responses.

Question: {query}

Response A:
{response_a}

Response B:
{response_b}

Evaluate both responses on:
1. Accuracy (factual correctness)
2. Completeness (covers all aspects)
3. Clarity (easy to understand)
4. Helpfulness (actually answers the question)

Output your evaluation as:
WINNER: A, B, or TIE
REASONING: Brief explanation
SCORE_A: 0-100
SCORE_B: 0-100"""

        try:
            result = await self.judge_model.generate(judge_prompt)
            response = result.content if hasattr(result, 'content') else str(result)
            
            # Parse response
            winner = ComparisonResult.TIE
            if "WINNER: A" in response:
                winner = ComparisonResult.LLMHIVE_BETTER
            elif "WINNER: B" in response:
                winner = ComparisonResult.BASELINE_BETTER
            
            scores = {"response_a": 0.5, "response_b": 0.5}
            
            return winner, scores, response
            
        except Exception as e:
            logger.error(f"LLM judge failed: {e}")
            return self._heuristic_compare(query, response_a, response_b)


# ==============================================================================
# A/B Tester
# ==============================================================================

class ABTester:
    """A/B testing framework for comparing LLMHive against baselines."""
    
    def __init__(
        self,
        llmhive_client: Optional[Any] = None,
        output_dir: str = "./ab_test_results",
    ):
        self.llmhive_client = llmhive_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.evaluator = ResponseEvaluator()
        self.results: List[ABTestResult] = []
    
    async def compare(
        self,
        queries: List[str],
        baseline: str = "gpt-4",
        test_name: Optional[str] = None,
        use_llm_judge: bool = False,
    ) -> ABTestResult:
        """
        Compare LLMHive against a baseline model.
        
        Args:
            queries: List of queries to test
            baseline: Baseline model name (gpt-4, claude-3, etc.)
            test_name: Name for this test run
            use_llm_judge: Use LLM as judge for comparison
            
        Returns:
            ABTestResult with comparison data
        """
        test_name = test_name or f"ab_test_{baseline}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting A/B test: {test_name} ({len(queries)} queries)")
        
        comparisons: List[ResponseComparison] = []
        
        for query in queries:
            comparison = await self._compare_single(query, baseline, use_llm_judge)
            comparisons.append(comparison)
            
            # Log progress
            logger.debug(f"Query: {query[:50]}... Winner: {comparison.winner.value}")
        
        # Aggregate results
        llmhive_wins = sum(1 for c in comparisons if c.winner == ComparisonResult.LLMHIVE_BETTER)
        baseline_wins = sum(1 for c in comparisons if c.winner == ComparisonResult.BASELINE_BETTER)
        ties = sum(1 for c in comparisons if c.winner == ComparisonResult.TIE)
        errors = sum(1 for c in comparisons if c.winner == ComparisonResult.ERROR)
        
        result = ABTestResult(
            test_name=test_name,
            total_queries=len(queries),
            llmhive_wins=llmhive_wins,
            baseline_wins=baseline_wins,
            ties=ties,
            errors=errors,
            llmhive_win_rate=llmhive_wins / len(queries) if queries else 0,
            avg_llmhive_latency_ms=sum(c.llmhive_latency_ms for c in comparisons) / len(comparisons) if comparisons else 0,
            avg_baseline_latency_ms=sum(c.baseline_latency_ms for c in comparisons) / len(comparisons) if comparisons else 0,
            comparisons=comparisons,
            baseline_model=baseline,
        )
        
        self.results.append(result)
        self._save_result(result)
        
        logger.info(result.summary())
        
        return result
    
    async def _compare_single(
        self,
        query: str,
        baseline: str,
        use_llm_judge: bool,
    ) -> ResponseComparison:
        """Compare a single query."""
        # Get LLMHive response
        llmhive_response = ""
        llmhive_latency = 0.0
        llmhive_model = "unknown"
        
        try:
            start = time.time()
            if self.llmhive_client:
                result = await self.llmhive_client.orchestrate(query)
                llmhive_response = getattr(result, 'content', str(result))
                llmhive_model = getattr(result, 'model', 'llmhive')
            else:
                llmhive_response = f"[Stub LLMHive response for: {query}]"
                llmhive_model = "stub"
            llmhive_latency = (time.time() - start) * 1000
        except Exception as e:
            llmhive_response = f"Error: {e}"
            llmhive_model = "error"
        
        # Get baseline response
        baseline_response = ""
        baseline_latency = 0.0
        
        try:
            start = time.time()
            baseline_response = await self._get_baseline_response(query, baseline)
            baseline_latency = (time.time() - start) * 1000
        except Exception as e:
            baseline_response = f"Error: {e}"
        
        # Compare
        try:
            winner, scores, reasoning = await self.evaluator.compare(
                query, llmhive_response, baseline_response, use_llm_judge
            )
        except Exception as e:
            winner = ComparisonResult.ERROR
            scores = {}
            reasoning = str(e)
        
        return ResponseComparison(
            query=query,
            llmhive_response=llmhive_response,
            baseline_response=baseline_response,
            llmhive_latency_ms=llmhive_latency,
            baseline_latency_ms=baseline_latency,
            llmhive_model=llmhive_model,
            baseline_model=baseline,
            winner=winner,
            scores=scores,
            reasoning=reasoning,
        )
    
    async def _get_baseline_response(self, query: str, baseline: str) -> str:
        """Get response from baseline model."""
        if baseline.startswith("gpt"):
            return await self._call_openai(query, baseline)
        elif baseline.startswith("claude"):
            return await self._call_anthropic(query, baseline)
        else:
            return f"[Stub baseline response for {baseline}]"
    
    async def _call_openai(self, query: str, model: str) -> str:
        """Call OpenAI API."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "[OpenAI API key not set]"
        
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": query}],
            )
            
            return response.choices[0].message.content or ""
        except ImportError:
            return "[openai package not installed]"
        except Exception as e:
            return f"[OpenAI error: {e}]"
    
    async def _call_anthropic(self, query: str, model: str) -> str:
        """Call Anthropic API."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "[Anthropic API key not set]"
        
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": query}],
            )
            
            return response.content[0].text if response.content else ""
        except ImportError:
            return "[anthropic package not installed]"
        except Exception as e:
            return f"[Anthropic error: {e}]"
    
    def _save_result(self, result: ABTestResult) -> None:
        """Save test results."""
        filename = self.output_dir / f"{result.test_name}.json"
        
        data = result.to_dict()
        data["comparisons"] = [
            {
                "query": c.query,
                "llmhive_response": c.llmhive_response[:500],  # Truncate
                "baseline_response": c.baseline_response[:500],
                "llmhive_latency_ms": c.llmhive_latency_ms,
                "baseline_latency_ms": c.baseline_latency_ms,
                "winner": c.winner.value,
                "reasoning": c.reasoning,
            }
            for c in result.comparisons
        ]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
    
    def print_summary(self) -> None:
        """Print summary of all A/B tests."""
        print("\n" + "=" * 60)
        print("A/B TEST RESULTS SUMMARY")
        print("=" * 60)
        
        for result in self.results:
            print(f"\n{result.test_name}:")
            print(f"  vs {result.baseline_model}")
            print(f"  LLMHive wins: {result.llmhive_wins} ({result.llmhive_win_rate:.1%})")
            print(f"  Baseline wins: {result.baseline_wins}")
            print(f"  Ties: {result.ties}")
            print(f"  Avg latency: LLMHive={result.avg_llmhive_latency_ms:.0f}ms, Baseline={result.avg_baseline_latency_ms:.0f}ms")
        
        print("\n" + "=" * 60)


# ==============================================================================
# Test Queries
# ==============================================================================

STANDARD_TEST_QUERIES = [
    # Factual
    "What is the capital of Australia?",
    "Who invented the telephone?",
    "When did World War I start?",
    
    # Reasoning
    "If I have 3 apples and buy 5 more, then give away 2, how many do I have?",
    "Explain why the sky is blue in simple terms.",
    
    # Creative
    "Write a haiku about technology.",
    "Come up with 3 creative names for a coffee shop.",
    
    # Technical
    "What is the difference between a list and a tuple in Python?",
    "Explain what an API is to a non-technical person.",
    
    # Analysis
    "What are the pros and cons of remote work?",
    "Compare electric and gasoline cars.",
]

