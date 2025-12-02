"""Meta-Orchestrator - Coordinates multiple orchestrator instances.

The Meta-Orchestrator is the supreme coordinator that manages complex tasks
requiring collaboration between specialized AI orchestrator instances.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class MetaAction(Enum):
    """Actions the meta-orchestrator can take."""
    DELEGATE = auto()      # Assign task to an orchestrator
    QUERY = auto()         # Ask an orchestrator for information
    MERGE = auto()         # Combine results from multiple orchestrators
    COORDINATE = auto()    # Enable collaboration between orchestrators
    MONITOR = auto()       # Check progress of delegated tasks
    REDIRECT = auto()      # Move task to different orchestrator (on failure)


@dataclass
class MetaOrchestratorConfig:
    """Configuration for the meta-orchestrator."""
    max_concurrent_delegations: int = 10
    delegation_timeout_seconds: int = 300
    enable_parallel_execution: bool = True
    auto_retry_on_failure: bool = True
    max_retries: int = 2
    require_result_verification: bool = True


@dataclass
class DelegationResult:
    """Result from a delegated task."""
    instance_id: str
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaTask:
    """A task managed by the meta-orchestrator."""
    task_id: str
    description: str
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)
    delegations: List[str] = field(default_factory=list)  # instance_ids
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    results: List[DelegationResult] = field(default_factory=list)


class MetaOrchestrator:
    """Orchestrator-of-orchestrators for cross-instance collaboration.
    
    The Meta-Orchestrator manages complex tasks that require:
    - Multiple specialized AI systems
    - Parallel execution across instances
    - Result synthesis from different domains
    - Fault tolerance and load balancing
    """
    
    def __init__(self, config: Optional[MetaOrchestratorConfig] = None):
        """Initialize the meta-orchestrator.
        
        Args:
            config: Optional configuration
        """
        self.config = config or MetaOrchestratorConfig()
        self._active_tasks: Dict[str, MetaTask] = {}
        self._instance_registry = None  # Set by get_meta_orchestrator
        self._task_distributor = None
        self._result_merger = None
        self._audit_log: List[Dict[str, Any]] = []
        
        logger.info("MetaOrchestrator initialized")
    
    def set_registry(self, registry) -> None:
        """Set the instance registry reference."""
        self._instance_registry = registry
    
    async def orchestrate(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrate a complex task across multiple instances.
        
        Args:
            query: The user's query/task
            context: Optional context information
            user_id: Optional user identifier
            
        Returns:
            Combined result from all participating orchestrators
        """
        task_id = f"meta-{datetime.now().timestamp()}"
        
        # Phase 1: Analyze and decompose
        analysis = await self._analyze_task(query, context)
        
        if not analysis["requires_meta"]:
            # Simple task - delegate to single best instance
            return await self._single_instance_delegation(query, context)
        
        # Phase 2: Create meta-task and plan
        meta_task = MetaTask(
            task_id=task_id,
            description=query,
            sub_tasks=analysis["sub_tasks"],
        )
        self._active_tasks[task_id] = meta_task
        
        # Phase 3: Distribute to instances
        delegations = await self._distribute_tasks(meta_task, analysis)
        meta_task.delegations = [d["instance_id"] for d in delegations]
        meta_task.status = "executing"
        
        # Phase 4: Execute (parallel or sequential based on dependencies)
        if analysis.get("parallel_safe", False) and self.config.enable_parallel_execution:
            results = await self._execute_parallel(delegations)
        else:
            results = await self._execute_sequential(delegations)
        
        meta_task.results = results
        
        # Phase 5: Merge results
        merged = await self._merge_results(query, results, analysis)
        
        # Phase 6: Verify if required
        if self.config.require_result_verification:
            verified = await self._verify_merged_result(merged, query)
            if not verified["passed"]:
                # Attempt refinement
                merged = await self._refine_result(merged, verified["issues"])
        
        meta_task.status = "completed"
        
        # Log for audit
        self._log_orchestration(meta_task, merged)
        
        return {
            "task_id": task_id,
            "result": merged,
            "instances_used": meta_task.delegations,
            "sub_task_count": len(meta_task.sub_tasks),
        }
    
    async def _analyze_task(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze task to determine decomposition and instance needs.
        
        Args:
            query: The task query
            context: Optional context
            
        Returns:
            Analysis with sub-tasks and requirements
        """
        # Detect domains needed
        domains = self._detect_domains(query)
        
        # Determine if meta-orchestration is needed
        requires_meta = len(domains) > 1 or self._is_complex_task(query)
        
        # Decompose into sub-tasks
        sub_tasks = []
        if requires_meta:
            sub_tasks = await self._decompose_task(query, domains)
        
        # Check for dependencies (some tasks must be sequential)
        parallel_safe = self._check_parallel_safety(sub_tasks)
        
        return {
            "requires_meta": requires_meta,
            "domains": domains,
            "sub_tasks": sub_tasks,
            "parallel_safe": parallel_safe,
            "estimated_complexity": len(sub_tasks),
        }
    
    def _detect_domains(self, query: str) -> List[str]:
        """Detect which domains a query spans."""
        query_lower = query.lower()
        
        domain_keywords = {
            "medical": ["medical", "health", "patient", "diagnosis", "treatment", "drug"],
            "financial": ["financial", "money", "investment", "budget", "cost", "revenue"],
            "code": ["code", "program", "software", "implement", "bug", "function"],
            "research": ["research", "study", "paper", "academic", "cite", "analysis"],
            "creative": ["write", "story", "creative", "design", "content", "article"],
        }
        
        detected = []
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected.append(domain)
        
        return detected if detected else ["general"]
    
    def _is_complex_task(self, query: str) -> bool:
        """Determine if a task is complex enough to warrant meta-orchestration."""
        # Simple heuristics
        complexity_indicators = [
            len(query) > 500,  # Long query
            query.count("and") > 2,  # Multiple requirements
            "step" in query.lower(),  # Multi-step request
            "then" in query.lower(),  # Sequential operations
            "compare" in query.lower(),  # Comparison needed
            "analyze" in query.lower() and "report" in query.lower(),
        ]
        return sum(complexity_indicators) >= 2
    
    async def _decompose_task(
        self,
        query: str,
        domains: List[str]
    ) -> List[Dict[str, Any]]:
        """Decompose task into sub-tasks for different instances."""
        # In production, use an LLM to decompose
        # For now, simple domain-based decomposition
        sub_tasks = []
        
        for i, domain in enumerate(domains):
            sub_tasks.append({
                "id": f"sub-{i}",
                "domain": domain,
                "description": f"Handle {domain} aspects of: {query[:200]}",
                "dependencies": [],
                "priority": i,
            })
        
        return sub_tasks
    
    def _check_parallel_safety(self, sub_tasks: List[Dict]) -> bool:
        """Check if sub-tasks can be executed in parallel."""
        # Check for dependencies between tasks
        for task in sub_tasks:
            if task.get("dependencies"):
                return False
        return True
    
    async def _single_instance_delegation(
        self,
        query: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Delegate to a single instance for simple tasks."""
        # Select best instance
        if self._instance_registry:
            instance = await self._instance_registry.get_best_instance("general")
            if instance:
                result = await self._delegate_to_instance(instance.id, query, context)
                return {
                    "result": result.output,
                    "instance_used": instance.id,
                    "meta_orchestration": False,
                }
        
        # Fallback to local processing
        return {
            "result": f"Processed locally: {query[:100]}...",
            "instance_used": "local",
            "meta_orchestration": False,
        }
    
    async def _distribute_tasks(
        self,
        meta_task: MetaTask,
        analysis: Dict
    ) -> List[Dict[str, Any]]:
        """Distribute sub-tasks to appropriate instances."""
        delegations = []
        
        for sub_task in meta_task.sub_tasks:
            # Find best instance for this domain
            domain = sub_task.get("domain", "general")
            
            if self._instance_registry:
                instance = await self._instance_registry.get_best_instance(domain)
                instance_id = instance.id if instance else "local"
            else:
                instance_id = "local"
            
            delegations.append({
                "sub_task_id": sub_task["id"],
                "instance_id": instance_id,
                "description": sub_task["description"],
                "domain": domain,
            })
        
        return delegations
    
    async def _execute_parallel(
        self,
        delegations: List[Dict]
    ) -> List[DelegationResult]:
        """Execute delegations in parallel."""
        tasks = []
        for delegation in delegations:
            task = self._delegate_to_instance(
                delegation["instance_id"],
                delegation["description"],
                {"sub_task_id": delegation["sub_task_id"]}
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        delegation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                delegation_results.append(DelegationResult(
                    instance_id=delegations[i]["instance_id"],
                    task_id=delegations[i]["sub_task_id"],
                    success=False,
                    error=str(result),
                ))
            else:
                delegation_results.append(result)
        
        return delegation_results
    
    async def _execute_sequential(
        self,
        delegations: List[Dict]
    ) -> List[DelegationResult]:
        """Execute delegations sequentially (for dependent tasks)."""
        results = []
        context = {}
        
        for delegation in delegations:
            result = await self._delegate_to_instance(
                delegation["instance_id"],
                delegation["description"],
                {"sub_task_id": delegation["sub_task_id"], **context}
            )
            results.append(result)
            
            # Pass output to next task as context
            if result.success:
                context[f"result_{delegation['sub_task_id']}"] = result.output
        
        return results
    
    async def _delegate_to_instance(
        self,
        instance_id: str,
        task: str,
        context: Optional[Dict] = None
    ) -> DelegationResult:
        """Delegate a task to a specific orchestrator instance."""
        start_time = datetime.now()
        
        try:
            # In production, make API call to instance
            # For now, simulate
            await asyncio.sleep(0.1)  # Simulate network latency
            
            output = f"[{instance_id}] Processed: {task[:100]}..."
            
            return DelegationResult(
                instance_id=instance_id,
                task_id=context.get("sub_task_id", "unknown") if context else "unknown",
                success=True,
                output=output,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )
            
        except Exception as e:
            return DelegationResult(
                instance_id=instance_id,
                task_id=context.get("sub_task_id", "unknown") if context else "unknown",
                success=False,
                error=str(e),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )
    
    async def _merge_results(
        self,
        original_query: str,
        results: List[DelegationResult],
        analysis: Dict
    ) -> str:
        """Merge results from multiple instances into coherent output."""
        # Collect successful outputs
        successful_outputs = [
            r.output for r in results if r.success and r.output
        ]
        
        if not successful_outputs:
            return "Unable to complete task - all delegations failed"
        
        if len(successful_outputs) == 1:
            return successful_outputs[0]
        
        # Merge multiple outputs
        # In production, use an LLM to synthesize
        merged = "## Combined Results\n\n"
        for i, output in enumerate(successful_outputs):
            merged += f"### Part {i + 1}\n{output}\n\n"
        
        return merged
    
    async def _verify_merged_result(
        self,
        result: str,
        query: str
    ) -> Dict[str, Any]:
        """Verify the merged result meets requirements."""
        # Simple verification - in production use verifier agent
        issues = []
        
        if len(result) < 50:
            issues.append("Result too short")
        
        if "error" in result.lower() or "failed" in result.lower():
            issues.append("Result contains error indicators")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }
    
    async def _refine_result(
        self,
        result: str,
        issues: List[str]
    ) -> str:
        """Attempt to refine result based on verification issues."""
        # In production, trigger refinement loop
        return result + f"\n\n[Note: Verification flagged issues: {', '.join(issues)}]"
    
    def _log_orchestration(
        self,
        task: MetaTask,
        result: str
    ) -> None:
        """Log orchestration for audit purposes."""
        self._audit_log.append({
            "task_id": task.task_id,
            "description": task.description[:200],
            "instances_used": task.delegations,
            "sub_task_count": len(task.sub_tasks),
            "success_count": sum(1 for r in task.results if r.success),
            "total_duration_ms": sum(r.duration_ms for r in task.results),
            "timestamp": datetime.now().isoformat(),
        })
        
        # Trim audit log
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get meta-orchestrator statistics."""
        return {
            "active_tasks": len(self._active_tasks),
            "total_orchestrations": len(self._audit_log),
            "config": {
                "max_concurrent": self.config.max_concurrent_delegations,
                "parallel_enabled": self.config.enable_parallel_execution,
            },
        }


# Global meta-orchestrator instance
_global_meta_orchestrator: Optional[MetaOrchestrator] = None


def get_meta_orchestrator() -> MetaOrchestrator:
    """Get or create the global meta-orchestrator."""
    global _global_meta_orchestrator
    if _global_meta_orchestrator is None:
        _global_meta_orchestrator = MetaOrchestrator()
    return _global_meta_orchestrator

