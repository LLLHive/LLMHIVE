"""A minimal orchestrator that coordinates the simple agent roles."""

from __future__ import annotations

from typing import Any, Dict

from .roles import Critic, LeadResponder, Researcher, Synthesizer
from .scratchpad import Scratchpad
from .validator import Validator


class Orchestrator:
    """Runs a deterministic multi-agent workflow used in tests."""

    def __init__(self) -> None:
        self.scratchpad = Scratchpad()
        self.validator = Validator()

    def orchestrate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        lead = LeadResponder("LeadResponder")
        draft_payload = lead.execute(input_data)
        draft_text = draft_payload.get("draft", "")
        self.scratchpad.add_entry("draft", draft_text)

        researcher = Researcher("Researcher")
        research_payload = researcher.execute(input_data)
        research_notes = research_payload.get("research", "")
        self.scratchpad.add_entry("research", research_notes)

        critic = Critic("Critic")
        critique_payload = critic.execute({
            "draft": draft_text,
            "research": research_notes,
        })
        critique_notes = critique_payload.get("critique", "")
        self.scratchpad.add_entry("critique", critique_notes)

        synthesizer = Synthesizer("Synthesizer")
        final_payload = synthesizer.execute(self.scratchpad.snapshot())
        final_text = final_payload.get("final_response", "")

        result = {
            "draft": draft_text,
            "research": research_notes,
            "critique": critique_notes,
            "final_response": final_text,
            "format": "text",
        }

        if not self.validator.validate_output(result):
            return {"error": "Validation failed"}

        self.scratchpad.add_entry("final_response", final_text)
        return result
