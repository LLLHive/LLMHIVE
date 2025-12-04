"""Unit tests for hierarchical planning module."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llmhive.app.orchestration.hierarchical_planning import (
    HierarchicalPlanner,
    ExecutionPlan,
    PlanStep,
    PlanResult,
    PlanRole,
    should_use_hrm,
)

# Note: PlanRole values are PLANNER, RESEARCHER, ANALYST, CODER, EXPLAINER, VERIFIER, SYNTHESIZER


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    
    async def mock_generate(prompt: str, model: str = "test-model", **kwargs):
        result = MagicMock()
        # Return a structured plan-like response
        result.content = '''
        {
            "complexity": "moderate",
            "steps": [
                {
                    "step_id": "step_1",
                    "role": "researcher",
                    "description": "Research the topic",
                    "goal": "Gather relevant information",
                    "inputs": ["query"],
                    "expected_output": "Research summary",
                    "depends_on": [],
                    "parallelizable": false
                },
                {
                    "step_id": "step_2",
                    "role": "analyst",
                    "description": "Analyze findings",
                    "goal": "Draw conclusions from research",
                    "inputs": ["research_summary"],
                    "expected_output": "Analysis",
                    "depends_on": ["step_1"],
                    "parallelizable": false
                }
            ],
            "synthesis_approach": "Combine research and analysis into final answer"
        }
        '''
        result.tokens_used = 200
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
def sample_simple_plan():
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
def sample_complex_plan():
    """Create a complex multi-step plan."""
    steps = [
        PlanStep(
            step_id="step_1",
            description="Research economic impacts",
            role=PlanRole.RESEARCHER,
            goal="Gather economic data",
            inputs=["query"],
            expected_output="Economic research",
            depends_on=[],
            parallelizable=True,
        ),
        PlanStep(
            step_id="step_2",
            description="Research environmental impacts",
            role=PlanRole.RESEARCHER,
            goal="Gather environmental data",
            inputs=["query"],
            expected_output="Environmental research",
            depends_on=[],
            parallelizable=True,
        ),
        PlanStep(
            step_id="step_3",
            description="Analyze findings",
            role=PlanRole.ANALYST,
            goal="Synthesize research",
            inputs=["economic_research", "environmental_research"],
            expected_output="Comprehensive analysis",
            depends_on=["step_1", "step_2"],
            parallelizable=False,
        ),
    ]
    
    return ExecutionPlan(
        query="Compare economic and environmental impacts of renewable energy",
        steps=steps,
        total_steps=3,
        parallelizable_groups=[["step_1", "step_2"]],
        estimated_complexity="complex",
        planning_notes=["Parallel research, sequential analysis"],
    )


# ==============================================================================
# PlanStep Tests
# ==============================================================================

class TestPlanStep:
    """Tests for PlanStep data class."""
    
    def test_create_step(self):
        """Test creating a plan step."""
        step = PlanStep(
            step_id="step_1",
            description="Test step",
            role=PlanRole.RESEARCHER,
            goal="Test goal",
            inputs=["input1"],
            expected_output="output",
        )
        
        assert step.step_id == "step_1"
        assert step.description == "Test step"
        assert step.role == PlanRole.RESEARCHER
        assert step.goal == "Test goal"
    
    def test_step_defaults(self):
        """Test default values for optional fields."""
        step = PlanStep(
            step_id="step_1",
            description="Test",
            role=PlanRole.EXPLAINER,  # Use valid enum value
            goal="Goal",
            inputs=[],
            expected_output="Output",
        )
        
        assert step.depends_on == []
        assert step.parallelizable is False
        assert step.assigned_model is None
        assert step.result is None
        assert step.completed is False


# ==============================================================================
# ExecutionPlan Tests
# ==============================================================================

class TestExecutionPlan:
    """Tests for ExecutionPlan data class."""
    
    def test_create_plan(self, sample_simple_plan):
        """Test creating an execution plan."""
        assert sample_simple_plan.query == "What is 2+2?"
        assert len(sample_simple_plan.steps) == 1
        assert sample_simple_plan.total_steps == 1
        assert sample_simple_plan.estimated_complexity == "simple"
    
    def test_complex_plan_structure(self, sample_complex_plan):
        """Test complex plan structure."""
        assert len(sample_complex_plan.steps) == 3
        assert sample_complex_plan.total_steps == 3
        assert len(sample_complex_plan.parallelizable_groups) == 1
        assert sample_complex_plan.estimated_complexity == "complex"
    
    def test_plan_dependencies(self, sample_complex_plan):
        """Test that dependencies are correctly structured."""
        step3 = sample_complex_plan.steps[2]
        assert "step_1" in step3.depends_on
        assert "step_2" in step3.depends_on


# ==============================================================================
# HierarchicalPlanner Tests
# ==============================================================================

class TestHierarchicalPlanner:
    """Tests for HierarchicalPlanner class."""
    
    def test_initialization(self, mock_providers):
        """Test planner initialization."""
        planner = HierarchicalPlanner(
            providers=mock_providers,
            planning_model="gpt-4o",
        )
        
        assert planner.planning_model == "gpt-4o"
        assert len(planner.providers) == 3
    
    @pytest.mark.asyncio
    async def test_create_plan_simple_query(self, mock_providers):
        """Test creating a plan for a simple query."""
        planner = HierarchicalPlanner(providers=mock_providers)
        
        # Mock to return a simple plan
        with patch.object(planner, '_create_fallback_plan') as mock_fallback:
            mock_fallback.return_value = ExecutionPlan(
                query="What is 2+2?",
                steps=[PlanStep(
                    step_id="step_1",
                    description="Calculate",
                    role=PlanRole.EXPLAINER,  # Use valid enum value
                    goal="Compute answer",
                    inputs=["query"],
                    expected_output="4",
                )],
                total_steps=1,
                parallelizable_groups=[],
                estimated_complexity="simple",
                planning_notes=["Simple calculation"],
            )
            
            plan = await planner.create_plan("What is 2+2?")
            
            assert plan is not None
            assert plan.query == "What is 2+2?"
    
    @pytest.mark.asyncio
    async def test_create_plan_complex_query(self, mock_providers, mock_provider):
        """Test creating a plan for a complex query."""
        planner = HierarchicalPlanner(providers=mock_providers)
        
        complex_query = (
            "Research and analyze the economic and environmental impacts "
            "of renewable energy adoption and provide policy recommendations."
        )
        
        plan = await planner.create_plan(complex_query)
        
        assert plan is not None
        assert plan.query == complex_query
        # Plan should have been created (either via LLM or fallback)
        assert plan.total_steps >= 1
    
    @pytest.mark.asyncio
    async def test_create_plan_with_complexity_hint(self, mock_providers):
        """Test creating a plan with complexity hint."""
        planner = HierarchicalPlanner(providers=mock_providers)
        
        plan = await planner.create_plan(
            "Analyze this topic",
            complexity_hint="high",
        )
        
        assert plan is not None
    
    @pytest.mark.asyncio
    async def test_fallback_plan_on_error(self, mock_providers):
        """Test that fallback plan is created on LLM error."""
        # Create a provider that fails
        failing_provider = MagicMock()
        
        async def failing_generate(*args, **kwargs):
            raise Exception("LLM error")
        
        failing_provider.generate = failing_generate
        failing_providers = {"openai": failing_provider}
        
        planner = HierarchicalPlanner(providers=failing_providers)
        
        # Should fall back to simple plan
        plan = await planner.create_plan("Test query")
        
        assert plan is not None
        # Fallback plan should exist


# ==============================================================================
# Helper Function Tests
# ==============================================================================

class TestShouldUseHRM:
    """Tests for should_use_hrm helper function."""
    
    def test_simple_query_no_hrm(self):
        """Test that simple queries don't trigger HRM."""
        # should_use_hrm takes complexity, task_type, query_length
        result = should_use_hrm("simple", "general", 5)
        assert result is False
    
    def test_complex_query_triggers_hrm(self):
        """Test that complex queries trigger HRM."""
        # Complex queries with research_analysis should use HRM
        result = should_use_hrm("complex", "research_analysis", 100)
        assert result is True
    
    def test_moderate_query(self):
        """Test moderate complexity query."""
        result = should_use_hrm("moderate", "comparison", 20)
        # Comparison tasks may trigger HRM
        assert isinstance(result, bool)
    
    def test_research_task_type(self):
        """Test that research tasks trigger HRM."""
        result = should_use_hrm("moderate", "research_analysis", 30)
        assert result is True
    
    def test_planning_task_type(self):
        """Test that planning tasks trigger HRM."""
        result = should_use_hrm("moderate", "planning", 25)
        assert result is True


# ==============================================================================
# PlanResult Tests
# ==============================================================================

class TestPlanResult:
    """Tests for PlanResult data class."""
    
    def test_create_result(self):
        """Test creating a plan result."""
        result = PlanResult(
            success=True,
            final_answer="The answer is 4.",
            steps_executed=2,
            steps_successful=2,
            step_results={"step_1": "Intermediate", "step_2": "Final"},
            synthesis_notes=["Combined results"],
        )
        
        assert result.success is True
        assert result.final_answer == "The answer is 4."
        assert result.steps_executed == 2
        assert result.steps_successful == 2
        assert len(result.step_results) == 2
    
    def test_failed_result(self):
        """Test creating a failed result."""
        result = PlanResult(
            success=False,
            final_answer="Error: Could not complete plan",
            steps_executed=1,
            steps_successful=0,
            step_results={},
            synthesis_notes=["Step 1 failed"],
        )
        
        assert result.success is False
        assert result.steps_successful == 0


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestPlanningIntegration:
    """Integration tests for hierarchical planning."""
    
    @pytest.mark.asyncio
    async def test_plan_and_structure_consistency(self, mock_providers):
        """Test that plan structure is consistent."""
        planner = HierarchicalPlanner(providers=mock_providers)
        
        plan = await planner.create_plan("Analyze multiple factors")
        
        # Verify structural integrity
        assert plan.total_steps == len(plan.steps)
        
        # All steps should have required fields
        for step in plan.steps:
            assert step.step_id is not None
            assert step.description is not None
            assert step.role is not None
            assert step.goal is not None
    
    @pytest.mark.asyncio
    async def test_dependency_validation(self, mock_providers):
        """Test that dependencies reference valid steps."""
        planner = HierarchicalPlanner(providers=mock_providers)
        
        plan = await planner.create_plan(
            "First research, then analyze, finally synthesize"
        )
        
        step_ids = {step.step_id for step in plan.steps}
        
        # All dependencies should reference existing steps
        for step in plan.steps:
            for dep in step.depends_on:
                assert dep in step_ids, f"Invalid dependency: {dep}"
    
    @pytest.mark.asyncio
    async def test_multiple_plans_independent(self, mock_providers):
        """Test that multiple plan creations are independent."""
        planner = HierarchicalPlanner(providers=mock_providers)
        
        plan1 = await planner.create_plan("Query 1")
        plan2 = await planner.create_plan("Query 2")
        
        # Plans should be independent
        assert plan1.query != plan2.query
        # They should not share step references
        assert plan1.steps is not plan2.steps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
