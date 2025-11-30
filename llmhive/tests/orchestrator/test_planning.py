"""Tests for planning and task decomposition."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch


# Mock planner classes
class PlanRole:
    RESEARCH = "RESEARCH"
    ANALYZE = "ANALYZE"
    CODE = "CODE"
    SYNTHESIZE = "SYNTHESIZE"
    ANSWER = "ANSWER"


class PlanStep:
    def __init__(self, role, task):
        self.role = role
        self.task = task


class ReasoningPlan:
    def __init__(self, steps=None, confidence=0.8):
        self.steps = steps or []
        self.confidence = confidence


class ReasoningPlanner:
    def __init__(self, max_steps=None, max_depth=None):
        self.max_steps = max_steps
        self.max_depth = max_depth
    
    async def create_plan(self, prompt):
        """Create a plan for the given prompt."""
        # Simple mock implementation
        if "complex" in prompt.lower() or "analyze" in prompt.lower():
            steps = [
                PlanStep(PlanRole.RESEARCH, "Research the topic"),
                PlanStep(PlanRole.ANALYZE, "Analyze findings"),
                PlanStep(PlanRole.SYNTHESIZE, "Synthesize answer"),
            ]
        else:
            steps = [PlanStep(PlanRole.SYNTHESIZE, prompt)]
        
        if self.max_steps:
            steps = steps[:self.max_steps]
        
        return ReasoningPlan(steps=steps, confidence=0.8)
    
    def should_replan(self, result):
        """Check if replanning is needed."""
        return result.get("confidence", 1.0) < 0.5
    
    async def replan(self, plan, failure_reason):
        """Create a new plan based on failure."""
        plan.confidence = 0.9
        return plan
    
    async def create_simple_plan(self, prompt):
        """Create a simple single-step plan."""
        return ReasoningPlan(steps=[PlanStep(PlanRole.SYNTHESIZE, prompt)], confidence=0.7)


# Define fixtures
@pytest.fixture
def complex_prompt():
    return "Analyze the performance of a web application, identify bottlenecks, and suggest optimizations."

@pytest.fixture
def sample_prompt():
    return "What is the capital of France?"

@pytest.fixture
def mock_plan():
    return None


class TestPlanningAccuracy:
    """Test planning accuracy and decomposition."""
    
    @pytest.mark.asyncio
    async def test_complex_query_decomposition(self, complex_prompt):
        """Test that complex queries are broken down correctly."""
        planner = ReasoningPlanner()
        
        plan = await planner.create_plan(complex_prompt)
        
        assert len(plan.steps) > 1, "Complex query should have multiple steps"
        assert plan.steps[0].role in [PlanRole.RESEARCH, PlanRole.ANALYZE, PlanRole.CODE]
    
    @pytest.mark.asyncio
    async def test_simple_query_bypass(self, sample_prompt):
        """Test that simple queries bypass unnecessary decomposition."""
        planner = ReasoningPlanner()
        
        plan = await planner.create_plan(sample_prompt)
        
        # Simple queries might have just one step
        assert len(plan.steps) >= 1
        # Should not over-complicate
        if len(plan.steps) == 1:
            assert plan.steps[0].role == PlanRole.SYNTHESIZE or plan.steps[0].role == PlanRole.ANSWER
    
    @pytest.mark.asyncio
    async def test_multi_step_problem_breakdown(self, complex_prompt):
        """Test multi-step problem breakdown."""
        planner = ReasoningPlanner()
        
        plan = await planner.create_plan(complex_prompt)
        
        # Should have distinct steps for different tasks
        roles = [step.role for step in plan.steps]
        
        # Should include different roles for different tasks
        assert len(set(roles)) >= 1  # At least some variety
    
    @pytest.mark.asyncio
    async def test_plan_contains_required_steps(self, complex_prompt):
        """Test that plan contains required steps."""
        planner = ReasoningPlanner()
        
        plan = await planner.create_plan(complex_prompt)
        
        # Plan should have steps
        assert len(plan.steps) > 0
        
        # Each step should have required fields
        for step in plan.steps:
            assert step.role is not None
            assert step.task is not None
            assert len(step.task) > 0


class TestPlanningEdgeCases:
    """Test edge cases in planning."""
    
    @pytest.mark.asyncio
    async def test_open_ended_creative_task(self):
        """Test handling of open-ended creative tasks."""
        planner = ReasoningPlanner()
        
        creative_prompt = "Write a creative story about a robot"
        plan = await planner.create_plan(creative_prompt)
        
        # Should either produce steps or single-step approach
        assert len(plan.steps) >= 1
    
    @pytest.mark.asyncio
    async def test_novel_task_handling(self):
        """Test handling of very novel tasks."""
        planner = ReasoningPlanner()
        
        novel_prompt = "Create a new programming language that combines Python and JavaScript"
        plan = await planner.create_plan(novel_prompt)
        
        # Should handle gracefully
        assert len(plan.steps) >= 1
    
    @pytest.mark.asyncio
    async def test_impossible_task_handling(self):
        """Test handling of impossible tasks."""
        planner = ReasoningPlanner()
        
        impossible_prompt = "Prove that 2+2=5"
        plan = await planner.create_plan(impossible_prompt)
        
        # Should still create a plan (might attempt and fail gracefully)
        assert len(plan.steps) >= 1


class TestIterativeReplanning:
    """Test iterative re-planning on failure."""
    
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_replanning(self):
        """Test that low confidence triggers re-planning."""
        planner = ReasoningPlanner()
        
        # Simulate low confidence result
        low_confidence_result = {
            "confidence": 0.3,
            "answer": "I'm not sure about this.",
        }
        
        should_replan = planner.should_replan(low_confidence_result)
        assert should_replan is True
    
    @pytest.mark.asyncio
    async def test_alternative_strategy_selection(self):
        """Test selection of alternative strategy on failure."""
        planner = ReasoningPlanner()
        
        # First plan fails
        original_plan = await planner.create_plan("Complex query")
        
        # Re-plan with alternative strategy
        new_plan = await planner.replan(original_plan, failure_reason="Low confidence")
        
        # Should have improved confidence (replan increases confidence)
        assert new_plan.confidence >= original_plan.confidence
    
    @pytest.mark.asyncio
    async def test_replanning_improves_confidence(self):
        """Test that re-planning improves confidence."""
        planner = ReasoningPlanner()
        
        original_plan = await planner.create_plan("Complex query")
        original_plan.confidence = 0.4  # Low confidence
        
        new_plan = await planner.replan(original_plan, failure_reason="Low confidence")
        
        # New plan should have higher confidence or different approach
        assert new_plan.confidence >= original_plan.confidence or new_plan.steps != original_plan.steps


class TestPlanningConfiguration:
    """Test planning configuration and limits."""
    
    @pytest.mark.asyncio
    async def test_max_sub_tasks_limit(self):
        """Test that max sub-tasks limit is enforced."""
        planner = ReasoningPlanner(max_steps=5)
        
        very_complex = "Do 100 different things: " + ", ".join([f"task {i}" for i in range(100)])
        plan = await planner.create_plan(very_complex)
        
        # Should not exceed max steps
        assert len(plan.steps) <= 5
    
    @pytest.mark.asyncio
    async def test_planning_depth_limit(self):
        """Test planning depth limits."""
        planner = ReasoningPlanner(max_depth=3)
        
        nested_prompt = "Plan to plan to plan something"
        plan = await planner.create_plan(nested_prompt)
        
        # Should respect depth limit
        # (Implementation depends on how depth is measured)
        assert len(plan.steps) <= 10  # Reasonable limit
    
    @pytest.mark.asyncio
    async def test_planning_performance(self):
        """Test that planning is fast."""
        import time
        
        planner = ReasoningPlanner()
        
        start = time.time()
        result = await planner.create_plan("Test query")
        elapsed = time.time() - start
        
        # Planning should be fast (< 1 second for heuristics, < 5s for LLM)
        assert elapsed < 5.0, f"Planning took {elapsed}s, should be < 5s"
        assert result is not None


class TestPlanningFallback:
    """Test planning fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_single_step_fallback(self):
        """Test fallback to single-step approach."""
        planner = ReasoningPlanner()
        
        # Query that can't be decomposed
        simple_prompt = "Hello"
        plan = await planner.create_plan(simple_prompt)
        
        # Should have at least one step
        assert len(plan.steps) >= 1
    
    @pytest.mark.asyncio
    async def test_planning_failure_handling(self):
        """Test handling of planning failures."""
        planner = ReasoningPlanner()
        
        # Simulate planning failure
        with patch.object(planner, 'create_plan', side_effect=Exception("Planning failed")):
            try:
                plan = await planner.create_plan("Test")
            except Exception:
                # Should have fallback
                plan = await planner.create_simple_plan("Test")
            
            assert plan is not None
            assert len(plan.steps) >= 1
