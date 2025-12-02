"""Action Simulator - Projects action effects on world state."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from .state_store import WorldState

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of simulating an action."""
    success: bool
    resulting_state: Optional[WorldState] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[str] = field(default_factory=list)
    constraint_violations: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ActionDefinition:
    """Definition of an action that can be simulated."""
    name: str
    preconditions: List[str]  # Conditions that must be true
    effects: List[Dict[str, Any]]  # Changes to state
    cost: float = 1.0
    duration_estimate: int = 0  # milliseconds


class ActionSimulator:
    """Simulates actions on world state without executing them.
    
    Used for:
    - Planning: Test sequences before execution
    - Verification: Check if action leads to goal
    - Safety: Detect constraint violations before real execution
    """
    
    def __init__(self):
        self._action_library: Dict[str, ActionDefinition] = {}
        self._custom_simulators: Dict[str, Callable] = {}
        
        # Register built-in actions
        self._register_builtin_actions()
        
        logger.info("ActionSimulator initialized")
    
    def _register_builtin_actions(self) -> None:
        """Register built-in action definitions."""
        # Example actions - in production, load from config
        self._action_library["set_variable"] = ActionDefinition(
            name="set_variable",
            preconditions=[],
            effects=[{"type": "set", "target": "variables"}],
        )
        
        self._action_library["create_entity"] = ActionDefinition(
            name="create_entity",
            preconditions=[],
            effects=[{"type": "add_entity"}],
        )
        
        self._action_library["delete_entity"] = ActionDefinition(
            name="delete_entity",
            preconditions=["entity_exists"],
            effects=[{"type": "remove_entity"}],
        )
    
    def register_action(self, action: ActionDefinition) -> None:
        """Register a new action type."""
        self._action_library[action.name] = action
    
    def register_custom_simulator(
        self,
        action_name: str,
        simulator: Callable[[WorldState, Dict], SimulationResult]
    ) -> None:
        """Register a custom simulation function for an action."""
        self._custom_simulators[action_name] = simulator
    
    async def simulate(
        self,
        state: WorldState,
        action: str,
        parameters: Dict[str, Any]
    ) -> SimulationResult:
        """Simulate an action on a state copy.
        
        Args:
            state: Current world state (will not be modified)
            action: Action name
            parameters: Action parameters
            
        Returns:
            SimulationResult with outcome
        """
        # Create state copy for simulation
        sim_state = state.snapshot()
        
        # Check for custom simulator
        if action in self._custom_simulators:
            return await self._run_custom_simulator(
                action, sim_state, parameters
            )
        
        # Get action definition
        action_def = self._action_library.get(action)
        if not action_def:
            return SimulationResult(
                success=False,
                error=f"Unknown action: {action}",
            )
        
        # Check preconditions
        precondition_issues = self._check_preconditions(
            sim_state, action_def.preconditions, parameters
        )
        if precondition_issues:
            return SimulationResult(
                success=False,
                error=f"Precondition failed: {precondition_issues[0]}",
                constraint_violations=precondition_issues,
            )
        
        # Apply effects
        changes = self._apply_effects(sim_state, action_def.effects, parameters)
        
        # Check constraints after effects
        violations = sim_state.check_constraints()
        
        return SimulationResult(
            success=len(violations) == 0,
            resulting_state=sim_state,
            changes=changes,
            constraint_violations=violations,
        )
    
    async def simulate_sequence(
        self,
        state: WorldState,
        actions: List[Dict[str, Any]]
    ) -> List[SimulationResult]:
        """Simulate a sequence of actions.
        
        Args:
            state: Starting state
            actions: List of {action, parameters} dicts
            
        Returns:
            List of results, one per action
        """
        results = []
        current_state = state.snapshot()
        
        for action_spec in actions:
            action = action_spec.get("action", "")
            parameters = action_spec.get("parameters", {})
            
            result = await self.simulate(current_state, action, parameters)
            results.append(result)
            
            if not result.success:
                # Stop sequence on failure
                break
            
            # Continue with resulting state
            if result.resulting_state:
                current_state = result.resulting_state
        
        return results
    
    def _check_preconditions(
        self,
        state: WorldState,
        preconditions: List[str],
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Check if preconditions are satisfied."""
        issues = []
        
        for precond in preconditions:
            if precond == "entity_exists":
                entity_id = parameters.get("entity_id")
                if entity_id and entity_id not in state.entities:
                    issues.append(f"Entity {entity_id} does not exist")
        
        return issues
    
    def _apply_effects(
        self,
        state: WorldState,
        effects: List[Dict],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply action effects to state."""
        changes = {}
        
        for effect in effects:
            effect_type = effect.get("type")
            
            if effect_type == "set":
                path = parameters.get("path", "")
                value = parameters.get("value")
                if path:
                    state.set(path, value)
                    changes[path] = value
            
            elif effect_type == "add_entity":
                entity_id = parameters.get("entity_id")
                entity_type = parameters.get("entity_type", "object")
                props = parameters.get("properties", {})
                if entity_id:
                    state.add_entity(entity_id, entity_type, props)
                    changes[f"entities.{entity_id}"] = "created"
            
            elif effect_type == "remove_entity":
                entity_id = parameters.get("entity_id")
                if entity_id and entity_id in state.entities:
                    del state.entities[entity_id]
                    changes[f"entities.{entity_id}"] = "deleted"
        
        return changes
    
    async def _run_custom_simulator(
        self,
        action: str,
        state: WorldState,
        parameters: Dict[str, Any]
    ) -> SimulationResult:
        """Run a custom simulation function."""
        simulator = self._custom_simulators[action]
        try:
            return simulator(state, parameters)
        except Exception as e:
            return SimulationResult(
                success=False,
                error=f"Simulation error: {str(e)}",
            )

