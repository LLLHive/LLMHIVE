"""Enhanced MCP2 Planner with step verification, limits, and domain shards.

This module implements a robust planning system for multi-step tool operations:
1. Planner step verification
2. Global timeout and step limits
3. Domain-specific planner shards
4. Fallback strategies
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class PlannerConfig:
    """Configuration for the MCP2 planner."""
    
    # Step limits
    max_tool_invocations: int = 3  # Maximum tools per query
    max_planning_time_seconds: float = 20.0  # Total planning budget
    step_timeout_seconds: float = 10.0  # Timeout per step
    
    # Verification
    enable_step_verification: bool = True
    verification_confidence_threshold: float = 0.5
    
    # Fallback
    fallback_to_llm_on_failure: bool = True
    partial_result_threshold: int = 1  # Min steps before partial result is useful
    
    # Domain routing
    enable_domain_routing: bool = True


class PlannerDomain(str, Enum):
    """Domain categories for specialized planning."""
    SEARCH = "mcp_search"
    COMPUTE = "mcp_compute"
    CODE = "mcp_code"
    KNOWLEDGE = "mcp_knowledge"
    GENERAL = "mcp_general"


# =============================================================================
# Plan Data Structures
# =============================================================================

@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_id: str
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    expected_output_type: str = "text"
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 1


@dataclass
class StepResult:
    """Result of executing a plan step."""
    step_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    verified: bool = False
    verification_confidence: float = 0.0


@dataclass
class PlanResult:
    """Result of plan execution."""
    success: bool
    steps_completed: int
    steps_total: int
    results: List[StepResult]
    final_output: Any
    total_time_ms: float
    fallback_used: bool = False
    partial_result: bool = False
    domain: PlannerDomain = PlannerDomain.GENERAL


# =============================================================================
# Step Verification
# =============================================================================

class StepVerifier:
    """Verifies that plan steps achieved their intended results."""
    
    def __init__(self, config: PlannerConfig):
        """Initialize verifier.
        
        Args:
            config: Planner configuration
        """
        self.config = config
    
    def verify(
        self,
        step: PlanStep,
        result: StepResult,
        query_context: str,
    ) -> Tuple[bool, float, str]:
        """Verify that a step result is useful.
        
        Args:
            step: The executed step
            result: Step execution result
            query_context: Original query for context
            
        Returns:
            Tuple of (is_valid, confidence, reason)
        """
        if not self.config.enable_step_verification:
            return True, 1.0, "Verification disabled"
        
        if not result.success:
            return False, 0.0, f"Step failed: {result.error}"
        
        output = result.output
        
        # Check for empty or null results
        if output is None or output == "" or output == []:
            return False, 0.1, "Empty result"
        
        # Check for error indicators in text output
        if isinstance(output, str):
            error_indicators = [
                "error", "failed", "not found", "no results",
                "unavailable", "timeout", "exception",
            ]
            lower_output = output.lower()
            for indicator in error_indicators:
                if indicator in lower_output and len(output) < 100:
                    return False, 0.2, f"Result contains error indicator: {indicator}"
        
        # Check for type match
        if step.expected_output_type == "list" and not isinstance(output, (list, tuple)):
            return False, 0.3, "Expected list output"
        
        if step.expected_output_type == "dict" and not isinstance(output, dict):
            return False, 0.3, "Expected dict output"
        
        # Check for relevance to query context
        confidence = self._calculate_relevance(output, query_context, step.description)
        
        if confidence < self.config.verification_confidence_threshold:
            return False, confidence, "Low relevance to query"
        
        return True, confidence, "Verification passed"
    
    def _calculate_relevance(
        self,
        output: Any,
        query: str,
        step_description: str,
    ) -> float:
        """Calculate relevance score of output to query.
        
        Args:
            output: Step output
            query: Original query
            step_description: Step description
            
        Returns:
            Relevance score 0-1
        """
        # Simple term overlap heuristic
        query_terms = set(query.lower().split())
        step_terms = set(step_description.lower().split())
        
        output_str = str(output).lower() if output else ""
        output_terms = set(output_str.split())
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'must', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'and', 'or'}
        query_terms -= stopwords
        step_terms -= stopwords
        
        if not query_terms and not step_terms:
            return 0.5  # Default moderate confidence
        
        # Calculate overlap
        all_terms = query_terms | step_terms
        overlap = len(all_terms & output_terms)
        
        if not all_terms:
            return 0.5
        
        return min(1.0, overlap / len(all_terms) * 2)  # Scaled up


# =============================================================================
# Domain-Specific Planners
# =============================================================================

class DomainRouter:
    """Routes queries to specialized planner shards."""
    
    # Domain keywords for routing
    DOMAIN_KEYWORDS = {
        PlannerDomain.SEARCH: [
            "search", "find", "look up", "google", "news", "latest",
            "current", "recent", "information about", "what is",
        ],
        PlannerDomain.COMPUTE: [
            "calculate", "compute", "math", "sum", "average", "total",
            "percentage", "convert", "measure", "formula",
        ],
        PlannerDomain.CODE: [
            "code", "program", "script", "function", "algorithm",
            "implement", "debug", "run", "execute", "python",
        ],
        PlannerDomain.KNOWLEDGE: [
            "remember", "recall", "previous", "history", "stored",
            "saved", "my data", "my files", "documents",
        ],
    }
    
    @classmethod
    def route(cls, query: str) -> PlannerDomain:
        """Route query to appropriate domain planner.
        
        Args:
            query: User query
            
        Returns:
            Target domain
        """
        query_lower = query.lower()
        
        # Count keyword matches per domain
        scores = {domain: 0 for domain in PlannerDomain}
        
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[domain] += 1
        
        # Find highest scoring domain
        best_domain = PlannerDomain.GENERAL
        best_score = 0
        
        for domain, score in scores.items():
            if score > best_score:
                best_score = score
                best_domain = domain
        
        return best_domain


class DomainPlanner:
    """Base class for domain-specific planners."""
    
    def __init__(self, domain: PlannerDomain, config: PlannerConfig):
        """Initialize domain planner.
        
        Args:
            domain: Planner domain
            config: Planner configuration
        """
        self.domain = domain
        self.config = config
    
    def create_plan(
        self,
        query: str,
        available_tools: List[str],
    ) -> List[PlanStep]:
        """Create an execution plan for the query.
        
        Args:
            query: User query
            available_tools: Available tool names
            
        Returns:
            List of plan steps
        """
        # Default implementation - single step
        return [
            PlanStep(
                step_id="step_1",
                tool_name="web_search" if "web_search" in available_tools else available_tools[0] if available_tools else "",
                arguments={"query": query},
                description=f"Search for: {query}",
            )
        ]


class SearchDomainPlanner(DomainPlanner):
    """Specialized planner for search-related queries."""
    
    def create_plan(
        self,
        query: str,
        available_tools: List[str],
    ) -> List[PlanStep]:
        """Create search-focused plan."""
        steps = []
        
        # Primary search step
        if "web_search" in available_tools:
            steps.append(PlanStep(
                step_id="search_1",
                tool_name="web_search",
                arguments={"query": query},
                description=f"Web search: {query}",
                expected_output_type="list",
            ))
        
        # Knowledge lookup as backup/supplement
        if "knowledge_lookup" in available_tools:
            steps.append(PlanStep(
                step_id="search_2",
                tool_name="knowledge_lookup",
                arguments={"query": query},
                description=f"Knowledge base lookup: {query}",
                expected_output_type="list",
            ))
        
        return steps[:self.config.max_tool_invocations]


class ComputeDomainPlanner(DomainPlanner):
    """Specialized planner for computation queries."""
    
    def create_plan(
        self,
        query: str,
        available_tools: List[str],
    ) -> List[PlanStep]:
        """Create computation-focused plan."""
        steps = []
        
        # Calculator for math
        if "calculator" in available_tools:
            # Extract math expression from query if present
            import re
            math_expr = re.search(r'[\d\+\-\*\/\(\)\s\.]+', query)
            expr = math_expr.group(0) if math_expr else query
            
            steps.append(PlanStep(
                step_id="calc_1",
                tool_name="calculator",
                arguments={"expression": expr},
                description=f"Calculate: {expr}",
                expected_output_type="text",
            ))
        
        # Unit conversion
        if "convert" in available_tools and any(
            word in query.lower() for word in ["convert", "to", "from", "in"]
        ):
            steps.append(PlanStep(
                step_id="convert_1",
                tool_name="convert",
                arguments={"query": query},
                description=f"Convert: {query}",
                expected_output_type="text",
            ))
        
        return steps[:self.config.max_tool_invocations]


class CodeDomainPlanner(DomainPlanner):
    """Specialized planner for code execution queries."""
    
    def create_plan(
        self,
        query: str,
        available_tools: List[str],
    ) -> List[PlanStep]:
        """Create code-focused plan."""
        steps = []
        
        if "python_exec" in available_tools:
            steps.append(PlanStep(
                step_id="code_1",
                tool_name="python_exec",
                arguments={"code": query},
                description=f"Execute code",
                expected_output_type="text",
                max_retries=2,
            ))
        
        return steps[:self.config.max_tool_invocations]


# =============================================================================
# Main Planner
# =============================================================================

class MCP2Planner:
    """Enhanced MCP2 planner with verification and domain routing.
    
    Features:
    - Step verification after each tool call
    - Global timeout and step limits
    - Domain-specific planning strategies
    - Graceful fallback on failures
    """
    
    def __init__(
        self,
        config: Optional[PlannerConfig] = None,
        tool_executor: Optional[Callable] = None,
    ):
        """Initialize planner.
        
        Args:
            config: Planner configuration
            tool_executor: Async function to execute tools
        """
        self.config = config or PlannerConfig()
        self.tool_executor = tool_executor
        self.verifier = StepVerifier(self.config)
        
        # Domain planners
        self._domain_planners: Dict[PlannerDomain, DomainPlanner] = {
            PlannerDomain.SEARCH: SearchDomainPlanner(PlannerDomain.SEARCH, self.config),
            PlannerDomain.COMPUTE: ComputeDomainPlanner(PlannerDomain.COMPUTE, self.config),
            PlannerDomain.CODE: CodeDomainPlanner(PlannerDomain.CODE, self.config),
            PlannerDomain.KNOWLEDGE: DomainPlanner(PlannerDomain.KNOWLEDGE, self.config),
            PlannerDomain.GENERAL: DomainPlanner(PlannerDomain.GENERAL, self.config),
        }
    
    async def execute_plan(
        self,
        query: str,
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanResult:
        """Execute a plan for the given query.
        
        Args:
            query: User query
            available_tools: Available tool names
            context: Additional context
            
        Returns:
            Plan execution result
        """
        start_time = time.time()
        
        # Route to domain
        domain = PlannerDomain.GENERAL
        if self.config.enable_domain_routing:
            domain = DomainRouter.route(query)
            logger.debug("Query routed to domain: %s", domain.value)
        
        # Get domain planner and create plan
        planner = self._domain_planners.get(domain, self._domain_planners[PlannerDomain.GENERAL])
        steps = planner.create_plan(query, available_tools)
        
        if not steps:
            return PlanResult(
                success=False,
                steps_completed=0,
                steps_total=0,
                results=[],
                final_output=None,
                total_time_ms=0,
                fallback_used=True,
                domain=domain,
            )
        
        # Execute plan with limits
        results: List[StepResult] = []
        completed = 0
        final_output = None
        
        for i, step in enumerate(steps):
            # Check time budget
            elapsed = time.time() - start_time
            if elapsed > self.config.max_planning_time_seconds:
                logger.warning(
                    "Planning time budget exceeded (%.1fs > %.1fs)",
                    elapsed,
                    self.config.max_planning_time_seconds,
                )
                break
            
            # Check step limit
            if i >= self.config.max_tool_invocations:
                logger.info("Step limit reached (%d)", self.config.max_tool_invocations)
                break
            
            # Execute step
            result = await self._execute_step(step, query)
            results.append(result)
            
            # Verify step
            if result.success:
                is_valid, confidence, reason = self.verifier.verify(step, result, query)
                result.verified = is_valid
                result.verification_confidence = confidence
                
                if is_valid:
                    completed += 1
                    final_output = result.output
                else:
                    logger.info("Step verification failed: %s", reason)
                    
                    # Try alternative approach if available
                    if step.retry_count < step.max_retries:
                        step.retry_count += 1
                        retry_result = await self._execute_step(step, query)
                        if retry_result.success:
                            is_valid, confidence, _ = self.verifier.verify(step, retry_result, query)
                            if is_valid:
                                completed += 1
                                final_output = retry_result.output
                                results[-1] = retry_result
            else:
                logger.warning("Step execution failed: %s", result.error)
        
        total_time = (time.time() - start_time) * 1000
        
        # Determine success
        success = completed > 0
        partial = completed < len(steps) and completed >= self.config.partial_result_threshold
        
        # Fallback if nothing worked
        fallback_used = False
        if not success and self.config.fallback_to_llm_on_failure:
            fallback_used = True
            final_output = None  # Will trigger LLM fallback in caller
        
        return PlanResult(
            success=success,
            steps_completed=completed,
            steps_total=len(steps),
            results=results,
            final_output=final_output,
            total_time_ms=total_time,
            fallback_used=fallback_used,
            partial_result=partial,
            domain=domain,
        )
    
    async def _execute_step(
        self,
        step: PlanStep,
        query: str,
    ) -> StepResult:
        """Execute a single plan step.
        
        Args:
            step: Step to execute
            query: Original query for context
            
        Returns:
            Step execution result
        """
        start_time = time.time()
        
        if not self.tool_executor:
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                error="No tool executor configured",
            )
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.tool_executor(step.tool_name, step.arguments),
                timeout=self.config.step_timeout_seconds,
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Handle various result formats
            if isinstance(result, dict):
                success = result.get("success", True)
                output = result.get("result", result.get("output", result))
                error = result.get("error")
            else:
                success = result is not None
                output = result
                error = None
            
            return StepResult(
                step_id=step.step_id,
                success=success,
                output=output,
                error=error,
                execution_time_ms=execution_time,
            )
            
        except asyncio.TimeoutError:
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                error=f"Step timed out after {self.config.step_timeout_seconds}s",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )


# =============================================================================
# Factory Functions
# =============================================================================

_planner: Optional[MCP2Planner] = None


def get_planner(
    config: Optional[PlannerConfig] = None,
    tool_executor: Optional[Callable] = None,
) -> MCP2Planner:
    """Get or create the global planner instance.
    
    Args:
        config: Planner configuration
        tool_executor: Tool execution function
        
    Returns:
        MCP2Planner instance
    """
    global _planner
    
    if _planner is None:
        _planner = MCP2Planner(config=config, tool_executor=tool_executor)
    
    return _planner


def reset_planner() -> None:
    """Reset the global planner instance."""
    global _planner
    _planner = None

