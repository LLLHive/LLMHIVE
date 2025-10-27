from app.models.language_model import LanguageModel
from .models import Plan

class Planner:
    """
    The Maestro. It analyzes the user's prompt and creates a multi-step plan.
    It receives its LLM dependency via its constructor.
    """
    def __init__(self, llm: LanguageModel):
        self.llm = llm

    def plan(self, prompt: str) -> Plan:
        system_prompt = """You are the Maestro, an expert planner for a powerful AI orchestration engine. Your job is to analyze a user's prompt and create a JSON object representing a step-by-step plan to fulfill it.

# Available Agents:
- "tavily": Web search tool. Use for questions about recent events, facts, or public information.
- "summarizer": An LLM agent that can summarize, analyze, or transform text.

# Instructions:
1.  Create a "reasoning" string explaining your plan.
2.  Create a "steps" list. Each step must have:
    - "step_name": A unique, single-word identifier (e.g., "research", "summarize").
    - "agent": The name of the agent to use (e.g., "tavily", "summarizer").
    - "prompt": The exact prompt for that agent.
3.  To use the output of a previous step, use this exact template format in the prompt: `{{steps.previous_step_name.result}}`.
"""
        plan_str = self.llm.generate(prompt, system_prompt=system_prompt, response_format={"type": "json_object"})
        return Plan.model_validate_json(plan_str)
