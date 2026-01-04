"""Protocol Chaining Robustness for LLMHive Stage 4.

This module implements Section 13 of Stage 4 upgrades:
- Atomic chain execution with partial results
- DAG visualizer for complex tasks
"""
from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# CHAIN STEP DEFINITIONS
# ==============================================================================

class StepStatus(Enum):
    """Status of a chain step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ChainStep:
    """A single step in a protocol chain."""
    step_id: str
    name: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 2
    
    def duration_ms(self) -> Optional[float]:
        """Calculate step duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass
class ChainResult:
    """Result of a complete chain execution."""
    chain_id: str
    steps: List[ChainStep]
    final_result: Optional[Any]
    partial: bool
    failed_step: Optional[str]
    total_duration_ms: float
    warning: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# ATOMIC STEP EXECUTOR
# ==============================================================================

class AtomicStepExecutor:
    """Executes chain steps atomically with isolation.
    
    Each step runs in isolation - failures don't corrupt the chain.
    """
    
    def __init__(
        self,
        tool_registry: Optional[Dict[str, Callable]] = None,
        timeout_seconds: float = 30.0,
    ):
        self._tools = tool_registry or {}
        self._timeout = timeout_seconds
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool function."""
        self._tools[name] = func
    
    async def execute_step(
        self,
        step: ChainStep,
        context: Dict[str, Any],
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute a single step atomically.
        
        Args:
            step: The step to execute
            context: Execution context with results from previous steps
            
        Returns:
            Tuple of (success, result, error_message)
        """
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)
        
        try:
            # Get the tool function
            tool_func = self._tools.get(step.tool)
            if not tool_func:
                raise ValueError(f"Tool not found: {step.tool}")
            
            # Resolve parameter references from context
            resolved_params = self._resolve_params(step.parameters, context)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._run_tool(tool_func, resolved_params),
                timeout=self._timeout,
            )
            
            step.status = StepStatus.COMPLETED
            step.result = result
            step.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                "Step %s completed in %.1fms",
                step.step_id, step.duration_ms() or 0
            )
            
            return True, result, None
            
        except asyncio.TimeoutError:
            error = f"Step timed out after {self._timeout}s"
            step.status = StepStatus.FAILED
            step.error = error
            step.completed_at = datetime.now(timezone.utc)
            logger.warning("Step %s timed out", step.step_id)
            return False, None, error
            
        except Exception as e:
            error = str(e)
            step.status = StepStatus.FAILED
            step.error = error
            step.completed_at = datetime.now(timezone.utc)
            logger.warning("Step %s failed: %s", step.step_id, error)
            return False, None, error
    
    async def _run_tool(
        self,
        tool_func: Callable,
        params: Dict[str, Any],
    ) -> Any:
        """Run a tool function, handling sync and async."""
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(**params)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: tool_func(**params))
    
    def _resolve_params(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve parameter references from context."""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to previous step result
                ref = value[1:]  # Remove $
                if ref in context:
                    resolved[key] = context[ref]
                else:
                    resolved[key] = value  # Keep as-is if not found
            else:
                resolved[key] = value
        
        return resolved


# ==============================================================================
# CHAIN EXECUTOR WITH PARTIAL RESULTS
# ==============================================================================

class ChainExecutor:
    """Executes protocol chains with partial result support.
    
    Implements Stage 4 Section 13: Atomic chain execution.
    """
    
    def __init__(
        self,
        step_executor: Optional[AtomicStepExecutor] = None,
        continue_on_failure: bool = True,
    ):
        self._executor = step_executor or AtomicStepExecutor()
        self._continue_on_failure = continue_on_failure
    
    async def execute(
        self,
        chain_id: str,
        steps: List[ChainStep],
    ) -> ChainResult:
        """
        Execute a chain of steps with partial result handling.
        
        Args:
            chain_id: Unique chain identifier
            steps: Ordered list of steps to execute
            
        Returns:
            ChainResult with results and any partial data
        """
        start_time = datetime.now(timezone.utc)
        context: Dict[str, Any] = {}
        step_results: Dict[str, Any] = {}
        failed_step = None
        warning = None
        
        logger.info("Starting chain %s with %d steps", chain_id, len(steps))
        
        for step in steps:
            # Check if dependencies are satisfied
            if not self._check_dependencies(step, steps, context):
                step.status = StepStatus.SKIPPED
                logger.info("Skipping step %s - dependencies not met", step.step_id)
                continue
            
            # Execute step with retries
            success = False
            result = None
            error = None
            
            for attempt in range(step.max_retries + 1):
                step.retry_count = attempt
                success, result, error = await self._executor.execute_step(step, context)
                
                if success:
                    break
                elif attempt < step.max_retries:
                    logger.info("Retrying step %s (attempt %d)", step.step_id, attempt + 2)
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
            
            if success:
                context[step.step_id] = result
                step_results[step.step_id] = result
            else:
                failed_step = step.step_id
                
                if not self._continue_on_failure:
                    warning = f"Chain stopped at step '{step.name}': {error}"
                    break
                else:
                    warning = f"Step '{step.name}' failed but chain continued: {error}"
        
        # Calculate total duration
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Determine final result
        completed_steps = [s for s in steps if s.status == StepStatus.COMPLETED]
        final_result = None
        
        if completed_steps:
            # Use result from last completed step
            last_step = completed_steps[-1]
            final_result = last_step.result
        
        partial = failed_step is not None
        
        logger.info(
            "Chain %s completed in %.1fms (partial=%s, failed_step=%s)",
            chain_id, duration_ms, partial, failed_step
        )
        
        return ChainResult(
            chain_id=chain_id,
            steps=steps,
            final_result=final_result,
            partial=partial,
            failed_step=failed_step,
            total_duration_ms=duration_ms,
            warning=warning,
            step_results=step_results,
        )
    
    def _check_dependencies(
        self,
        step: ChainStep,
        all_steps: List[ChainStep],
        context: Dict[str, Any],
    ) -> bool:
        """Check if step dependencies are satisfied."""
        for dep_id in step.dependencies:
            # Check if dependency completed
            if dep_id not in context:
                return False
            
            # Check if dependency step actually completed
            dep_step = next((s for s in all_steps if s.step_id == dep_id), None)
            if dep_step and dep_step.status != StepStatus.COMPLETED:
                return False
        
        return True


# ==============================================================================
# DAG BUILDER AND VISUALIZER
# ==============================================================================

@dataclass
class DAGNode:
    """A node in the execution DAG."""
    node_id: str
    label: str
    step: Optional[ChainStep] = None
    status: StepStatus = StepStatus.PENDING


@dataclass
class DAGEdge:
    """An edge in the execution DAG."""
    from_node: str
    to_node: str
    label: Optional[str] = None


class DAGBuilder:
    """Builds a DAG representation from chain steps."""
    
    def build(self, steps: List[ChainStep]) -> Tuple[List[DAGNode], List[DAGEdge]]:
        """
        Build a DAG from chain steps.
        
        Args:
            steps: List of chain steps
            
        Returns:
            Tuple of (nodes, edges)
        """
        nodes = []
        edges = []
        
        # Create nodes
        for step in steps:
            node = DAGNode(
                node_id=step.step_id,
                label=step.name,
                step=step,
                status=step.status,
            )
            nodes.append(node)
        
        # Create edges from dependencies
        for step in steps:
            for dep_id in step.dependencies:
                edge = DAGEdge(
                    from_node=dep_id,
                    to_node=step.step_id,
                )
                edges.append(edge)
        
        return nodes, edges


class DAGVisualizer:
    """Visualizes execution DAGs.
    
    Implements Stage 4 Section 13: DAG visualizer for complex tasks.
    """
    
    def __init__(self, dag_builder: Optional[DAGBuilder] = None):
        self._builder = dag_builder or DAGBuilder()
    
    def visualize_to_dot(self, steps: List[ChainStep]) -> str:
        """
        Generate Graphviz DOT format visualization.
        
        Args:
            steps: List of chain steps
            
        Returns:
            DOT format string
        """
        nodes, edges = self._builder.build(steps)
        
        lines = [
            "digraph ExecutionPlan {",
            "    rankdir=TB;",
            "    node [shape=box, style=filled];",
            "",
        ]
        
        # Add nodes with status colors
        for node in nodes:
            color = self._status_color(node.status)
            label = f"{node.label}\\n({node.node_id})"
            lines.append(f'    "{node.node_id}" [label="{label}", fillcolor="{color}"];')
        
        lines.append("")
        
        # Add edges
        for edge in edges:
            label = f'label="{edge.label}"' if edge.label else ""
            lines.append(f'    "{edge.from_node}" -> "{edge.to_node}" [{label}];')
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def visualize_to_ascii(self, steps: List[ChainStep]) -> str:
        """
        Generate ASCII art visualization.
        
        Args:
            steps: List of chain steps
            
        Returns:
            ASCII art string
        """
        if not steps:
            return "(empty chain)"
        
        lines = ["Chain Execution Flow:", "=" * 40, ""]
        
        # Build adjacency list
        deps = {s.step_id: s.dependencies for s in steps}
        step_map = {s.step_id: s for s in steps}
        
        # Find roots (no dependencies)
        roots = [s.step_id for s in steps if not s.dependencies]
        
        # BFS to build levels
        levels: List[List[str]] = []
        visited: Set[str] = set()
        current_level = roots
        
        while current_level:
            levels.append(current_level)
            visited.update(current_level)
            
            next_level = []
            for step in steps:
                step_id = step.step_id
                if step_id not in visited:
                    if all(d in visited for d in step.dependencies):
                        next_level.append(step_id)
            
            # Deduplicate
            current_level = [sid for sid in next_level if sid not in visited]
        
        # Render levels
        for i, level in enumerate(levels):
            level_str = " | ".join(f"[{step_map[sid].name}]" for sid in level if sid in step_map)
            lines.append(f"Level {i + 1}: {level_str}")
            
            if i < len(levels) - 1:
                lines.append("      ↓")
        
        lines.append("")
        lines.append("=" * 40)
        
        # Status summary
        lines.append("Status:")
        for step in steps:
            status_icon = {
                StepStatus.PENDING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
            }.get(step.status, "?")
            lines.append(f"  {status_icon} {step.name}")
        
        return "\n".join(lines)
    
    def visualize_to_json(self, steps: List[ChainStep]) -> str:
        """
        Generate JSON format visualization data.
        
        Args:
            steps: List of chain steps
            
        Returns:
            JSON string
        """
        nodes, edges = self._builder.build(steps)
        
        data = {
            "nodes": [
                {
                    "id": n.node_id,
                    "label": n.label,
                    "status": n.status.value,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "from": e.from_node,
                    "to": e.to_node,
                    "label": e.label,
                }
                for e in edges
            ],
        }
        
        return json.dumps(data, indent=2)
    
    def _status_color(self, status: StepStatus) -> str:
        """Get Graphviz color for status."""
        return {
            StepStatus.PENDING: "white",
            StepStatus.RUNNING: "yellow",
            StepStatus.COMPLETED: "lightgreen",
            StepStatus.FAILED: "lightcoral",
            StepStatus.SKIPPED: "lightgray",
        }.get(status, "white")


# ==============================================================================
# CHAIN PLANNER
# ==============================================================================

class ChainPlanner:
    """Plans execution chains from task descriptions.
    
    Analyzes queries to build appropriate execution plans.
    
    Production Safeguards:
    - max_steps: Limits total steps to prevent runaway planning
    - max_fanout: Limits parallel branches to prevent unbounded fan-out
    - max_depth: Limits chain depth to prevent infinite recursion
    """
    
    # Safety limits
    MAX_STEPS = 20  # Maximum total steps in a plan
    MAX_FANOUT = 5  # Maximum parallel branches
    MAX_DEPTH = 8   # Maximum dependency chain depth
    MAX_PLAN_TIME_SECONDS = 5.0  # Maximum time for planning
    
    def __init__(
        self,
        available_tools: Optional[List[str]] = None,
        max_steps: int = MAX_STEPS,
        max_fanout: int = MAX_FANOUT,
        max_depth: int = MAX_DEPTH,
    ):
        self._tools = available_tools or [
            "search", "calculate", "database_query",
            "summarize", "translate", "analyze",
        ]
        self._max_steps = min(max_steps, self.MAX_STEPS)
        self._max_fanout = min(max_fanout, self.MAX_FANOUT)
        self._max_depth = min(max_depth, self.MAX_DEPTH)
    
    def plan(self, task: str) -> List[ChainStep]:
        """
        Create an execution plan from a task description.
        
        Args:
            task: Task description
            
        Returns:
            List of ChainStep objects forming the plan
        """
        steps = []
        task_lower = task.lower()
        
        # Simple heuristic planning
        # In a real system, this would use an LLM
        
        step_idx = 0
        
        # Check for search-related keywords
        if any(kw in task_lower for kw in ["find", "search", "look up"]):
            steps.append(ChainStep(
                step_id=f"step_{step_idx}",
                name="Search",
                tool="search",
                parameters={"query": task},
            ))
            step_idx += 1
        
        # Check for calculation keywords
        if any(kw in task_lower for kw in ["calculate", "compute", "sum", "average"]):
            step = ChainStep(
                step_id=f"step_{step_idx}",
                name="Calculate",
                tool="calculate",
                parameters={"expression": task},
            )
            if steps:
                step.dependencies = [steps[-1].step_id]
            steps.append(step)
            step_idx += 1
        
        # Check for summary keywords
        if any(kw in task_lower for kw in ["summarize", "summary", "overview"]):
            step = ChainStep(
                step_id=f"step_{step_idx}",
                name="Summarize",
                tool="summarize",
                parameters={"text": f"$step_{step_idx - 1}" if steps else task},
            )
            if steps:
                step.dependencies = [steps[-1].step_id]
            steps.append(step)
            step_idx += 1
        
        # Default: just run analysis
        if not steps:
            steps.append(ChainStep(
                step_id="step_0",
                name="Analyze",
                tool="analyze",
                parameters={"input": task},
            ))
        
        # Apply safety limits
        steps = self._apply_safety_limits(steps)
        
        return steps
    
    def _apply_safety_limits(self, steps: List[ChainStep]) -> List[ChainStep]:
        """Apply safety limits to the plan."""
        # Limit total steps
        if len(steps) > self._max_steps:
            logger.warning(
                "Plan truncated from %d to %d steps (max_steps limit)",
                len(steps), self._max_steps
            )
            steps = steps[:self._max_steps]
        
        # Check and limit fanout
        self._check_fanout(steps)
        
        # Check depth
        self._check_depth(steps)
        
        return steps
    
    def _check_fanout(self, steps: List[ChainStep]) -> None:
        """Check and warn about excessive fanout."""
        # Count steps at each dependency level
        dep_counts: Dict[str, int] = {}
        for step in steps:
            for dep in step.dependencies:
                dep_counts[dep] = dep_counts.get(dep, 0) + 1
        
        # Check for excessive fanout
        for dep, count in dep_counts.items():
            if count > self._max_fanout:
                logger.warning(
                    "Step %s has %d dependents (max_fanout=%d)",
                    dep, count, self._max_fanout
                )
    
    def _check_depth(self, steps: List[ChainStep]) -> None:
        """Check for excessive chain depth."""
        step_map = {s.step_id: s for s in steps}
        
        def get_depth(step_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            
            if step_id in visited:
                # Circular dependency detected
                logger.error("Circular dependency detected at step %s", step_id)
                return float('inf')
            
            step = step_map.get(step_id)
            if not step or not step.dependencies:
                return 1
            
            visited.add(step_id)
            max_dep_depth = max(
                get_depth(dep, visited.copy()) 
                for dep in step.dependencies
            )
            return 1 + max_dep_depth
        
        max_depth = 0
        for step in steps:
            depth = get_depth(step.step_id)
            max_depth = max(max_depth, depth)
        
        if max_depth > self._max_depth:
            logger.warning(
                "Chain depth %d exceeds max_depth %d",
                max_depth, self._max_depth
            )


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================

def create_step_executor(
    tool_registry: Optional[Dict[str, Callable]] = None,
    timeout_seconds: float = 30.0,
) -> AtomicStepExecutor:
    """Create an atomic step executor."""
    return AtomicStepExecutor(tool_registry, timeout_seconds)


def create_chain_executor(
    continue_on_failure: bool = True,
) -> ChainExecutor:
    """Create a chain executor."""
    return ChainExecutor(continue_on_failure=continue_on_failure)


def create_dag_visualizer() -> DAGVisualizer:
    """Create a DAG visualizer."""
    return DAGVisualizer()


def create_chain_planner(tools: Optional[List[str]] = None) -> ChainPlanner:
    """Create a chain planner."""
    return ChainPlanner(available_tools=tools)

