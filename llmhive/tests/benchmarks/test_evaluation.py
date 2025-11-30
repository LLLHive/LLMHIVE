"""Tests for the Evaluation and Benchmarking Framework.

This module tests:
- Benchmark loading and execution
- Metric calculations
- A/B testing
- Security audit
- Load testing
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Import evaluation modules
import sys
from pathlib import Path

# Add source to path
src_path = Path(__file__).parent.parent.parent / "src" / "llmhive"
sys.path.insert(0, str(src_path))

from app.evaluation.benchmarks import (
    BenchmarkRunner,
    BenchmarkResult,
    BenchmarkSample,
    BenchmarkType,
    SQuADBenchmark,
    TriviaQABenchmark,
    GSM8KBenchmark,
    exact_match,
    f1_score,
    normalize_answer,
    percentile,
)
from app.evaluation.ab_testing import (
    ABTester,
    ABTestResult,
    ComparisonResult,
    ResponseEvaluator,
)
from app.evaluation.security_audit import (
    SecurityAudit,
    AuditCategory,
    AuditSeverity,
    AuditStatus,
    AuditFinding,
)


# ==============================================================================
# Metric Tests
# ==============================================================================

class TestMetrics:
    """Test evaluation metrics."""
    
    def test_normalize_answer(self):
        """Test answer normalization."""
        assert normalize_answer("The Answer") == "answer"
        assert normalize_answer("  spaces  ") == "spaces"
        assert normalize_answer("A test!") == "test"
    
    def test_exact_match(self):
        """Test exact match comparison."""
        assert exact_match("Paris", "paris") is True
        assert exact_match("The Capital", "capital") is True
        assert exact_match("Paris", "London") is False
    
    def test_f1_score(self):
        """Test F1 score calculation."""
        # Perfect match
        assert f1_score("the quick brown fox", "the quick brown fox") == 1.0
        
        # Partial match
        score = f1_score("the quick fox", "the quick brown fox")
        assert 0.5 < score < 1.0
        
        # No match
        assert f1_score("hello", "goodbye") == 0.0
        
        # Empty strings
        assert f1_score("", "test") == 0.0
    
    def test_percentile(self):
        """Test percentile calculation."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        assert percentile(values, 50) == 5
        assert percentile(values, 90) == 9
        assert percentile([], 50) == 0.0


# ==============================================================================
# Benchmark Tests
# ==============================================================================

class TestBenchmarks:
    """Test benchmark loading and evaluation."""
    
    def test_squad_benchmark_load(self):
        """Test SQuAD benchmark loading."""
        benchmark = SQuADBenchmark()
        samples = benchmark.load_data(sample_size=3)
        
        assert len(samples) == 3
        assert all(isinstance(s, BenchmarkSample) for s in samples)
        assert all(s.question for s in samples)
    
    def test_squad_evaluate_correct(self):
        """Test SQuAD evaluation with correct answer."""
        benchmark = SQuADBenchmark()
        sample = BenchmarkSample(
            id="test",
            question="What is the capital of France?",
            expected_answer="Paris",
        )
        
        correct, score = benchmark.evaluate_sample(sample, "Paris")
        assert correct is True
        assert score == 1.0
    
    def test_squad_evaluate_partial(self):
        """Test SQuAD evaluation with partial match."""
        benchmark = SQuADBenchmark()
        sample = BenchmarkSample(
            id="test",
            question="What is the capital of France?",
            expected_answer="Paris",
        )
        
        correct, score = benchmark.evaluate_sample(
            sample, 
            "The capital of France is Paris, a beautiful city."
        )
        assert correct is True
        assert score >= 0.9
    
    def test_triviaqa_benchmark(self):
        """Test TriviaQA benchmark."""
        benchmark = TriviaQABenchmark()
        samples = benchmark.load_data(sample_size=5)
        
        assert len(samples) == 5
        
        # Test evaluation
        sample = samples[0]  # "What year did World War II end?"
        correct, score = benchmark.evaluate_sample(sample, "1945")
        assert correct is True
    
    def test_gsm8k_benchmark(self):
        """Test GSM8K math benchmark."""
        benchmark = GSM8KBenchmark()
        samples = benchmark.load_data(sample_size=3)
        
        assert len(samples) == 3
        
        # Test prompt generation
        prompt = benchmark.get_prompt(samples[0])
        assert "step by step" in prompt.lower()
    
    def test_gsm8k_evaluate_math(self):
        """Test GSM8K math evaluation."""
        benchmark = GSM8KBenchmark()
        sample = BenchmarkSample(
            id="test",
            question="What is 5 + 3?",
            expected_answer="8",
        )
        
        # Correct answer with reasoning
        correct, score = benchmark.evaluate_sample(
            sample,
            "Let me calculate: 5 + 3 = 8. The answer is 8."
        )
        assert correct is True
        assert score == 1.0


# ==============================================================================
# Benchmark Runner Tests
# ==============================================================================

class TestBenchmarkRunner:
    """Test benchmark runner."""
    
    @pytest.fixture
    def runner(self, tmp_path):
        """Create benchmark runner with temp output."""
        return BenchmarkRunner(output_dir=str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_run_benchmark_stub(self, runner):
        """Test running benchmark with stub client."""
        result = await runner.run_benchmark("squad", sample_size=2)
        
        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "squad"
        assert result.total_samples == 2
    
    @pytest.mark.asyncio
    async def test_run_all_benchmarks(self, runner):
        """Test running all benchmarks."""
        results = await runner.run_all(sample_size=2)
        
        assert "squad" in results
        assert "triviaqa" in results
        assert "gsm8k" in results
    
    def test_result_to_dict(self, runner):
        """Test result serialization."""
        result = BenchmarkResult(
            benchmark_name="test",
            benchmark_type=BenchmarkType.QA,
            total_samples=10,
            correct_count=8,
            accuracy=0.8,
            avg_score=0.75,
            avg_latency_ms=100,
            p50_latency_ms=90,
            p95_latency_ms=150,
            p99_latency_ms=200,
            model_breakdown={"gpt-4": 0.8},
            results=[],
        )
        
        data = result.to_dict()
        assert data["accuracy"] == 0.8
        assert data["benchmark_name"] == "test"


# ==============================================================================
# A/B Testing Tests
# ==============================================================================

class TestABTesting:
    """Test A/B testing framework."""
    
    def test_response_evaluator_heuristic(self):
        """Test heuristic comparison."""
        evaluator = ResponseEvaluator()
        
        # Compare responses
        winner, scores, reasoning = asyncio.run(
            evaluator.compare(
                query="What is Python?",
                response_a="Python is a programming language known for its simplicity and readability. It's widely used in data science, web development, and automation.",
                response_b="idk",
                use_llm_judge=False,
            )
        )
        
        assert winner == ComparisonResult.LLMHIVE_BETTER
        assert scores["response_a"] > scores["response_b"]
    
    @pytest.fixture
    def ab_tester(self, tmp_path):
        """Create A/B tester with temp output."""
        return ABTester(output_dir=str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_ab_compare_stub(self, ab_tester):
        """Test A/B comparison with stub."""
        result = await ab_tester.compare(
            queries=["What is 2+2?", "Hello"],
            baseline="gpt-4",
        )
        
        assert isinstance(result, ABTestResult)
        assert result.total_queries == 2
    
    def test_ab_result_summary(self):
        """Test A/B result summary."""
        result = ABTestResult(
            test_name="test",
            total_queries=10,
            llmhive_wins=6,
            baseline_wins=3,
            ties=1,
            errors=0,
            llmhive_win_rate=0.6,
            avg_llmhive_latency_ms=100,
            avg_baseline_latency_ms=150,
            comparisons=[],
            baseline_model="gpt-4",
        )
        
        summary = result.summary()
        assert "60.0%" in summary
        assert "gpt-4" in summary


# ==============================================================================
# Security Audit Tests
# ==============================================================================

class TestSecurityAudit:
    """Test security audit framework."""
    
    @pytest.fixture
    def auditor(self, tmp_path):
        """Create security auditor with temp output."""
        return SecurityAudit(output_dir=str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_run_full_audit(self, auditor):
        """Test running full security audit."""
        result = await auditor.run_full_audit()
        
        assert result is not None
        assert result.total_checks > 0
        assert isinstance(result.findings, list)
    
    def test_audit_finding_creation(self):
        """Test audit finding creation."""
        finding = AuditFinding(
            id="test_001",
            category=AuditCategory.PROMPT_INJECTION,
            title="Test finding",
            description="A test finding",
            severity=AuditSeverity.HIGH,
            status=AuditStatus.FAILED,
            recommendation="Fix this",
        )
        
        assert finding.id == "test_001"
        assert finding.severity == AuditSeverity.HIGH
    
    def test_audit_result_critical_findings(self):
        """Test filtering critical findings."""
        from app.evaluation.security_audit import AuditResult
        
        findings = [
            AuditFinding(
                id="1",
                category=AuditCategory.PROMPT_INJECTION,
                title="Critical",
                description="Critical issue",
                severity=AuditSeverity.CRITICAL,
                status=AuditStatus.FAILED,
            ),
            AuditFinding(
                id="2",
                category=AuditCategory.CONTENT_POLICY,
                title="Low",
                description="Low issue",
                severity=AuditSeverity.LOW,
                status=AuditStatus.PASSED,
            ),
        ]
        
        result = AuditResult(
            audit_name="test",
            timestamp=datetime.now(),
            duration_seconds=10,
            total_checks=2,
            passed=1,
            failed=1,
            warnings=0,
            findings=findings,
        )
        
        assert len(result.critical_findings) == 1
        assert result.critical_findings[0].id == "1"


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestEvaluationIntegration:
    """Integration tests for evaluation system."""
    
    @pytest.mark.asyncio
    async def test_benchmark_with_mock_client(self, tmp_path):
        """Test benchmark with mock LLMHive client."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.orchestrate = AsyncMock(return_value=MagicMock(
            content="Paris",
            model="gpt-4o",
        ))
        
        runner = BenchmarkRunner(
            llmhive_client=mock_client,
            output_dir=str(tmp_path),
        )
        
        result = await runner.run_benchmark("triviaqa", sample_size=2)
        
        # Verify client was called
        assert mock_client.orchestrate.called
        assert result.total_samples == 2
    
    @pytest.mark.asyncio
    async def test_end_to_end_evaluation(self, tmp_path):
        """Test end-to-end evaluation flow."""
        from app.evaluation.runner import EvaluationRunner
        
        runner = EvaluationRunner(output_dir=str(tmp_path))
        
        report = await runner.run_full_evaluation(
            benchmark_sample_size=2,
            run_ab_tests=False,  # Skip A/B tests for speed
            run_security=True,
        )
        
        assert report is not None
        assert "squad" in report.benchmarks
        assert report.security_audit is not None
        assert report.overall_status != ""


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

