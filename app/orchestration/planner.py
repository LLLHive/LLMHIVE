from models.language_model import LanguageModel
from .models import Plan, Step
import os

class Planner:
    """
    The Maestro. It analyzes the user's prompt and creates a multi-step plan.
    """
    def __init__(self):
        # The planner uses its own LLM to reason about the plan.
        self.llm = LanguageModel(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

    def plan(self, prompt: str) -> Plan:
        system_prompt = """You are the Maestro, an expert planner for a powerful AI orchestration engine. Your job is to analyze a user's prompt and create a clear, step-by-step plan to fulfill it.

Available agents:
- "tavily": A web search tool. Use it for any questions about recent events, facts, or public information.
- "summarizer": An LLM agent that can summarize or transform text. Use it to process the results of other tools.

Based on the user's prompt, create a JSON object representing the plan.
The plan should have "reasoning" and a list of "steps".
Each step must have a "step_name" (a unique, single-word identifier), an "agent" to use, and a "prompt" for that agent.
If a step needs to use the result of a previous step, use the template format `{{steps.step_name.result}}` in the prompt.

Example:
User Prompt: "Search for the weather in SF and summarize it for a 5-year-old."
{
  "reasoning": "First, I will search for the weather. Then, I will use the summarizer to rephrase the result in simple terms.",
  "steps": [
    {
      "step_name": "search",
      "agent": "tavily",
      "prompt": "Weather in San Francisco"
    },
    {
      "step_name": "summarize",
      "agent": "summarizer",
      "prompt": "Summarize the following text for a 5-year-old: {{steps.search.result}}"
    }
  ]
}
"""
        plan_str = self.llm.generate(prompt, system_prompt=system_prompt, response_format={"type": "json_object"})
        return Plan.model_validate_json(plan_str)
