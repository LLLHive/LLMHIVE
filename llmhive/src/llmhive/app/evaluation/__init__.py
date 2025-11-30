"""Evaluation and Benchmarking Framework for LLMHive.

This module provides comprehensive evaluation capabilities:
- Standard QA benchmarks (SQuAD, WikiQA, TriviaQA)
- Reasoning benchmarks (GSM8K, MMLU)
- Code generation benchmarks (HumanEval, MBPP)
- A/B testing against baselines
- Performance metrics and reporting

Usage:
    from llmhive.app.evaluation import (
        BenchmarkRunner,
        QABenchmark,
        ReasoningBenchmark,
        ABTester,
        run_full_evaluation,
    )
    
    runner = BenchmarkRunner()
    results = await runner.run_all()
"""
from __future__ import annotations

__all__ = [
    "BenchmarkRunner",
    "BenchmarkResult",
    "QABenchmark",
    "ReasoningBenchmark",
    "CodeBenchmark",
    "ABTester",
    "SecurityAudit",
    "LoadTester",
]

