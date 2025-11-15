from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from pydantic import ValidationError

from app.config import settings
from app.models.model_pool import model_pool
from .models import Plan


logger = logging.getLogger(__name__)


DEFAULT_PROTOCOL = "simple"
DEFAULT_PROTOCOL_PARAMS: Dict[str, Dict[str, Any]] = {
    "simple": {
        "role": "lead",
        "task": "Provide a direct, thorough answer to the user's request.",
    },
    "critique_and_improve": {
        "drafting_roles": ["researcher", "analyst"],
        "drafting_task": (
            "Create an initial draft addressing the request with relevant details and evidence."
        ),
        "improving_role": "editor",
    },
}

PROTOCOL_DESCRIPTIONS = {
    "simple": (
        "Single-agent response. Use when the request is straightforward or primarily"
        " needs synthesis into one high-quality answer."
    ),
    "critique_and_improve": (
        "Multi-agent workflow with parallel drafting, cross-critique, and refinement."
        " Use for complex, high-stakes, or creative work that benefits from multiple"
        " perspectives."
    ),
}

LEGACY_SYSTEM_PROMPT = """You are the Maestro, an expert planner for a powerful AI orchestration engine. Your job is to analyze a user's prompt and create a JSON object representing a step-by-step plan to fulfill it.

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

SYSTEM_PROMPT = (
    "You are the Maestro planner for the LLMHive collaborative engine. "
    "Select the best reasoning protocol for the user's request.\n\n"
    "Available protocols:\n"
    + "\n".join(
        f"- {name}: {description}" for name, description in PROTOCOL_DESCRIPTIONS.items()
    )
    + "\n\n"
    "Return a JSON object with keys 'reasoning', 'protocol', and 'params'.\n"
    "- 'protocol' must be one of: "
    + ", ".join(PROTOCOL_DESCRIPTIONS.keys())
    + "\n"
    "- 'params' is an object providing protocol-specific configuration.\n"
    "  * For 'simple', include 'role' (agent role) and optional 'task'.\n"
    "  * For 'critique_and_improve', include 'drafting_roles' (list of roles),\n"
    "    'drafting_task' (instructions for draft creation), and 'improving_role'.\n"
    "Do not include additional keys."
)


class Planner:
    """Protocol-aware planner that can also service the legacy step planner API."""

    def __init__(self, preferred_protocol: Optional[str] = None):
        self._preferred_protocol = (
            preferred_protocol.strip().lower() if preferred_protocol else None
        )
        # Backwards compatible attribute expected by existing tests and tooling.
        self.preferred_protocol = self._preferred_protocol
        preferred_model_id = settings.PLANNING_MODEL or "gpt-4o"
        llm = model_pool.get_llm(preferred_model_id)
        if llm is None:
            llm = model_pool.get_llm("gpt-4o")
        if llm is None:
            raise RuntimeError(
                "Planning model unavailable in the model pool; cannot initialize Planner."
            )
        self.llm = llm

    def plan(self, prompt: str) -> Plan:
        """Legacy planner interface that returns a step-based plan."""

        plan_str = self.llm.generate(
            prompt,
            system_prompt=LEGACY_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
        )
        return Plan.model_validate_json(plan_str)

    async def create_plan(self, prompt: str) -> Plan:
        """Select a reasoning protocol and configuration for the collaborative engine."""

        if self._preferred_protocol:
            protocol = self._normalize_protocol(self._preferred_protocol)
            return Plan(
                reasoning=(
                    "User explicitly requested the "
                    f"'{protocol}' protocol; skipping planner LLM call."
                ),
                protocol=protocol,
                params=self._default_params(protocol),
            )

        try:
            raw_plan = await asyncio.to_thread(
                self.llm.generate,
                prompt,
                system_prompt=SYSTEM_PROMPT,
                response_format={"type": "json_object"},
            )
            plan = Plan.model_validate_json(raw_plan)
        except (ValidationError, ValueError) as exc:
            logger.warning(
                "Planner LLM returned an invalid payload; using fallback simple protocol: %s",
                exc,
            )
            return Plan(
                reasoning="Planner fallback: defaulting to simple protocol.",
                protocol=DEFAULT_PROTOCOL,
                params=self._default_params(DEFAULT_PROTOCOL),
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Planner LLM call failed; using fallback simple protocol.", exc_info=exc)
            return Plan(
                reasoning="Planner failed; defaulting to simple protocol.",
                protocol=DEFAULT_PROTOCOL,
                params=self._default_params(DEFAULT_PROTOCOL),
            )

        return self._merge_with_defaults(plan)

    def _normalize_protocol(self, protocol: Optional[str]) -> str:
        if not protocol:
            return DEFAULT_PROTOCOL
        normalized = protocol.strip().lower()
        if normalized not in DEFAULT_PROTOCOL_PARAMS:
            return DEFAULT_PROTOCOL
        return normalized

    def _default_params(self, protocol: str) -> Dict[str, Any]:
        defaults = DEFAULT_PROTOCOL_PARAMS.get(protocol, DEFAULT_PROTOCOL_PARAMS[DEFAULT_PROTOCOL])
        return {**defaults}

    def _merge_with_defaults(self, plan: Plan) -> Plan:
        protocol = self._normalize_protocol(plan.protocol)
        merged_params = self._default_params(protocol)
        merged_params.update(plan.params or {})
        reasoning = plan.reasoning or f"Planner selected the '{protocol}' protocol."
        return Plan(
            reasoning=reasoning,
            protocol=protocol,
            params=merged_params,
            steps=plan.steps,
        )
