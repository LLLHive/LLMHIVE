"""Tests for LLMHive runner contract.

Verifies that the LLMHive runner:
- Produces correct RunResult structure
- Includes expected metadata fields
- Handles errors gracefully
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "llmhive" / "src"))

from llmhive.app.benchmarks.runner_base import (
    BenchmarkCase,
    RunConfig,
    RunResult,
    RunnerStatus,
    RunMetadata,
)
from llmhive.app.benchmarks.runner_llmhive import LLMHiveRunner


class TestLLMHiveRunnerContract:
    """Test LLMHive runner produces correct output structure."""
    
    @pytest.fixture
    def runner(self):
        """Create a runner instance."""
        return LLMHiveRunner(mode="local")
    
    @pytest.fixture
    def sample_case(self):
        """Create a sample benchmark case."""
        return BenchmarkCase(
            id="test_001",
            category="test",
            prompt="What is 2 + 2?",
            expected={"expected_contains": "4"},
            requirements={},
            scoring={"objective_weight": 1.0, "rubric_weight": 0.0},
        )
    
    def test_runner_has_correct_system_name(self, runner):
        """Runner should report correct system name."""
        assert runner.system_name == "LLMHive"
    
    def test_runner_has_model_id(self, runner):
        """Runner should have a model ID."""
        assert runner.model_id is not None
        assert "llmhive" in runner.model_id.lower()
    
    def test_runner_reports_capabilities(self, runner):
        """Runner should report its capabilities."""
        capabilities = runner._get_capabilities()
        
        assert "tools" in capabilities
        assert "rag" in capabilities
        assert "mcp2" in capabilities
        assert capabilities["tools"] is True  # LLMHive has tools
    
    def test_runner_produces_skip_result(self, runner):
        """Skip result should have correct structure."""
        result = runner.skip_result("test_001", "Test skip reason")
        
        assert isinstance(result, RunResult)
        assert result.status == RunnerStatus.SKIPPED
        assert result.prompt_id == "test_001"
        assert result.answer_text == ""
        assert "Test skip reason" in result.error_message
    
    def test_runner_produces_error_result(self, runner):
        """Error result should have correct structure."""
        result = runner.error_result("test_001", "Test error", latency_ms=100)
        
        assert isinstance(result, RunResult)
        assert result.status == RunnerStatus.ERROR
        assert result.prompt_id == "test_001"
        assert result.latency_ms == 100
        assert "Test error" in result.error_message
    
    def test_runner_produces_timeout_result(self, runner):
        """Timeout result should have correct structure."""
        result = runner.timeout_result("test_001", timeout_seconds=30)
        
        assert isinstance(result, RunResult)
        assert result.status == RunnerStatus.TIMEOUT
        assert result.latency_ms == 30000
        assert "30" in result.error_message
    
    def test_result_to_dict_includes_required_fields(self, runner):
        """Result dict should include all required fields."""
        result = runner.skip_result("test_001", "Reason")
        result_dict = result.to_dict()
        
        required_fields = [
            "system_name",
            "model_id",
            "prompt_id",
            "status",
            "answer_text",
            "latency_ms",
            "timestamp",
            "metadata",
        ]
        
        for field in required_fields:
            assert field in result_dict, f"Missing field: {field}"
    
    def test_metadata_to_dict_includes_required_fields(self):
        """Metadata dict should include required fields."""
        metadata = RunMetadata(
            models_used=["gpt-4"],
            strategy_used="direct",
            tokens_in=100,
            tokens_out=50,
        )
        
        meta_dict = metadata.to_dict()
        
        assert "models_used" in meta_dict
        assert "strategy_used" in meta_dict
        assert "tokens_in" in meta_dict
        assert "tokens_out" in meta_dict
    
    @pytest.mark.asyncio
    async def test_run_case_returns_result_structure(self, runner, sample_case):
        """run_case should return proper RunResult structure."""
        # Mock the orchestrator to avoid actual API calls
        mock_response = MagicMock()
        mock_response.message = "The answer is 4."
        mock_response.models_used = ["mock-model"]
        mock_response.tokens_used = 50
        mock_response.extra = {"trace_id": "test-trace"}
        
        with patch.object(runner, '_run_local', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = RunResult(
                system_name="LLMHive",
                model_id="llmhive-test",
                prompt_id=sample_case.id,
                status=RunnerStatus.SUCCESS,
                answer_text="The answer is 4.",
                metadata=RunMetadata(
                    models_used=["mock-model"],
                    tokens_out=50,
                    trace_id="test-trace",
                ),
            )
            
            result = await runner.run_case(sample_case)
        
        # Verify result structure
        assert isinstance(result, RunResult)
        assert result.system_name == "LLMHive"
        assert result.prompt_id == sample_case.id
        assert result.answer_text != ""
        assert isinstance(result.metadata, RunMetadata)


class TestLLMHiveRunnerMetadataExtraction:
    """Test metadata extraction from orchestrator responses."""
    
    @pytest.fixture
    def runner(self):
        return LLMHiveRunner(mode="local")
    
    def test_extract_strategy_hrm(self, runner):
        """Should detect HRM strategy."""
        mock_response = MagicMock()
        mock_response.models_used = ["gpt-4"]
        mock_response.tokens_used = 100
        mock_response.extra = {"hrm_used": True}
        
        metadata = runner._extract_metadata(mock_response)
        
        assert metadata.strategy_used == "hrm"
    
    def test_extract_strategy_consensus(self, runner):
        """Should detect consensus strategy."""
        mock_response = MagicMock()
        mock_response.models_used = ["gpt-4", "claude-3"]
        mock_response.tokens_used = 200
        mock_response.extra = {"consensus_used": True}
        
        metadata = runner._extract_metadata(mock_response)
        
        assert metadata.strategy_used == "consensus"
    
    def test_extract_tool_traces(self, runner):
        """Should extract tool traces."""
        mock_response = MagicMock()
        mock_response.models_used = []
        mock_response.tokens_used = 50
        mock_response.extra = {
            "tool_traces": [
                {
                    "tool_name": "calculator",
                    "triggered": True,
                    "success": True,
                    "execution_time_ms": 50,
                }
            ]
        }
        
        metadata = runner._extract_metadata(mock_response)
        
        assert len(metadata.tool_traces) == 1
        assert metadata.tool_traces[0].tool_name == "calculator"
        assert metadata.tool_traces[0].triggered is True

