from __future__ import annotations

from app.orchestration.execution import execute_task

from .base_protocol import BaseProtocol


class SimpleProtocol(BaseProtocol):
    async def execute(self) -> None:
        role = self.params.get("role", "lead")
        task = self.params.get(
            "task", "Provide a direct and comprehensive answer."
        )
        model_id = self.assignments.get(role)

        if not model_id:
            raise ValueError(
                f"No model assigned for role '{role}' in SimpleProtocol."
            )

        result = await execute_task(role, model_id, task, self.blackboard)
        self.blackboard.set("results.final_draft", result)
