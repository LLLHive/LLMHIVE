"""Meta-Orchestration Layer for LLMHive Opus 6.0.

This module enables orchestrator-of-orchestrators coordination,
allowing multiple LLMHive instances to collaborate on complex tasks.

Architecture:
- MetaOrchestrator: Coordinates multiple orchestrator instances
- InstanceRegistry: Tracks available instances and their capabilities  
- TaskDistributor: Routes sub-tasks to appropriate instances
- ResultMerger: Combines outputs from multiple instances
- Protocols: Inter-instance communication standards

Use Cases:
- Complex multi-domain tasks (medical + financial + technical)
- Scaling to parallel sub-task execution
- Fault tolerance through instance redundancy
- Load balancing across deployments
"""
from __future__ import annotations

from .meta_orchestrator import (
    MetaOrchestrator,
    MetaOrchestratorConfig,
    get_meta_orchestrator,
)

from .instance_registry import (
    InstanceRegistry,
    OrchestratorInstance,
    InstanceCapability,
    get_instance_registry,
)

from .task_distributor import (
    TaskDistributor,
    DistributionStrategy,
    TaskAssignment,
)

from .result_merger import (
    ResultMerger,
    MergeStrategy,
    MergedResult,
)

from .protocols import (
    InterInstanceProtocol,
    DelegateRequest,
    DelegateResponse,
    CoordinationMessage,
)

__all__ = [
    # Meta orchestrator
    "MetaOrchestrator",
    "MetaOrchestratorConfig",
    "get_meta_orchestrator",
    # Instance registry
    "InstanceRegistry",
    "OrchestratorInstance",
    "InstanceCapability",
    "get_instance_registry",
    # Task distribution
    "TaskDistributor",
    "DistributionStrategy",
    "TaskAssignment",
    # Result merging
    "ResultMerger",
    "MergeStrategy",
    "MergedResult",
    # Protocols
    "InterInstanceProtocol",
    "DelegateRequest",
    "DelegateResponse",
    "CoordinationMessage",
]

