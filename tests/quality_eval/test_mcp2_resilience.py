"""Tests for MCP2 sandbox and planner resilience.

This module tests:
1. Cold boot detection and pre-warming
2. Timeout retry logic
3. Error redaction
4. Planner step verification
5. Domain routing
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestColdBootManager:
    """Tests for cold boot detection and pre-warming."""
    
    def test_is_cold_boot_new_session(self):
        """Test new sessions are detected as cold boot."""
        from llmhive.app.mcp2.sandbox_executor import ColdBootManager, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig()
        manager = ColdBootManager(config)
        
        is_cold = manager.is_cold_boot("new_session_123")
        
        assert is_cold
    
    def test_mark_warmed(self):
        """Test session can be marked as warmed."""
        from llmhive.app.mcp2.sandbox_executor import ColdBootManager, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig()
        manager = ColdBootManager(config)
        
        manager.mark_warmed("session_123")
        
        # Should no longer be cold
        is_cold = manager.is_cold_boot("session_123")
        assert not is_cold
    
    def test_cleanup_session(self):
        """Test session cleanup removes warm state."""
        from llmhive.app.mcp2.sandbox_executor import ColdBootManager, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig()
        manager = ColdBootManager(config)
        
        manager.mark_warmed("session_123")
        manager.cleanup_session("session_123")
        
        # Should be cold again
        is_cold = manager.is_cold_boot("session_123")
        assert is_cold


class TestErrorRedactor:
    """Tests for error traceback redaction."""
    
    def test_redact_file_paths(self):
        """Test file paths are redacted."""
        from llmhive.app.mcp2.sandbox_executor import ErrorRedactor, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig()
        redactor = ErrorRedactor(config)
        
        error = "File '/tmp/sandbox_abc123/execute.py', line 42, in <module>"
        redacted = redactor.redact(error)
        
        assert "/tmp/sandbox" not in redacted
        assert "[redacted]" in redacted
    
    def test_redact_home_paths(self):
        """Test home directory paths are redacted."""
        from llmhive.app.mcp2.sandbox_executor import ErrorRedactor, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig()
        redactor = ErrorRedactor(config)
        
        error = "Error loading /home/user/secrets/config.py"
        redacted = redactor.redact(error)
        
        assert "/home/user" not in redacted
    
    def test_extract_user_friendly_error(self):
        """Test user-friendly error extraction."""
        from llmhive.app.mcp2.sandbox_executor import ErrorRedactor, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig()
        redactor = ErrorRedactor(config)
        
        error = "Traceback...\nNameError: name 'undefined_var' is not defined"
        friendly = redactor.extract_user_friendly_error(error)
        
        assert "undefined_var" in friendly
    
    def test_truncate_long_errors(self):
        """Test long errors are truncated."""
        from llmhive.app.mcp2.sandbox_executor import ErrorRedactor, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig(max_error_length=100)
        redactor = ErrorRedactor(config)
        
        error = "A" * 1000  # Long error
        redacted = redactor.redact(error)
        
        assert len(redacted) <= 120  # Allow for truncation message
        assert "truncated" in redacted


class TestInputSimplification:
    """Tests for code input simplification."""
    
    def test_reduce_range_sizes(self):
        """Test large ranges are reduced."""
        from llmhive.app.mcp2.sandbox_executor import simplify_code_input
        
        code = "for i in range(10000): print(i)"
        simplified = simplify_code_input(code)
        
        assert "10000" not in simplified
        assert "100" in simplified
    
    def test_add_while_loop_limit(self):
        """Test while loops get iteration limits."""
        from llmhive.app.mcp2.sandbox_executor import simplify_code_input
        
        code = "while True: do_something()"
        simplified = simplify_code_input(code)
        
        assert "iter" in simplified.lower() or "1000" in simplified


class TestEnhancedSandboxExecutor:
    """Tests for enhanced sandbox executor."""
    
    @pytest.mark.asyncio
    async def test_executor_stats(self):
        """Test executor tracks statistics."""
        from llmhive.app.mcp2.sandbox_executor import EnhancedSandboxExecutor, EnhancedSandboxConfig
        
        config = EnhancedSandboxConfig(enable_prewarm=False)
        executor = EnhancedSandboxExecutor(config=config, session_token="test_session")
        
        stats = executor.get_stats()
        
        assert "total_executions" in stats
        assert "timeout_count" in stats
        assert "retry_count" in stats


class TestPlannerStepVerifier:
    """Tests for planner step verification."""
    
    def test_verify_empty_result(self):
        """Test verification fails for empty results."""
        from llmhive.app.mcp2.planner import StepVerifier, PlannerConfig, PlanStep, StepResult
        
        config = PlannerConfig(enable_step_verification=True)
        verifier = StepVerifier(config)
        
        step = PlanStep(step_id="1", tool_name="search", arguments={}, description="Search test")
        result = StepResult(step_id="1", success=True, output="")  # Empty output
        
        is_valid, confidence, reason = verifier.verify(step, result, "test query")
        
        assert not is_valid
        assert confidence < 0.5
    
    def test_verify_error_in_output(self):
        """Test verification detects error indicators."""
        from llmhive.app.mcp2.planner import StepVerifier, PlannerConfig, PlanStep, StepResult
        
        config = PlannerConfig()
        verifier = StepVerifier(config)
        
        step = PlanStep(step_id="1", tool_name="search", arguments={}, description="Search")
        result = StepResult(step_id="1", success=True, output="Error: not found")
        
        is_valid, confidence, reason = verifier.verify(step, result, "test query")
        
        assert not is_valid
    
    def test_verify_good_result(self):
        """Test verification passes for good results."""
        from llmhive.app.mcp2.planner import StepVerifier, PlannerConfig, PlanStep, StepResult
        
        config = PlannerConfig(verification_confidence_threshold=0.1)
        verifier = StepVerifier(config)
        
        step = PlanStep(step_id="1", tool_name="search", arguments={}, description="Search for Python")
        result = StepResult(step_id="1", success=True, output="Python is a programming language used for web development and data science.")
        
        is_valid, confidence, reason = verifier.verify(step, result, "What is Python?")
        
        assert is_valid
        assert confidence > 0


class TestDomainRouter:
    """Tests for domain-specific routing."""
    
    def test_route_search_query(self):
        """Test search queries route to search domain."""
        from llmhive.app.mcp2.planner import DomainRouter, PlannerDomain
        
        domain = DomainRouter.route("search for latest news about AI")
        
        assert domain == PlannerDomain.SEARCH
    
    def test_route_compute_query(self):
        """Test computation queries route to compute domain."""
        from llmhive.app.mcp2.planner import DomainRouter, PlannerDomain
        
        domain = DomainRouter.route("calculate 15% of 200")
        
        assert domain == PlannerDomain.COMPUTE
    
    def test_route_code_query(self):
        """Test code queries route to code domain."""
        from llmhive.app.mcp2.planner import DomainRouter, PlannerDomain
        
        domain = DomainRouter.route("write a Python function to sort a list")
        
        assert domain == PlannerDomain.CODE
    
    def test_route_general_query(self):
        """Test general queries route to general domain."""
        from llmhive.app.mcp2.planner import DomainRouter, PlannerDomain
        
        domain = DomainRouter.route("hello how are you")
        
        assert domain == PlannerDomain.GENERAL


class TestMCP2Planner:
    """Tests for the main MCP2 planner."""
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_mock_executor(self):
        """Test plan execution with mock tool executor."""
        from llmhive.app.mcp2.planner import MCP2Planner, PlannerConfig
        
        # Mock tool executor
        async def mock_executor(tool_name, arguments):
            return {"success": True, "result": f"Result from {tool_name}"}
        
        config = PlannerConfig(
            max_tool_invocations=3,
            max_planning_time_seconds=20.0,
        )
        planner = MCP2Planner(config=config, tool_executor=mock_executor)
        
        result = await planner.execute_plan(
            query="search for Python tutorials",
            available_tools=["web_search", "calculator"],
        )
        
        assert result.steps_total > 0
    
    @pytest.mark.asyncio
    async def test_execute_plan_respects_limits(self):
        """Test plan execution respects step limits."""
        from llmhive.app.mcp2.planner import MCP2Planner, PlannerConfig
        
        async def slow_executor(tool_name, arguments):
            await asyncio.sleep(0.1)
            return {"success": True, "result": "OK"}
        
        config = PlannerConfig(max_tool_invocations=2)
        planner = MCP2Planner(config=config, tool_executor=slow_executor)
        
        result = await planner.execute_plan(
            query="complex query requiring many steps",
            available_tools=["tool1", "tool2", "tool3", "tool4"],
        )
        
        # Should not exceed limit
        assert result.steps_completed <= 2
    
    @pytest.mark.asyncio
    async def test_execute_plan_fallback_on_no_tools(self):
        """Test plan falls back when no tools available."""
        from llmhive.app.mcp2.planner import MCP2Planner, PlannerConfig
        
        config = PlannerConfig(fallback_to_llm_on_failure=True)
        planner = MCP2Planner(config=config, tool_executor=None)
        
        result = await planner.execute_plan(
            query="test query",
            available_tools=[],
        )
        
        assert result.fallback_used


# Need asyncio import for sleep
import asyncio


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

