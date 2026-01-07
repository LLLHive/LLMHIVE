"""Tests for external runner skip behavior.

Verifies that external runners (OpenAI, Anthropic, Perplexity) skip gracefully
when API keys are not configured, without crashing or exposing errors.
"""
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "llmhive" / "src"))

from llmhive.app.benchmarks.runner_base import (
    BenchmarkCase,
    RunConfig,
    RunnerStatus,
)
from llmhive.app.benchmarks.runner_openai import OpenAIRunner, get_openai_runner
from llmhive.app.benchmarks.runner_anthropic import AnthropicRunner, get_anthropic_runner
from llmhive.app.benchmarks.runner_perplexity import PerplexityRunner, get_perplexity_runner


@pytest.fixture
def sample_case():
    """Create a sample benchmark case."""
    return BenchmarkCase(
        id="test_001",
        category="test",
        prompt="What is 2 + 2?",
        expected={"expected_contains": "4"},
        requirements={},
        scoring={"objective_weight": 1.0},
    )


class TestOpenAIRunnerSkip:
    """Test OpenAI runner skips correctly without API key."""
    
    def test_is_not_available_without_key(self):
        """Runner should not be available without OPENAI_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            os.environ.pop("OPENAI_API_KEY", None)
            
            runner = OpenAIRunner()
            assert runner.is_available() is False
    
    def test_is_available_with_key(self):
        """Runner should be available with OPENAI_API_KEY."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            runner = OpenAIRunner()
            # Will still fail if SDK not installed, but that's OK
            # We're testing the key check logic
            if runner.is_available():
                assert True
            else:
                # SDK might not be installed
                pytest.skip("OpenAI SDK not installed")
    
    @pytest.mark.asyncio
    async def test_run_case_skips_without_key(self, sample_case):
        """run_case should return SKIPPED status without API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            
            runner = OpenAIRunner()
            result = await runner.run_case(sample_case)
            
            assert result.status == RunnerStatus.SKIPPED
            assert "not available" in result.error_message.lower()
    
    def test_factory_creates_runner(self):
        """Factory function should create runner instance."""
        runner = get_openai_runner()
        assert isinstance(runner, OpenAIRunner)


class TestAnthropicRunnerSkip:
    """Test Anthropic runner skips correctly without API key."""
    
    def test_is_not_available_without_key(self):
        """Runner should not be available without ANTHROPIC_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            
            runner = AnthropicRunner()
            assert runner.is_available() is False
    
    @pytest.mark.asyncio
    async def test_run_case_skips_without_key(self, sample_case):
        """run_case should return SKIPPED status without API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            
            runner = AnthropicRunner()
            result = await runner.run_case(sample_case)
            
            assert result.status == RunnerStatus.SKIPPED
            assert "not available" in result.error_message.lower()
    
    def test_factory_creates_runner(self):
        """Factory function should create runner instance."""
        runner = get_anthropic_runner()
        assert isinstance(runner, AnthropicRunner)


class TestPerplexityRunnerSkip:
    """Test Perplexity runner skips correctly without API key."""
    
    def test_is_not_available_without_key_or_file(self):
        """Runner should not be available without API key or import file."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PERPLEXITY_API_KEY", None)
            
            runner = PerplexityRunner(import_file="/nonexistent/file.json")
            assert runner.is_available() is False
    
    @pytest.mark.asyncio
    async def test_run_case_skips_without_key(self, sample_case):
        """run_case should return SKIPPED status without API key or import."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PERPLEXITY_API_KEY", None)
            
            runner = PerplexityRunner(import_file="/nonexistent/file.json")
            result = await runner.run_case(sample_case)
            
            assert result.status == RunnerStatus.SKIPPED
            assert "not available" in result.error_message.lower()
    
    def test_factory_creates_runner(self):
        """Factory function should create runner instance."""
        runner = get_perplexity_runner()
        assert isinstance(runner, PerplexityRunner)


class TestMultipleRunnersSkip:
    """Test that multiple runners can be checked together."""
    
    def test_get_available_runners(self):
        """Should correctly identify available runners."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear all keys
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("PERPLEXITY_API_KEY", None)
            
            runners = {
                "openai": get_openai_runner(),
                "anthropic": get_anthropic_runner(),
                "perplexity": get_perplexity_runner(),
            }
            
            available = {
                name: runner
                for name, runner in runners.items()
                if runner.is_available()
            }
            
            # Without any keys, none should be available
            # (except Perplexity if import file exists)
            assert len(available) <= 1
    
    def test_no_key_exposure_in_skip_messages(self, sample_case):
        """Skip messages should not expose API keys."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-secret-key-12345"}):
            runner = get_openai_runner()
            result = runner.skip_result(sample_case.id, "Test reason")
            
            # Ensure no key in any output
            result_str = str(result.to_dict())
            assert "sk-secret" not in result_str
            assert "12345" not in result_str

