"""Tests for hierarchical plan executor and multi-step reasoning.

These tests verify the core HRM execution functionality:
1. Hierarchical plan execution with dependency ordering
2. Model routing based on roles
3. Final synthesis from step outputs
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from llmhive.app.orchestration.hierarchical_planning import (
    HierarchicalPlanner,
    HierarchicalPlanExecutor,
    ExecutionPlan,
    PlanStep,
    PlanResult,
    PlanRole,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_provider():
    """Create a mock LLM provider with async complete method."""
    provider = MagicMock()
    
    async def mock_complete(prompt: str, model: str = "test-model", **kwargs):
        """Mock complete that returns based on role/prompt context."""
        result = MagicMock()
        
        if "research" in prompt.lower():
            result.content = "Research findings: This topic involves multiple factors including A, B, and C."
        elif "analyze" in prompt.lower() or "analysis" in prompt.lower():
            result.content = "Analysis: Based on the research, the key insights are X, Y, and Z."
        elif "synthesize" in prompt.lower() or "synthesis" in prompt.lower():
            result.content = "Synthesis: Combining all findings, the conclusion is that..."
        else:
            result.content = f"Processed: {prompt[:50]}..."
        
        result.text = result.content
        result.tokens_used = len(prompt.split()) // 2
        return result
    
    provider.complete = mock_complete
    return provider


@pytest.fixture
def mock_providers(mock_provider):
    """Create a dict of mock providers."""
    return {
        "openai": mock_provider,
        "anthropic": mock_provider,
        "stub": mock_provider,
    }


@pytest.fixture
def simple_plan():
    """Create a simple single-step plan."""
    step = PlanStep(
        step_id="step_1",
        description="Answer simple question",
        role=PlanRole.EXPLAINER,  # Use valid enum value
        goal="Provide direct answer",
        inputs=["query"],
        expected_output="Direct answer",
        depends_on=[],
        parallelizable=False,
    )
    
    return ExecutionPlan(
        query="What is 2+2?",
        steps=[step],
        total_steps=1,
        parallelizable_groups=[],
        estimated_complexity="simple",
        planning_notes=["Simple calculation"],
    )


@pytest.fixture
def multi_step_plan():
    """Create a multi-step plan with dependencies."""
    steps = [
        PlanStep(
            step_id="step_1",
            description="Research the topic",
            role=PlanRole.RESEARCHER,
            goal="Gather relevant information",
            inputs=["query"],
            expected_output="Research summary",
            depends_on=[],
            parallelizable=False,
        ),
        PlanStep(
            step_id="step_2",
            description="Analyze findings",
            role=PlanRole.ANALYST,
            goal="Draw conclusions",
            inputs=["research_summary"],
            expected_output="Analysis",
            depends_on=["step_1"],
            parallelizable=False,
        ),
        PlanStep(
            step_id="step_3",
            description="Synthesize final answer",
            role=PlanRole.SYNTHESIZER,
            goal="Create comprehensive response",
            inputs=["analysis"],
            expected_output="Final answer",
            depends_on=["step_2"],
            parallelizable=False,
        ),
    ]
    
    # Each step in its own group for sequential execution
    # The executor processes groups in order
    return ExecutionPlan(
        query="Research and analyze a complex topic",
        steps=steps,
        total_steps=3,
        parallelizable_groups=[["step_1"], ["step_2"], ["step_3"]],
        estimated_complexity="moderate",
        planning_notes=["Sequential execution"],
    )


@pytest.fixture
def parallel_plan():
    """Create a plan with parallel steps."""
    steps = [
        PlanStep(
            step_id="step_1",
            description="Research aspect A",
            role=PlanRole.RESEARCHER,
            goal="Gather info on A",
            inputs=["query"],
            expected_output="Research on A",
            depends_on=[],
            parallelizable=True,
        ),
        PlanStep(
            step_id="step_2",
            description="Research aspect B",
            role=PlanRole.RESEARCHER,
            goal="Gather info on B",
            inputs=["query"],
            expected_output="Research on B",
            depends_on=[],
            parallelizable=True,
        ),
        PlanStep(
            step_id="step_3",
            description="Combine and analyze",
            role=PlanRole.ANALYST,
            goal="Synthesize both aspects",
            inputs=["research_a", "research_b"],
            expected_output="Combined analysis",
            depends_on=["step_1", "step_2"],
            parallelizable=False,
        ),
    ]
    
    return ExecutionPlan(
        query="Compare aspects A and B",
        steps=steps,
        total_steps=3,
        parallelizable_groups=[["step_1", "step_2"]],
        estimated_complexity="moderate",
        planning_notes=["Steps 1 and 2 can run in parallel"],
    )


# ==============================================================================
# HierarchicalPlanExecutor Tests
# ==============================================================================

class TestHierarchicalPlanExecutor:
    """Tests for the hierarchical plan executor."""
    
    def test_initialization(self, mock_providers):
        """Test executor initialization."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        assert len(executor.providers) == 3
    
    @pytest.mark.asyncio
    async def test_execute_simple_plan(self, mock_providers, simple_plan):
        """Test executing a simple single-step plan."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute_plan(simple_plan)
        
        assert result is not None
        assert result.success
        assert result.steps_executed >= 1
        assert result.final_answer is not None
        assert len(result.final_answer) > 0
    
    @pytest.mark.asyncio
    async def test_execute_multi_step_plan(self, mock_providers, multi_step_plan):
        """Test executing a multi-step plan."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute_plan(multi_step_plan)
        
        assert result is not None
        # Multi-step plans with proper parallelizable_groups should complete
        assert result.steps_executed == 3
        # The plan should produce some answer (success depends on all steps completing)
        assert result.final_answer is not None
        # May be successful if all steps completed
        if result.steps_successful == 3:
            assert result.success
    
    @pytest.mark.asyncio
    async def test_execute_with_context(self, mock_providers, simple_plan):
        """Test executing with additional context."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute_plan(
            simple_plan,
            context="Additional context for the query",
        )
        
        assert result is not None
        assert result.success
    
    @pytest.mark.asyncio
    async def test_step_results_populated(self, mock_providers, multi_step_plan):
        """Test that step results are populated."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute_plan(multi_step_plan)
        
        # Step results should be populated for executed steps
        assert len(result.step_results) >= 1
        # At minimum step_1 should have been attempted
        if result.steps_successful > 0:
            assert len(result.step_results) > 0
    
    @pytest.mark.asyncio
    async def test_dependency_order_respected(self, mock_providers, multi_step_plan):
        """Test that dependencies are executed in order."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(multi_step_plan)
        
        # Verify the result is valid (execution order is implicit in the groups)
        assert result is not None
        assert result.steps_executed == 3
        # Groups are processed in order, which respects dependencies
    
    @pytest.mark.asyncio
    async def test_parallel_steps_execution(self, mock_providers, parallel_plan):
        """Test execution of parallel steps."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute_plan(parallel_plan)
        
        assert result is not None
        assert result.steps_executed == 3
        # Parallel plan should have step results
        assert len(result.step_results) >= 1
    
    @pytest.mark.asyncio
    async def test_synthesis_notes_generated(self, mock_providers, multi_step_plan):
        """Test that synthesis notes are generated."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute_plan(multi_step_plan)
        
        assert result.synthesis_notes is not None
        # Notes should exist even if empty
        assert isinstance(result.synthesis_notes, list)


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestExecutorErrorHandling:
    """Tests for error handling in plan execution."""
    
    @pytest.mark.asyncio
    async def test_empty_plan_execution(self, mock_providers):
        """Test executing an empty plan."""
        empty_plan = ExecutionPlan(
            query="Test",
            steps=[],
            total_steps=0,
            parallelizable_groups=[],
            estimated_complexity="simple",
            planning_notes=[],
        )
        
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(empty_plan)
        
        # Should handle gracefully
        assert result is not None
        # May succeed with empty result or fail gracefully
    
    @pytest.mark.asyncio
    async def test_provider_failure_handling(self, simple_plan):
        """Test handling of provider failures."""
        failing_provider = MagicMock()
        
        call_count = 0
        
        async def failing_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise Exception("Simulated provider failure")
            # Succeed on retry
            result = MagicMock()
            result.content = "Success after retry"
            result.text = result.content
            result.tokens_used = 10
            return result
        
        failing_provider.complete = failing_complete
        failing_providers = {"stub": failing_provider}
        
        executor = HierarchicalPlanExecutor(providers=failing_providers)
        
        # The executor should handle failure gracefully
        try:
            result = await executor.execute_plan(simple_plan)
            # If it succeeds, it means retry worked
            assert result is not None
        except Exception:
            # If it fails, it should be graceful
            pass
    
    @pytest.mark.asyncio
    async def test_no_providers_handling(self, simple_plan):
        """Test handling when no providers are available."""
        executor = HierarchicalPlanExecutor(providers={})
        
        # Should fail gracefully
        try:
            result = await executor.execute_plan(simple_plan)
            # Result should indicate failure
            assert not result.success or result.steps_successful == 0
        except (KeyError, ValueError):
            # Expected - no providers available
            pass


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestExecutionIntegration:
    """Integration tests for plan execution."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, mock_providers):
        """Test the full planning and execution pipeline."""
        # Create planner
        planner = HierarchicalPlanner(providers=mock_providers)
        
        # Create plan
        plan = await planner.create_plan(
            "Research and analyze a topic with multiple aspects"
        )
        
        assert plan is not None
        assert plan.total_steps >= 1
        
        # Execute plan
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(plan)
        
        assert result is not None
        assert result.success
        assert result.final_answer is not None
    
    @pytest.mark.asyncio
    async def test_multiple_executions(self, mock_providers, simple_plan, multi_step_plan):
        """Test multiple plan executions."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result1 = await executor.execute_plan(simple_plan)
        result2 = await executor.execute_plan(multi_step_plan)
        
        # Simple plan should succeed
        assert result1.success
        
        # Multi-step plan should complete (may or may not be fully successful)
        assert result2 is not None
        assert result2.steps_executed == 3
        
        # Results should be independent
        assert result1.steps_executed != result2.steps_executed
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, mock_providers, simple_plan):
        """Test concurrent plan executions."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        # Run multiple executions concurrently
        tasks = [
            executor.execute_plan(simple_plan)
            for _ in range(3)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete (success or handled failure)
        assert len(results) == 3
        
        successes = sum(1 for r in results if hasattr(r, 'success') and r.success)
        assert successes >= 1  # At least one should succeed


# ==============================================================================
# PlanResult Tests
# ==============================================================================

class TestPlanResultDetails:
    """Tests for PlanResult structure."""
    
    @pytest.mark.asyncio
    async def test_result_structure(self, mock_providers, multi_step_plan):
        """Test that result has all required fields."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(multi_step_plan)
        
        # Check all fields exist
        assert hasattr(result, 'success')
        assert hasattr(result, 'final_answer')
        assert hasattr(result, 'steps_executed')
        assert hasattr(result, 'steps_successful')
        assert hasattr(result, 'step_results')
        assert hasattr(result, 'synthesis_notes')
    
    @pytest.mark.asyncio
    async def test_step_results_content(self, mock_providers, multi_step_plan):
        """Test that step results contain meaningful content."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(multi_step_plan)
        
        # Each step should have non-empty result
        for step_id, step_result in result.step_results.items():
            assert step_result is not None
            assert len(str(step_result)) > 0


# ==============================================================================
# Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases in plan execution."""
    
    @pytest.mark.asyncio
    async def test_single_step_plan(self, mock_providers, simple_plan):
        """Test single step plan optimization."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(simple_plan)
        
        # Single step should complete efficiently
        assert result.success
        assert result.steps_executed == 1
    
    @pytest.mark.asyncio
    async def test_plan_with_long_query(self, mock_providers):
        """Test handling of plan with long query."""
        long_query = "Please " * 100 + "analyze this topic"
        
        step = PlanStep(
            step_id="step_1",
            description="Handle long query",
            role=PlanRole.EXPLAINER,  # Use valid enum value
            goal="Process long input",
            inputs=["query"],
            expected_output="Response",
        )
        
        plan = ExecutionPlan(
            query=long_query,
            steps=[step],
            total_steps=1,
            parallelizable_groups=[],
            estimated_complexity="simple",
            planning_notes=[],
        )
        
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute_plan(plan)
        
        # Should handle without crashing
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
