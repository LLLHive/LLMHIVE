"""LLMHive Benchmarking System.

This package provides a comprehensive benchmarking framework for comparing
LLMHive against baseline systems (OpenAI, Anthropic, Perplexity) across
complex reasoning tasks.

Components:
- runner_base: Abstract interface for system runners
- runner_llmhive: LLMHive orchestration runner
- runner_openai: OpenAI baseline runner (optional)
- runner_anthropic: Anthropic baseline runner (optional)
- runner_perplexity: Perplexity baseline runner (optional/import)
- scoring: Objective and rubric-based scoring
- cli: Command-line interface for running benchmarks
"""
from __future__ import annotations

from .runner_base import (
    RunResult,
    RunnerBase,
    RunConfig,
    BenchmarkCase,
    SystemInfo,
)
from .scoring import (
    ObjectiveScorer,
    RubricScorer,
    CompositeScorer,
    ScoringResult,
)

__all__ = [
    "RunResult",
    "RunnerBase",
    "RunConfig",
    "BenchmarkCase",
    "SystemInfo",
    "ObjectiveScorer",
    "RubricScorer", 
    "CompositeScorer",
    "ScoringResult",
]

