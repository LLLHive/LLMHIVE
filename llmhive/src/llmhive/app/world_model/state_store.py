"""World State Store - Internal state representation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import copy
import json

logger = logging.getLogger(__name__)


@dataclass
class WorldState:
    """Represents the current state of the world for a task.
    
    Contains:
    - variables: Key-value pairs of tracked values
    - entities: Objects/actors in the scenario
    - relations: Connections between entities
    - constraints: Rules that must be satisfied
    - progress: Task completion status
    """
    variables: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    progress: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 0
    
    def get(self, path: str) -> Any:
        """Get value by dot-notation path.
        
        Examples:
            state.get("variables.count")
            state.get("entities.user1.name")
        """
        parts = path.split(".")
        current = self._get_base(parts[0])
        
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    def _get_base(self, base: str) -> Any:
        """Get base container by name."""
        if base == "variables":
            return self.variables
        elif base == "entities":
            return self.entities
        elif base == "progress":
            return self.progress
        return None
    
    def set(self, path: str, value: Any) -> None:
        """Set value by dot-notation path."""
        parts = path.split(".")
        
        if len(parts) == 1:
            # Can't set top-level containers
            return
        
        base = self._get_base(parts[0])
        if base is None:
            return
        
        # Navigate to parent
        for part in parts[1:-1]:
            if part not in base:
                base[part] = {}
            base = base[part]
        
        # Set value
        base[parts[-1]] = value
        self.updated_at = datetime.now()
        self.version += 1
    
    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: Optional[Dict] = None
    ) -> None:
        """Add an entity to the world."""
        self.entities[entity_id] = {
            "type": entity_type,
            "properties": properties or {},
            "created_at": datetime.now().isoformat(),
        }
        self.version += 1
    
    def add_relation(
        self,
        subject: str,
        predicate: str,
        object_: str,
        properties: Optional[Dict] = None
    ) -> None:
        """Add a relation between entities."""
        self.relations.append({
            "subject": subject,
            "predicate": predicate,
            "object": object_,
            "properties": properties or {},
        })
        self.version += 1
    
    def add_constraint(
        self,
        constraint_type: str,
        condition: str,
        error_message: str
    ) -> None:
        """Add a constraint that must be satisfied."""
        self.constraints.append({
            "type": constraint_type,
            "condition": condition,
            "error_message": error_message,
        })
    
    def check_constraints(self) -> List[str]:
        """Check all constraints and return violations."""
        violations = []
        # In production, evaluate constraint conditions
        # For now, return empty (all OK)
        return violations
    
    def snapshot(self) -> "WorldState":
        """Create a deep copy of current state."""
        return WorldState(
            variables=copy.deepcopy(self.variables),
            entities=copy.deepcopy(self.entities),
            relations=copy.deepcopy(self.relations),
            constraints=copy.deepcopy(self.constraints),
            progress=copy.deepcopy(self.progress),
            version=self.version,
        )
    
    def diff(self, other: "WorldState") -> Dict[str, Any]:
        """Calculate differences between two states."""
        changes = {
            "variables": {},
            "entities_added": [],
            "entities_removed": [],
            "relations_added": [],
            "relations_removed": [],
        }
        
        # Variable changes
        all_keys = set(self.variables.keys()) | set(other.variables.keys())
        for key in all_keys:
            if self.variables.get(key) != other.variables.get(key):
                changes["variables"][key] = {
                    "before": other.variables.get(key),
                    "after": self.variables.get(key),
                }
        
        # Entity changes
        for entity_id in self.entities:
            if entity_id not in other.entities:
                changes["entities_added"].append(entity_id)
        
        for entity_id in other.entities:
            if entity_id not in self.entities:
                changes["entities_removed"].append(entity_id)
        
        return changes
    
    def to_json(self) -> str:
        """Serialize state to JSON."""
        return json.dumps({
            "variables": self.variables,
            "entities": self.entities,
            "relations": self.relations,
            "constraints": self.constraints,
            "progress": self.progress,
            "version": self.version,
        }, default=str)
    
    @classmethod
    def from_json(cls, data: str) -> "WorldState":
        """Deserialize state from JSON."""
        obj = json.loads(data)
        return cls(
            variables=obj.get("variables", {}),
            entities=obj.get("entities", {}),
            relations=obj.get("relations", []),
            constraints=obj.get("constraints", []),
            progress=obj.get("progress", {}),
            version=obj.get("version", 0),
        )


class StateStore:
    """Manages world states for tasks.
    
    Features:
    - State CRUD operations
    - Version history
    - State snapshots for simulation
    - Rollback capability
    """
    
    def __init__(self):
        self._states: Dict[str, WorldState] = {}
        self._history: Dict[str, List[WorldState]] = {}
        self._max_history = 10
        
        logger.info("StateStore initialized")
    
    def create_state(self, task_id: str) -> WorldState:
        """Create a new world state for a task."""
        state = WorldState()
        self._states[task_id] = state
        self._history[task_id] = [state.snapshot()]
        
        logger.debug(f"Created state for task {task_id}")
        return state
    
    def get_state(self, task_id: str) -> Optional[WorldState]:
        """Get the current state for a task."""
        return self._states.get(task_id)
    
    def update_state(
        self,
        task_id: str,
        updates: Dict[str, Any]
    ) -> Optional[WorldState]:
        """Update a task's world state."""
        state = self._states.get(task_id)
        if not state:
            return None
        
        # Save history before update
        self._save_history(task_id, state)
        
        # Apply updates
        for path, value in updates.items():
            state.set(path, value)
        
        return state
    
    def rollback(self, task_id: str, steps: int = 1) -> Optional[WorldState]:
        """Rollback state by N steps."""
        history = self._history.get(task_id, [])
        
        if len(history) <= steps:
            return None
        
        # Get historical state
        historical = history[-(steps + 1)]
        
        # Replace current with copy of historical
        self._states[task_id] = historical.snapshot()
        
        # Trim history
        self._history[task_id] = history[:-(steps)]
        
        logger.info(f"Rolled back task {task_id} by {steps} steps")
        return self._states[task_id]
    
    def _save_history(self, task_id: str, state: WorldState) -> None:
        """Save state to history."""
        if task_id not in self._history:
            self._history[task_id] = []
        
        self._history[task_id].append(state.snapshot())
        
        # Trim history
        if len(self._history[task_id]) > self._max_history:
            self._history[task_id] = self._history[task_id][-self._max_history:]
    
    def delete_state(self, task_id: str) -> bool:
        """Delete a task's state."""
        if task_id in self._states:
            del self._states[task_id]
        if task_id in self._history:
            del self._history[task_id]
        return True
    
    def list_tasks(self) -> List[str]:
        """List all tasks with states."""
        return list(self._states.keys())


# Global state store
_global_state_store: Optional[StateStore] = None


def get_state_store() -> StateStore:
    """Get or create global state store."""
    global _global_state_store
    if _global_state_store is None:
        _global_state_store = StateStore()
    return _global_state_store

