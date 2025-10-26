from .blackboard import Blackboard
from agents import Agent, ResearcherAgent, CriticAgent, EditorAgent, LeadAgent
from core.validators import Validator

def get_agent(role: str, model_id: str) -> Agent:
    role_map = {"researcher": ResearcherAgent, "critic": CriticAgent, "editor": EditorAgent, "lead": LeadAgent, "analyst": LeadAgent}
    agent_class = role_map.get(role.lower())
    if not agent_class: raise ValueError(f"Agent role '{role}' not supported.")
    return agent_class(model_id=model_id)

async def execute_task(role: str, model_id: str, task: str, blackboard: Blackboard) -> str:
    context = blackboard.get_full_context()
    validator = Validator()
    try:
        agent = get_agent(role, model_id)
        result = await agent.execute(task, context=context)
        if validator.check_content_policy(result):
            result = "[Content Redacted due to Policy Violation]"
        blackboard.append_to_list("logs.execution", f"SUCCESS: Role '{role}' on model '{model_id}' completed task.")
        return result
    except Exception as e:
        error_msg = f"FAILURE: Role '{role}' on model '{model_id}' failed. Error: {e}"
        blackboard.append_to_list("logs.errors", error_msg)
        return f"Agent {role} failed to execute."