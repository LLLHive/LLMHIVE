"""Governance Kernel for LLMHive Opus 6.0.

This module provides self-evolving policy management, safety enforcement,
and auditable decision-making for the orchestration system.

Components:
- GovernanceKernel: Main policy enforcement engine
- PolicyEngine: Rule evaluation and management
- ActionGatekeeper: Pre-action safety checks
- AuditLogger: Decision and action logging
- PolicyEvolution: Automatic policy improvement
- Controls: User and admin preference management
"""
from __future__ import annotations

from .kernel import (
    GovernanceKernel,
    GovernanceConfig,
    get_governance_kernel,
)

from .policy_engine import (
    PolicyEngine,
    Policy,
    PolicyCategory,
    PolicyDecision,
)

from .action_gatekeeper import (
    ActionGatekeeper,
    GateDecision,
    ApprovalRequest,
)

from .audit_logger import (
    AuditLogger,
    AuditEntry,
    get_audit_logger,
)

__all__ = [
    "GovernanceKernel",
    "GovernanceConfig",
    "get_governance_kernel",
    "PolicyEngine",
    "Policy",
    "PolicyCategory",
    "PolicyDecision",
    "ActionGatekeeper",
    "GateDecision",
    "ApprovalRequest",
    "AuditLogger",
    "AuditEntry",
    "get_audit_logger",
]

