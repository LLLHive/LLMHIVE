"""
The Orchestrator Engine for LLMHive.

This is the "brain" of the platform, responsible for managing the entire
workflow from prompt analysis to final response synthesis. It coordinates
the various components like the Planner, Router, and Synthesizer.
"""

from .planner import Planner
from .router import Router
from .synthesizer import Synthesizer
from ..models.model_pool import ModelPool
from ..memory.conversation_memory import ConversationMemory

class Orchestrator:
    """
    Orchestrates the multi-agent workflow.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.planner = Planner()
        self.router = Router()
        self.synthesizer = Synthesizer()
        self.model_pool = ModelPool()
        self.memory = ConversationMemory(user_id)

    async def run(self, prompt: str) -> str:
        """
        Executes the full orchestration pipeline for a given prompt.

        1. Retrieves conversation history.
        2. Creates an execution plan.
        3. Selects the "dream team" of LLM agents.
        4. Executes the plan by invoking the agents.
        5. Synthesizes the results into a final answer.
        6. Stores the interaction in memory.
        """
        print(f"Orchestrator running for user '{self.user_id}' with prompt: '{prompt}'")

        # 1. Get context from memory
        context = self.memory.retrieve_history()

        # 2. Analyze prompt and create a plan
        plan = self.planner.create_plan(prompt, context)
        print(f"Plan created: {plan.steps}")

        # 3. Select models based on the plan
        dream_team = self.router.select_models(plan)
        print(f"Dream team selected: {[model.model_id for model in dream_team]}")

        # 4. Execute the plan (stubbed for now)
        # In a real implementation, this would involve asynchronously calling
        # the selected models/agents according to the plan's steps.
        partial_results = {}
        for i, step in enumerate(plan.steps):
            agent_role = step['role']
            # Find a model in the dream team that fits the role
            agent_model = next((model for model in dream_team if model.role == agent_role), dream_team[0])
            print(f"Executing step {i+1}: Role '{agent_role}' using model '{agent_model.model_id}'")
            # This is a stub. A real agent would be invoked here.
            result = f"Partial result for '{step['task']}' from model '{agent_model.model_id}'."
            partial_results[agent_role] = result

        # 5. Synthesize the final answer
        final_answer = self.synthesizer.synthesize(partial_results, plan)
        print(f"Synthesized answer: {final_answer}")

        # 6. Store interaction in memory
        self.memory.store_interaction(prompt, final_answer)

        return final_answer
