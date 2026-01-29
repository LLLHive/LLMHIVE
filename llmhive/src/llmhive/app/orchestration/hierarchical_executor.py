"""Hierarchical Plan Executor for Multi-Step Reasoning.

This module implements the actual step-by-step execution of hierarchical plans
created by the HRM planner. It:
1. Executes each step in proper dependency order
2. Routes each step to appropriate specialist models
3. Maintains a shared blackboard for intermediate results
4. Has a final synthesis step where the coordinator merges all outputs

This enables true multi-agent reasoning chains for complex queries.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .hierarchical_planning import (
    HierarchicalPlan,
    HierarchicalPlanStep,
    HierarchicalRole,
    TaskComplexity,
)
from .hrm import RoleLevel, get_hrm_registry

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class StepStatus(str, Enum):
    """Status of a plan step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(str, Enum):
    """Mode of plan execution."""
    SEQUENTIAL = "sequential"  # Execute steps one by one
    PARALLEL_SAFE = "parallel_safe"  # Parallelize independent steps
    FULL_PARALLEL = "full_parallel"  # Maximum parallelization


# ==============================================================================
# HRM Blackboard (Shared Memory for Inter-Step Communication)
# ==============================================================================

def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    from datetime import timezone
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class HRMBlackboardEntry:
    """An entry in the HRM blackboard."""
    step_id: str
    role_name: str
    content: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    tokens_used: int = 0


class HRMBlackboard:
    """Shared blackboard for inter-step communication.
    
    The blackboard serves as a shared memory space where:
    - Each step can write its outputs
    - Subsequent steps can read outputs from dependencies
    - The coordinator can access all outputs for synthesis
    """
    
    def __init__(self):
        self._entries: Dict[str, BlackboardEntry] = {}
        self._step_outputs: Dict[str, str] = {}
        self._context_chain: List[str] = []
        self._metadata: Dict[str, Any] = {}
    
    def write(
        self,
        step_id: str,
        role_name: str,
        content: str,
        *,
        confidence: float = 1.0,
        tokens_used: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write step output to the blackboard."""
        entry = HRMBlackboardEntry(
            step_id=step_id,
            role_name=role_name,
            content=content,
            confidence=confidence,
            tokens_used=tokens_used,
            metadata=metadata or {},
        )
        self._entries[step_id] = entry
        self._step_outputs[step_id] = content
        self._context_chain.append(f"[{role_name}] {content[:200]}...")
        
        logger.debug("Blackboard: Wrote entry for step %s (role: %s)", step_id, role_name)
    
    def read(self, step_id: str) -> Optional[HRMBlackboardEntry]:
        """Read a specific step's output."""
        return self._entries.get(step_id)
    
    def read_output(self, step_id: str) -> Optional[str]:
        """Read just the content output of a step."""
        return self._step_outputs.get(step_id)
    
    def read_dependencies(self, step_ids: List[str]) -> List[HRMBlackboardEntry]:
        """Read outputs from multiple dependency steps."""
        return [
            self._entries[sid]
            for sid in step_ids
            if sid in self._entries
        ]
    
    def get_context_for_step(
        self,
        step: HierarchicalPlanStep,
        max_context_length: int = 4000,
    ) -> str:
        """Build context string for a step from its dependencies."""
        if not step.dependencies:
            return ""
        
        context_parts = ["=== Context from Previous Steps ===\n"]
        total_length = 0
        
        for dep_id in step.dependencies:
            entry = self._entries.get(dep_id)
            if entry:
                part = f"\n[{entry.role_name} Output]:\n{entry.content}\n"
                if total_length + len(part) > max_context_length:
                    # Truncate if too long
                    remaining = max_context_length - total_length - 50
                    if remaining > 100:
                        part = f"\n[{entry.role_name} Output (truncated)]:\n{entry.content[:remaining]}...\n"
                    else:
                        break
                context_parts.append(part)
                total_length += len(part)
        
        context_parts.append("\n=== End Context ===\n")
        return "".join(context_parts)
    
    def get_all_outputs(self) -> Dict[str, str]:
        """Get all step outputs."""
        return dict(self._step_outputs)
    
    def get_synthesis_context(self) -> str:
        """Get full context for the synthesis step."""
        if not self._entries:
            return ""
        
        parts = ["=== All Step Outputs for Synthesis ===\n"]
        
        # Sort by timestamp
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: e.timestamp
        )
        
        for entry in sorted_entries:
            parts.append(f"\n## {entry.role_name.upper()} ({entry.step_id})\n")
            parts.append(f"{entry.content}\n")
            if entry.confidence < 1.0:
                parts.append(f"[Confidence: {entry.confidence:.2f}]\n")
        
        parts.append("\n=== End All Outputs ===\n")
        return "".join(parts)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of blackboard contents."""
        return {
            "total_entries": len(self._entries),
            "total_tokens": sum(e.tokens_used for e in self._entries.values()),
            "avg_confidence": (
                sum(e.confidence for e in self._entries.values()) / len(self._entries)
                if self._entries else 0.0
            ),
            "roles_involved": list(set(e.role_name for e in self._entries.values())),
        }
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set execution metadata."""
        self._metadata[key] = value
    
    def get_metadata(self, key: str) -> Any:
        """Get execution metadata."""
        return self._metadata.get(key)


# ==============================================================================
# Step Result
# ==============================================================================

@dataclass(slots=True)
class StepResult:
    """Result of executing a single step."""
    step_id: str
    role_name: str
    status: StepStatus
    output: str
    model_used: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    confidence: float = 1.0


@dataclass(slots=True)
class ExecutionResult:
    """Result of executing the entire hierarchical plan."""
    final_answer: str
    final_model: str
    step_results: List[StepResult]
    blackboard: HRMBlackboard
    total_tokens: int
    total_latency_ms: float
    strategy: str
    complexity: TaskComplexity
    success: bool
    transparency_notes: List[str] = field(default_factory=list)
    
    @property
    def steps_completed(self) -> int:
        return sum(1 for r in self.step_results if r.status == StepStatus.COMPLETED)
    
    @property
    def steps_failed(self) -> int:
        return sum(1 for r in self.step_results if r.status == StepStatus.FAILED)


# ==============================================================================
# Role-to-Model Mapping
# ==============================================================================

# Default model preferences by role level
DEFAULT_ROLE_MODELS = {
    RoleLevel.EXECUTIVE: ["gpt-4o", "claude-3-opus", "gpt-4"],
    RoleLevel.MANAGER: ["gpt-4o", "claude-3-sonnet", "gpt-4o-mini"],
    RoleLevel.SPECIALIST: ["claude-3-sonnet", "gpt-4o-mini", "gemini-2.5-flash"],
    RoleLevel.ASSISTANT: ["gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash"],
}

# Capability-based model preferences
CAPABILITY_MODELS = {
    "synthesis": ["gpt-4o", "claude-3-opus", "claude-3-sonnet"],
    "analysis": ["gpt-4o", "claude-3-sonnet", "gemini-2.5-pro"],
    "research": ["gemini-2.5-flash", "claude-3-sonnet", "gpt-4o-mini"],
    "retrieval": ["gpt-4o-mini", "gemini-1.5-flash", "claude-3-haiku"],
    "critical_thinking": ["deepseek-reasoner", "grok-3-mini", "claude-3-opus"],
    "validation": ["gpt-4o-mini", "deepseek-chat", "claude-3-haiku"],
    "coordination": ["gpt-4o", "claude-3-sonnet", "gpt-4"],
    "fact_checking": ["gpt-4o-mini", "deepseek-chat", "claude-3-haiku"],
}


# ==============================================================================
# Hierarchical Plan Executor
# ==============================================================================

class HierarchicalPlanExecutor:
    """Executes hierarchical plans step by step.
    
    This executor:
    1. Takes a HierarchicalPlan from the planner
    2. Executes each step in dependency order
    3. Routes each step to appropriate specialist models
    4. Maintains a blackboard for intermediate results
    5. Synthesizes final answer from all step outputs
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        *,
        model_assignments: Optional[Dict[str, str]] = None,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        max_retries: int = 2,
        timeout_per_step: float = 60.0,
    ):
        """
        Initialize the executor.
        
        Args:
            providers: Dict of provider_name -> provider instance
            model_assignments: Optional custom role -> model mapping
            execution_mode: How to parallelize execution
            max_retries: Max retries per step on failure
            timeout_per_step: Timeout in seconds per step
        """
        self.providers = providers
        self.model_assignments = model_assignments or {}
        self.execution_mode = execution_mode
        self.max_retries = max_retries
        self.timeout_per_step = timeout_per_step
        
        self._available_models = list(providers.keys())
    
    async def execute(
        self,
        plan: HierarchicalPlan,
        *,
        context: Optional[str] = None,
        accuracy_level: int = 3,
    ) -> ExecutionResult:
        """
        Execute a hierarchical plan.
        
        Args:
            plan: The hierarchical plan to execute
            context: Optional context (e.g., from memory)
            accuracy_level: 1-5 accuracy level
            
        Returns:
            ExecutionResult with final answer and step results
        """
        start_time = time.time()
        blackboard = HRMBlackboard()
        step_results: List[StepResult] = []
        transparency_notes: List[str] = []
        
        # Set execution metadata
        blackboard.set_metadata("original_query", plan.original_query)
        blackboard.set_metadata("strategy", plan.strategy)
        blackboard.set_metadata("complexity", plan.complexity.value)
        
        logger.info(
            "Starting hierarchical execution: %d steps, strategy=%s, complexity=%s",
            len(plan.steps),
            plan.strategy,
            plan.complexity.value,
        )
        transparency_notes.append(
            f"Hierarchical plan: {len(plan.steps)} steps, {plan.strategy} strategy"
        )
        
        # Get execution order (respects dependencies)
        ordered_steps = plan.get_execution_order()
        
        if not ordered_steps:
            logger.warning("No steps to execute in plan")
            return ExecutionResult(
                final_answer="Unable to process: plan has no executable steps",
                final_model="none",
                step_results=[],
                blackboard=blackboard,
                total_tokens=0,
                total_latency_ms=0,
                strategy=plan.strategy,
                complexity=plan.complexity,
                success=False,
            )
        
        # Execute steps
        for i, step in enumerate(ordered_steps):
            logger.info(
                "Executing step %d/%d: %s (role: %s)",
                i + 1,
                len(ordered_steps),
                step.step_id,
                step.role.name,
            )
            
            # Build context from dependencies
            step_context = blackboard.get_context_for_step(step)
            full_context = ""
            if context:
                full_context += f"=== Background Context ===\n{context}\n\n"
            if step_context:
                full_context += step_context
            
            # Execute the step
            result = await self._execute_step(
                step,
                context=full_context,
                accuracy_level=accuracy_level,
            )
            step_results.append(result)
            
            if result.status == StepStatus.COMPLETED:
                # Write to blackboard
                blackboard.write(
                    step_id=step.step_id,
                    role_name=step.role.name,
                    content=result.output,
                    confidence=result.confidence,
                    tokens_used=result.tokens_used,
                )
                
                transparency_notes.append(
                    f"Step {i+1} ({step.role.name}): completed with {result.model_used}"
                )
            else:
                logger.warning(
                    "Step %s failed: %s",
                    step.step_id,
                    result.error,
                )
                transparency_notes.append(
                    f"Step {i+1} ({step.role.name}): failed - {result.error}"
                )
        
        # Synthesize final answer
        final_answer, synthesis_model, synthesis_tokens = await self._synthesize(
            plan=plan,
            blackboard=blackboard,
            step_results=step_results,
            accuracy_level=accuracy_level,
        )
        
        total_latency = (time.time() - start_time) * 1000
        total_tokens = sum(r.tokens_used for r in step_results) + synthesis_tokens
        
        success = all(r.status == StepStatus.COMPLETED for r in step_results)
        
        transparency_notes.append(
            f"Final synthesis by {synthesis_model}: {total_tokens} total tokens"
        )
        
        logger.info(
            "Hierarchical execution complete: %d/%d steps successful, %d tokens, %.1fms",
            sum(1 for r in step_results if r.status == StepStatus.COMPLETED),
            len(step_results),
            total_tokens,
            total_latency,
        )
        
        return ExecutionResult(
            final_answer=final_answer,
            final_model=synthesis_model,
            step_results=step_results,
            blackboard=blackboard,
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            strategy=plan.strategy,
            complexity=plan.complexity,
            success=success,
            transparency_notes=transparency_notes,
        )
    
    async def _execute_step(
        self,
        step: HierarchicalPlanStep,
        *,
        context: str = "",
        accuracy_level: int = 3,
    ) -> StepResult:
        """Execute a single step."""
        start_time = time.time()
        
        # Select model for this step
        model = self._select_model_for_role(step.role, accuracy_level)
        
        # Build prompt for this step
        prompt = self._build_step_prompt(step, context)
        
        # Execute with retries
        for attempt in range(self.max_retries + 1):
            try:
                output, tokens = await self._invoke_model(model, prompt)
                
                latency = (time.time() - start_time) * 1000
                
                return StepResult(
                    step_id=step.step_id,
                    role_name=step.role.name,
                    status=StepStatus.COMPLETED,
                    output=output,
                    model_used=model,
                    tokens_used=tokens,
                    latency_ms=latency,
                    confidence=0.9 if attempt == 0 else 0.8,
                )
                
            except asyncio.TimeoutError:
                if attempt == self.max_retries:
                    return StepResult(
                        step_id=step.step_id,
                        role_name=step.role.name,
                        status=StepStatus.FAILED,
                        output="",
                        model_used=model,
                        error=f"Timeout after {self.timeout_per_step}s",
                    )
                logger.warning("Step %s timed out, retrying...", step.step_id)
                
            except Exception as e:
                if attempt == self.max_retries:
                    return StepResult(
                        step_id=step.step_id,
                        role_name=step.role.name,
                        status=StepStatus.FAILED,
                        output="",
                        model_used=model,
                        error=str(e),
                    )
                logger.warning("Step %s failed: %s, retrying...", step.step_id, e)
        
        return StepResult(
            step_id=step.step_id,
            role_name=step.role.name,
            status=StepStatus.FAILED,
            output="",
            model_used=model,
            error="Max retries exceeded",
        )
    
    def _select_model_for_role(
        self,
        role: HierarchicalRole,
        accuracy_level: int,
    ) -> str:
        """Select the best model for a role."""
        # Check for explicit assignment
        if role.assigned_model:
            if role.assigned_model in self._available_models:
                return role.assigned_model
        
        # Check custom model assignments
        if role.name in self.model_assignments:
            return self.model_assignments[role.name]
        
        # Check level-based defaults
        level_models = DEFAULT_ROLE_MODELS.get(role.level, [])
        for model in level_models:
            # Match model names flexibly
            for available in self._available_models:
                if model.lower() in available.lower() or available.lower() in model.lower():
                    return available
        
        # Check capability-based defaults
        for capability in role.required_capabilities:
            cap_models = CAPABILITY_MODELS.get(capability, [])
            for model in cap_models:
                for available in self._available_models:
                    if model.lower() in available.lower():
                        return available
        
        # Fallback to first available
        if self._available_models:
            return self._available_models[0]
        
        # NEVER return stub - use a real model
        return "openai/gpt-4o-mini"
    
    def _build_step_prompt(
        self,
        step: HierarchicalPlanStep,
        context: str = "",
    ) -> str:
        """Build the prompt for a step."""
        parts = []
        
        # Role instruction
        parts.append(f"You are acting as a {step.role.name.replace('_', ' ').title()}.")
        parts.append(f"Role: {step.role.description}")
        parts.append("")
        
        # Context from previous steps
        if context:
            parts.append(context)
            parts.append("")
        
        # The task
        parts.append("=== Your Task ===")
        parts.append(step.query)
        parts.append("")
        
        # Instructions based on role type
        if step.is_coordinator:
            parts.append("As a coordinator, your job is to break down the problem and identify key aspects to address.")
            parts.append("Provide a structured analysis that can guide specialists.")
        elif step.role.level == RoleLevel.SPECIALIST:
            parts.append("As a specialist, provide detailed, expert-level analysis on your assigned aspect.")
            parts.append("Be thorough and cite evidence where possible.")
        elif step.role.level == RoleLevel.ASSISTANT:
            parts.append("As an assistant, gather supporting information and summarize key points.")
            parts.append("Be concise but comprehensive.")
        elif step.role.level == RoleLevel.EXECUTIVE:
            if "synthesis" in step.role.name.lower():
                parts.append("Synthesize all the information provided into a coherent, comprehensive final response.")
                parts.append("Ensure the response addresses the original query fully.")
            else:
                parts.append("Provide strategic guidance and make key decisions.")
        
        parts.append("")
        parts.append("Provide your response now:")
        
        return "\n".join(parts)
    
    async def _invoke_model(
        self,
        model: str,
        prompt: str,
    ) -> Tuple[str, int]:
        """Invoke a model and return (output, tokens)."""
        # Map model to provider
        provider = None
        model_lower = model.lower()
        
        if "gpt" in model_lower or "openai" in model_lower:
            provider = self.providers.get("openai")
        elif "claude" in model_lower or "anthropic" in model_lower:
            provider = self.providers.get("anthropic")
        elif "grok" in model_lower:
            provider = self.providers.get("grok")
        elif "gemini" in model_lower:
            provider = self.providers.get("gemini")
        elif "deepseek" in model_lower:
            provider = self.providers.get("deepseek")
        else:
            # Try direct match
            provider = self.providers.get(model)
        
        if not provider:
            # Try openrouter first (NEVER stub), then first available
            provider = self.providers.get("openrouter") or next((p for n, p in self.providers.items() if n != "stub"), None)
        
        if not provider:
            raise ValueError(f"No provider available for model: {model}")
        
        # Invoke with timeout
        try:
            if hasattr(provider, 'generate'):
                import inspect
                if inspect.iscoroutinefunction(provider.generate):
                    result = await asyncio.wait_for(
                        provider.generate(prompt, model=model),
                        timeout=self.timeout_per_step,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(provider.generate, prompt, model=model),
                        timeout=self.timeout_per_step,
                    )
            elif hasattr(provider, 'complete'):
                import inspect
                if inspect.iscoroutinefunction(provider.complete):
                    result = await asyncio.wait_for(
                        provider.complete(prompt, model=model),
                        timeout=self.timeout_per_step,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(provider.complete, prompt, model=model),
                        timeout=self.timeout_per_step,
                    )
            else:
                # Stub response
                result = f"[{model}] Processed: {prompt[:100]}..."
            
            # Extract content and tokens
            if hasattr(result, 'content'):
                content = result.content
            elif hasattr(result, 'text'):
                content = result.text
            elif isinstance(result, str):
                content = result
            else:
                content = str(result)
            
            tokens = getattr(result, 'tokens_used', 0) or getattr(result, 'tokens', 0) or len(prompt.split()) // 2
            
            return content, tokens
            
        except Exception as e:
            logger.error("Model invocation failed for %s: %s", model, e)
            raise
    
    async def _synthesize(
        self,
        plan: HierarchicalPlan,
        blackboard: Blackboard,
        step_results: List[StepResult],
        accuracy_level: int,
    ) -> Tuple[str, str, int]:
        """Synthesize final answer from all step outputs."""
        # Get synthesis context
        synthesis_context = blackboard.get_synthesis_context()
        
        # If no successful steps, return error
        successful_outputs = [r for r in step_results if r.status == StepStatus.COMPLETED]
        if not successful_outputs:
            return (
                "Unable to generate a complete response due to execution failures.",
                "synthesis_fallback",
                0,
            )
        
        # If only one step and it's complete, use its output directly
        if len(successful_outputs) == 1 and plan.complexity == TaskComplexity.SIMPLE:
            return (
                successful_outputs[0].output,
                successful_outputs[0].model_used,
                0,
            )
        
        # Build synthesis prompt
        synthesis_prompt = f"""You are the Executive Synthesizer responsible for combining all specialist outputs into a final, coherent response.

=== Original Query ===
{plan.original_query}

{synthesis_context}

=== Your Task ===
Synthesize all the above specialist outputs into a single, comprehensive, well-organized response that:
1. Directly addresses the original query
2. Integrates insights from all specialists coherently
3. Resolves any contradictions between specialists
4. Provides a clear, actionable conclusion
5. Is written in a clear, professional tone

Provide your synthesized response now:"""
        
        # Select synthesis model (use executive level)
        executive_role = HierarchicalRole(
            name="executive_synthesizer",
            level=RoleLevel.EXECUTIVE,
            description="Final synthesis and integration",
            required_capabilities={"synthesis", "reasoning", "decision_making"},
        )
        synthesis_model = self._select_model_for_role(executive_role, accuracy_level)
        
        try:
            output, tokens = await self._invoke_model(synthesis_model, synthesis_prompt)
            return output, synthesis_model, tokens
        except Exception as e:
            logger.error("Synthesis failed: %s, using fallback", e)
            # Fallback: concatenate outputs
            fallback = "\n\n---\n\n".join(
                f"[{r.role_name}]\n{r.output}" for r in successful_outputs
            )
            return fallback, "synthesis_fallback", 0


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def execute_hierarchical_plan(
    plan: HierarchicalPlan,
    providers: Dict[str, Any],
    *,
    context: Optional[str] = None,
    accuracy_level: int = 3,
    model_assignments: Optional[Dict[str, str]] = None,
) -> ExecutionResult:
    """
    Execute a hierarchical plan with the given providers.
    
    Args:
        plan: The hierarchical plan to execute
        providers: Dict of provider instances
        context: Optional memory/background context
        accuracy_level: 1-5 accuracy level
        model_assignments: Custom role -> model mapping
        
    Returns:
        ExecutionResult with final answer and step details
    """
    executor = HierarchicalPlanExecutor(
        providers=providers,
        model_assignments=model_assignments or {},
    )
    
    return await executor.execute(
        plan,
        context=context,
        accuracy_level=accuracy_level,
    )

