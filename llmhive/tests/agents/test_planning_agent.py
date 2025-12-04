"""Tests for Planning Agent.

Tests the task decomposition, prioritization, and execution planning capabilities.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from llmhive.app.agents.planning_agent import (
    PlanningAgent,
    PlannedTask,
    ExecutionPlan,
    TaskStatus,
    TaskPriority,
    TaskCategory,
    detect_task_category,
    estimate_task_time,
    extract_dependencies,
)
from llmhive.app.agents.base import AgentTask


# ============================================================
# Test Task Category Detection
# ============================================================

class TestTaskCategoryDetection:
    """Tests for task category detection."""
    
    def test_detect_code_category(self):
        """Test detection of code-related tasks."""
        assert detect_task_category("Implement a new feature") == TaskCategory.CODE
        assert detect_task_category("Debug the login issue") == TaskCategory.CODE
        assert detect_task_category("Write unit tests") == TaskCategory.CODE
        assert detect_task_category("Refactor the API module") == TaskCategory.CODE
    
    def test_detect_research_category(self):
        """Test detection of research-related tasks."""
        assert detect_task_category("Research best practices") == TaskCategory.RESEARCH
        assert detect_task_category("Investigate the performance issue") == TaskCategory.RESEARCH
        assert detect_task_category("Explore new technologies") == TaskCategory.RESEARCH
    
    def test_detect_analysis_category(self):
        """Test detection of analysis-related tasks."""
        assert detect_task_category("Analyze user feedback") == TaskCategory.ANALYSIS
        assert detect_task_category("Evaluate the proposal") == TaskCategory.ANALYSIS
        assert detect_task_category("Compare different approaches") == TaskCategory.ANALYSIS
    
    def test_detect_writing_category(self):
        """Test detection of writing-related tasks."""
        assert detect_task_category("Write documentation") == TaskCategory.WRITING
        assert detect_task_category("Document this feature") == TaskCategory.WRITING
        assert detect_task_category("Summarize the results") == TaskCategory.WRITING
    
    def test_detect_review_category(self):
        """Test detection of review-related tasks."""
        assert detect_task_category("Review the pull request") == TaskCategory.REVIEW
        assert detect_task_category("Check for errors") == TaskCategory.REVIEW
        assert detect_task_category("Validate the results") == TaskCategory.REVIEW
    
    def test_detect_coordination_category(self):
        """Test detection of coordination-related tasks."""
        assert detect_task_category("Coordinate with the team") == TaskCategory.COORDINATION
        assert detect_task_category("Plan the sprint") == TaskCategory.COORDINATION
        assert detect_task_category("Schedule the meeting") == TaskCategory.COORDINATION
    
    def test_detect_other_category(self):
        """Test fallback to other category."""
        assert detect_task_category("Something random") == TaskCategory.OTHER
        assert detect_task_category("") == TaskCategory.OTHER


# ============================================================
# Test Time Estimation
# ============================================================

class TestTimeEstimation:
    """Tests for task time estimation."""
    
    def test_base_time_by_category(self):
        """Test that different categories have different base times."""
        code_time = estimate_task_time("Implement feature", TaskCategory.CODE)
        review_time = estimate_task_time("Review code", TaskCategory.REVIEW)
        
        # Code tasks should take longer than review
        assert code_time > review_time
    
    def test_complexity_increases_time(self):
        """Test that complex tasks take longer."""
        simple_time = estimate_task_time("Simple fix", TaskCategory.CODE)
        complex_time = estimate_task_time("Complex implementation", TaskCategory.CODE)
        
        assert complex_time > simple_time
    
    def test_quick_decreases_time(self):
        """Test that quick tasks take less time."""
        normal_time = estimate_task_time("Fix the bug", TaskCategory.CODE)
        quick_time = estimate_task_time("Quick fix", TaskCategory.CODE)
        
        assert quick_time < normal_time
    
    def test_time_bounds(self):
        """Test that time is bounded between 5 and 120 minutes."""
        short_time = estimate_task_time("simple", TaskCategory.COORDINATION)
        long_time = estimate_task_time("comprehensive detailed complex analysis", TaskCategory.RESEARCH)
        
        assert short_time >= 5
        assert long_time <= 120


# ============================================================
# Test PlannedTask Model
# ============================================================

class TestPlannedTask:
    """Tests for PlannedTask model."""
    
    def test_create_task(self):
        """Test task creation."""
        task = PlannedTask(
            id="task_1",
            title="Test Task",
            description="A test task",
            category=TaskCategory.CODE,
            priority=TaskPriority.HIGH,
        )
        
        assert task.id == "task_1"
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []
    
    def test_task_to_dict(self):
        """Test task serialization."""
        task = PlannedTask(
            id="task_1",
            title="Test Task",
            description="A test task",
            category=TaskCategory.CODE,
            priority=TaskPriority.HIGH,
        )
        
        data = task.to_dict()
        
        assert data["id"] == "task_1"
        assert data["category"] == "code"
        assert data["priority"] == "high"
        assert data["status"] == "pending"


# ============================================================
# Test ExecutionPlan Model
# ============================================================

class TestExecutionPlan:
    """Tests for ExecutionPlan model."""
    
    def test_create_plan(self):
        """Test plan creation."""
        tasks = [
            PlannedTask(
                id="task_1",
                title="Step 1",
                description="First step",
                category=TaskCategory.CODE,
                priority=TaskPriority.HIGH,
            ),
            PlannedTask(
                id="task_2",
                title="Step 2",
                description="Second step",
                category=TaskCategory.REVIEW,
                priority=TaskPriority.MEDIUM,
                dependencies=["task_1"],
            ),
        ]
        
        plan = ExecutionPlan(
            id="plan_1",
            name="Test Plan",
            description="A test plan",
            tasks=tasks,
            total_estimated_minutes=60,
        )
        
        assert plan.id == "plan_1"
        assert len(plan.tasks) == 2
    
    def test_plan_progress(self):
        """Test plan progress calculation."""
        tasks = [
            PlannedTask(
                id="task_1",
                title="Step 1",
                description="First step",
                category=TaskCategory.CODE,
                priority=TaskPriority.HIGH,
                status=TaskStatus.COMPLETED,
            ),
            PlannedTask(
                id="task_2",
                title="Step 2",
                description="Second step",
                category=TaskCategory.REVIEW,
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
            ),
        ]
        
        plan = ExecutionPlan(
            id="plan_1",
            name="Test Plan",
            description="A test plan",
            tasks=tasks,
        )
        
        progress = plan.get_progress()
        
        assert progress["completed"] == 1
        assert progress["total"] == 2
        assert progress["percentage"] == 50.0
    
    def test_get_next_tasks(self):
        """Test getting next available tasks."""
        tasks = [
            PlannedTask(
                id="task_1",
                title="Step 1",
                description="First step",
                category=TaskCategory.CODE,
                priority=TaskPriority.HIGH,
                status=TaskStatus.COMPLETED,
            ),
            PlannedTask(
                id="task_2",
                title="Step 2",
                description="Second step",
                category=TaskCategory.CODE,
                priority=TaskPriority.HIGH,
                dependencies=["task_1"],
                status=TaskStatus.PENDING,
            ),
            PlannedTask(
                id="task_3",
                title="Step 3",
                description="Third step",
                category=TaskCategory.CODE,
                priority=TaskPriority.LOW,
                dependencies=["task_2"],
                status=TaskStatus.PENDING,
            ),
        ]
        
        plan = ExecutionPlan(
            id="plan_1",
            name="Test Plan",
            description="A test plan",
            tasks=tasks,
        )
        
        next_tasks = plan.get_next_tasks()
        
        assert len(next_tasks) == 1
        assert next_tasks[0].id == "task_2"
    
    def test_get_next_tasks_respects_priority(self):
        """Test that next tasks are sorted by priority."""
        tasks = [
            PlannedTask(
                id="task_1",
                title="Low priority",
                description="Low priority task",
                category=TaskCategory.CODE,
                priority=TaskPriority.LOW,
                status=TaskStatus.PENDING,
            ),
            PlannedTask(
                id="task_2",
                title="High priority",
                description="High priority task",
                category=TaskCategory.CODE,
                priority=TaskPriority.HIGH,
                status=TaskStatus.PENDING,
            ),
            PlannedTask(
                id="task_3",
                title="Critical priority",
                description="Critical priority task",
                category=TaskCategory.CODE,
                priority=TaskPriority.CRITICAL,
                status=TaskStatus.PENDING,
            ),
        ]
        
        plan = ExecutionPlan(
            id="plan_1",
            name="Test Plan",
            description="A test plan",
            tasks=tasks,
        )
        
        next_tasks = plan.get_next_tasks()
        
        assert next_tasks[0].priority == TaskPriority.CRITICAL
        assert next_tasks[1].priority == TaskPriority.HIGH
        assert next_tasks[2].priority == TaskPriority.LOW


# ============================================================
# Test PlanningAgent
# ============================================================

class TestPlanningAgent:
    """Tests for PlanningAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a planning agent for tests."""
        return PlanningAgent()
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent):
        """Test getting agent capabilities."""
        task = AgentTask(
            task_id="test_1",
            task_type="get_capabilities",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert result.success
        assert "name" in result.output
        assert result.output["name"] == "Planning Agent"
        assert "supported_tasks" in result.output
    
    @pytest.mark.asyncio
    async def test_create_plan_with_goal(self, agent):
        """Test creating a plan from a goal."""
        task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={
                "goal": "Implement a new user authentication system",
            },
        )
        
        result = await agent.execute(task)
        
        assert result.success
        assert "plan_id" in result.output
        assert "plan" in result.output
        assert len(result.output["plan"]["tasks"]) > 0
    
    @pytest.mark.asyncio
    async def test_create_plan_with_steps(self, agent):
        """Test creating a plan with provided steps."""
        task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={
                "goal": "Complete the project",
                "steps": [
                    "Research requirements",
                    "Implement core features",
                    "Write tests",
                    "Deploy",
                ],
            },
        )
        
        result = await agent.execute(task)
        
        assert result.success
        assert len(result.output["plan"]["tasks"]) == 4
    
    @pytest.mark.asyncio
    async def test_create_plan_without_goal_fails(self, agent):
        """Test that creating a plan without goal fails."""
        task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert not result.success
        assert "error" in result.output
    
    @pytest.mark.asyncio
    async def test_get_plan_status(self, agent):
        """Test getting plan status."""
        # First create a plan
        create_task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={"goal": "Build a feature"},
        )
        create_result = await agent.execute(create_task)
        plan_id = create_result.output["plan_id"]
        
        # Get status
        status_task = AgentTask(
            task_id="test_2",
            task_type="get_plan_status",
            payload={"plan_id": plan_id},
        )
        result = await agent.execute(status_task)
        
        assert result.success
        assert "plan" in result.output
        assert "progress" in result.output
    
    @pytest.mark.asyncio
    async def test_get_next_tasks(self, agent):
        """Test getting next tasks."""
        # Create a plan
        create_task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={"goal": "Build a feature"},
        )
        create_result = await agent.execute(create_task)
        plan_id = create_result.output["plan_id"]
        
        # Get next tasks
        next_task = AgentTask(
            task_id="test_2",
            task_type="get_next_tasks",
            payload={"plan_id": plan_id, "limit": 2},
        )
        result = await agent.execute(next_task)
        
        assert result.success
        assert "next_tasks" in result.output
        assert len(result.output["next_tasks"]) > 0
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, agent):
        """Test updating task status."""
        # Create a plan
        create_task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={
                "goal": "Build a feature",
                "steps": ["Step 1", "Step 2"],
            },
        )
        create_result = await agent.execute(create_task)
        plan_id = create_result.output["plan_id"]
        task_id = create_result.output["plan"]["tasks"][0]["id"]
        
        # Update task status
        update_task = AgentTask(
            task_id="test_2",
            task_type="update_task",
            payload={
                "plan_id": plan_id,
                "task_id": task_id,
                "status": "completed",
                "result": "Task completed successfully",
            },
        )
        result = await agent.execute(update_task)
        
        assert result.success
        assert result.output["new_status"] == "completed"
        assert result.output["plan_progress"]["completed"] == 1
    
    @pytest.mark.asyncio
    async def test_prioritize_tasks(self, agent):
        """Test task prioritization."""
        # Create a plan
        create_task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={
                "goal": "Build a feature",
                "steps": [
                    {"description": "Research", "priority": "low"},
                    {"description": "Implement", "priority": "high"},
                    {"description": "Test", "priority": "medium"},
                ],
            },
        )
        create_result = await agent.execute(create_task)
        plan_id = create_result.output["plan_id"]
        
        # Prioritize by impact
        prioritize_task = AgentTask(
            task_id="test_2",
            task_type="prioritize",
            payload={
                "plan_id": plan_id,
                "criteria": "impact",
            },
        )
        result = await agent.execute(prioritize_task)
        
        assert result.success
        assert "ordered_tasks" in result.output
    
    @pytest.mark.asyncio
    async def test_get_history(self, agent):
        """Test getting planning history."""
        # Execute some tasks first
        create_task = AgentTask(
            task_id="test_1",
            task_type="create_plan",
            payload={"goal": "Build a feature"},
        )
        await agent.execute(create_task)
        
        # Get history
        history_task = AgentTask(
            task_id="test_2",
            task_type="get_history",
            payload={},
        )
        result = await agent.execute(history_task)
        
        assert result.success
        assert "history" in result.output
        assert len(result.output["history"]) > 0
    
    @pytest.mark.asyncio
    async def test_unknown_task_type_fails(self, agent):
        """Test that unknown task types fail gracefully."""
        task = AgentTask(
            task_id="test_1",
            task_type="unknown_task",
            payload={},
        )
        
        result = await agent.execute(task)
        
        assert not result.success
        assert "error" in result.output
    
    @pytest.mark.asyncio
    async def test_no_task_fails(self, agent):
        """Test that execution without task fails."""
        result = await agent.execute(None)
        
        assert not result.success


# ============================================================
# Test Integration Scenarios
# ============================================================

class TestIntegrationScenarios:
    """Integration tests for planning workflows."""
    
    @pytest.mark.asyncio
    async def test_full_planning_workflow(self):
        """Test a complete planning workflow."""
        agent = PlanningAgent()
        
        # 1. Create a plan
        create_task = AgentTask(
            task_id="step_1",
            task_type="create_plan",
            payload={
                "goal": "Implement user authentication",
                "steps": [
                    "Design authentication flow",
                    "Implement login API",
                    "Implement logout API",
                    "Add session management",
                    "Write tests",
                ],
            },
        )
        create_result = await agent.execute(create_task)
        assert create_result.success
        plan_id = create_result.output["plan_id"]
        
        # 2. Get next tasks
        next_task = AgentTask(
            task_id="step_2",
            task_type="get_next_tasks",
            payload={"plan_id": plan_id},
        )
        next_result = await agent.execute(next_task)
        assert next_result.success
        
        # 3. Complete first task
        first_task_id = next_result.output["next_tasks"][0]["id"]
        update_task = AgentTask(
            task_id="step_3",
            task_type="update_task",
            payload={
                "plan_id": plan_id,
                "task_id": first_task_id,
                "status": "completed",
            },
        )
        update_result = await agent.execute(update_task)
        assert update_result.success
        
        # 4. Check progress
        status_task = AgentTask(
            task_id="step_4",
            task_type="get_plan_status",
            payload={"plan_id": plan_id},
        )
        status_result = await agent.execute(status_task)
        assert status_result.success
        assert status_result.output["progress"]["completed"] == 1
    
    @pytest.mark.asyncio
    async def test_auto_decomposition_for_different_goals(self):
        """Test that different goal types get appropriate decomposition."""
        agent = PlanningAgent()
        
        goals = [
            ("Implement a new feature", "code"),
            ("Fix the login bug", "fix"),
            ("Analyze user feedback", "analysis"),
            ("Research new technologies", "research"),
        ]
        
        for goal, goal_type in goals:
            task = AgentTask(
                task_id=f"test_{goal_type}",
                task_type="create_plan",
                payload={"goal": goal},
            )
            result = await agent.execute(task)
            
            assert result.success, f"Failed for goal: {goal}"
            assert len(result.output["plan"]["tasks"]) >= 3, f"Not enough tasks for: {goal}"
