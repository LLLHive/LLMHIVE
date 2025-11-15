from __future__ import annotations

import asyncio

from app.config import settings
from app.orchestration.execution import execute_task

from .base_protocol import BaseProtocol


DEFAULT_DRAFTING_TASK = (
    "Create an initial draft addressing the request with relevant details and evidence."
)
DEFAULT_DRAFTING_ROLES = ["researcher", "analyst"]
DEFAULT_IMPROVING_ROLE = "editor"
CRITIC_ROLE = "critic"


class CritiqueAndImproveProtocol(BaseProtocol):
    async def execute(self) -> None:
        drafting_task = self.params.get("drafting_task", DEFAULT_DRAFTING_TASK)
        drafting_roles = self.params.get("drafting_roles", DEFAULT_DRAFTING_ROLES)
        improving_role = self.params.get("improving_role", DEFAULT_IMPROVING_ROLE)

        available_roles = [
            role for role in drafting_roles if role in self.assignments
        ]
        if not available_roles:
            raise ValueError(
                "No drafting roles were assigned models for Critique & Improve protocol."
            )

        self.blackboard.append_to_list(
            "logs.execution", "Starting Critique & Improve Protocol."
        )

        draft_coros = {
            role: execute_task(
                role, self.assignments[role], drafting_task, self.blackboard
            )
            for role in available_roles
        }
        draft_results = await asyncio.gather(*draft_coros.values())
        drafts = dict(zip(draft_coros.keys(), draft_results))

        critic_model_id = self.assignments.get(CRITIC_ROLE, settings.CRITIQUE_MODEL)
        critique_tasks = {}
        for role, draft in drafts.items():
            critique_prompt = (
                "Critique the following draft from the '{role}' agent. Provide"
                " actionable feedback focused on correctness, completeness, and"
                " clarity.\n\n---\n{draft}\n---"
            ).format(role=role, draft=draft)
            critique_tasks[f"critique_on_{role}"] = execute_task(
                CRITIC_ROLE,
                critic_model_id,
                critique_prompt,
                self.blackboard,
            )

        critiques = dict(
            zip(critique_tasks.keys(), await asyncio.gather(*critique_tasks.values()))
        )

        improvement_tasks = {}
        improving_model_id = self.assignments.get(
            improving_role, self.assignments.get("lead", settings.SYNTHESIS_MODEL)
        )
        for role, draft in drafts.items():
            feedback = critiques.get(f"critique_on_{role}", "No feedback received.")
            improvement_prompt = (
                "Based on the following critique, improve your original draft."
                "\n\nCRITIQUE:\n{feedback}\n\nORIGINAL DRAFT:\n{draft}"
            ).format(feedback=feedback, draft=draft)
            improvement_tasks[f"improved_{role}"] = execute_task(
                improving_role,
                improving_model_id,
                improvement_prompt,
                self.blackboard,
            )

        improved_drafts = dict(
            zip(
                improvement_tasks.keys(),
                await asyncio.gather(*improvement_tasks.values()),
            )
        )

        self.blackboard.set(
            "results.critique_workflow",
            {
                "drafts": drafts,
                "critiques": critiques,
                "improved_drafts": improved_drafts,
            },
        )
        self.blackboard.append_to_list(
            "logs.execution", "Critique & Improve Protocol Complete."
        )
