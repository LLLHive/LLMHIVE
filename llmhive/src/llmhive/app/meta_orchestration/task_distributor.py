"""Task Distributor - Routes sub-tasks to appropriate instances."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum, auto

logger = logging.getLogger(__name__)


class DistributionStrategy(Enum):
    """Strategies for distributing tasks."""
    CAPABILITY_MATCH = auto()  # Match by capability
    LOAD_BALANCE = auto()       # Distribute evenly
    PERFORMANCE = auto()        # Route to fastest
    COST_OPTIMIZE = auto()      # Route to cheapest
    LOCALITY = auto()           # Keep related tasks together


@dataclass
class TaskAssignment:
    """An assignment of a task to an instance."""
    task_id: str
    instance_id: str
    description: str
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskDistributor:
    """Distributes tasks to orchestrator instances.
    
    Handles:
    - Task-to-instance matching by capability
    - Load balancing across instances
    - Dependency-aware scheduling
    - Fallback handling
    """
    
    def __init__(
        self,
        strategy: DistributionStrategy = DistributionStrategy.CAPABILITY_MATCH
    ):
        self.strategy = strategy
        self._assignments: List[TaskAssignment] = []
    
    async def distribute(
        self,
        tasks: List[Dict[str, Any]],
        registry,  # InstanceRegistry
    ) -> List[TaskAssignment]:
        """Distribute tasks to instances.
        
        Args:
            tasks: List of tasks to distribute
            registry: Instance registry for lookup
            
        Returns:
            List of task assignments
        """
        assignments = []
        
        for task in tasks:
            assignment = await self._assign_task(task, registry, assignments)
            assignments.append(assignment)
        
        self._assignments = assignments
        return assignments
    
    async def _assign_task(
        self,
        task: Dict[str, Any],
        registry,
        existing_assignments: List[TaskAssignment]
    ) -> TaskAssignment:
        """Assign a single task to an instance."""
        domain = task.get("domain", "general")
        
        # Get already-used instances
        used_instances = [a.instance_id for a in existing_assignments]
        
        # Strategy-based selection
        if self.strategy == DistributionStrategy.LOAD_BALANCE:
            # Avoid already-used instances if possible
            instance = await registry.get_best_instance(domain, exclude=used_instances)
            if not instance:
                instance = await registry.get_best_instance(domain)
        else:
            # Default: capability match
            instance = await registry.get_best_instance(domain)
        
        instance_id = instance.id if instance else "local"
        
        return TaskAssignment(
            task_id=task.get("id", "unknown"),
            instance_id=instance_id,
            description=task.get("description", ""),
            priority=task.get("priority", 0),
            dependencies=task.get("dependencies", []),
        )
    
    def get_assignments(self) -> List[TaskAssignment]:
        """Get current assignments."""
        return self._assignments

