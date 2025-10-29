"""Definitions of lightweight agent roles used by the orchestrator tests."""

from __future__ import annotations

from typing import Any, Dict


class AgentRole:
    """Base class representing a simple agent role."""

    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - interface contract
        """Execute the role's task."""

        raise NotImplementedError("Subclasses must implement execute().")


class LeadResponder(AgentRole):
    """Agent responsible for producing an initial draft response."""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("input")
        return {
            "draft": "Generated main draft response",
            "context": topic,
        }


class Researcher(AgentRole):
    """Agent responsible for fetching supporting information."""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("input")
        return {
            "research": "Fetched supporting information",
            "context": topic,
        }


class Critic(AgentRole):
    """Agent responsible for evaluating draft content."""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "critique": "Critique of the draft provided",
            "notes": input_data.get("draft"),
        }


class Synthesizer(AgentRole):
    """Agent responsible for combining intermediate results."""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "final_response": "Synthesized final response",
            "sources": list(input_data.keys()),
        }
