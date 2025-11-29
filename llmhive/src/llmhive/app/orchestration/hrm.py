"""Hierarchical Role Management (HRM) system for LLMHive orchestrator.

HRM implements a hierarchical role structure where roles have parent-child relationships,
inherited permissions, and role-based access control. This enables sophisticated multi-agent
coordination with clear authority chains and responsibility delegation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class RoleLevel(str, Enum):
    """Hierarchical levels in the role structure."""

    EXECUTIVE = "executive"  # Top-level decision making
    MANAGER = "manager"  # Coordination and oversight
    SPECIALIST = "specialist"  # Domain expertise
    ASSISTANT = "assistant"  # Support and execution


@dataclass(slots=True)
class RolePermission:
    """Represents a permission that can be granted to a role."""

    name: str
    description: str
    scope: str  # "read", "write", "execute", "approve", "delegate"


@dataclass(slots=True)
class HRMRole:
    """Represents a role in the hierarchical role management system."""

    name: str
    level: RoleLevel
    parent: Optional[str] = None  # Name of parent role
    children: List[str] = field(default_factory=list)  # Names of child roles
    permissions: Set[str] = field(default_factory=set)  # Permission names
    capabilities: Set[str] = field(default_factory=set)  # Required capabilities
    description: str = ""
    max_delegations: int = 3  # Maximum number of sub-roles this role can delegate to

    def can_delegate_to(self, target_role: HRMRole) -> bool:
        """Check if this role can delegate to the target role."""
        if self.max_delegations <= 0:
            return False
        # Executive can delegate to any role
        if self.level == RoleLevel.EXECUTIVE:
            return True
        # Manager can delegate to specialist and assistant
        if self.level == RoleLevel.MANAGER:
            return target_role.level in (RoleLevel.SPECIALIST, RoleLevel.ASSISTANT)
        # Specialist can delegate to assistant
        if self.level == RoleLevel.SPECIALIST:
            return target_role.level == RoleLevel.ASSISTANT
        # Assistant cannot delegate
        return False

    def has_permission(self, permission: str) -> bool:
        """Check if this role has a specific permission."""
        return permission in self.permissions

    def inherits_from(self, role_name: str, role_hierarchy: Dict[str, HRMRole]) -> bool:
        """Check if this role inherits from the given role (directly or indirectly)."""
        if self.parent is None:
            return False
        if self.parent == role_name:
            return True
        parent_role = role_hierarchy.get(self.parent)
        if parent_role is None:
            return False
        return parent_role.inherits_from(role_name, role_hierarchy)


class HRMRegistry:
    """Registry for managing hierarchical roles and their relationships."""

    def __init__(self) -> None:
        self.roles: Dict[str, HRMRole] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self) -> None:
        """Initialize the default HRM role hierarchy."""
        # Executive level
        executive = HRMRole(
            name="executive",
            level=RoleLevel.EXECUTIVE,
            parent=None,
            permissions={"approve", "delegate", "execute", "read", "write"},
            capabilities={"reasoning", "synthesis", "decision_making"},
            description="Top-level decision maker with full authority",
            max_delegations=5,
        )

        # Manager level
        coordinator = HRMRole(
            name="coordinator",
            level=RoleLevel.MANAGER,
            parent="executive",
            permissions={"delegate", "execute", "read", "write"},
            capabilities={"coordination", "synthesis", "analysis"},
            description="Coordinates multiple specialists and synthesizes outputs",
            max_delegations=4,
        )
        executive.children.append("coordinator")

        quality_manager = HRMRole(
            name="quality_manager",
            level=RoleLevel.MANAGER,
            parent="executive",
            permissions={"approve", "read", "write"},
            capabilities={"critical_thinking", "validation", "quality_assessment"},
            description="Manages quality control and validation processes",
            max_delegations=3,
        )
        executive.children.append("quality_manager")

        # Specialist level
        lead_researcher = HRMRole(
            name="lead_researcher",
            level=RoleLevel.SPECIALIST,
            parent="coordinator",
            permissions={"execute", "read", "write", "delegate"},
            capabilities={"retrieval", "research", "analysis"},
            description="Leads research efforts and delegates to research assistants",
            max_delegations=2,
        )
        coordinator.children.append("lead_researcher")

        lead_analyst = HRMRole(
            name="lead_analyst",
            level=RoleLevel.SPECIALIST,
            parent="coordinator",
            permissions={"execute", "read", "write", "delegate"},
            capabilities={"analysis", "reasoning", "synthesis"},
            description="Leads analytical work and delegates to analysis assistants",
            max_delegations=2,
        )
        coordinator.children.append("lead_analyst")

        fact_checker = HRMRole(
            name="fact_checker",
            level=RoleLevel.SPECIALIST,
            parent="quality_manager",
            permissions={"read", "write"},
            capabilities={"fact_checking", "validation", "verification"},
            description="Verifies factual accuracy of claims",
            max_delegations=1,
        )
        quality_manager.children.append("fact_checker")

        critic = HRMRole(
            name="critic",
            level=RoleLevel.SPECIALIST,
            parent="quality_manager",
            permissions={"read", "write"},
            capabilities={"critical_thinking", "evaluation", "quality_assessment"},
            description="Critically evaluates outputs for quality and accuracy",
            max_delegations=1,
        )
        quality_manager.children.append("critic")

        # Assistant level
        research_assistant = HRMRole(
            name="research_assistant",
            level=RoleLevel.ASSISTANT,
            parent="lead_researcher",
            permissions={"read", "write"},
            capabilities={"retrieval", "summarization"},
            description="Assists with research tasks under lead researcher supervision",
            max_delegations=0,
        )
        lead_researcher.children.append("research_assistant")

        analysis_assistant = HRMRole(
            name="analysis_assistant",
            level=RoleLevel.ASSISTANT,
            parent="lead_analyst",
            permissions={"read", "write"},
            capabilities={"analysis", "summarization"},
            description="Assists with analysis tasks under lead analyst supervision",
            max_delegations=0,
        )
        lead_analyst.children.append("analysis_assistant")

        # Register all roles
        for role in [
            executive,
            coordinator,
            quality_manager,
            lead_researcher,
            lead_analyst,
            fact_checker,
            critic,
            research_assistant,
            analysis_assistant,
        ]:
            self.roles[role.name] = role

    def get_role(self, name: str) -> Optional[HRMRole]:
        """Get a role by name."""
        return self.roles.get(name)

    def get_children(self, role_name: str) -> List[HRMRole]:
        """Get all direct children of a role."""
        role = self.roles.get(role_name)
        if role is None:
            return []
        return [self.roles[child] for child in role.children if child in self.roles]

    def get_descendants(self, role_name: str) -> List[HRMRole]:
        """Get all descendants (children, grandchildren, etc.) of a role."""
        descendants: List[HRMRole] = []
        role = self.roles.get(role_name)
        if role is None:
            return descendants

        for child_name in role.children:
            child_role = self.roles.get(child_name)
            if child_role:
                descendants.append(child_role)
                descendants.extend(self.get_descendants(child_name))

        return descendants

    def get_ancestors(self, role_name: str) -> List[HRMRole]:
        """Get all ancestors (parent, grandparent, etc.) of a role."""
        ancestors: List[HRMRole] = []
        role = self.roles.get(role_name)
        if role is None or role.parent is None:
            return ancestors

        parent = self.roles.get(role.parent)
        if parent:
            ancestors.append(parent)
            ancestors.extend(self.get_ancestors(role.parent))

        return ancestors

    def can_delegate(self, from_role: str, to_role: str) -> bool:
        """Check if one role can delegate to another."""
        from_role_obj = self.roles.get(from_role)
        to_role_obj = self.roles.get(to_role)
        if from_role_obj is None or to_role_obj is None:
            return False
        return from_role_obj.can_delegate_to(to_role_obj)

    def get_role_path(self, role_name: str) -> List[str]:
        """Get the full path from root to this role."""
        path: List[str] = []
        role = self.roles.get(role_name)
        if role is None:
            return path

        if role.parent:
            path.extend(self.get_role_path(role.parent))
        path.append(role_name)
        return path

    def get_execution_order(self, roles: List[str]) -> List[str]:
        """Get roles in execution order based on hierarchy (executives first, assistants last)."""
        role_objects = [self.roles[r] for r in roles if r in self.roles]
        # Sort by level priority (executive=0, manager=1, specialist=2, assistant=3)
        level_priority = {
            RoleLevel.EXECUTIVE: 0,
            RoleLevel.MANAGER: 1,
            RoleLevel.SPECIALIST: 2,
            RoleLevel.ASSISTANT: 3,
        }
        role_objects.sort(key=lambda r: level_priority.get(r.level, 99))
        return [r.name for r in role_objects]


# Global HRM registry instance
_hrm_registry: Optional[HRMRegistry] = None


def get_hrm_registry() -> HRMRegistry:
    """Get the global HRM registry instance."""
    global _hrm_registry
    if _hrm_registry is None:
        _hrm_registry = HRMRegistry()
    return _hrm_registry

