"""
Abstract Base Class for all Thinking Protocols.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any
from ..orchestration.blackboard import Blackboard

class BaseProtocol(ABC):
    """
    A protocol defines a specific multi-step workflow or reasoning strategy
    for handling a user query.
    """
    def __init__(self, blackboard: Blackboard, assignments: Dict[str, str], params: Dict[str, Any]):
        self.blackboard = blackboard
        self.assignments = assignments  # Model assignments for roles
        self.params = params            # Protocol-specific parameters from the planner

    @abstractmethod
    async def execute(self) -> None:
        """
        Executes the protocol's workflow. All results should be written
        to the blackboard.
        """
        pass
