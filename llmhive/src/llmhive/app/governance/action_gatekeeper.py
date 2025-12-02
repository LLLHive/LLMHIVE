"""Action Gatekeeper - Pre-action safety checks."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class GateDecision(Enum):
    """Possible gatekeeper decisions."""
    ALLOW = auto()           # Action permitted
    DENY = auto()            # Action blocked
    REQUIRE_APPROVAL = auto()  # Needs human approval
    MODIFY = auto()          # Action modified (e.g., sanitized)


@dataclass
class ApprovalRequest:
    """Request for human approval of an action."""
    request_id: str
    action_type: str
    action_details: Dict[str, Any]
    reason: str
    requested_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class ActionGatekeeper:
    """Gates actions before execution with safety checks.
    
    Features:
    - Pre-execution validation
    - Approval workflows for high-risk actions
    - Action modification/sanitization
    - Audit trail for all decisions
    """
    
    def __init__(self):
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._approval_history: List[ApprovalRequest] = []
        
        # Action risk classification
        self._high_risk_actions = {
            "delete_data": "Deletes user or system data",
            "send_email": "Sends email on behalf of user",
            "make_payment": "Initiates financial transaction",
            "system_command": "Executes system-level command",
            "external_api_call": "Calls external API with user data",
        }
        
        self._medium_risk_actions = {
            "web_search": "Performs web search",
            "file_write": "Writes to file system",
            "database_query": "Queries database",
        }
        
        logger.info("ActionGatekeeper initialized")
    
    async def check(
        self,
        action_type: str,
        action_details: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> tuple[GateDecision, Optional[str], Optional[Dict]]:
        """Check if an action should be allowed.
        
        Args:
            action_type: Type of action
            action_details: Details of the action
            user_id: Optional user identifier
            
        Returns:
            Tuple of (decision, reason, modified_action)
        """
        # Check if high-risk
        if action_type in self._high_risk_actions:
            return await self._handle_high_risk(
                action_type, action_details, user_id
            )
        
        # Check if medium-risk
        if action_type in self._medium_risk_actions:
            return await self._handle_medium_risk(
                action_type, action_details, user_id
            )
        
        # Low-risk: allow with logging
        return (GateDecision.ALLOW, "Low-risk action permitted", None)
    
    async def _handle_high_risk(
        self,
        action_type: str,
        action_details: Dict,
        user_id: Optional[str]
    ) -> tuple[GateDecision, Optional[str], Optional[Dict]]:
        """Handle high-risk action."""
        risk_description = self._high_risk_actions[action_type]
        
        # Create approval request
        request = ApprovalRequest(
            request_id=f"approval-{datetime.now().timestamp()}",
            action_type=action_type,
            action_details=action_details,
            reason=f"High-risk action: {risk_description}",
        )
        
        self._pending_approvals[request.request_id] = request
        
        return (
            GateDecision.REQUIRE_APPROVAL,
            f"Requires approval: {risk_description}",
            {"approval_request_id": request.request_id}
        )
    
    async def _handle_medium_risk(
        self,
        action_type: str,
        action_details: Dict,
        user_id: Optional[str]
    ) -> tuple[GateDecision, Optional[str], Optional[Dict]]:
        """Handle medium-risk action."""
        # For medium risk, apply modifications/safeguards
        modified_details = dict(action_details)
        
        if action_type == "file_write":
            # Ensure writing to allowed directory
            path = modified_details.get("path", "")
            if not path.startswith("/tmp/") and not path.startswith("./output/"):
                modified_details["path"] = f"/tmp/{path}"
                return (
                    GateDecision.MODIFY,
                    "Path modified to safe location",
                    modified_details
                )
        
        if action_type == "database_query":
            # Add read-only flag if not specified
            if "read_only" not in modified_details:
                modified_details["read_only"] = True
                return (
                    GateDecision.MODIFY,
                    "Query restricted to read-only",
                    modified_details
                )
        
        return (GateDecision.ALLOW, "Medium-risk action with safeguards", None)
    
    def approve_action(
        self,
        request_id: str,
        approved_by: str,
        approved: bool = True
    ) -> bool:
        """Approve or deny a pending approval request.
        
        Args:
            request_id: Approval request ID
            approved_by: Approver identifier
            approved: Whether to approve
            
        Returns:
            True if request was found and updated
        """
        request = self._pending_approvals.get(request_id)
        if not request:
            return False
        
        request.approved = approved
        request.approved_by = approved_by
        request.approved_at = datetime.now()
        
        # Move to history
        self._approval_history.append(request)
        del self._pending_approvals[request_id]
        
        logger.info(
            f"Action {request.action_type} {'approved' if approved else 'denied'} "
            f"by {approved_by}"
        )
        
        return True
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        return [
            {
                "request_id": r.request_id,
                "action_type": r.action_type,
                "reason": r.reason,
                "requested_at": r.requested_at.isoformat(),
            }
            for r in self._pending_approvals.values()
        ]
    
    def check_approval_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Check status of an approval request."""
        # Check pending
        if request_id in self._pending_approvals:
            return {
                "status": "pending",
                "request": self._pending_approvals[request_id],
            }
        
        # Check history
        for req in self._approval_history:
            if req.request_id == request_id:
                return {
                    "status": "completed",
                    "approved": req.approved,
                    "approved_by": req.approved_by,
                    "approved_at": req.approved_at.isoformat() if req.approved_at else None,
                }
        
        return None

