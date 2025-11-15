from __future__ import annotations

from app.agents import (
    Agent,
    CriticAgent,
    EditorAgent,
    LeadAgent,
    ResearcherAgent,
)
from app.core.validators import Validator

from .blackboard import Blackboard


ROLE_MAP = {
    "researcher": ResearcherAgent,
    "critic": CriticAgent,
    "editor": EditorAgent,
    "lead": LeadAgent,
    "analyst": LeadAgent,
}


def get_agent(role: str, model_id: str) -> Agent:
    agent_class = ROLE_MAP.get(role.lower())
    if not agent_class:
        raise ValueError(f"Agent role '{role}' not supported.")
    return agent_class(model_id=model_id)


async def execute_task(role: str, model_id: str, task: str, blackboard: Blackboard) -> str:
    context = blackboard.get_full_context()
    validator = Validator()

    try:
        agent = get_agent(role, model_id)
        result = await agent.execute(task, context=context)

        if validator.check_for_pii(result) or validator.check_content_policy(result):
            blackboard.append_to_list(
                "logs.errors",
                f"Validation warning for role '{role}' on model '{model_id}'.",
            )
            result = "[Content Redacted due to Policy Violation]"

        blackboard.set(f"results.{role}", result)
        blackboard.append_to_list(
            "logs.execution",
            f"SUCCESS: Role '{role}' on model '{model_id}' completed task.",
        )
        return result
    except Exception as exc:
        error_msg = (
            f"FAILURE: Role '{role}' on model '{model_id}' failed. Error: {exc}"
        )
        blackboard.append_to_list("logs.errors", error_msg)
        return f"Agent {role} failed to execute."
