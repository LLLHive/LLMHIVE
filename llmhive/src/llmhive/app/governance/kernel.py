"""Governance Kernel - Main policy enforcement engine."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GovernanceConfig:
    """Configuration for the governance kernel."""
    enable_content_filtering: bool = True
    enable_action_gating: bool = True
    enable_audit_logging: bool = True
    enable_policy_evolution: bool = False
    
    # Risk thresholds
    high_risk_actions: List[str] = field(default_factory=lambda: [
        "delete_data", "send_email", "make_payment",
        "external_api_call", "system_command"
    ])
    require_approval_for_high_risk: bool = True
    
    # Rate limits
    max_actions_per_minute: int = 60
    max_external_calls_per_minute: int = 20


@dataclass
class GovernanceDecision:
    """A governance decision on an action or output."""
    decision_id: str
    action_type: str
    approved: bool
    conditions: List[str] = field(default_factory=list)
    requires_human_approval: bool = False
    rationale: str = ""
    policies_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class GovernanceKernel:
    """Central governance engine for LLMHive.
    
    Responsibilities:
    - Policy enforcement at all decision points
    - Content filtering for safety
    - Action gating with approval workflows
    - Comprehensive audit logging
    - Policy evolution based on incidents
    """
    
    def __init__(self, config: Optional[GovernanceConfig] = None):
        """Initialize the governance kernel.
        
        Args:
            config: Optional configuration
        """
        self.config = config or GovernanceConfig()
        
        # Sub-components (lazy loaded)
        self._policy_engine = None
        self._action_gatekeeper = None
        self._audit_logger = None
        self._policy_evolution = None
        
        # User/admin controls
        self._user_controls: Dict[str, Dict[str, Any]] = {}
        self._admin_overrides: Dict[str, Any] = {}
        
        # Rate limiting
        self._action_counts: Dict[str, List[datetime]] = {}
        
        logger.info("GovernanceKernel initialized")
    
    @property
    def policy_engine(self):
        """Get policy engine (lazy load)."""
        if self._policy_engine is None:
            from .policy_engine import PolicyEngine
            self._policy_engine = PolicyEngine()
        return self._policy_engine
    
    @property
    def action_gatekeeper(self):
        """Get action gatekeeper (lazy load)."""
        if self._action_gatekeeper is None:
            from .action_gatekeeper import ActionGatekeeper
            self._action_gatekeeper = ActionGatekeeper()
        return self._action_gatekeeper
    
    @property
    def audit_logger(self):
        """Get audit logger (lazy load)."""
        if self._audit_logger is None:
            from .audit_logger import get_audit_logger
            self._audit_logger = get_audit_logger()
        return self._audit_logger
    
    async def check_action(
        self,
        action_type: str,
        action_details: Dict[str, Any],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GovernanceDecision:
        """Check if an action is allowed.
        
        Args:
            action_type: Type of action (e.g., "web_search", "code_execute")
            action_details: Details of the action
            user_id: Optional user identifier
            context: Optional additional context
            
        Returns:
            GovernanceDecision with approval status
        """
        decision_id = f"gov-{datetime.now().timestamp()}"
        policies_applied = []
        conditions = []
        rationale_parts = []
        
        # Check rate limits
        if not self._check_rate_limit(action_type):
            return GovernanceDecision(
                decision_id=decision_id,
                action_type=action_type,
                approved=False,
                rationale="Rate limit exceeded",
                policies_applied=["rate_limit"],
            )
        
        # Check user controls
        if user_id:
            user_controls = self._user_controls.get(user_id, {})
            if not user_controls.get("allow_" + action_type, True):
                return GovernanceDecision(
                    decision_id=decision_id,
                    action_type=action_type,
                    approved=False,
                    rationale="Action disabled by user preference",
                    policies_applied=["user_control"],
                )
        
        # Check if high-risk action requiring approval
        requires_approval = (
            self.config.require_approval_for_high_risk and
            action_type in self.config.high_risk_actions
        )
        
        # Apply policy engine checks
        if self.config.enable_action_gating:
            policy_decision = await self.policy_engine.evaluate(
                action_type, action_details, context
            )
            
            if not policy_decision.allowed:
                return GovernanceDecision(
                    decision_id=decision_id,
                    action_type=action_type,
                    approved=False,
                    rationale=policy_decision.reason,
                    policies_applied=policy_decision.policies_checked,
                )
            
            policies_applied.extend(policy_decision.policies_checked)
            if policy_decision.conditions:
                conditions.extend(policy_decision.conditions)
            
            rationale_parts.append(policy_decision.reason)
        
        # Log the decision
        if self.config.enable_audit_logging:
            await self.audit_logger.log_decision(
                decision_id=decision_id,
                action_type=action_type,
                action_details=action_details,
                approved=True,
                policies_applied=policies_applied,
                user_id=user_id,
            )
        
        return GovernanceDecision(
            decision_id=decision_id,
            action_type=action_type,
            approved=True,
            conditions=conditions,
            requires_human_approval=requires_approval,
            rationale="; ".join(rationale_parts) or "Action permitted",
            policies_applied=policies_applied,
        )
    
    async def check_content(
        self,
        content: str,
        content_type: str = "output",
        user_id: Optional[str] = None,
    ) -> GovernanceDecision:
        """Check if content passes safety filters.
        
        Args:
            content: Content to check
            content_type: Type ("input", "output", "intermediate")
            user_id: Optional user identifier
            
        Returns:
            GovernanceDecision with approval status
        """
        decision_id = f"content-{datetime.now().timestamp()}"
        
        if not self.config.enable_content_filtering:
            return GovernanceDecision(
                decision_id=decision_id,
                action_type=f"content_{content_type}",
                approved=True,
                rationale="Content filtering disabled",
            )
        
        # Apply content policies
        issues = []
        
        # Basic safety checks (in production, use proper classifiers)
        harmful_patterns = [
            "how to make a bomb",
            "instructions for hacking",
            "create malware",
        ]
        
        content_lower = content.lower()
        for pattern in harmful_patterns:
            if pattern in content_lower:
                issues.append(f"Potentially harmful content detected: {pattern}")
        
        # PII detection (simplified)
        pii_indicators = ["ssn:", "credit card:", "password:"]
        for indicator in pii_indicators:
            if indicator in content_lower:
                issues.append(f"Potential PII detected: {indicator}")
        
        if issues:
            # Log the block
            if self.config.enable_audit_logging:
                await self.audit_logger.log_content_block(
                    decision_id=decision_id,
                    content_type=content_type,
                    issues=issues,
                    user_id=user_id,
                )
            
            return GovernanceDecision(
                decision_id=decision_id,
                action_type=f"content_{content_type}",
                approved=False,
                rationale=f"Content blocked: {issues[0]}",
                policies_applied=["content_safety"],
            )
        
        return GovernanceDecision(
            decision_id=decision_id,
            action_type=f"content_{content_type}",
            approved=True,
            rationale="Content passed safety checks",
            policies_applied=["content_safety"],
        )
    
    def _check_rate_limit(self, action_type: str) -> bool:
        """Check if action is within rate limits."""
        now = datetime.now()
        
        # Get or create action history
        if action_type not in self._action_counts:
            self._action_counts[action_type] = []
        
        # Remove old entries (older than 1 minute)
        one_minute_ago = datetime.now().timestamp() - 60
        self._action_counts[action_type] = [
            t for t in self._action_counts[action_type]
            if t.timestamp() > one_minute_ago
        ]
        
        # Check limit
        current_count = len(self._action_counts[action_type])
        limit = self.config.max_actions_per_minute
        
        if action_type.startswith("external"):
            limit = self.config.max_external_calls_per_minute
        
        if current_count >= limit:
            return False
        
        # Record this action
        self._action_counts[action_type].append(now)
        return True
    
    def set_user_control(
        self,
        user_id: str,
        control_name: str,
        value: Any
    ) -> None:
        """Set a user preference/control.
        
        Args:
            user_id: User identifier
            control_name: Name of control (e.g., "allow_web_search")
            value: Control value
        """
        if user_id not in self._user_controls:
            self._user_controls[user_id] = {}
        
        self._user_controls[user_id][control_name] = value
        logger.info(f"Set user control {control_name}={value} for {user_id}")
    
    def get_user_controls(self, user_id: str) -> Dict[str, Any]:
        """Get all controls for a user."""
        return self._user_controls.get(user_id, {})
    
    async def explain_decision(self, decision_id: str) -> Dict[str, Any]:
        """Get explanation for a governance decision.
        
        Args:
            decision_id: Decision identifier
            
        Returns:
            Explanation with rationale and policies
        """
        # In production, look up from audit log
        return {
            "decision_id": decision_id,
            "explanation": "Decision details retrieved from audit log",
            "policies": [],
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return {
            "config": {
                "content_filtering": self.config.enable_content_filtering,
                "action_gating": self.config.enable_action_gating,
                "audit_logging": self.config.enable_audit_logging,
            },
            "user_controls_count": len(self._user_controls),
            "rate_limit_status": {
                action: len(counts)
                for action, counts in self._action_counts.items()
            },
        }


# Global governance kernel
_global_kernel: Optional[GovernanceKernel] = None


def get_governance_kernel() -> GovernanceKernel:
    """Get or create global governance kernel."""
    global _global_kernel
    if _global_kernel is None:
        _global_kernel = GovernanceKernel()
    return _global_kernel

