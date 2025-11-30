"""Hierarchical Planning for HRM-based orchestration.

This module implements hierarchical task decomposition and role assignment
based on the Hierarchical Role Management (HRM) system. It creates structured
plans with coordinator roles that delegate to specialists.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .hrm import HRMRegistry, HRMRole, RoleLevel, get_hrm_registry

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """Complexity level of a task."""
    SIMPLE = "simple"  # Single-step, straightforward
    MODERATE = "moderate"  # Multi-step but not nested
    COMPLEX = "complex"  # Requires hierarchical decomposition


@dataclass(slots=True)
class HierarchicalRole:
    """Represents a role in the hierarchical plan."""
    name: str
    level: RoleLevel
    description: str
    required_capabilities: set = field(default_factory=set)
    parent_role: Optional[str] = None
    child_roles: List[str] = field(default_factory=list)
    assigned_model: Optional[str] = None
    sub_query: Optional[str] = None


@dataclass(slots=True)
class HierarchicalPlanStep:
    """A step in the hierarchical execution plan."""
    step_id: str
    role: HierarchicalRole
    query: str
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    outputs_to: List[str] = field(default_factory=list)  # Step IDs that receive output
    is_coordinator: bool = False
    estimated_tokens: int = 0


@dataclass(slots=True)
class HierarchicalPlan:
    """Complete hierarchical execution plan."""
    original_query: str
    complexity: TaskComplexity
    top_role: Optional[HierarchicalRole] = None
    steps: List[HierarchicalPlanStep] = field(default_factory=list)
    sub_tasks: List[str] = field(default_factory=list)
    strategy: str = "hrm_hierarchical"
    confidence: float = 0.8
    
    def get_execution_order(self) -> List[HierarchicalPlanStep]:
        """Get steps in proper execution order (respecting dependencies)."""
        # Topological sort based on dependencies
        executed: set = set()
        ordered: List[HierarchicalPlanStep] = []
        
        # Keep iterating until all steps are executed
        max_iterations = len(self.steps) * 2  # Prevent infinite loops
        iterations = 0
        
        while len(ordered) < len(self.steps) and iterations < max_iterations:
            iterations += 1
            for step in self.steps:
                if step.step_id in executed:
                    continue
                # Check if all dependencies are met
                deps_met = all(dep in executed for dep in step.dependencies)
                if deps_met:
                    ordered.append(step)
                    executed.add(step.step_id)
        
        return ordered


class HierarchicalPlanner:
    """Creates hierarchical plans using HRM role structure."""
    
    def __init__(self, hrm_registry: Optional[HRMRegistry] = None) -> None:
        self.hrm = hrm_registry or get_hrm_registry()
        self._step_counter = 0
    
    def _next_step_id(self) -> str:
        self._step_counter += 1
        return f"step_{self._step_counter}"
    
    def plan_with_hierarchy(self, query: str, *, use_full_hierarchy: bool = True) -> HierarchicalPlan:
        """
        Decompose query into a hierarchical plan of sub-tasks and roles.
        
        Args:
            query: User query to decompose
            use_full_hierarchy: If True, uses full HRM hierarchy; if False, simplified
            
        Returns:
            HierarchicalPlan with nested steps and role assignments
        """
        self._step_counter = 0
        
        # Analyze query complexity
        complexity = self._analyze_complexity(query)
        logger.info("Query complexity: %s", complexity.value)
        
        plan = HierarchicalPlan(
            original_query=query,
            complexity=complexity,
        )
        
        if complexity == TaskComplexity.SIMPLE:
            # Simple queries don't need hierarchy
            plan.steps.append(self._create_simple_step(query))
            plan.strategy = "single_step"
            plan.confidence = 0.9
            
        elif complexity == TaskComplexity.MODERATE:
            # Moderate: Coordinator + Specialists
            plan = self._create_moderate_plan(query, plan)
            
        else:
            # Complex: Full hierarchy with Executive -> Manager -> Specialists -> Assistants
            plan = self._create_complex_plan(query, plan, use_full_hierarchy)
        
        return plan
    
    def _analyze_complexity(self, query: str) -> TaskComplexity:
        """Analyze query to determine its complexity level."""
        query_lower = query.lower()
        
        # Complex indicators
        complex_patterns = [
            r"\band\b.*\band\b",  # Multiple "and" conjunctions
            r"(research|analyze|compare|evaluate).*and.*(research|analyze|compare|evaluate)",
            r"(comprehensive|detailed|thorough|exhaustive)",
            r"(multiple|various|several|different).*aspects",
            r"(pros\s+and\s+cons|advantages\s+and\s+disadvantages)",
            r"step.by.step.*analysis",
        ]
        
        for pattern in complex_patterns:
            if re.search(pattern, query_lower):
                return TaskComplexity.COMPLEX
        
        # Moderate indicators
        moderate_patterns = [
            r"(explain|describe|summarize).*and.*(explain|describe|summarize)",
            r"(how|what|why|when).*\?.*\?",  # Multiple questions
            r"(first|then|next|finally)",
            r"(compare|contrast|evaluate)",
        ]
        
        for pattern in moderate_patterns:
            if re.search(pattern, query_lower):
                return TaskComplexity.MODERATE
        
        # Check length - longer queries tend to be more complex
        word_count = len(query.split())
        if word_count > 50:
            return TaskComplexity.MODERATE
        if word_count > 100:
            return TaskComplexity.COMPLEX
        
        return TaskComplexity.SIMPLE
    
    def _decompose_query(self, query: str) -> List[str]:
        """Decompose a complex query into sub-tasks."""
        sub_tasks: List[str] = []
        query_lower = query.lower()
        
        # Try to split on common conjunctions
        parts = re.split(r'\.\s+(?=[A-Z])|;\s*|\band\bthen\b|\bfirst\b|\bthen\b|\bnext\b|\bfinally\b', query)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]
        
        if len(parts) > 1:
            sub_tasks.extend(parts)
        else:
            # Try splitting on question marks
            questions = [q.strip() + "?" for q in query.split("?") if q.strip()]
            if len(questions) > 1:
                sub_tasks.extend(questions)
            else:
                # Create sub-tasks based on query type
                if "compare" in query_lower or "contrast" in query_lower:
                    sub_tasks = [
                        f"Analyze the first subject: {query}",
                        f"Analyze the second subject: {query}",
                        f"Compare and synthesize findings: {query}",
                    ]
                elif "research" in query_lower or "analyze" in query_lower:
                    sub_tasks = [
                        f"Gather background information: {query}",
                        f"Perform detailed analysis: {query}",
                        f"Synthesize findings into conclusions: {query}",
                    ]
                else:
                    # Default decomposition
                    sub_tasks = [
                        f"Initial analysis: {query}",
                        f"Detailed response: {query}",
                    ]
        
        return sub_tasks
    
    def _create_simple_step(self, query: str) -> HierarchicalPlanStep:
        """Create a simple single-step plan."""
        role = HierarchicalRole(
            name="executor",
            level=RoleLevel.SPECIALIST,
            description="Direct execution of simple query",
            required_capabilities={"reasoning", "generation"},
        )
        
        return HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=role,
            query=query,
        )
    
    def _create_moderate_plan(
        self, query: str, plan: HierarchicalPlan
    ) -> HierarchicalPlan:
        """Create a moderate complexity plan with coordinator + specialists."""
        # Coordinator role
        coordinator = HierarchicalRole(
            name="coordinator",
            level=RoleLevel.MANAGER,
            description="Coordinate response generation across specialists",
            required_capabilities={"coordination", "synthesis", "analysis"},
        )
        plan.top_role = coordinator
        
        # Create coordinator step
        coord_step = HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=coordinator,
            query=f"Coordinate the following query by identifying key aspects: {query}",
            is_coordinator=True,
        )
        
        # Create specialist steps
        sub_tasks = self._decompose_query(query)
        plan.sub_tasks = sub_tasks
        
        specialist_steps: List[HierarchicalPlanStep] = []
        for i, sub_task in enumerate(sub_tasks[:3]):  # Limit to 3 sub-tasks
            specialist = HierarchicalRole(
                name=f"specialist_{i+1}",
                level=RoleLevel.SPECIALIST,
                description=f"Handle sub-task {i+1}",
                required_capabilities={"analysis", "generation"},
                parent_role="coordinator",
            )
            coordinator.child_roles.append(specialist.name)
            
            step = HierarchicalPlanStep(
                step_id=self._next_step_id(),
                role=specialist,
                query=sub_task,
                dependencies=[coord_step.step_id],
            )
            specialist_steps.append(step)
            coord_step.outputs_to.append(step.step_id)
        
        # Create synthesis step
        synthesizer = HierarchicalRole(
            name="synthesizer",
            level=RoleLevel.MANAGER,
            description="Synthesize all specialist outputs into final response",
            required_capabilities={"synthesis", "reasoning"},
        )
        
        synthesis_step = HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=synthesizer,
            query=f"Synthesize all findings into a comprehensive response for: {query}",
            dependencies=[s.step_id for s in specialist_steps],
        )
        
        for step in specialist_steps:
            step.outputs_to.append(synthesis_step.step_id)
        
        # Add all steps to plan
        plan.steps = [coord_step] + specialist_steps + [synthesis_step]
        plan.strategy = "moderate_hierarchical"
        plan.confidence = 0.8
        
        return plan
    
    def _create_complex_plan(
        self, query: str, plan: HierarchicalPlan, use_full_hierarchy: bool
    ) -> HierarchicalPlan:
        """Create a complex plan with full HRM hierarchy."""
        # Executive role (top level)
        executive = HierarchicalRole(
            name="executive",
            level=RoleLevel.EXECUTIVE,
            description="Top-level decision making and final synthesis",
            required_capabilities={"synthesis", "reasoning", "decision_making"},
        )
        plan.top_role = executive
        
        # Executive coordination step
        exec_step = HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=executive,
            query=f"Strategic analysis and task delegation for: {query}",
            is_coordinator=True,
        )
        
        # Coordinator (Manager level)
        coordinator = HierarchicalRole(
            name="coordinator",
            level=RoleLevel.MANAGER,
            description="Coordinate specialists and manage workflow",
            required_capabilities={"coordination", "analysis"},
            parent_role="executive",
        )
        executive.child_roles.append("coordinator")
        
        coord_step = HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=coordinator,
            query=f"Break down and coordinate: {query}",
            dependencies=[exec_step.step_id],
            is_coordinator=True,
        )
        exec_step.outputs_to.append(coord_step.step_id)
        
        # Decompose into sub-tasks
        sub_tasks = self._decompose_query(query)
        plan.sub_tasks = sub_tasks
        
        specialist_steps: List[HierarchicalPlanStep] = []
        assistant_steps: List[HierarchicalPlanStep] = []
        
        for i, sub_task in enumerate(sub_tasks[:4]):  # Limit to 4 sub-tasks
            # Lead Specialist
            lead = HierarchicalRole(
                name=f"lead_specialist_{i+1}",
                level=RoleLevel.SPECIALIST,
                description=f"Lead specialist for sub-task {i+1}",
                required_capabilities={"analysis", "research", "synthesis"},
                parent_role="coordinator",
            )
            coordinator.child_roles.append(lead.name)
            
            lead_step = HierarchicalPlanStep(
                step_id=self._next_step_id(),
                role=lead,
                query=f"Lead analysis for: {sub_task}",
                dependencies=[coord_step.step_id],
            )
            coord_step.outputs_to.append(lead_step.step_id)
            specialist_steps.append(lead_step)
            
            if use_full_hierarchy:
                # Research Assistant
                assistant = HierarchicalRole(
                    name=f"assistant_{i+1}",
                    level=RoleLevel.ASSISTANT,
                    description=f"Research assistant for sub-task {i+1}",
                    required_capabilities={"retrieval", "summarization"},
                    parent_role=lead.name,
                )
                lead.child_roles.append(assistant.name)
                
                assist_step = HierarchicalPlanStep(
                    step_id=self._next_step_id(),
                    role=assistant,
                    query=f"Gather supporting information for: {sub_task}",
                    dependencies=[lead_step.step_id],
                )
                lead_step.outputs_to.append(assist_step.step_id)
                assistant_steps.append(assist_step)
        
        # Quality Manager
        quality_mgr = HierarchicalRole(
            name="quality_manager",
            level=RoleLevel.MANAGER,
            description="Quality control and validation",
            required_capabilities={"validation", "critical_thinking"},
            parent_role="executive",
        )
        executive.child_roles.append("quality_manager")
        
        quality_deps = [s.step_id for s in specialist_steps]
        if assistant_steps:
            quality_deps.extend([s.step_id for s in assistant_steps])
        
        quality_step = HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=quality_mgr,
            query=f"Validate and quality check all findings for: {query}",
            dependencies=quality_deps,
        )
        
        for step in specialist_steps:
            step.outputs_to.append(quality_step.step_id)
        for step in assistant_steps:
            step.outputs_to.append(quality_step.step_id)
        
        # Final synthesis by executive
        synthesis = HierarchicalRole(
            name="executive_synthesis",
            level=RoleLevel.EXECUTIVE,
            description="Final synthesis and response generation",
            required_capabilities={"synthesis", "decision_making"},
        )
        
        synthesis_step = HierarchicalPlanStep(
            step_id=self._next_step_id(),
            role=synthesis,
            query=f"Synthesize all validated findings into final response for: {query}",
            dependencies=[quality_step.step_id],
        )
        quality_step.outputs_to.append(synthesis_step.step_id)
        
        # Assemble plan
        plan.steps = (
            [exec_step, coord_step] 
            + specialist_steps 
            + assistant_steps 
            + [quality_step, synthesis_step]
        )
        plan.strategy = "full_hrm_hierarchy" if use_full_hierarchy else "simplified_hrm_hierarchy"
        plan.confidence = 0.85 if use_full_hierarchy else 0.8
        
        return plan
    
    def get_required_model_count(self, plan: HierarchicalPlan, accuracy_level: int) -> int:
        """Get recommended number of models based on plan complexity and accuracy level."""
        base_count = len(plan.steps)
        
        # Adjust based on accuracy level (1-5)
        if accuracy_level <= 2:
            # Fast mode: fewer models, reuse
            return min(2, base_count)
        elif accuracy_level == 3:
            # Balanced: moderate model count
            return min(3, base_count)
        elif accuracy_level == 4:
            # Accurate: more models
            return min(4, base_count)
        else:
            # Most accurate: maximum models
            return min(5, base_count)
    
    def assign_models_to_roles(
        self,
        plan: HierarchicalPlan,
        model_assignments: Dict[str, str],
    ) -> HierarchicalPlan:
        """Assign models to roles in the plan based on model assignments."""
        for step in plan.steps:
            role_name = step.role.name
            # Try exact match first
            if role_name in model_assignments:
                step.role.assigned_model = model_assignments[role_name]
            # Try level-based match
            elif step.role.level.value in model_assignments:
                step.role.assigned_model = model_assignments[step.role.level.value]
            # Try capability-based match
            else:
                for capability in step.role.required_capabilities:
                    if capability in model_assignments:
                        step.role.assigned_model = model_assignments[capability]
                        break
        
        return plan


def is_complex_query(query: str) -> bool:
    """Check if a query is complex enough to warrant hierarchical planning."""
    planner = HierarchicalPlanner()
    complexity = planner._analyze_complexity(query)
    return complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX)


def decompose_query(query: str) -> List[str]:
    """Decompose a query into sub-queries for hierarchical processing."""
    planner = HierarchicalPlanner()
    return planner._decompose_query(query)

