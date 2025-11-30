"""Unit tests for hierarchical planning module."""
from __future__ import annotations

import pytest

from llmhive.src.llmhive.app.orchestration.hierarchical_planning import (
    HierarchicalPlanner,
    HierarchicalPlan,
    TaskComplexity,
    is_complex_query,
    decompose_query,
)
from llmhive.src.llmhive.app.orchestration.hrm import RoleLevel


class TestHierarchicalPlanner:
    """Tests for HierarchicalPlanner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.planner = HierarchicalPlanner()
    
    def test_simple_query_analysis(self):
        """Test that simple queries are classified correctly."""
        simple_queries = [
            "What is the capital of France?",
            "How do I print 'Hello World' in Python?",
            "What is 2 + 2?",
        ]
        
        for query in simple_queries:
            plan = self.planner.plan_with_hierarchy(query)
            assert plan.complexity == TaskComplexity.SIMPLE
            assert len(plan.steps) == 1
            assert plan.strategy == "single_step"
    
    def test_moderate_query_analysis(self):
        """Test that moderate complexity queries are classified correctly."""
        moderate_queries = [
            "Explain machine learning and describe its main types.",
            "Compare Python and JavaScript for web development.",
            "First explain what REST APIs are, then describe best practices.",
        ]
        
        for query in moderate_queries:
            plan = self.planner.plan_with_hierarchy(query)
            assert plan.complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX)
            assert len(plan.steps) > 1
    
    def test_complex_query_creates_nested_plan(self):
        """Test that complex queries create proper hierarchical plans."""
        complex_query = (
            "Research and analyze the pros and cons of renewable energy sources, "
            "compare solar and wind power in detail, and provide comprehensive "
            "recommendations for a sustainable energy strategy."
        )
        
        plan = self.planner.plan_with_hierarchy(complex_query, use_full_hierarchy=True)
        
        # Should be complex
        assert plan.complexity == TaskComplexity.COMPLEX
        
        # Should have multiple steps
        assert len(plan.steps) >= 3
        
        # Should have a top role
        assert plan.top_role is not None
        assert plan.top_role.name == "executive"
        
        # Should have coordinator step
        coordinator_steps = [s for s in plan.steps if s.is_coordinator]
        assert len(coordinator_steps) >= 1
        
        # Should have sub-tasks
        assert len(plan.sub_tasks) >= 1
    
    def test_execution_order_respects_dependencies(self):
        """Test that execution order respects step dependencies."""
        complex_query = "Research machine learning, analyze its applications, and synthesize findings."
        plan = self.planner.plan_with_hierarchy(complex_query)
        
        ordered_steps = plan.get_execution_order()
        
        # Each step's dependencies should come before it
        executed_ids = set()
        for step in ordered_steps:
            for dep in step.dependencies:
                assert dep in executed_ids, f"Dependency {dep} should come before {step.step_id}"
            executed_ids.add(step.step_id)
    
    def test_role_hierarchy_structure(self):
        """Test that role hierarchy is properly structured."""
        complex_query = "Comprehensive analysis of AI ethics and provide recommendations."
        plan = self.planner.plan_with_hierarchy(complex_query, use_full_hierarchy=True)
        
        # Check role levels are assigned correctly
        role_levels = {step.role.level for step in plan.steps}
        
        # Should have multiple levels for complex queries
        assert len(role_levels) >= 2
        
        # Check parent-child relationships
        for step in plan.steps:
            if step.role.parent_role:
                # Parent should be in child's list
                parent_steps = [s for s in plan.steps if s.role.name == step.role.parent_role]
                if parent_steps:
                    parent = parent_steps[0]
                    assert step.role.name in parent.role.child_roles or len(parent.role.child_roles) == 0
    
    def test_required_model_count_by_accuracy(self):
        """Test that model count recommendations vary by accuracy level."""
        complex_query = "Analyze and compare multiple AI frameworks."
        plan = self.planner.plan_with_hierarchy(complex_query)
        
        # Low accuracy = fewer models
        low_count = self.planner.get_required_model_count(plan, accuracy_level=1)
        
        # High accuracy = more models
        high_count = self.planner.get_required_model_count(plan, accuracy_level=5)
        
        assert low_count <= high_count
        assert low_count >= 1
        assert high_count <= 5


class TestComplexityAnalysis:
    """Tests for query complexity analysis functions."""
    
    def test_is_complex_query_simple(self):
        """Test is_complex_query returns False for simple queries."""
        assert not is_complex_query("Hello")
        assert not is_complex_query("What time is it?")
    
    def test_is_complex_query_complex(self):
        """Test is_complex_query returns True for complex queries."""
        assert is_complex_query(
            "Research and analyze the comprehensive impact of climate change "
            "on agriculture and compare different mitigation strategies."
        )
    
    def test_decompose_query_multiple_parts(self):
        """Test decompose_query breaks down complex queries."""
        query = "First explain Python basics. Then describe advanced features."
        parts = decompose_query(query)
        
        assert len(parts) >= 1
    
    def test_decompose_query_compare_contrast(self):
        """Test decompose_query handles compare/contrast queries."""
        query = "Compare and contrast machine learning and deep learning."
        parts = decompose_query(query)
        
        # Should create analysis sub-tasks
        assert len(parts) >= 2


class TestModelAssignment:
    """Tests for model assignment to roles."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.planner = HierarchicalPlanner()
    
    def test_assign_models_to_roles(self):
        """Test that models are correctly assigned to roles."""
        query = "Research AI trends and provide analysis."
        plan = self.planner.plan_with_hierarchy(query)
        
        model_assignments = {
            "coordinator": "gpt-4o",
            "specialist": "claude-3-sonnet",
            "assistant": "gpt-4o-mini",
            "executive": "gpt-4o",
        }
        
        updated_plan = self.planner.assign_models_to_roles(plan, model_assignments)
        
        # Check that coordinator steps get coordinator model
        for step in updated_plan.steps:
            if "coordinator" in step.role.name.lower():
                assert step.role.assigned_model is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

