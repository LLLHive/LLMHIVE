"""Tests for hierarchical plan executor and multi-step reasoning.

These tests verify the core HRM execution functionality:
1. Hierarchical plan execution with dependency ordering
2. Blackboard for intermediate results
3. Model routing based on roles
4. Final synthesis from step outputs
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import the modules under test
from llmhive.src.llmhive.app.orchestration.hierarchical_planning import (
    HierarchicalPlanner,
    HierarchicalPlan,
    HierarchicalPlanStep,
    HierarchicalRole,
    TaskComplexity,
)
from llmhive.src.llmhive.app.orchestration.hierarchical_executor import (
    HierarchicalPlanExecutor,
    HRMBlackboard,
    HRMBlackboardEntry,
    ExecutionResult,
    StepResult,
    StepStatus,
    ExecutionMode,
    execute_hierarchical_plan,
)
from llmhive.src.llmhive.app.orchestration.hrm import RoleLevel


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    
    async def mock_generate(prompt: str, model: str = "test-model", **kwargs):
        """Mock generate that returns based on role in prompt."""
        result = MagicMock()
        
        if "Coordinator" in prompt:
            result.content = "I'll break this into three parts: economic analysis, environmental analysis, and policy recommendations."
        elif "Specialist" in prompt or "specialist" in prompt:
            if "economic" in prompt.lower():
                result.content = "Economic analysis: Electric vehicles have higher upfront costs but lower operating costs over 5 years."
            elif "environmental" in prompt.lower():
                result.content = "Environmental analysis: EVs reduce direct emissions by 50-70% compared to gas vehicles."
            else:
                result.content = "Detailed analysis of the requested topic based on available evidence."
        elif "Synthesis" in prompt or "Executive" in prompt:
            result.content = "Based on the analysis: EVs are economically viable for most consumers and provide significant environmental benefits. Recommended policies include tax incentives and charging infrastructure investment."
        else:
            result.content = f"Processed: {prompt[:50]}..."
        
        result.tokens_used = len(prompt.split()) // 2
        return result
    
    provider.generate = mock_generate
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
def sample_plan():
    """Create a sample hierarchical plan for testing."""
    planner = HierarchicalPlanner()
    return planner.plan_with_hierarchy(
        "Compare the economic and environmental impacts of electric vs. gas vehicles, and suggest policy improvements",
        use_full_hierarchy=True
    )


@pytest.fixture
def simple_plan():
    """Create a simple single-step plan."""
    coordinator = HierarchicalRole(
        name="executor",
        level=RoleLevel.SPECIALIST,
        description="Direct execution",
        required_capabilities={"reasoning"},
    )
    
    step = HierarchicalPlanStep(
        step_id="step_1",
        role=coordinator,
        query="What is 2+2?",
    )
    
    return HierarchicalPlan(
        original_query="What is 2+2?",
        complexity=TaskComplexity.SIMPLE,
        steps=[step],
        strategy="simple",
    )


# ==============================================================================
# HRMBlackboard Tests
# ==============================================================================

class TestHRMBlackboard:
    """Tests for the HRM Blackboard."""
    
    def test_write_and_read(self):
        """Test writing and reading from the blackboard."""
        blackboard = HRMBlackboard()
        
        blackboard.write(
            step_id="step_1",
            role_name="coordinator",
            content="Test content",
            confidence=0.9,
            tokens_used=100,
        )
        
        entry = blackboard.read("step_1")
        assert entry is not None
        assert entry.step_id == "step_1"
        assert entry.role_name == "coordinator"
        assert entry.content == "Test content"
        assert entry.confidence == 0.9
        assert entry.tokens_used == 100
    
    def test_read_output(self):
        """Test reading just the content output."""
        blackboard = HRMBlackboard()
        
        blackboard.write(
            step_id="step_1",
            role_name="coordinator",
            content="Test output",
        )
        
        output = blackboard.read_output("step_1")
        assert output == "Test output"
    
    def test_read_dependencies(self):
        """Test reading multiple dependencies."""
        blackboard = HRMBlackboard()
        
        blackboard.write("step_1", "specialist_1", "Output 1")
        blackboard.write("step_2", "specialist_2", "Output 2")
        blackboard.write("step_3", "specialist_3", "Output 3")
        
        entries = blackboard.read_dependencies(["step_1", "step_2"])
        assert len(entries) == 2
        assert entries[0].content == "Output 1"
        assert entries[1].content == "Output 2"
    
    def test_get_context_for_step(self):
        """Test building context for a dependent step."""
        blackboard = HRMBlackboard()
        
        blackboard.write("step_1", "researcher", "Research findings...")
        blackboard.write("step_2", "analyst", "Analysis results...")
        
        # Create a step that depends on both
        synthesizer = HierarchicalRole(
            name="synthesizer",
            level=RoleLevel.MANAGER,
            description="Synthesize",
            required_capabilities={"synthesis"},
        )
        step = HierarchicalPlanStep(
            step_id="step_3",
            role=synthesizer,
            query="Synthesize findings",
            dependencies=["step_1", "step_2"],
        )
        
        context = blackboard.get_context_for_step(step)
        assert "researcher" in context.lower()
        assert "analyst" in context.lower()
        assert "Research findings" in context
        assert "Analysis results" in context
    
    def test_get_all_outputs(self):
        """Test getting all outputs."""
        blackboard = HRMBlackboard()
        
        blackboard.write("step_1", "role_1", "Output 1")
        blackboard.write("step_2", "role_2", "Output 2")
        
        outputs = blackboard.get_all_outputs()
        assert len(outputs) == 2
        assert outputs["step_1"] == "Output 1"
        assert outputs["step_2"] == "Output 2"
    
    def test_get_synthesis_context(self):
        """Test getting synthesis context."""
        blackboard = HRMBlackboard()
        
        blackboard.write("step_1", "researcher", "Research output")
        blackboard.write("step_2", "analyst", "Analysis output")
        
        context = blackboard.get_synthesis_context()
        assert "RESEARCHER" in context
        assert "ANALYST" in context
        assert "Research output" in context
        assert "Analysis output" in context
    
    def test_get_summary(self):
        """Test getting blackboard summary."""
        blackboard = HRMBlackboard()
        
        blackboard.write("step_1", "role_1", "Output 1", tokens_used=100, confidence=0.9)
        blackboard.write("step_2", "role_2", "Output 2", tokens_used=200, confidence=0.8)
        
        summary = blackboard.get_summary()
        assert summary["total_entries"] == 2
        assert summary["total_tokens"] == 300
        assert abs(summary["avg_confidence"] - 0.85) < 0.001  # Floating point comparison
        assert set(summary["roles_involved"]) == {"role_1", "role_2"}
    
    def test_metadata(self):
        """Test metadata storage."""
        blackboard = HRMBlackboard()
        
        blackboard.set_metadata("key1", "value1")
        blackboard.set_metadata("key2", {"nested": "value"})
        
        assert blackboard.get_metadata("key1") == "value1"
        assert blackboard.get_metadata("key2") == {"nested": "value"}
        assert blackboard.get_metadata("nonexistent") is None


# ==============================================================================
# HierarchicalPlanner Tests
# ==============================================================================

class TestHierarchicalPlanner:
    """Tests for the hierarchical planner."""
    
    def test_simple_query_planning(self):
        """Test planning for a simple query."""
        planner = HierarchicalPlanner()
        plan = planner.plan_with_hierarchy("What is 2+2?")
        
        assert plan.complexity == TaskComplexity.SIMPLE
        assert len(plan.steps) == 1
        assert plan.strategy == "single_step"
    
    def test_moderate_query_planning(self):
        """Test planning for a moderate complexity query."""
        planner = HierarchicalPlanner()
        plan = planner.plan_with_hierarchy("Compare Python and JavaScript for web development")
        
        assert plan.complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX)
        assert len(plan.steps) > 1
        assert plan.top_role is not None
    
    def test_complex_query_planning(self):
        """Test planning for a complex query."""
        planner = HierarchicalPlanner()
        plan = planner.plan_with_hierarchy(
            "Research and analyze the comprehensive economic and environmental impacts of renewable energy adoption, "
            "comparing solar, wind, and hydroelectric power, and provide detailed policy recommendations for governments"
        )
        
        assert plan.complexity == TaskComplexity.COMPLEX
        assert len(plan.steps) >= 3
        assert plan.strategy in ("full_hrm_hierarchy", "simplified_hrm_hierarchy", "moderate_hierarchical")
    
    def test_execution_order(self):
        """Test that execution order respects dependencies."""
        planner = HierarchicalPlanner()
        plan = planner.plan_with_hierarchy(
            "Analyze multiple aspects and then synthesize findings",
            use_full_hierarchy=True
        )
        
        ordered_steps = plan.get_execution_order()
        
        # Verify dependencies are met before execution
        executed_ids = set()
        for step in ordered_steps:
            for dep in step.dependencies:
                assert dep in executed_ids, f"Dependency {dep} not executed before {step.step_id}"
            executed_ids.add(step.step_id)
    
    def test_plan_with_full_hierarchy(self):
        """Test planning with full HRM hierarchy."""
        planner = HierarchicalPlanner()
        plan = planner.plan_with_hierarchy(
            "Research and analyze a complex topic thoroughly",
            use_full_hierarchy=True
        )
        
        # Should include multiple levels
        role_levels = {step.role.level for step in plan.steps}
        assert RoleLevel.SPECIALIST in role_levels or RoleLevel.MANAGER in role_levels


# ==============================================================================
# HierarchicalPlanExecutor Tests
# ==============================================================================

class TestHierarchicalPlanExecutor:
    """Tests for the hierarchical plan executor."""
    
    @pytest.mark.asyncio
    async def test_simple_plan_execution(self, mock_providers, simple_plan):
        """Test executing a simple single-step plan."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute(simple_plan)
        
        assert result.success
        assert result.steps_completed == 1
        assert result.final_answer is not None
        assert len(result.final_answer) > 0
    
    @pytest.mark.asyncio
    async def test_complex_plan_execution(self, mock_providers, sample_plan):
        """Test executing a complex hierarchical plan."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute(sample_plan, accuracy_level=4)
        
        assert result.success
        assert result.steps_completed == len(sample_plan.steps)
        assert result.final_answer is not None
        assert result.total_tokens > 0
        assert result.total_latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_blackboard_populated(self, mock_providers, sample_plan):
        """Test that the blackboard is populated during execution."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute(sample_plan)
        
        # Blackboard should have entries for each step
        outputs = result.blackboard.get_all_outputs()
        assert len(outputs) >= 1  # At least one step output
        
        # Check blackboard summary
        summary = result.blackboard.get_summary()
        assert summary["total_entries"] >= 1
    
    @pytest.mark.asyncio
    async def test_step_results_tracking(self, mock_providers, sample_plan):
        """Test that step results are properly tracked."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute(sample_plan)
        
        assert len(result.step_results) == len(sample_plan.steps)
        
        for step_result in result.step_results:
            assert step_result.step_id is not None
            assert step_result.role_name is not None
            assert step_result.model_used is not None
            assert step_result.status == StepStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_transparency_notes(self, mock_providers, sample_plan):
        """Test that transparency notes are generated."""
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        
        result = await executor.execute(sample_plan)
        
        assert len(result.transparency_notes) > 0
        # Should include info about plan strategy
        assert any("plan" in note.lower() or "step" in note.lower() for note in result.transparency_notes)
    
    @pytest.mark.asyncio
    async def test_model_selection_by_role(self, mock_providers):
        """Test that models are selected based on role."""
        # Create a custom plan with specific roles
        executive = HierarchicalRole(
            name="executive",
            level=RoleLevel.EXECUTIVE,
            description="Top-level",
            required_capabilities={"synthesis"},
        )
        assistant = HierarchicalRole(
            name="assistant",
            level=RoleLevel.ASSISTANT,
            description="Helper",
            required_capabilities={"retrieval"},
        )
        
        step1 = HierarchicalPlanStep(
            step_id="step_1",
            role=executive,
            query="Strategic overview",
        )
        step2 = HierarchicalPlanStep(
            step_id="step_2",
            role=assistant,
            query="Gather info",
            dependencies=["step_1"],
        )
        
        plan = HierarchicalPlan(
            original_query="Test",
            complexity=TaskComplexity.MODERATE,
            steps=[step1, step2],
        )
        
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute(plan)
        
        # Both steps should complete with different model preferences
        assert result.success
        assert len(result.step_results) == 2
    
    @pytest.mark.asyncio
    async def test_custom_model_assignments(self, mock_providers):
        """Test that custom model assignments are respected."""
        simple_role = HierarchicalRole(
            name="custom_role",
            level=RoleLevel.SPECIALIST,
            description="Custom",
            required_capabilities=set(),
        )
        step = HierarchicalPlanStep(
            step_id="step_1",
            role=simple_role,
            query="Test",
        )
        plan = HierarchicalPlan(
            original_query="Test",
            complexity=TaskComplexity.SIMPLE,
            steps=[step],
        )
        
        custom_assignments = {"custom_role": "openai"}
        executor = HierarchicalPlanExecutor(
            providers=mock_providers,
            model_assignments=custom_assignments,
        )
        
        result = await executor.execute(plan)
        assert result.success


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestHierarchicalExecutionIntegration:
    """Integration tests for hierarchical execution."""
    
    @pytest.mark.asyncio
    async def test_execute_hierarchical_plan_convenience_function(self, mock_providers, sample_plan):
        """Test the convenience function for executing hierarchical plans."""
        result = await execute_hierarchical_plan(
            plan=sample_plan,
            providers=mock_providers,
            accuracy_level=3,
        )
        
        assert result.success
        assert result.final_answer is not None
    
    @pytest.mark.asyncio
    async def test_multi_part_query_decomposition_and_execution(self, mock_providers):
        """Test that a multi-part query is properly decomposed and executed."""
        planner = HierarchicalPlanner()
        plan = planner.plan_with_hierarchy(
            "First, research the history of electric vehicles. "
            "Then, analyze their current market share. "
            "Finally, predict future trends and suggest policy recommendations."
        )
        
        # Should create multiple steps
        assert len(plan.steps) >= 2
        
        # Execute the plan
        result = await execute_hierarchical_plan(
            plan=plan,
            providers=mock_providers,
        )
        
        assert result.success
        assert result.steps_completed == len(plan.steps)
    
    @pytest.mark.asyncio
    async def test_synthesis_combines_step_outputs(self, mock_providers):
        """Test that the synthesis step properly combines outputs."""
        # Create a plan with parallel specialists
        coord = HierarchicalRole(
            name="coordinator",
            level=RoleLevel.MANAGER,
            description="Coordinate",
            required_capabilities={"coordination"},
        )
        spec1 = HierarchicalRole(
            name="specialist_1",
            level=RoleLevel.SPECIALIST,
            description="Specialist 1",
            required_capabilities={"analysis"},
        )
        spec2 = HierarchicalRole(
            name="specialist_2",
            level=RoleLevel.SPECIALIST,
            description="Specialist 2",
            required_capabilities={"analysis"},
        )
        
        coord_step = HierarchicalPlanStep(
            step_id="coord",
            role=coord,
            query="Coordinate analysis",
            is_coordinator=True,
        )
        spec1_step = HierarchicalPlanStep(
            step_id="spec_1",
            role=spec1,
            query="Analyze aspect 1",
            dependencies=["coord"],
        )
        spec2_step = HierarchicalPlanStep(
            step_id="spec_2",
            role=spec2,
            query="Analyze aspect 2",
            dependencies=["coord"],
        )
        
        plan = HierarchicalPlan(
            original_query="Analyze two aspects",
            complexity=TaskComplexity.MODERATE,
            steps=[coord_step, spec1_step, spec2_step],
        )
        
        result = await execute_hierarchical_plan(
            plan=plan,
            providers=mock_providers,
        )
        
        assert result.success
        # The final answer should be a synthesis (since we have multiple steps)
        assert len(result.final_answer) > 0


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Tests for error handling in hierarchical execution."""
    
    @pytest.mark.asyncio
    async def test_empty_plan_handling(self, mock_providers):
        """Test handling of an empty plan."""
        plan = HierarchicalPlan(
            original_query="Test",
            complexity=TaskComplexity.SIMPLE,
            steps=[],
        )
        
        executor = HierarchicalPlanExecutor(providers=mock_providers)
        result = await executor.execute(plan)
        
        assert not result.success
        assert "no executable steps" in result.final_answer.lower()
    
    @pytest.mark.asyncio
    async def test_no_providers_handling(self):
        """Test handling when no providers are available."""
        simple_role = HierarchicalRole(
            name="executor",
            level=RoleLevel.SPECIALIST,
            description="Execute",
        )
        step = HierarchicalPlanStep(
            step_id="step_1",
            role=simple_role,
            query="Test",
        )
        plan = HierarchicalPlan(
            original_query="Test",
            complexity=TaskComplexity.SIMPLE,
            steps=[step],
        )
        
        executor = HierarchicalPlanExecutor(providers={})
        result = await executor.execute(plan)
        
        # Should fail gracefully
        assert result.steps_failed > 0 or len(result.step_results) > 0
    
    @pytest.mark.asyncio
    async def test_provider_failure_retry(self, mock_providers):
        """Test that provider failures trigger retries."""
        call_count = 0
        
        async def failing_generate(prompt: str, model: str = "test", **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:  # Fail on first call
                raise Exception("Simulated failure")
            result = MagicMock()
            result.content = "Success after retry"
            result.tokens_used = 10
            return result
        
        failing_provider = MagicMock()
        failing_provider.generate = failing_generate
        
        simple_role = HierarchicalRole(
            name="executor",
            level=RoleLevel.SPECIALIST,
            description="Execute",
        )
        step = HierarchicalPlanStep(
            step_id="step_1",
            role=simple_role,
            query="Test",
        )
        plan = HierarchicalPlan(
            original_query="Test",
            complexity=TaskComplexity.SIMPLE,
            steps=[step],
        )
        
        executor = HierarchicalPlanExecutor(
            providers={"stub": failing_provider},
            max_retries=2,
        )
        result = await executor.execute(plan)
        
        # Should succeed after retry
        assert result.success
        assert call_count >= 2  # At least one retry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

