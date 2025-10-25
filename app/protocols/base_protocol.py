from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any
from ..orchestration.blackboard import Blackboard

class BaseProtocol(ABC):
    def __init__(self, blackboard: Blackboard, assignments: Dict[str, str], params: Dict[str, Any]):
        self.blackboard = blackboard
        self.assignments = assignments
        self.params = params

    @abstractmethod
    async def execute(self) -> None:
        pass
