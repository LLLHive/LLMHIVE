"""Orchestration logic for LLMHive."""

from typing import Dict, Any
from .roles import LeadResponder, Researcher, Critic, Synthesizer
from .scratchpad import Scratchpad
from .validator import Validator


class Orchestrator:
    """Coordinates multiple agents to generate a final response."""

    def __init__(self):
        self.scratchpad = Scratchpad()
        self.validator = Validator()

    def orchestrate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration workflow."""

        # Step 1: Lead Responder generates draft
        lead = LeadResponder("LeadResponder")
        draft = lead.execute(input_data)
        self.scratchpad.add_entry("draft", draft)

        # Step 2: Researcher fetches supporting information
        researcher = Researcher("Researcher")
        research = researcher.execute(input_data)
        self.scratchpad.add_entry("research", research)

        # Step 3: Critic evaluates the draft
        critic = Critic("Critic")
        critique = critic.execute({"draft": draft, "research": research})
        self.scratchpad.add_entry("critique", critique)

        # Step 4: Synthesizer composes final response
        synthesizer = Synthesizer("Synthesizer")
        final_response = synthesizer.execute(self.scratchpad.context)

        # Step 5: Validate the final response
        if not self.validator.validate_output(final_response):
            return {"error": "Validation failed"}

        return final_response
