"""
Simple Protocol: A single agent performs a single task.
"""
from .base_protocol import BaseProtocol
from ..orchestration.execution import execute_task

class SimpleProtocol(BaseProtocol):
    """Executes a single task with a single agent."""
    async def execute(self) -> None:
        role = self.params.get("role", "lead")
        task = self.params.get("task", "Provide a direct and comprehensive answer.")
        model_id = self.assignments.get(role)

        if not model_id:
            raise ValueError(f"No model assigned for role '{role}' in SimpleProtocol.")

        result = await execute_task(role, model_id, task, self.blackboard)
        self.blackboard.set(f"results.final_draft", result)
