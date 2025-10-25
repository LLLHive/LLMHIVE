"""
The Orchestrator Engine for LLMHive.

This is the "brain" of the platform, responsible for managing the entire
workflow from prompt analysis to final response synthesis. It coordinates
the various components like the Planner, Router, and Synthesizer.
"""
from typing import Any, AsyncGenerator, List, Set, Optional, Dict

from .planner import Planner
from .router import Router
from .synthesizer import Synthesizer
from .blackboard import Blackboard
from ..memory.conversation_memory import ConversationMemory
from ..protocols.simple_protocol import SimpleProtocol
from ..protocols.critique_and_improve_protocol import CritiqueAndImproveProtocol

class Orchestrator:
    """Orchestrates the multi-agent workflow."""
    def __init__(self, user_id: str, preferred_models: Optional[List[str]] = None, preferred_protocol: Optional[str] = None):
        self.user_id = user_id
        self.planner = Planner(preferred_protocol)
        self.router = Router(preferred_models)
        self.synthesizer = Synthesizer()
        self.memory = ConversationMemory(user_id)
        self.protocol_map = {
            "simple": SimpleProtocol,
            "critique_and_improve": CritiqueAndImproveProtocol,
        }

    async def run(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Executes the full orchestration pipeline and streams the final answer.
        """
        print(f"Orchestrator running for user '{self.user_id}' with prompt: '{prompt}'")
        
        blackboard = Blackboard(prompt)
        blackboard.set("history", "\n".join(self.memory.retrieve_history()))

        plan = await self.planner.create_plan(prompt)
        blackboard.set("plan", plan.model_dump())
        
        roles = self._extract_roles_from_plan(plan.protocol, plan.params)
        assignments = self.router.assign_models_to_roles(roles)
        blackboard.set("assignments", assignments)
        
        protocol_class = self.protocol_map.get(plan.protocol)
        if not protocol_class:
            raise ValueError(f"Protocol '{plan.protocol}' is not registered.")
            
        protocol = protocol_class(blackboard, assignments, plan.params)
        await protocol.execute()

        final_answer_text = ""
        async for token in self.synthesizer.synthesize_stream(blackboard):
            final_answer_text += token
            yield token
        
        self.memory.store_interaction(prompt, final_answer_text)

    def _extract_roles_from_plan(self, protocol: str, params: Dict[str, Any]) -> Set[str]:
        """Extract all unique roles from the plan."""
        roles = set()
        if protocol == "simple":
            roles.add(params.get("role", "lead"))
        elif protocol == "critique_and_improve":
            roles.update(params.get("drafting_roles", []))
            roles.add(params.get("improving_role", "lead"))
            roles.add("critic")
        return roles
