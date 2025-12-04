"""Planning Agent for LLMHive.

This agent coordinates system improvements, breaks down complex tasks,
and manages execution planning for multi-step operations.

Responsibilities:
- Break down complex tasks into actionable steps
- Prioritize tasks based on dependencies and impact
- Create execution plans with proper sequencing
- Track plan progress and adapt as needed
- Coordinate with other agents for specialized tasks
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of a planned task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority level for tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskCategory(str, Enum):
    """Category of task for routing."""
    CODE = "code"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    REVIEW = "review"
    COORDINATION = "coordination"
    OTHER = "other"


@dataclass
class PlannedTask:
    """A task in the execution plan."""
    id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # IDs of tasks this depends on
    estimated_time_minutes: int = 15
    assigned_agent: Optional[str] = None
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "estimated_time_minutes": self.estimated_time_minutes,
            "assigned_agent": self.assigned_agent,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan with ordered tasks."""
    id: str
    name: str
    description: str
    tasks: List[PlannedTask]
    created_at: datetime = field(default_factory=datetime.now)
    total_estimated_minutes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
            "total_estimated_minutes": self.total_estimated_minutes,
            "progress": self.get_progress(),
        }
    
    def get_progress(self) -> Dict[str, Any]:
        """Calculate plan progress statistics."""
        if not self.tasks:
            return {"completed": 0, "total": 0, "percentage": 0}
        
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS)
        blocked = sum(1 for t in self.tasks if t.status == TaskStatus.BLOCKED)
        
        return {
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "total": len(self.tasks),
            "percentage": round(completed / len(self.tasks) * 100, 1),
        }
    
    def get_next_tasks(self) -> List[PlannedTask]:
        """Get tasks that are ready to be executed (no pending dependencies)."""
        ready = []
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            # Check if all dependencies are complete
            if all(dep_id in completed_ids for dep_id in task.dependencies):
                ready.append(task)
        
        # Sort by priority
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        ready.sort(key=lambda t: priority_order.get(t.priority, 99))
        
        return ready


# Task categorization patterns
CATEGORY_PATTERNS = {
    TaskCategory.CODE: [
        r"implement", r"code", r"program", r"develop", r"build",
        r"debug", r"fix bug", r"refactor", r"test", r"unit test",
    ],
    TaskCategory.RESEARCH: [
        r"research", r"investigate", r"explore", r"study", r"analyze data",
        r"find", r"discover", r"learn about",
    ],
    TaskCategory.ANALYSIS: [
        r"analyze", r"evaluate", r"assess", r"review code", r"audit",
        r"compare", r"benchmark", r"measure",
    ],
    TaskCategory.WRITING: [
        r"write", r"document", r"describe", r"explain", r"summarize",
        r"create report", r"draft",
    ],
    TaskCategory.REVIEW: [
        r"review", r"check", r"verify", r"validate", r"approve",
        r"inspect", r"quality",
    ],
    TaskCategory.COORDINATION: [
        r"coordinate", r"organize", r"plan", r"schedule", r"manage",
        r"delegate", r"assign",
    ],
}


def detect_task_category(text: str) -> TaskCategory:
    """Detect the category of a task from its description."""
    text_lower = text.lower()
    
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return category
    
    return TaskCategory.OTHER


def estimate_task_time(task_text: str, category: TaskCategory) -> int:
    """Estimate time in minutes for a task."""
    # Base times by category
    base_times = {
        TaskCategory.CODE: 30,
        TaskCategory.RESEARCH: 45,
        TaskCategory.ANALYSIS: 25,
        TaskCategory.WRITING: 20,
        TaskCategory.REVIEW: 15,
        TaskCategory.COORDINATION: 10,
        TaskCategory.OTHER: 20,
    }
    
    base = base_times.get(category, 20)
    
    # Adjust based on complexity indicators
    text_lower = task_text.lower()
    
    if any(word in text_lower for word in ["complex", "comprehensive", "detailed", "thorough"]):
        base = int(base * 1.5)
    elif any(word in text_lower for word in ["simple", "quick", "brief", "minor"]):
        base = int(base * 0.5)
    
    if any(word in text_lower for word in ["multiple", "several", "all", "each"]):
        base = int(base * 1.3)
    
    return max(5, min(base, 120))  # Clamp between 5 and 120 minutes


def extract_dependencies(task_text: str, existing_tasks: List[PlannedTask]) -> List[str]:
    """Extract task dependencies from description."""
    dependencies = []
    text_lower = task_text.lower()
    
    # Look for explicit dependency patterns
    dependency_patterns = [
        r"after (?:completing |finishing )?(task|step) (\d+)",
        r"depends on (task|step) (\d+)",
        r"requires (task|step) (\d+)",
        r"following (task|step) (\d+)",
    ]
    
    for pattern in dependency_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            task_num = match[1] if isinstance(match, tuple) else match
            # Find task by number in existing tasks
            for existing in existing_tasks:
                if task_num in existing.id:
                    dependencies.append(existing.id)
    
    return list(set(dependencies))


class PlanningAgent(BaseAgent):
    """Agent that coordinates improvements and manages execution plans.
    
    This agent breaks down complex requests into actionable steps,
    creates execution plans with proper task ordering, and tracks progress.
    
    Supported task types:
    - create_plan: Break down a complex task into steps
    - prioritize: Order tasks by importance and dependencies
    - get_next_tasks: Get tasks ready for execution
    - update_task: Update task status
    - get_plan_status: Get current plan progress
    - get_history: Get planning history
    - get_capabilities: Get agent capabilities
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="planning_agent",
                agent_type=AgentType.REACTIVE,
                priority=AgentPriority.MEDIUM,
                max_tokens_per_run=5000,
                allowed_tools=["task_scheduler"],
                can_modify_routing=True,
                memory_namespace="planning",
            )
        super().__init__(config)
        self._plans: Dict[str, ExecutionPlan] = {}
        self._task_history: List[Dict[str, Any]] = []
        self._stats = {
            "plans_created": 0,
            "tasks_completed": 0,
            "total_tasks_planned": 0,
        }
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute planning tasks based on task type."""
        start_time = time.time()
        
        if task is None:
            return AgentResult(
                success=False,
                output={"error": "No task provided"},
                error="Task is required for planning agent",
            )
        
        task_type = task.task_type
        task_input = task.payload or {}
        
        try:
            if task_type == "create_plan":
                result = await self._create_plan(task_input)
            elif task_type == "prioritize":
                result = await self._prioritize_tasks(task_input)
            elif task_type == "get_next_tasks":
                result = await self._get_next_tasks(task_input)
            elif task_type == "update_task":
                result = await self._update_task(task_input)
            elif task_type == "get_plan_status":
                result = await self._get_plan_status(task_input)
            elif task_type == "get_history":
                result = self._get_history()
            elif task_type == "get_capabilities":
                result = self.get_capabilities()
            else:
                return AgentResult(
                    success=False,
                    output={"error": f"Unknown task type: {task_type}"},
                    error=f"Unsupported task type: {task_type}",
                )
            
            execution_time = time.time() - start_time
            
            # Track history
            self._task_history.append({
                "task_type": task_type,
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "execution_time_ms": int(execution_time * 1000),
            })
            
            return AgentResult(
                success=True,
                output=result,
                duration_ms=int(execution_time * 1000),
            )
            
        except Exception as e:
            logger.exception(f"Planning agent error: {e}")
            return AgentResult(
                success=False,
                output={"error": str(e)},
                error=str(e),
            )
    
    async def _create_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution plan from a complex task description."""
        goal = input_data.get("goal", "")
        steps = input_data.get("steps", [])
        
        if not goal:
            raise ValueError("Goal is required for plan creation")
        
        # Generate plan ID
        plan_id = f"plan_{int(time.time())}_{len(self._plans)}"
        
        # Parse or generate steps
        planned_tasks: List[PlannedTask] = []
        
        if steps:
            # Use provided steps
            for i, step in enumerate(steps):
                if isinstance(step, str):
                    step_text = step
                    step_priority = TaskPriority.MEDIUM
                elif isinstance(step, dict):
                    step_text = step.get("description", step.get("text", str(step)))
                    step_priority = TaskPriority(step.get("priority", "medium"))
                else:
                    step_text = str(step)
                    step_priority = TaskPriority.MEDIUM
                
                category = detect_task_category(step_text)
                estimated_time = estimate_task_time(step_text, category)
                
                task = PlannedTask(
                    id=f"{plan_id}_task_{i+1}",
                    title=f"Step {i+1}",
                    description=step_text,
                    category=category,
                    priority=step_priority,
                    estimated_time_minutes=estimated_time,
                    dependencies=extract_dependencies(step_text, planned_tasks),
                )
                planned_tasks.append(task)
        else:
            # Auto-generate steps from goal (simple heuristic decomposition)
            planned_tasks = self._decompose_goal(goal, plan_id)
        
        # Calculate total time
        total_time = sum(t.estimated_time_minutes for t in planned_tasks)
        
        # Create plan
        plan = ExecutionPlan(
            id=plan_id,
            name=f"Plan: {goal[:50]}...",
            description=goal,
            tasks=planned_tasks,
            total_estimated_minutes=total_time,
        )
        
        self._plans[plan_id] = plan
        self._stats["plans_created"] += 1
        self._stats["total_tasks_planned"] += len(planned_tasks)
        
        logger.info(f"Created plan '{plan_id}' with {len(planned_tasks)} tasks")
        
        return {
            "plan_id": plan_id,
            "plan": plan.to_dict(),
            "summary": f"Created plan with {len(planned_tasks)} tasks, estimated {total_time} minutes",
        }
    
    def _decompose_goal(self, goal: str, plan_id: str) -> List[PlannedTask]:
        """Decompose a goal into steps using heuristics."""
        tasks: List[PlannedTask] = []
        goal_lower = goal.lower()
        
        # Default decomposition based on goal type
        if any(kw in goal_lower for kw in ["implement", "build", "create", "develop"]):
            steps = [
                ("Research and understand requirements", TaskCategory.RESEARCH, TaskPriority.HIGH),
                ("Design the solution architecture", TaskCategory.ANALYSIS, TaskPriority.HIGH),
                ("Implement core functionality", TaskCategory.CODE, TaskPriority.CRITICAL),
                ("Write tests", TaskCategory.CODE, TaskPriority.HIGH),
                ("Review and refactor", TaskCategory.REVIEW, TaskPriority.MEDIUM),
                ("Document the implementation", TaskCategory.WRITING, TaskPriority.MEDIUM),
            ]
        elif any(kw in goal_lower for kw in ["fix", "debug", "resolve", "repair"]):
            steps = [
                ("Reproduce and understand the issue", TaskCategory.ANALYSIS, TaskPriority.CRITICAL),
                ("Identify root cause", TaskCategory.RESEARCH, TaskPriority.HIGH),
                ("Implement fix", TaskCategory.CODE, TaskPriority.CRITICAL),
                ("Test the fix", TaskCategory.CODE, TaskPriority.HIGH),
                ("Verify no regressions", TaskCategory.REVIEW, TaskPriority.MEDIUM),
            ]
        elif any(kw in goal_lower for kw in ["analyze", "evaluate", "assess", "review"]):
            steps = [
                ("Gather data and context", TaskCategory.RESEARCH, TaskPriority.HIGH),
                ("Perform analysis", TaskCategory.ANALYSIS, TaskPriority.CRITICAL),
                ("Identify findings and insights", TaskCategory.ANALYSIS, TaskPriority.HIGH),
                ("Create summary report", TaskCategory.WRITING, TaskPriority.MEDIUM),
            ]
        elif any(kw in goal_lower for kw in ["research", "investigate", "explore"]):
            steps = [
                ("Define research questions", TaskCategory.ANALYSIS, TaskPriority.HIGH),
                ("Gather information from sources", TaskCategory.RESEARCH, TaskPriority.CRITICAL),
                ("Analyze and synthesize findings", TaskCategory.ANALYSIS, TaskPriority.HIGH),
                ("Document conclusions", TaskCategory.WRITING, TaskPriority.MEDIUM),
            ]
        else:
            # Generic decomposition
            steps = [
                ("Understand the goal and requirements", TaskCategory.ANALYSIS, TaskPriority.HIGH),
                ("Plan the approach", TaskCategory.COORDINATION, TaskPriority.HIGH),
                ("Execute the main work", TaskCategory.OTHER, TaskPriority.CRITICAL),
                ("Review and verify results", TaskCategory.REVIEW, TaskPriority.MEDIUM),
            ]
        
        # Create tasks with dependencies (each depends on previous)
        for i, (desc, category, priority) in enumerate(steps):
            task = PlannedTask(
                id=f"{plan_id}_task_{i+1}",
                title=f"Step {i+1}",
                description=desc,
                category=category,
                priority=priority,
                estimated_time_minutes=estimate_task_time(desc, category),
                dependencies=[f"{plan_id}_task_{i}"] if i > 0 else [],
            )
            tasks.append(task)
        
        return tasks
    
    async def _prioritize_tasks(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize tasks within a plan."""
        plan_id = input_data.get("plan_id")
        criteria = input_data.get("criteria", "default")  # default, deadline, impact, effort
        
        if not plan_id or plan_id not in self._plans:
            raise ValueError(f"Plan not found: {plan_id}")
        
        plan = self._plans[plan_id]
        
        # Sort based on criteria
        if criteria == "deadline":
            # Sort by estimated time (shorter first)
            plan.tasks.sort(key=lambda t: t.estimated_time_minutes)
        elif criteria == "impact":
            # Sort by priority
            priority_order = {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }
            plan.tasks.sort(key=lambda t: priority_order.get(t.priority, 99))
        elif criteria == "effort":
            # Sort by estimated time (longer first for bigger impact tasks)
            plan.tasks.sort(key=lambda t: -t.estimated_time_minutes)
        else:
            # Default: priority then dependencies
            priority_order = {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }
            plan.tasks.sort(key=lambda t: (len(t.dependencies), priority_order.get(t.priority, 99)))
        
        return {
            "plan_id": plan_id,
            "criteria": criteria,
            "ordered_tasks": [t.to_dict() for t in plan.tasks],
        }
    
    async def _get_next_tasks(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get the next tasks ready for execution."""
        plan_id = input_data.get("plan_id")
        limit = input_data.get("limit", 3)
        
        if not plan_id or plan_id not in self._plans:
            raise ValueError(f"Plan not found: {plan_id}")
        
        plan = self._plans[plan_id]
        next_tasks = plan.get_next_tasks()[:limit]
        
        return {
            "plan_id": plan_id,
            "next_tasks": [t.to_dict() for t in next_tasks],
            "count": len(next_tasks),
            "plan_progress": plan.get_progress(),
        }
    
    async def _update_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update the status of a task."""
        plan_id = input_data.get("plan_id")
        task_id = input_data.get("task_id")
        new_status = input_data.get("status")
        result = input_data.get("result")
        
        if not plan_id or plan_id not in self._plans:
            raise ValueError(f"Plan not found: {plan_id}")
        
        plan = self._plans[plan_id]
        task = None
        for t in plan.tasks:
            if t.id == task_id:
                task = t
                break
        
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Update status
        old_status = task.status
        task.status = TaskStatus(new_status)
        
        if task.status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        elif task.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
            self._stats["tasks_completed"] += 1
        
        if result:
            task.result = result
        
        return {
            "plan_id": plan_id,
            "task_id": task_id,
            "old_status": old_status.value,
            "new_status": task.status.value,
            "task": task.to_dict(),
            "plan_progress": plan.get_progress(),
        }
    
    async def _get_plan_status(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get the status of a plan."""
        plan_id = input_data.get("plan_id")
        
        if plan_id:
            if plan_id not in self._plans:
                raise ValueError(f"Plan not found: {plan_id}")
            plan = self._plans[plan_id]
            return {
                "plan": plan.to_dict(),
                "progress": plan.get_progress(),
            }
        else:
            # Return all plans
            return {
                "plans": [p.to_dict() for p in self._plans.values()],
                "total_plans": len(self._plans),
                "stats": self._stats,
            }
    
    def _get_history(self) -> Dict[str, Any]:
        """Get planning history."""
        return {
            "history": self._task_history[-50:],  # Last 50 entries
            "total_entries": len(self._task_history),
            "stats": self._stats,
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities description."""
        return {
            "name": "Planning Agent",
            "type": self.config.agent_type.value,
            "description": "Coordinates improvements, breaks down complex tasks, and manages execution plans",
            "supported_tasks": [
                {
                    "type": "create_plan",
                    "description": "Break down a complex goal into actionable steps",
                    "required_input": ["goal"],
                    "optional_input": ["steps"],
                },
                {
                    "type": "prioritize",
                    "description": "Order tasks by criteria (deadline, impact, effort, default)",
                    "required_input": ["plan_id"],
                    "optional_input": ["criteria"],
                },
                {
                    "type": "get_next_tasks",
                    "description": "Get tasks ready for execution (no pending dependencies)",
                    "required_input": ["plan_id"],
                    "optional_input": ["limit"],
                },
                {
                    "type": "update_task",
                    "description": "Update task status and result",
                    "required_input": ["plan_id", "task_id", "status"],
                    "optional_input": ["result"],
                },
                {
                    "type": "get_plan_status",
                    "description": "Get status of a plan or all plans",
                    "required_input": [],
                    "optional_input": ["plan_id"],
                },
                {
                    "type": "get_history",
                    "description": "Get planning history",
                },
                {
                    "type": "get_capabilities",
                    "description": "Get this agent's capabilities",
                },
            ],
            "stats": self._stats,
        }
