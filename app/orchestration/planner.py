import instructor
from openai import AsyncOpenAI
from typing import Dict, Any, Optional
from pydantic import BaseModel
from config import settings

# This check is important for graceful failure if the key is missing
client = None
if settings.OPENAI_API_KEY:
    try:
        client = instructor.patch(AsyncOpenAI(api_key=settings.OPENAI_API_KEY))
    except Exception as e:
        print(f"Failed to initialize OpenAI client for Planner: {e}")

class Plan(BaseModel):
    reasoning: str
    protocol: str
    params: Dict[str, Any] = {}
    tool: Optional[str] = None
    query: Optional[str] = None

class Planner:
    def __init__(self, preferred_protocol: Optional[str] = None):
        self.preferred_protocol = preferred_protocol

    def plan(self, prompt: str) -> Plan:
        """
        Synchronous planning method for simple tool-based workflows.
        This is a simplified version for Phase 1 of the N3 architecture.
        """
        # For now, we use a simple heuristic: if the prompt looks like a search query,
        # use Tavily. Otherwise, use reasoning.
        search_keywords = ["search", "find", "look up", "what is", "who is", "when", "where", "how"]
        prompt_lower = prompt.lower()
        
        if any(keyword in prompt_lower for keyword in search_keywords):
            return Plan(
                reasoning="User query appears to require web search for current information.",
                protocol="tool",
                tool="tavily",
                query=prompt
            )
        else:
            return Plan(
                reasoning="Query can be answered with internal knowledge.",
                protocol="simple",
                tool=None,
                query=None
            )

    async def create_plan(self, prompt: str) -> Plan:
        if self.preferred_protocol:
            return Plan(
                reasoning=f"Using user-specified protocol '{self.preferred_protocol}'.",
                protocol=self.preferred_protocol,
                params={"task": prompt, "drafting_task": prompt, "drafting_roles": ["lead", "analyst"], "improving_role": "lead"}
            )

        # Fallback if the client couldn't be initialized
        if not client:
            return self.fallback_plan(prompt)

        prompt_for_planner = self._build_planning_prompt(prompt)
        
        try:
            plan = await client.chat.completions.create(
                model=settings.PLANNING_MODEL,
                response_model=Plan,
                messages=[{"role": "user", "content": prompt_for_planner}],
                max_retries=1,
            )
            return plan
        except Exception as e:
            return self.fallback_plan(prompt)

    def fallback_plan(self, prompt: str) -> Plan:
        return Plan(reasoning="Fell back to default plan.", protocol="simple", params={"role": "lead", "task": f"Provide a direct answer to: {prompt}"})

    def _build_planning_prompt(self, prompt: str) -> str:
        return f"""
You are an expert AI orchestrator. Your job is to select the best "Thinking Protocol" to answer a user's prompt.
Available Protocols:
1. `simple`: For straightforward questions.
2. `critique_and_improve`: For complex or high-stakes queries requiring maximum accuracy.
Analyze the user's prompt and choose the optimal protocol.
User's Prompt: "{prompt}"
"""
