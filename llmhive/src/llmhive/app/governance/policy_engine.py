"""Policy Engine - Rule evaluation and management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum, auto
from datetime import datetime

logger = logging.getLogger(__name__)


class PolicyCategory(Enum):
    """Categories of governance policies."""
    DATA_PRIVACY = auto()
    SECURITY = auto()
    ETHICAL = auto()
    OPERATIONAL = auto()
    COMPLIANCE = auto()


@dataclass
class Policy:
    """A governance policy definition."""
    policy_id: str
    name: str
    category: PolicyCategory
    description: str
    
    # Rule definition
    applies_to: List[str]  # Action types this applies to
    conditions: List[Dict[str, Any]]  # Conditions to check
    effect: str  # "allow", "deny", "require_approval"
    
    # Metadata
    severity: str = "medium"  # low, medium, high, critical
    enabled: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    allowed: bool
    reason: str
    policies_checked: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # Conditions to meet
    confidence: float = 1.0


class PolicyEngine:
    """Evaluates actions against governance policies.
    
    Features:
    - Rule-based policy evaluation
    - Policy versioning
    - Category-based organization
    - Conflict resolution
    """
    
    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._load_default_policies()
        
        logger.info("PolicyEngine initialized")
    
    def _load_default_policies(self) -> None:
        """Load default policies."""
        # Data Privacy Policy
        self.add_policy(Policy(
            policy_id="privacy-pii",
            name="PII Protection",
            category=PolicyCategory.DATA_PRIVACY,
            description="Prevent exposure of personally identifiable information",
            applies_to=["*"],  # All actions
            conditions=[
                {"type": "no_pii_in_output"},
            ],
            effect="deny",
            severity="high",
        ))
        
        # Security Policy
        self.add_policy(Policy(
            policy_id="security-sandbox",
            name="Code Sandbox Enforcement",
            category=PolicyCategory.SECURITY,
            description="All code execution must be sandboxed",
            applies_to=["code_execute", "script_run"],
            conditions=[
                {"type": "sandbox_enabled"},
                {"type": "timeout_set"},
            ],
            effect="require_approval",
            severity="high",
        ))
        
        # Ethical Policy
        self.add_policy(Policy(
            policy_id="ethical-no-harm",
            name="No Harmful Content",
            category=PolicyCategory.ETHICAL,
            description="Prevent generation of harmful or dangerous content",
            applies_to=["content_generate", "response_output"],
            conditions=[
                {"type": "no_harmful_instructions"},
                {"type": "no_hate_speech"},
            ],
            effect="deny",
            severity="critical",
        ))
        
        # Operational Policy
        self.add_policy(Policy(
            policy_id="ops-rate-limit",
            name="API Rate Limiting",
            category=PolicyCategory.OPERATIONAL,
            description="Prevent excessive API calls",
            applies_to=["external_api_call", "web_search"],
            conditions=[
                {"type": "within_rate_limit"},
            ],
            effect="deny",
            severity="medium",
        ))
    
    def add_policy(self, policy: Policy) -> None:
        """Add or update a policy."""
        self._policies[policy.policy_id] = policy
        logger.debug(f"Added policy: {policy.policy_id}")
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    async def evaluate(
        self,
        action_type: str,
        action_details: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """Evaluate an action against all applicable policies.
        
        Args:
            action_type: Type of action
            action_details: Details of the action
            context: Optional context
            
        Returns:
            PolicyDecision with result
        """
        applicable_policies = self._get_applicable_policies(action_type)
        
        if not applicable_policies:
            return PolicyDecision(
                allowed=True,
                reason="No applicable policies",
                policies_checked=[],
            )
        
        checked = []
        conditions_to_meet = []
        denied_reason = None
        
        for policy in applicable_policies:
            checked.append(policy.policy_id)
            
            # Evaluate conditions
            evaluation = await self._evaluate_conditions(
                policy.conditions, action_details, context
            )
            
            if not evaluation["passed"]:
                if policy.effect == "deny":
                    denied_reason = (
                        f"Policy '{policy.name}' violated: {evaluation['reason']}"
                    )
                    break
                elif policy.effect == "require_approval":
                    conditions_to_meet.append(
                        f"{policy.name}: {evaluation['reason']}"
                    )
        
        if denied_reason:
            return PolicyDecision(
                allowed=False,
                reason=denied_reason,
                policies_checked=checked,
            )
        
        return PolicyDecision(
            allowed=True,
            reason="All policies passed",
            policies_checked=checked,
            conditions=conditions_to_meet,
        )
    
    def _get_applicable_policies(self, action_type: str) -> List[Policy]:
        """Get policies that apply to an action type."""
        applicable = []
        
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            
            if "*" in policy.applies_to or action_type in policy.applies_to:
                applicable.append(policy)
        
        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        applicable.sort(key=lambda p: severity_order.get(p.severity, 2))
        
        return applicable
    
    async def _evaluate_conditions(
        self,
        conditions: List[Dict],
        action_details: Dict,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Evaluate policy conditions."""
        for condition in conditions:
            condition_type = condition.get("type", "")
            
            # Evaluate each condition type
            if condition_type == "no_pii_in_output":
                # Check for PII patterns
                output = action_details.get("output", "")
                if isinstance(output, str):
                    pii_patterns = ["ssn", "credit card", "password"]
                    for pattern in pii_patterns:
                        if pattern in output.lower():
                            return {"passed": False, "reason": f"PII detected: {pattern}"}
            
            elif condition_type == "sandbox_enabled":
                if not action_details.get("sandbox", False):
                    return {"passed": False, "reason": "Sandbox not enabled"}
            
            elif condition_type == "timeout_set":
                if "timeout" not in action_details:
                    return {"passed": False, "reason": "Timeout not set"}
            
            elif condition_type == "no_harmful_instructions":
                content = action_details.get("content", "")
                # In production: use actual harmful content classifier
                pass
            
            elif condition_type == "within_rate_limit":
                # Rate limit checked by kernel
                pass
        
        return {"passed": True, "reason": "All conditions satisfied"}
    
    def list_policies(
        self,
        category: Optional[PolicyCategory] = None
    ) -> List[Dict[str, Any]]:
        """List all policies, optionally filtered by category."""
        policies = []
        
        for policy in self._policies.values():
            if category and policy.category != category:
                continue
            
            policies.append({
                "policy_id": policy.policy_id,
                "name": policy.name,
                "category": policy.category.name,
                "severity": policy.severity,
                "enabled": policy.enabled,
                "applies_to": policy.applies_to,
            })
        
        return policies

