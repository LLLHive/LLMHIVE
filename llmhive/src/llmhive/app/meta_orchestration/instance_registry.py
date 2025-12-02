"""Instance Registry - Tracks orchestrator instances and capabilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class InstanceCapability(Enum):
    """Capabilities an orchestrator instance can have."""
    GENERAL = auto()
    MEDICAL = auto()
    FINANCIAL = auto()
    CODE = auto()
    RESEARCH = auto()
    CREATIVE = auto()
    MULTIMODAL = auto()
    REALTIME = auto()


@dataclass
class OrchestratorInstance:
    """An orchestrator instance in the registry."""
    id: str
    name: str
    endpoint: str  # API endpoint for the instance
    capabilities: List[InstanceCapability]
    
    # Performance metrics
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    current_load: int = 0
    max_load: int = 100
    
    # Status
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    
    # Metadata
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """Check if instance is available for new tasks."""
        return self.is_healthy and self.current_load < self.max_load
    
    def can_handle(self, capability: InstanceCapability) -> bool:
        """Check if instance has a specific capability."""
        return capability in self.capabilities or InstanceCapability.GENERAL in self.capabilities


class InstanceRegistry:
    """Registry of available orchestrator instances.
    
    Tracks:
    - Available instances and their capabilities
    - Performance metrics for routing decisions
    - Health status of each instance
    """
    
    def __init__(self):
        self._instances: Dict[str, OrchestratorInstance] = {}
        self._capability_index: Dict[InstanceCapability, List[str]] = {}
        
        # Register default local instance
        self.register_instance(OrchestratorInstance(
            id="local",
            name="Local Orchestrator",
            endpoint="localhost",
            capabilities=[InstanceCapability.GENERAL],
        ))
        
        logger.info("InstanceRegistry initialized")
    
    def register_instance(self, instance: OrchestratorInstance) -> bool:
        """Register a new orchestrator instance."""
        if instance.id in self._instances:
            logger.warning(f"Instance {instance.id} already registered, updating")
        
        self._instances[instance.id] = instance
        
        # Update capability index
        for cap in instance.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = []
            if instance.id not in self._capability_index[cap]:
                self._capability_index[cap].append(instance.id)
        
        logger.info(f"Registered instance: {instance.id} ({instance.name})")
        return True
    
    def unregister_instance(self, instance_id: str) -> bool:
        """Unregister an instance."""
        if instance_id not in self._instances:
            return False
        
        instance = self._instances[instance_id]
        
        # Remove from capability index
        for cap in instance.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap] = [
                    i for i in self._capability_index[cap] if i != instance_id
                ]
        
        del self._instances[instance_id]
        logger.info(f"Unregistered instance: {instance_id}")
        return True
    
    def get_instance(self, instance_id: str) -> Optional[OrchestratorInstance]:
        """Get instance by ID."""
        return self._instances.get(instance_id)
    
    async def get_best_instance(
        self,
        domain: str,
        exclude: Optional[List[str]] = None
    ) -> Optional[OrchestratorInstance]:
        """Get the best available instance for a domain.
        
        Selection criteria:
        1. Has required capability
        2. Is available (healthy and not overloaded)
        3. Best performance (lowest latency, highest success rate)
        """
        # Map domain to capability
        capability_map = {
            "medical": InstanceCapability.MEDICAL,
            "financial": InstanceCapability.FINANCIAL,
            "code": InstanceCapability.CODE,
            "research": InstanceCapability.RESEARCH,
            "creative": InstanceCapability.CREATIVE,
            "general": InstanceCapability.GENERAL,
        }
        
        capability = capability_map.get(domain.lower(), InstanceCapability.GENERAL)
        
        # Get instances with this capability
        candidate_ids = self._capability_index.get(capability, [])
        
        # Also include general instances as fallback
        general_ids = self._capability_index.get(InstanceCapability.GENERAL, [])
        all_candidates = list(set(candidate_ids + general_ids))
        
        # Filter excluded
        if exclude:
            all_candidates = [i for i in all_candidates if i not in exclude]
        
        # Get available instances
        available = [
            self._instances[i] for i in all_candidates
            if i in self._instances and self._instances[i].is_available()
        ]
        
        if not available:
            return None
        
        # Score and sort by performance
        def score_instance(inst: OrchestratorInstance) -> float:
            # Lower is better
            latency_score = inst.avg_latency_ms / 1000  # Normalize
            success_score = 1 - inst.success_rate
            load_score = inst.current_load / inst.max_load
            
            # Bonus for having exact capability
            capability_bonus = 0 if inst.can_handle(capability) else 0.5
            
            return latency_score + success_score + load_score + capability_bonus
        
        available.sort(key=score_instance)
        return available[0]
    
    def update_metrics(
        self,
        instance_id: str,
        latency_ms: float,
        success: bool
    ) -> None:
        """Update instance performance metrics after a task."""
        instance = self._instances.get(instance_id)
        if not instance:
            return
        
        # Moving average for latency
        instance.avg_latency_ms = (
            instance.avg_latency_ms * 0.9 + latency_ms * 0.1
        )
        
        # Moving average for success rate
        instance.success_rate = (
            instance.success_rate * 0.95 + (1.0 if success else 0.0) * 0.05
        )
    
    def update_health(self, instance_id: str, is_healthy: bool) -> None:
        """Update instance health status."""
        instance = self._instances.get(instance_id)
        if instance:
            instance.is_healthy = is_healthy
            instance.last_health_check = datetime.now()
    
    def list_instances(self) -> List[Dict[str, Any]]:
        """List all registered instances."""
        return [
            {
                "id": inst.id,
                "name": inst.name,
                "endpoint": inst.endpoint,
                "capabilities": [c.name for c in inst.capabilities],
                "is_available": inst.is_available(),
                "avg_latency_ms": inst.avg_latency_ms,
                "success_rate": inst.success_rate,
                "load": f"{inst.current_load}/{inst.max_load}",
            }
            for inst in self._instances.values()
        ]


# Global registry
_global_registry: Optional[InstanceRegistry] = None


def get_instance_registry() -> InstanceRegistry:
    """Get or create global instance registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = InstanceRegistry()
    return _global_registry

