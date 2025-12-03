"""Hierarchical Planning (HRM) Module for LLMHive Orchestrator.

This module implements LLM-based task decomposition and hierarchical
execution planning for complex multi-step queries.

Features:
- LLM-based plan generation with structured output
- Role-based step assignment (Researcher, Analyst, etc.)
- Model routing per role
- Parallel execution of independent steps
- Plan synthesis and answer assembly
- Fallback to simple execution for single-step plans
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PlanRole(str, Enum):
    """Roles for plan execution."""
    PLANNER = "planner"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    CODER = "coder"
    EXPLAINER = "explainer"
    VERIFIER = "verifier"
    SYNTHESIZER = "synthesizer"


# Role to best model type mapping
ROLE_MODEL_PREFERENCES: Dict[PlanRole, List[str]] = {
    PlanRole.PLANNER: ["gpt-4o", "claude-sonnet-4"],
    PlanRole.RESEARCHER: ["gemini-2.5-pro", "gpt-4o", "claude-sonnet-4"],
    PlanRole.ANALYST: ["claude-sonnet-4", "gpt-4o", "deepseek-chat"],
    PlanRole.CODER: ["deepseek-chat", "claude-sonnet-4", "gpt-4o"],
    PlanRole.EXPLAINER: ["gpt-4o", "claude-sonnet-4"],
    PlanRole.VERIFIER: ["gpt-4o", "claude-sonnet-4"],
    PlanRole.SYNTHESIZER: ["claude-sonnet-4", "gpt-4o"],
}


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_id: str
    description: str
    role: PlanRole
    goal: str
    inputs: List[str]
    expected_output: str
    depends_on: List[str] = field(default_factory=list)
    parallelizable: bool = False
    assigned_model: Optional[str] = None
    result: Optional[str] = None
    completed: bool = False


@dataclass
class ExecutionPlan:
    """Complete execution plan for a query."""
    query: str
    steps: List[PlanStep]
    total_steps: int
    parallelizable_groups: List[List[str]]  # Groups of step IDs that can run in parallel
    estimated_complexity: str
    planning_notes: List[str]


@dataclass
class PlanResult:
    """Result of executing a plan."""
    success: bool
    final_answer: str
    steps_executed: int
    steps_successful: int
    step_results: Dict[str, str]
    synthesis_notes: List[str]


# LLM prompt for plan generation
PLANNING_PROMPT = '''You are a strategic planner that breaks down complex queries into executable steps.

Query: "{query}"

Analyze this query and create a structured execution plan. Each step should have:
- A clear role (researcher, analyst, coder, explainer, verifier, synthesizer)
- A specific goal
- Dependencies on previous steps (if any)
- Whether it can run in parallel with other steps

Respond in JSON format:
{{
    "complexity": "simple|moderate|complex|research",
    "steps": [
        {{
            "step_id": "step_1",
            "role": "researcher|analyst|coder|explainer|verifier|synthesizer",
            "description": "Brief description of what this step does",
            "goal": "The specific goal of this step",
            "inputs": ["What information this step needs"],
            "expected_output": "What this step will produce",
            "depends_on": ["step_ids this depends on, empty for first steps"],
            "parallelizable": true/false
        }}
    ],
    "synthesis_approach": "How to combine step results into final answer"
}}

For simple queries, just return a single step. For complex queries, break into logical sub-tasks.
Only output valid JSON, no other text.'''


class HierarchicalPlanner:
    """LLM-based hierarchical planner for complex queries.
    
    Uses an LLM to decompose complex queries into structured plans
    with role assignments and dependency tracking.
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        planning_model: str = "gpt-4o",
    ):
        """Initialize the planner.
        
        Args:
            providers: LLM providers
            planning_model: Model to use for planning
        """
        self.providers = providers
        self.planning_model = planning_model
    
    async def create_plan(
        self,
        query: str,
        complexity_hint: Optional[str] = None,
    ) -> ExecutionPlan:
        """Create an execution plan for a query.
        
        Args:
            query: The user's query
            complexity_hint: Optional hint about complexity
            
        Returns:
            ExecutionPlan with structured steps
        """
        try:
            # Use LLM to generate plan
            plan_data = await self._generate_plan_with_llm(query)
            
            # Parse and validate plan
            steps = self._parse_plan_steps(plan_data)
            
            # Identify parallelizable groups
            groups = self._identify_parallel_groups(steps)
            
            # Assign models to roles
            for step in steps:
                step.assigned_model = self._select_model_for_role(step.role)
            
            return ExecutionPlan(
                query=query,
                steps=steps,
                total_steps=len(steps),
                parallelizable_groups=groups,
                estimated_complexity=plan_data.get("complexity", "moderate"),
                planning_notes=[plan_data.get("synthesis_approach", "")],
            )
        except Exception as e:
            logger.warning("LLM planning failed, using fallback: %s", e)
            return self._create_fallback_plan(query)
    
    async def _generate_plan_with_llm(self, query: str) -> Dict[str, Any]:
        """Use LLM to generate plan."""
        provider = self.providers.get("openai") or next(iter(self.providers.values()), None)
        if not provider:
            raise ValueError("No LLM provider available for planning")
        
        prompt = PLANNING_PROMPT.format(query=query)
        
        result = await provider.complete(prompt, model=self.planning_model)
        content = getattr(result, 'content', '') or getattr(result, 'text', '')
        
        # Clean up JSON from potential markdown
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        return json.loads(content.strip())
    
    def _parse_plan_steps(self, plan_data: Dict[str, Any]) -> List[PlanStep]:
        """Parse plan data into PlanStep objects."""
        steps = []
        
        for step_data in plan_data.get("steps", []):
            try:
                role_str = step_data.get("role", "analyst").lower()
                role = PlanRole(role_str)
            except ValueError:
                role = PlanRole.ANALYST
            
            step = PlanStep(
                step_id=step_data.get("step_id", f"step_{len(steps)+1}"),
                description=step_data.get("description", ""),
                role=role,
                goal=step_data.get("goal", ""),
                inputs=step_data.get("inputs", []),
                expected_output=step_data.get("expected_output", ""),
                depends_on=step_data.get("depends_on", []),
                parallelizable=step_data.get("parallelizable", False),
            )
            steps.append(step)
        
        return steps
    
    def _identify_parallel_groups(self, steps: List[PlanStep]) -> List[List[str]]:
        """Identify groups of steps that can run in parallel."""
        groups = []
        remaining = set(step.step_id for step in steps)
        completed = set()
        
        while remaining:
            # Find steps whose dependencies are all completed
            current_group = []
            for step in steps:
                if step.step_id in remaining:
                    if all(dep in completed for dep in step.depends_on):
                        current_group.append(step.step_id)
            
            if not current_group:
                # No progress possible, add remaining as sequential
                current_group = list(remaining)
            
            groups.append(current_group)
            completed.update(current_group)
            remaining -= set(current_group)
        
        return groups
    
    def _select_model_for_role(self, role: PlanRole) -> str:
        """Select best available model for a role."""
        preferred = ROLE_MODEL_PREFERENCES.get(role, ["gpt-4o"])
        
        # Find first available model
        provider_models = {
            "openai": ["gpt-4o", "gpt-4o-mini"],
            "anthropic": ["claude-sonnet-4"],
            "gemini": ["gemini-2.5-pro"],
            "deepseek": ["deepseek-chat"],
        }
        
        available = []
        for provider_name, models in provider_models.items():
            if provider_name in self.providers:
                available.extend(models)
        
        for model in preferred:
            if model in available or any(m.startswith(model.split('-')[0]) for m in available):
                return model
        
        return available[0] if available else "gpt-4o"
    
    def _create_fallback_plan(self, query: str) -> ExecutionPlan:
        """Create a simple fallback plan when LLM planning fails."""
        step = PlanStep(
            step_id="step_1",
            description="Answer the query directly",
            role=PlanRole.ANALYST,
            goal="Provide a comprehensive answer",
            inputs=["User query"],
            expected_output="Complete answer",
            assigned_model="gpt-4o",
        )
        
        return ExecutionPlan(
            query=query,
            steps=[step],
            total_steps=1,
            parallelizable_groups=[["step_1"]],
            estimated_complexity="simple",
            planning_notes=["Fallback to simple single-step plan"],
        )


class HierarchicalPlanExecutor:
    """Executes hierarchical plans with role-based model routing."""
    
    def __init__(self, providers: Dict[str, Any]):
        """Initialize executor with providers."""
        self.providers = providers
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: Optional[str] = None,
    ) -> PlanResult:
        """Execute a plan and synthesize results.
        
        Args:
            plan: The execution plan
            context: Optional additional context
            
        Returns:
            PlanResult with synthesized answer
        """
        step_results: Dict[str, str] = {}
        synthesis_notes: List[str] = []
        
        # Check for single-step plan (fallback to normal execution)
        if plan.total_steps == 1:
            result = await self._execute_single_step(
                plan.steps[0], plan.query, context
            )
            return PlanResult(
                success=True,
                final_answer=result,
                steps_executed=1,
                steps_successful=1,
                step_results={plan.steps[0].step_id: result},
                synthesis_notes=["Single-step execution"],
            )
        
        # Execute groups in order (parallel within groups)
        for group in plan.parallelizable_groups:
            group_steps = [s for s in plan.steps if s.step_id in group]
            
            if len(group_steps) == 1:
                # Single step, execute directly
                step = group_steps[0]
                result = await self._execute_step(step, step_results, plan.query, context)
                step_results[step.step_id] = result
                step.result = result
                step.completed = True
            else:
                # Multiple steps, execute in parallel
                tasks = [
                    self._execute_step(step, step_results, plan.query, context)
                    for step in group_steps
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for step, result in zip(group_steps, results):
                    if isinstance(result, Exception):
                        step_results[step.step_id] = f"Error: {result}"
                        synthesis_notes.append(f"Step {step.step_id} failed: {result}")
                    else:
                        step_results[step.step_id] = result
                        step.result = result
                        step.completed = True
        
        # Synthesize final answer
        final_answer = await self._synthesize_results(
            plan, step_results, context
        )
        
        successful = sum(1 for s in plan.steps if s.completed)
        
        return PlanResult(
            success=successful == plan.total_steps,
            final_answer=final_answer,
            steps_executed=plan.total_steps,
            steps_successful=successful,
            step_results=step_results,
            synthesis_notes=synthesis_notes,
        )
    
    async def _execute_step(
        self,
        step: PlanStep,
        previous_results: Dict[str, str],
        query: str,
        context: Optional[str],
    ) -> str:
        """Execute a single step with context from previous steps."""
        # Build step context from dependencies
        step_context = f"Original query: {query}\n"
        
        if context:
            step_context += f"Context: {context}\n"
        
        if step.depends_on:
            step_context += "\nResults from previous steps:\n"
            for dep_id in step.depends_on:
                if dep_id in previous_results:
                    step_context += f"- {dep_id}: {previous_results[dep_id][:500]}\n"
        
        # Build step prompt
        prompt = f"""{step_context}

Your role: {step.role.value.title()}
Task: {step.description}
Goal: {step.goal}

Please complete this step and provide your output."""

        # Get appropriate provider
        model = step.assigned_model or "gpt-4o"
        provider = self._get_provider_for_model(model)
        
        if not provider:
            return f"Error: No provider for model {model}"
        
        try:
            result = await provider.complete(prompt, model=model)
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception as e:
            logger.error("Step execution failed: %s", e)
            return f"Error executing step: {e}"
    
    async def _execute_single_step(
        self,
        step: PlanStep,
        query: str,
        context: Optional[str],
    ) -> str:
        """Execute a single step directly (for simple plans)."""
        prompt = query
        if context:
            prompt = f"Context: {context}\n\nQuery: {query}"
        
        model = step.assigned_model or "gpt-4o"
        provider = self._get_provider_for_model(model)
        
        if not provider:
            raise ValueError(f"No provider for model {model}")
        
        result = await provider.complete(prompt, model=model)
        return getattr(result, 'content', '') or getattr(result, 'text', '')
    
    async def _synthesize_results(
        self,
        plan: ExecutionPlan,
        step_results: Dict[str, str],
        context: Optional[str],
    ) -> str:
        """Synthesize step results into final answer."""
        if len(step_results) == 1:
            return list(step_results.values())[0]
        
        # Build synthesis prompt
        synthesis_prompt = f"""Synthesize these results into a coherent final answer.

Original Query: {plan.query}

Step Results:
"""
        for step in plan.steps:
            if step.step_id in step_results:
                synthesis_prompt += f"\n--- {step.role.value.title()} ({step.description}) ---\n"
                synthesis_prompt += step_results[step.step_id][:1000] + "\n"
        
        synthesis_prompt += """
Based on all the above results, provide a comprehensive, well-organized final answer that:
1. Addresses the original query completely
2. Integrates insights from all steps
3. Is clear and well-structured

Final Answer:"""

        # Use synthesizer model
        provider = self.providers.get("openai") or next(iter(self.providers.values()))
        
        try:
            result = await provider.complete(synthesis_prompt, model="gpt-4o")
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            # Fallback: concatenate results
            return "\n\n".join(step_results.values())
    
    def _get_provider_for_model(self, model: str) -> Optional[Any]:
        """Get the appropriate provider for a model."""
        model_lower = model.lower()
        
        provider_map = {
            "gpt": "openai",
            "claude": "anthropic",
            "gemini": "gemini",
            "deepseek": "deepseek",
            "grok": "grok",
        }
        
        for prefix, provider_name in provider_map.items():
            if model_lower.startswith(prefix) and provider_name in self.providers:
                return self.providers[provider_name]
        
        # Return first available
        if self.providers:
            return next(iter(self.providers.values()))
        
        return None


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def plan_and_execute(
    query: str,
    providers: Dict[str, Any],
    complexity: Optional[str] = None,
    context: Optional[str] = None,
) -> PlanResult:
    """Convenience function to plan and execute a query.
    
    Args:
        query: User query
        providers: LLM providers
        complexity: Optional complexity hint
        context: Optional context
        
    Returns:
        PlanResult with final answer
    """
    planner = HierarchicalPlanner(providers)
    executor = HierarchicalPlanExecutor(providers)
    
    plan = await planner.create_plan(query, complexity)
    result = await executor.execute_plan(plan, context)
    
    return result


def should_use_hrm(
    complexity: str,
    task_type: str,
    query_length: int,
) -> bool:
    """Determine if HRM should be enabled for a query.
    
    Args:
        complexity: Detected complexity level
        task_type: Type of task
        query_length: Length of query in words
        
    Returns:
        True if HRM should be enabled
    """
    # Always use for complex/research queries
    if complexity in ["complex", "research"]:
        return True
    
    # Use for certain task types
    if task_type in ["research_analysis", "comparison", "planning"]:
        return True
    
    # Use for long queries (likely multi-part)
    if query_length > 50:
        return True
    
    return False
