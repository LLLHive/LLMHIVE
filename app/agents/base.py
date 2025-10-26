from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict
from services.model_gateway import model_gateway

class Agent(ABC):
    def __init__(self, model_id: str, role: str):
        self.model_id = model_id
        self.role = role
        self.gateway = model_gateway

    @abstractmethod
    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        pass

    async def execute(self, task: str, context: str = "") -> str:
        messages = self._create_prompt(task, context)
        response = await self.gateway.call(model_id=self.model_id, messages=messages)
        return response.content

    async def execute_stream(self, task: str, context: str = "") -> AsyncGenerator[str, None]:
        messages = self._create_prompt(task, context)
        async for token in self.gateway.call(model_id=self.model_id, messages=messages, stream=True):
            yield token