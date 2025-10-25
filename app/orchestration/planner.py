"""
The LLM-Powered Planner for LLMHive.

Selects the optimal Thinking Protocol using `instructor` for guaranteed
structured output.
"""

import instructor
from openai import AsyncOpenAI
from typing import Dict, Any, Optional
from pydantic import BaseModel
from ..config import settings

# Lazily initialize the client - will be set when first needed
_client = None

def get_client():
    """Get or create the instructor-patched OpenAI client."""
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for planning but is not set.")
        _client = instructor.patch(AsyncOpenAI(api_key=settings.OPENAI_API_KEY))
    return _client

class Plan(BaseModel):
    reasoning: str
    protocol: str  # The name of the protocol to use (e.g., 'simple', 'critique_and_improve')
    params: Dict[str, Any] = {} # Parameters for the chosen protocol

class Planner:
    """
    Analyzes prompts using an LLM to create dynamic execution plans.
    Uses instructor library to guarantee structured output.
    """
    def __init__(self, preferred_protocol: Optional[str] = None):
        self.preferred_protocol = preferred_protocol

    async def create_plan(self, prompt: str) -> Plan:
        """
        Creates a structured plan using an LLM to address the user's prompt.
        """
        if self.preferred_protocol:
            print(f"User specified preferred protocol: '{self.preferred_protocol}'.")
            return Plan(
                reasoning=f"Using user-specified protocol '{self.preferred_protocol}'.",
                protocol=self.preferred_protocol,
                params={
                    "task": prompt,
                    "drafting_task": prompt,
                    "drafting_roles": ["lead", "analyst"],
                    "improving_role": "lead"
                }
            )

        print(f"Creating LLM-driven plan for prompt: '{prompt}'")
        prompt_for_planner = self._build_planning_prompt(prompt)
        
        try:
            # Get the client (will raise if key not set)
            client = get_client()
            # This call is now guaranteed to return a valid Plan object or raise an exception
            plan = await client.chat.completions.create(
                model=settings.PLANNING_MODEL,
                response_model=Plan,
                messages=[{"role": "user", "content": prompt_for_planner}],
                max_retries=1,
            )
            return plan
        except Exception as e:
            print(f"ERROR: Failed to generate a valid plan with instructor: {e}. Falling back to default.")
            return self.fallback_plan(prompt)

    def fallback_plan(self, prompt: str) -> Plan:
        """A simple rule-based fallback plan."""
        return Plan(reasoning="Fell back to default plan.", protocol="simple", params={"role": "lead", "task": f"Provide a direct answer to: {prompt}"})

    def _build_planning_prompt(self, prompt: str) -> str:
        return f"""
You are an expert AI orchestrator. Your job is to select the best "Thinking Protocol" to answer a user's prompt.

Available Protocols:
1. `simple`: For straightforward questions.
   - params: `{{"role": "lead", "task": "..."}}`
2. `critique_and_improve`: For complex or high-stakes queries requiring maximum accuracy.
   - params: `{{"drafting_task": "...", "drafting_roles": ["lead", "analyst"], "improving_role": "lead"}}`

Analyze the user's prompt and choose the optimal protocol.

User's Prompt: "{prompt}"
"""
