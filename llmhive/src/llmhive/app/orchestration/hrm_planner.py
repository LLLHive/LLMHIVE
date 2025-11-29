"""HRM-based planning that uses hierarchical role management for orchestration."""
from __future__ import annotations

from typing import List, Optional, Set

from .hrm import HRMRegistry, HRMRole, RoleLevel, get_hrm_registry
from ..planner import PlanRole, PlanStep, ReasoningPlan


class HRMPlanner:
    """Planner that uses HRM hierarchy to create role-based execution plans."""

    def __init__(self, hrm_registry: Optional[HRMRegistry] = None) -> None:
        self.hrm = hrm_registry or get_hrm_registry()

    def create_hrm_plan(
        self,
        prompt: str,
        *,
        context: Optional[str] = None,
        use_full_hierarchy: bool = False,
    ) -> ReasoningPlan:
        """Create a plan using HRM role hierarchy.

        Args:
            prompt: User's prompt
            context: Optional context from memory
            use_full_hierarchy: If True, uses full hierarchy; if False, uses simplified structure

        Returns:
            ReasoningPlan with HRM-based role assignments
        """
        lowered = prompt.lower()
        focus: List[str] = []
        steps: List[PlanStep] = []

        # Determine complexity and required roles
        is_complex = any(
            keyword in lowered
            for keyword in (
                "research",
                "analyze",
                "compare",
                "evaluate",
                "comprehensive",
                "detailed",
            )
        )
        needs_fact_check = any(
            keyword in lowered
            for keyword in ("fact", "verify", "accurate", "correct", "true")
        )
        is_coding = any(
            keyword in lowered
            for keyword in ("code", "debug", "program", "function", "algorithm")
        )

        if use_full_hierarchy:
            # Full HRM hierarchy: Executive -> Manager -> Specialist -> Assistant
            steps.extend(self._create_full_hierarchy_steps(prompt, is_complex, needs_fact_check, is_coding))
            focus.append("hrm_full_hierarchy")
        else:
            # Simplified HRM: Manager -> Specialist
            steps.extend(self._create_simplified_hierarchy_steps(prompt, is_complex, needs_fact_check, is_coding))
            focus.append("hrm_simplified")

        if context:
            focus.append("contextual_memory")

        # Always end with synthesis (executive role)
        steps.append(
            PlanStep(
                role=PlanRole.SYNTHESIZE,
                description="Executive synthesis: Merge all outputs into final authoritative response",
                required_capabilities={"synthesis", "reasoning", "decision_making"},
                candidate_models=["gpt-4.1", "claude-3-opus-20240229"],
                parallelizable=False,
            )
        )

        strategy = "hrm_hierarchical_orchestration"
        confidence = 0.8 if use_full_hierarchy else 0.75

        return ReasoningPlan(
            strategy=strategy,
            steps=steps,
            confidence=confidence,
            focus_areas=focus,
            context_summary=context,
        )

    def _create_full_hierarchy_steps(
        self,
        prompt: str,
        is_complex: bool,
        needs_fact_check: bool,
        is_coding: bool,
    ) -> List[PlanStep]:
        """Create steps using full HRM hierarchy."""
        steps: List[PlanStep] = []

        # Executive level: High-level coordination (implicit, handled in synthesis)
        # Manager level: Coordinator
        steps.append(
            PlanStep(
                role=PlanRole.DRAFT,  # Coordinator role
                description="Coordinator: Analyze request and delegate to appropriate specialists",
                required_capabilities={"coordination", "analysis", "synthesis"},
                candidate_models=["gpt-4.1", "claude-3-opus-20240229"],
            )
        )

        # Specialist level: Domain experts
        if is_complex or "research" in prompt.lower():
            steps.append(
                PlanStep(
                    role=PlanRole.RESEARCH,  # Lead Researcher
                    description="Lead Researcher: Conduct comprehensive research and delegate to assistants",
                    required_capabilities={"retrieval", "research", "analysis"},
                    candidate_models=["gemini-2.5-flash", "claude-3-sonnet-20240229"],
                )
            )
            # Assistant level: Research Assistant
            steps.append(
                PlanStep(
                    role=PlanRole.RETRIEVAL,  # Research Assistant
                    description="Research Assistant: Gather specific information under lead researcher supervision",
                    required_capabilities={"retrieval", "summarization"},
                    candidate_models=["gpt-4o-mini", "claude-3-haiku-20240307"],
                )
            )

        if needs_fact_check:
            # Specialist: Fact Checker
            steps.append(
                PlanStep(
                    role=PlanRole.FACT_CHECK,  # Fact Checker
                    description="Fact Checker: Verify factual accuracy of claims",
                    required_capabilities={"fact_checking", "validation", "verification"},
                    candidate_models=["gpt-4o-mini", "deepseek-chat"],
                )
            )

        # Manager level: Quality Manager
        steps.append(
            PlanStep(
                role=PlanRole.CRITIQUE,  # Quality Manager / Critic
                description="Quality Manager: Critically evaluate outputs for quality and accuracy",
                required_capabilities={"critical_thinking", "evaluation", "quality_assessment"},
                candidate_models=["grok-3-mini", "deepseek-reasoner"],
            )
        )

        return steps

    def _create_simplified_hierarchy_steps(
        self,
        prompt: str,
        is_complex: bool,
        needs_fact_check: bool,
        is_coding: bool,
    ) -> List[PlanStep]:
        """Create steps using simplified HRM hierarchy (Manager -> Specialist)."""
        steps: List[PlanStep] = []

        # Manager: Coordinator
        steps.append(
            PlanStep(
                role=PlanRole.DRAFT,
                description="Coordinator: Analyze and coordinate response generation",
                required_capabilities={"coordination", "reasoning"},
                candidate_models=["gpt-4o", "claude-3-sonnet-20240229"],
            )
        )

        # Specialists
        if is_complex:
            steps.append(
                PlanStep(
                    role=PlanRole.RESEARCH,
                    description="Lead Researcher: Conduct research and analysis",
                    required_capabilities={"retrieval", "analysis"},
                    candidate_models=["gemini-2.5-flash", "claude-3-sonnet-20240229"],
                )
            )

        if needs_fact_check:
            steps.append(
                PlanStep(
                    role=PlanRole.FACT_CHECK,
                    description="Fact Checker: Verify factual claims",
                    required_capabilities={"fact_checking", "validation"},
                    candidate_models=["gpt-4o-mini", "deepseek-chat"],
                )
            )

        steps.append(
            PlanStep(
                role=PlanRole.CRITIQUE,
                description="Critic: Evaluate quality and accuracy",
                required_capabilities={"critical_thinking", "evaluation"},
                candidate_models=["grok-3-mini", "gpt-4o-mini"],
            )
        )

        return steps

    def map_hrm_role_to_plan_role(self, hrm_role_name: str) -> PlanRole:
        """Map HRM role name to PlanRole enum."""
        mapping = {
            "executive": PlanRole.SYNTHESIZE,
            "coordinator": PlanRole.DRAFT,
            "quality_manager": PlanRole.CRITIQUE,
            "lead_researcher": PlanRole.RESEARCH,
            "lead_analyst": PlanRole.DRAFT,
            "fact_checker": PlanRole.FACT_CHECK,
            "critic": PlanRole.CRITIQUE,
            "research_assistant": PlanRole.RETRIEVAL,
            "analysis_assistant": PlanRole.DRAFT,
        }
        return mapping.get(hrm_role_name, PlanRole.DRAFT)

    def get_execution_order(self, hrm_roles: List[str]) -> List[str]:
        """Get HRM roles in proper execution order based on hierarchy."""
        return self.hrm.get_execution_order(hrm_roles)

