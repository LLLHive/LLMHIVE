"""World Model for LLMHive Opus 6.0.

This module provides internal state representation and long-horizon
planning capabilities for complex multi-step tasks.

Components:
- StateStore: Tracks world state (variables, entities, relations)
- Simulator: Projects action effects on state
- Planner: Long-horizon plan generation with search
- GoalChecker: Verifies goal condition satisfaction
- Contingency: Handles backup plans and failures
"""
from __future__ import annotations

from .state_store import (
    WorldState,
    StateStore,
    get_state_store,
)

from .simulator import (
    ActionSimulator,
    SimulationResult,
)

from .planner import (
    WorldModelPlanner,
    Plan,
    PlanStep,
)

__all__ = [
    "WorldState",
    "StateStore",
    "get_state_store",
    "ActionSimulator",
    "SimulationResult",
    "WorldModelPlanner",
    "Plan",
    "PlanStep",
]

