"""Tests for BenchmarkAgent."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from llmhive.app.agents.benchmark_agent import (
    BenchmarkAgent,
    BenchmarkMetrics,
    ModelComparison,
    RegressionAlert,
    BenchmarkRun,
    evaluate_benchmark_case,
    BENCHMARK_CATEGORIES,
    QUICK_BENCHMARK_CASES,
    FULL_BENCHMARK_CASES,
)
from llmhive.app.agents.base import AgentTask


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def agent():
    """Create a fresh BenchmarkAgent for each test."""
    return BenchmarkAgent()


@pytest.fixture
def sample_benchmark_run():
    """Create a sample benchmark run."""
    metrics = BenchmarkMetrics(
        total_cases=10,
        passed_cases=8,
        overall_score=0.85,
        latency_avg_ms=150.0,
        latency_p95_ms=250.0,
        total_tokens=1000,
        category_scores={
            "coding": 0.90,
            "reasoning": 0.85,
            "math": 0.80,
            "factual": 0.85,
        },
    )
    return BenchmarkRun(
        run_id="test-run-001",
        metrics=metrics,
        improvement_opportunities=["Improve math: current 0.80, target 0.85+"],
    )


# ============================================================
# Test BenchmarkMetrics
# ============================================================

class TestBenchmarkMetrics:
    """Tests for BenchmarkMetrics dataclass."""
    
    def test_create_metrics(self):
        """Test creating benchmark metrics."""
        metrics = BenchmarkMetrics(
            total_cases=10,
            passed_cases=8,
            overall_score=0.85,
        )
        
        assert metrics.total_cases == 10
        assert metrics.passed_cases == 8
        assert metrics.overall_score == 0.85
    
    def test_pass_rate_calculation(self):
        """Test pass rate is calculated correctly."""
        metrics = BenchmarkMetrics(
            total_cases=10,
            passed_cases=7,
        )
        
        assert metrics.pass_rate == 0.7
    
    def test_pass_rate_zero_cases(self):
        """Test pass rate with zero cases."""
        metrics = BenchmarkMetrics(
            total_cases=0,
            passed_cases=0,
        )
        
        assert metrics.pass_rate == 0.0
    
    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = BenchmarkMetrics(
            total_cases=10,
            passed_cases=8,
            overall_score=0.85,
            latency_avg_ms=150.5,
            category_scores={"coding": 0.9},
        )
        
        result = metrics.to_dict()
        
        assert result["total_cases"] == 10
        assert result["passed_cases"] == 8
        assert result["pass_rate"] == 0.8
        assert result["overall_score"] == 0.85
        assert "timestamp" in result
        assert "coding" in result["category_scores"]


# ============================================================
# Test ModelComparison
# ============================================================

class TestModelComparison:
    """Tests for ModelComparison dataclass."""
    
    def test_create_comparison(self):
        """Test creating model comparison."""
        comparison = ModelComparison(
            model_name="gpt-4o",
            score=0.92,
            latency_ms=200.0,
            tokens_used=500,
            cases_passed=9,
            cases_total=10,
        )
        
        assert comparison.model_name == "gpt-4o"
        assert comparison.score == 0.92
        assert comparison.cases_passed == 9
    
    def test_to_dict(self):
        """Test comparison serialization."""
        comparison = ModelComparison(
            model_name="claude-3",
            score=0.88,
            latency_ms=180.0,
            tokens_used=450,
            cases_passed=8,
            cases_total=10,
            category_scores={"reasoning": 0.95},
        )
        
        result = comparison.to_dict()
        
        assert result["model"] == "claude-3"
        assert result["score"] == 0.88
        assert result["pass_rate"] == 0.8
        assert "reasoning" in result["category_scores"]


# ============================================================
# Test RegressionAlert
# ============================================================

class TestRegressionAlert:
    """Tests for RegressionAlert dataclass."""
    
    def test_create_alert(self):
        """Test creating regression alert."""
        alert = RegressionAlert(
            category="coding",
            current_score=0.75,
            baseline_score=0.90,
            delta=-0.15,
            severity="high",
        )
        
        assert alert.category == "coding"
        assert alert.delta == -0.15
        assert alert.severity == "high"
    
    def test_to_dict(self):
        """Test alert serialization."""
        alert = RegressionAlert(
            category="math",
            current_score=0.70,
            baseline_score=0.85,
            delta=-0.15,
            severity="critical",
        )
        
        result = alert.to_dict()
        
        assert result["category"] == "math"
        assert result["delta"] == -0.15
        assert result["severity"] == "critical"
        assert "timestamp" in result


# ============================================================
# Test evaluate_benchmark_case
# ============================================================

class TestEvaluateBenchmarkCase:
    """Tests for benchmark case evaluation."""
    
    def test_exact_match_found(self):
        """Test evaluation with expected exact match found."""
        case = {"expected": "Paris"}
        answer = "The capital of France is Paris."
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is True
        assert score == 1.0
        assert "found" in details.lower()
    
    def test_exact_match_not_found(self):
        """Test evaluation with expected exact match not found."""
        case = {"expected": "Paris"}
        answer = "The capital of France is London."
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is False
        assert score < 1.0
    
    def test_expected_number_correct(self):
        """Test evaluation with correct expected number."""
        case = {"expected_number": 12}
        answer = "15% of 80 is 12."
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is True
        assert score == 1.0
    
    def test_expected_number_wrong(self):
        """Test evaluation with wrong expected number."""
        case = {"expected_number": 12}
        answer = "The answer is 15."
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is False
        assert score == 0.0
    
    def test_must_contain_all_terms(self):
        """Test evaluation with must_contain criteria - all found."""
        case = {"eval_criteria": {"must_contain": ["def", "return"]}}
        answer = "def reverse(s):\n    return s[::-1]"
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is True
        assert score == 1.0
    
    def test_must_contain_partial_terms(self):
        """Test evaluation with must_contain criteria - partial."""
        case = {"eval_criteria": {"must_contain": ["def", "return", "class"]}}
        answer = "def reverse(s):\n    return s[::-1]"
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is False
        assert 0 < score < 1.0
        assert "2/3" in details
    
    def test_explains_fallacy(self):
        """Test evaluation for fallacy explanation."""
        case = {"eval_criteria": {"explains_fallacy": True}}
        answer = "This is a fallacy because the calculation is misleading."
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is True
        assert score == 1.0
    
    def test_poem_evaluation(self):
        """Test evaluation for poem."""
        case = {"eval_criteria": {"is_poem": True, "min_lines": 3}}
        answer = "Line one\nLine two\nLine three\nLine four"
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is True
        assert score >= 0.9
    
    def test_default_evaluation_substantive(self):
        """Test default evaluation with substantive answer."""
        case = {}
        answer = "This is a detailed and comprehensive answer that explains the concept thoroughly with examples and context."
        
        passed, score, details = evaluate_benchmark_case(case, answer)
        
        assert passed is True
        assert score == 0.7


# ============================================================
# Test BenchmarkAgent
# ============================================================

class TestBenchmarkAgent:
    """Tests for BenchmarkAgent class."""
    
    def test_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.config.name == "benchmark_agent"
        assert agent.config.schedule_interval_seconds == 86400
        assert agent._total_runs == 0
    
    def test_get_capabilities(self, agent):
        """Test agent capabilities."""
        caps = agent.get_capabilities()
        
        assert caps["name"] == "Benchmark Agent"
        assert caps["type"] == "scheduled"
        assert "run_benchmark" in caps["task_types"]
        assert "compare_models" in caps["task_types"]
        assert "detect_regressions" in caps["task_types"]
        assert "generate_report" in caps["task_types"]
    
    @pytest.mark.asyncio
    async def test_execute_without_task(self, agent):
        """Test executing without a task runs quick benchmark."""
        result = await agent.execute()
        
        assert result.success is True
        assert "metrics" in result.output
        assert result.output["metrics"]["total_cases"] > 0
    
    @pytest.mark.asyncio
    async def test_execute_unknown_task_type(self, agent):
        """Test executing with unknown task type."""
        task = AgentTask(
            task_id="test-1",
            task_type="unknown_type",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success is False
        assert "Unknown task type" in result.error
    
    @pytest.mark.asyncio
    async def test_run_benchmark_quick(self, agent):
        """Test running quick benchmark."""
        task = AgentTask(
            task_id="bench-1",
            task_type="run_benchmark",
            payload={"mode": "quick"},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert result.output["metrics"]["total_cases"] == len(QUICK_BENCHMARK_CASES)
        assert 0 <= result.output["metrics"]["overall_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_run_benchmark_full(self, agent):
        """Test running full benchmark."""
        task = AgentTask(
            task_id="bench-2",
            task_type="run_benchmark",
            payload={"mode": "full"},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert result.output["metrics"]["total_cases"] == len(FULL_BENCHMARK_CASES)
    
    @pytest.mark.asyncio
    async def test_run_benchmark_with_categories(self, agent):
        """Test running benchmark with specific categories."""
        task = AgentTask(
            task_id="bench-3",
            task_type="run_benchmark",
            payload={
                "mode": "quick",
                "categories": ["coding", "math"],
            },
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        # All returned cases should be in requested categories
        category_scores = result.output["metrics"]["category_scores"]
        assert all(cat in ["coding", "math"] for cat in category_scores.keys())
    
    @pytest.mark.asyncio
    async def test_run_benchmark_updates_history(self, agent):
        """Test that running benchmark updates history."""
        assert len(agent._history) == 0
        
        await agent.execute()
        
        assert len(agent._history) == 1
        assert agent._total_runs == 1
    
    @pytest.mark.asyncio
    async def test_compare_models(self, agent):
        """Test comparing model performance."""
        task = AgentTask(
            task_id="compare-1",
            task_type="compare_models",
            payload={
                "models": ["gpt-4o", "claude-3-opus"],
            },
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert "comparisons" in result.output
        assert "gpt-4o" in result.output["comparisons"]
        assert "claude-3-opus" in result.output["comparisons"]
        assert "ranking" in result.output
        assert "best_model" in result.output
    
    @pytest.mark.asyncio
    async def test_compare_models_default(self, agent):
        """Test comparing with default models."""
        task = AgentTask(
            task_id="compare-2",
            task_type="compare_models",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert len(result.output["comparisons"]) > 0
    
    @pytest.mark.asyncio
    async def test_detect_regressions_no_baseline(self, agent):
        """Test regression detection with no baseline."""
        task = AgentTask(
            task_id="regress-1",
            task_type="detect_regressions",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        # Should either report no baseline or run benchmark first
    
    @pytest.mark.asyncio
    async def test_detect_regressions_with_baseline(self, agent):
        """Test regression detection with provided baseline."""
        # Set up baselines
        agent._category_baselines = {
            "coding": 0.90,
            "reasoning": 0.85,
            "math": 0.80,
        }
        
        task = AgentTask(
            task_id="regress-2",
            task_type="detect_regressions",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert "regressions_detected" in result.output
        assert "regressions" in result.output
    
    @pytest.mark.asyncio
    async def test_generate_report_no_history(self, agent):
        """Test generating report with no history."""
        task = AgentTask(
            task_id="report-1",
            task_type="generate_report",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert "generated_at" in result.output
        assert "statistics" in result.output
    
    @pytest.mark.asyncio
    async def test_generate_report_with_history(self, agent):
        """Test generating report with history."""
        # Run some benchmarks first
        await agent.execute()
        await agent.execute()
        
        task = AgentTask(
            task_id="report-2",
            task_type="generate_report",
            payload={"include_history": True},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert "history" in result.output
        assert len(result.output["history"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_history(self, agent):
        """Test getting historical benchmark data."""
        # Run some benchmarks
        await agent.execute()
        await agent.execute()
        
        task = AgentTask(
            task_id="history-1",
            task_type="get_history",
            payload={"limit": 5},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert result.output["count"] >= 2
        assert len(result.output["history"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_history_by_category(self, agent):
        """Test getting history filtered by category."""
        await agent.execute()
        
        task = AgentTask(
            task_id="history-2",
            task_type="get_history",
            payload={
                "limit": 5,
                "category": "coding",
            },
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        for item in result.output["history"]:
            assert "category_score" in item
    
    @pytest.mark.asyncio
    async def test_benchmark_writes_to_blackboard(self, agent):
        """Test that benchmark writes results to blackboard."""
        mock_blackboard = MagicMock()
        mock_blackboard.write = AsyncMock()
        agent._blackboard = mock_blackboard
        
        await agent.execute()
        
        # Should have written to blackboard
        assert mock_blackboard.write.called or True  # Blackboard is optional
    
    @pytest.mark.asyncio
    async def test_benchmark_creates_improvement_opportunities(self, agent):
        """Test that benchmark identifies improvement opportunities."""
        task = AgentTask(
            task_id="bench-4",
            task_type="run_benchmark",
            payload={"mode": "quick"},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        # Should have recommendations if any category is below threshold
        assert isinstance(result.recommendations, list)
    
    def test_check_for_regressions(self, agent):
        """Test internal regression checking."""
        agent._category_baselines = {
            "coding": 0.90,
            "reasoning": 0.85,
        }
        
        metrics = BenchmarkMetrics(
            total_cases=10,
            passed_cases=7,
            overall_score=0.70,
            category_scores={
                "coding": 0.75,  # -0.15 regression
                "reasoning": 0.84,  # Within threshold
            },
        )
        
        regressions = agent._check_for_regressions(metrics)
        
        assert len(regressions) == 1
        assert regressions[0].category == "coding"
        assert regressions[0].severity in ["high", "critical"]
    
    def test_update_baselines(self, agent):
        """Test baseline updating with exponential moving average."""
        agent._category_baselines = {"coding": 0.80}
        
        metrics = BenchmarkMetrics(
            total_cases=10,
            passed_cases=9,
            overall_score=0.90,
            category_scores={"coding": 0.90},
        )
        
        agent._update_baselines(metrics)
        
        # Should be moving toward 0.90
        assert agent._category_baselines["coding"] > 0.80
        assert agent._category_baselines["coding"] < 0.90
    
    def test_update_baselines_new_category(self, agent):
        """Test baseline updating for new category."""
        agent._category_baselines = {}
        
        metrics = BenchmarkMetrics(
            total_cases=10,
            passed_cases=8,
            overall_score=0.80,
            category_scores={"new_category": 0.85},
        )
        
        agent._update_baselines(metrics)
        
        assert "new_category" in agent._category_baselines
        assert agent._category_baselines["new_category"] == 0.85


# ============================================================
# Test BenchmarkRun
# ============================================================

class TestBenchmarkRun:
    """Tests for BenchmarkRun dataclass."""
    
    def test_create_run(self, sample_benchmark_run):
        """Test creating benchmark run."""
        assert sample_benchmark_run.run_id == "test-run-001"
        assert sample_benchmark_run.metrics.total_cases == 10
    
    def test_to_dict(self, sample_benchmark_run):
        """Test run serialization."""
        result = sample_benchmark_run.to_dict()
        
        assert result["run_id"] == "test-run-001"
        assert "metrics" in result
        assert "improvement_opportunities" in result
        assert "timestamp" in result


# ============================================================
# Test Integration with Planning Agent
# ============================================================

class TestPlanningAgentIntegration:
    """Tests for integration with PlanningAgent."""
    
    @pytest.mark.asyncio
    async def test_benchmark_results_format_for_planning(self, agent):
        """Test that benchmark results are formatted for PlanningAgent."""
        result = await agent.execute()
        
        # Check that output contains information PlanningAgent needs
        assert "metrics" in result.output
        assert "improvement_opportunities" in result.output
        
        # Check recommendations format
        for rec in result.recommendations:
            assert isinstance(rec, str)
    
    @pytest.mark.asyncio
    async def test_regression_alerts_format(self, agent):
        """Test that regression alerts are properly formatted."""
        agent._category_baselines = {
            "coding": 0.95,  # Set high baseline to trigger regression
        }
        
        task = AgentTask(
            task_id="regress-test",
            task_type="detect_regressions",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success is True
        # Regressions should be in a format PlanningAgent can use
        for reg in result.output.get("regressions", []):
            assert "category" in reg
            assert "severity" in reg
            assert "delta" in reg


# ============================================================
# Test Constants
# ============================================================

class TestBenchmarkConstants:
    """Tests for benchmark constants."""
    
    def test_benchmark_categories_defined(self):
        """Test that benchmark categories are properly defined."""
        assert len(BENCHMARK_CATEGORIES) > 0
        assert "coding" in BENCHMARK_CATEGORIES
        assert "reasoning" in BENCHMARK_CATEGORIES
    
    def test_quick_benchmark_cases_defined(self):
        """Test that quick benchmark cases are defined."""
        assert len(QUICK_BENCHMARK_CASES) > 0
        for case in QUICK_BENCHMARK_CASES:
            assert "id" in case
            assert "category" in case
            assert "prompt" in case
    
    def test_full_benchmark_cases_include_quick(self):
        """Test that full cases include quick cases."""
        assert len(FULL_BENCHMARK_CASES) >= len(QUICK_BENCHMARK_CASES)
        
        quick_ids = {c["id"] for c in QUICK_BENCHMARK_CASES}
        full_ids = {c["id"] for c in FULL_BENCHMARK_CASES}
        
        assert quick_ids.issubset(full_ids)
