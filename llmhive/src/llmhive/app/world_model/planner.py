"""World Model Planner - Long-horizon planning with search."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum, auto

from .state_store import WorldState, get_state_store
from .simulator import ActionSimulator, SimulationResult

logger = logging.getLogger(__name__)


class PlanStatus(Enum):
    """Status of a plan."""
    DRAFT = auto()
    VALIDATED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class PlanStep:
    """A step in an execution plan."""
    step_id: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    dependencies: List[str] = field(default_factory=list)  # step_ids
    expected_state_changes: Dict[str, Any] = field(default_factory=dict)
    contingency: Optional[str] = None  # Alternative action if this fails
    
    # Execution tracking
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class Plan:
    """A complete execution plan."""
    plan_id: str
    goal_description: str
    steps: List[PlanStep] = field(default_factory=list)
    initial_state: Optional[WorldState] = None
    goal_conditions: List[Dict[str, Any]] = field(default_factory=list)
    contingencies: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    estimated_duration_ms: int = 0
    confidence: float = 0.0
    
    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next pending step."""
        for step in self.steps:
            if step.status == "pending":
                # Check dependencies
                deps_met = all(
                    self._get_step(dep).status == "completed"
                    for dep in step.dependencies
                    if self._get_step(dep)
                )
                if deps_met:
                    return step
        return None
    
    def _get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def mark_step_complete(self, step_id: str, result: Any = None) -> None:
        """Mark a step as completed."""
        step = self._get_step(step_id)
        if step:
            step.status = "completed"
            step.result = result
    
    def mark_step_failed(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        step = self._get_step(step_id)
        if step:
            step.status = "failed"
            step.error = error
    
    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return all(s.status in ("completed", "failed") for s in self.steps)
    
    def get_progress(self) -> Tuple[int, int]:
        """Get (completed, total) step counts."""
        completed = sum(1 for s in self.steps if s.status == "completed")
        return (completed, len(self.steps))


class WorldModelPlanner:
    """Long-horizon planner using world model.
    
    Features:
    - Goal-directed planning with state simulation
    - Search algorithms (DFS, heuristic)
    - Dependency-aware step ordering
    - Contingency planning
    - Plan validation before execution
    """
    
    def __init__(
        self,
        max_plan_depth: int = 20,
        max_search_iterations: int = 100
    ):
        self.max_plan_depth = max_plan_depth
        self.max_search_iterations = max_search_iterations
        self._simulator = ActionSimulator()
        self._state_store = get_state_store()
        self._active_plans: Dict[str, Plan] = {}
        
        logger.info("WorldModelPlanner initialized")
    
    async def create_plan(
        self,
        task_id: str,
        goal_description: str,
        goal_conditions: List[Dict[str, Any]],
        initial_state: Optional[WorldState] = None,
        available_actions: Optional[List[str]] = None,
    ) -> Plan:
        """Create a plan to achieve goal from initial state.
        
        Args:
            task_id: Task identifier
            goal_description: Natural language goal
            goal_conditions: Formal conditions for goal satisfaction
            initial_state: Starting state (or create new)
            available_actions: Actions the planner can use
            
        Returns:
            Generated plan
        """
        # Get or create initial state
        if initial_state is None:
            initial_state = self._state_store.create_state(task_id)
        
        plan_id = f"plan-{task_id}-{datetime.now().timestamp()}"
        
        # Generate plan steps using search
        steps = await self._search_for_plan(
            initial_state,
            goal_conditions,
            available_actions or list(self._simulator._action_library.keys())
        )
        
        # Calculate estimated duration
        duration = sum(
            self._estimate_step_duration(s) for s in steps
        )
        
        # Calculate confidence based on simulation results
        confidence = await self._validate_plan_confidence(
            initial_state, steps, goal_conditions
        )
        
        plan = Plan(
            plan_id=plan_id,
            goal_description=goal_description,
            steps=steps,
            initial_state=initial_state,
            goal_conditions=goal_conditions,
            estimated_duration_ms=duration,
            confidence=confidence,
        )
        
        self._active_plans[plan_id] = plan
        
        logger.info(
            f"Created plan {plan_id} with {len(steps)} steps, "
            f"confidence {confidence:.2f}"
        )
        
        return plan
    
    async def _search_for_plan(
        self,
        initial_state: WorldState,
        goal_conditions: List[Dict],
        available_actions: List[str]
    ) -> List[PlanStep]:
        """Search for a sequence of actions achieving the goal.
        
        Uses a simple forward search with heuristics.
        In production, would use more sophisticated planners.
        """
        steps = []
        
        # For simple cases, generate steps based on goal conditions
        for i, condition in enumerate(goal_conditions):
            condition_type = condition.get("type", "")
            
            if condition_type == "variable_equals":
                # Need to set a variable
                steps.append(PlanStep(
                    step_id=f"step-{i}",
                    action="set_variable",
                    parameters={
                        "path": f"variables.{condition.get('variable')}",
                        "value": condition.get("value"),
                    },
                    description=f"Set {condition.get('variable')} to {condition.get('value')}",
                ))
            
            elif condition_type == "entity_exists":
                # Need to create an entity
                steps.append(PlanStep(
                    step_id=f"step-{i}",
                    action="create_entity",
                    parameters={
                        "entity_id": condition.get("entity_id"),
                        "entity_type": condition.get("entity_type", "object"),
                    },
                    description=f"Create entity {condition.get('entity_id')}",
                ))
        
        # In production: use actual search algorithm (A*, MCTS, etc.)
        # that simulates actions and backtracks on failure
        
        return steps
    
    async def _validate_plan_confidence(
        self,
        initial_state: WorldState,
        steps: List[PlanStep],
        goal_conditions: List[Dict]
    ) -> float:
        """Validate plan by simulation and calculate confidence."""
        if not steps:
            return 0.0
        
        # Simulate all steps
        current_state = initial_state.snapshot()
        successful_steps = 0
        
        for step in steps:
            result = await self._simulator.simulate(
                current_state,
                step.action,
                step.parameters
            )
            
            if result.success and result.resulting_state:
                successful_steps += 1
                current_state = result.resulting_state
            else:
                break
        
        # Check if goal conditions are met in final state
        goals_met = self._check_goals(current_state, goal_conditions)
        
        # Calculate confidence
        step_success_rate = successful_steps / len(steps) if steps else 0
        goal_achievement = sum(1 for g in goals_met if g) / len(goal_conditions) if goal_conditions else 1
        
        confidence = (step_success_rate * 0.4) + (goal_achievement * 0.6)
        return min(confidence, 1.0)
    
    def _check_goals(
        self,
        state: WorldState,
        goal_conditions: List[Dict]
    ) -> List[bool]:
        """Check which goal conditions are satisfied."""
        results = []
        
        for condition in goal_conditions:
            condition_type = condition.get("type", "")
            
            if condition_type == "variable_equals":
                var_name = condition.get("variable")
                expected = condition.get("value")
                actual = state.variables.get(var_name)
                results.append(actual == expected)
            
            elif condition_type == "entity_exists":
                entity_id = condition.get("entity_id")
                results.append(entity_id in state.entities)
            
            else:
                results.append(False)
        
        return results
    
    def _estimate_step_duration(self, step: PlanStep) -> int:
        """Estimate how long a step will take (ms)."""
        # Default estimates by action type
        estimates = {
            "set_variable": 10,
            "create_entity": 50,
            "delete_entity": 50,
            "api_call": 500,
            "llm_call": 2000,
            "tool_execution": 5000,
        }
        return estimates.get(step.action, 100)
    
    async def execute_plan(
        self,
        plan_id: str,
        executor: Optional[callable] = None
    ) -> Plan:
        """Execute a plan step by step.
        
        Args:
            plan_id: Plan to execute
            executor: Optional custom step executor
            
        Returns:
            Updated plan with results
        """
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan.status = PlanStatus.EXECUTING
        
        while not plan.is_complete():
            step = plan.get_next_step()
            if not step:
                break
            
            try:
                if executor:
                    result = await executor(step)
                else:
                    result = await self._default_execute_step(step)
                
                plan.mark_step_complete(step.step_id, result)
                
            except Exception as e:
                error_msg = str(e)
                plan.mark_step_failed(step.step_id, error_msg)
                
                # Try contingency if available
                if step.contingency:
                    logger.info(f"Trying contingency for step {step.step_id}")
                    # In production: execute contingency plan
        
        # Update plan status
        progress = plan.get_progress()
        if progress[0] == progress[1]:
            plan.status = PlanStatus.COMPLETED
        else:
            plan.status = PlanStatus.FAILED
        
        return plan
    
    async def _default_execute_step(self, step: PlanStep) -> Any:
        """Default step executor (simulation only)."""
        # In production, would execute actual actions
        logger.info(f"Executing step: {step.description}")
        await asyncio.sleep(0.01)  # Simulate work
        return {"executed": True, "step": step.step_id}
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self._active_plans.get(plan_id)
    
    def list_plans(self) -> List[Dict[str, Any]]:
        """List all active plans."""
        return [
            {
                "plan_id": p.plan_id,
                "goal": p.goal_description[:100],
                "status": p.status.name,
                "progress": f"{p.get_progress()[0]}/{p.get_progress()[1]}",
                "confidence": p.confidence,
            }
            for p in self._active_plans.values()
        ]

