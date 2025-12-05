"""Audit & Compliance Agent for LLMHive.

This agent monitors system decisions for compliance, transparency,
and provides explainability for AI actions.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of auditable events."""
    QUERY_RECEIVED = "query_received"
    MODEL_SELECTED = "model_selected"
    TOOL_INVOKED = "tool_invoked"
    RESPONSE_GENERATED = "response_generated"
    FILTER_APPLIED = "filter_applied"
    ERROR_OCCURRED = "error_occurred"
    POLICY_VIOLATION = "policy_violation"
    USER_FEEDBACK = "user_feedback"
    CONFIG_CHANGED = "config_changed"
    AGENT_ACTION = "agent_action"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    UNKNOWN = "unknown"


@dataclass
class AuditEvent:
    """A single auditable event."""
    id: str
    event_type: AuditEventType
    timestamp: datetime
    
    # Context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    query_id: Optional[str] = None
    
    # Event details
    description: str = ""
    component: str = ""  # Which component generated this
    action: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Compliance
    compliance_status: ComplianceStatus = ComplianceStatus.COMPLIANT
    policy_checks: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    
    # Performance
    latency_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "description": self.description,
            "component": self.component,
            "compliance_status": self.compliance_status.value,
            "violations": self.violations,
            "latency_ms": self.latency_ms,
        }


@dataclass
class AuditTrail:
    """A complete audit trail for a query/session."""
    trail_id: str
    session_id: str
    started_at: datetime
    
    events: List[AuditEvent] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    
    # Summary
    total_events: int = 0
    compliance_violations: int = 0
    warnings: int = 0
    total_latency_ms: float = 0.0
    
    def add_event(self, event: AuditEvent):
        """Add an event to the trail."""
        self.events.append(event)
        self.total_events += 1
        
        if event.compliance_status == ComplianceStatus.VIOLATION:
            self.compliance_violations += 1
        elif event.compliance_status == ComplianceStatus.WARNING:
            self.warnings += 1
        
        if event.latency_ms:
            self.total_latency_ms += event.latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trail_id": self.trail_id,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_events": self.total_events,
            "compliance_violations": self.compliance_violations,
            "warnings": self.warnings,
            "total_latency_ms": self.total_latency_ms,
            "events": [e.to_dict() for e in self.events],
        }


@dataclass  
class CompliancePolicy:
    """A compliance policy to check against."""
    id: str
    name: str
    description: str
    category: str  # data_privacy, content_safety, rate_limiting, etc.
    check_function: Optional[str] = None  # Name of check function
    enabled: bool = True
    severity: str = "warning"  # warning, violation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "enabled": self.enabled,
            "severity": self.severity,
        }


# Default compliance policies
DEFAULT_POLICIES = [
    CompliancePolicy(
        id="pii_detection",
        name="PII Detection",
        description="Check for personally identifiable information in responses",
        category="data_privacy",
        check_function="check_pii",
        severity="violation",
    ),
    CompliancePolicy(
        id="content_safety",
        name="Content Safety",
        description="Check for harmful or inappropriate content",
        category="content_safety",
        check_function="check_content_safety",
        severity="violation",
    ),
    CompliancePolicy(
        id="rate_limit_compliance",
        name="Rate Limit Compliance",
        description="Ensure rate limits are respected",
        category="rate_limiting",
        check_function="check_rate_limits",
        severity="warning",
    ),
    CompliancePolicy(
        id="model_attribution",
        name="Model Attribution",
        description="Ensure AI responses are properly attributed",
        category="transparency",
        check_function="check_attribution",
        severity="warning",
    ),
    CompliancePolicy(
        id="data_retention",
        name="Data Retention",
        description="Ensure data retention policies are followed",
        category="data_privacy",
        check_function="check_data_retention",
        severity="warning",
    ),
]


class AuditAgent(BaseAgent):
    """Agent that monitors compliance and provides explainability.
    
    Responsibilities:
    - Monitor all agent actions and system events
    - Ensure policy compliance
    - Log decisions for traceability
    - Generate explanation reports
    - Flag anomalous behavior
    - Provide audit trails
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="audit_agent",
                agent_type=AgentType.PERSISTENT,
                priority=AgentPriority.HIGH,
                max_tokens_per_run=2000,
                allowed_tools=["log_analyzer"],
                memory_namespace="audit",
            )
        super().__init__(config)
        
        # Audit storage
        self._audit_log: List[AuditEvent] = []
        self._trails: Dict[str, AuditTrail] = {}
        self._policies: List[CompliancePolicy] = list(DEFAULT_POLICIES)
        
        # Statistics
        self._total_events: int = 0
        self._total_violations: int = 0
        self._total_warnings: int = 0
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute audit tasks.
        
        Task types:
        - "log_event": Log an audit event
        - "get_trail": Get audit trail for a session
        - "check_compliance": Run compliance checks on content
        - "generate_report": Generate compliance report
        - "get_policies": List compliance policies
        - "explain_decision": Explain a system decision
        - "get_statistics": Get audit statistics
        
        Returns:
            AgentResult with audit data
        """
        start_time = time.time()
        
        if task is None:
            return await self._get_summary()
        
        task_type = task.task_type
        payload = task.payload or {}
        
        try:
            if task_type == "log_event":
                result = self._log_event(payload)
            elif task_type == "get_trail":
                result = self._get_trail(payload)
            elif task_type == "check_compliance":
                result = await self._check_compliance(payload)
            elif task_type == "generate_report":
                result = await self._generate_report(payload)
            elif task_type == "get_policies":
                result = self._get_policies(payload)
            elif task_type == "explain_decision":
                result = await self._explain_decision(payload)
            elif task_type == "get_statistics":
                result = self._get_statistics()
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown task type: {task_type}",
                )
            
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result
            
        except Exception as e:
            logger.exception("Audit agent error: %s", e)
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _log_event(self, payload: Dict[str, Any]) -> AgentResult:
        """Log an audit event."""
        event_type_str = payload.get("event_type", "agent_action")
        try:
            event_type = AuditEventType(event_type_str)
        except ValueError:
            event_type = AuditEventType.AGENT_ACTION
        
        event = AuditEvent(
            id=f"evt-{int(time.time() * 1000)}",
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=payload.get("session_id"),
            user_id=payload.get("user_id"),
            query_id=payload.get("query_id"),
            description=payload.get("description", ""),
            component=payload.get("component", "unknown"),
            action=payload.get("action", ""),
            inputs=payload.get("inputs", {}),
            outputs=payload.get("outputs", {}),
            latency_ms=payload.get("latency_ms"),
            tokens_used=payload.get("tokens_used"),
        )
        
        # Run compliance checks
        self._run_policy_checks(event, payload)
        
        # Store event
        self._audit_log.append(event)
        self._total_events += 1
        
        if event.compliance_status == ComplianceStatus.VIOLATION:
            self._total_violations += 1
        elif event.compliance_status == ComplianceStatus.WARNING:
            self._total_warnings += 1
        
        # Add to trail if session exists
        session_id = event.session_id
        if session_id:
            if session_id not in self._trails:
                self._trails[session_id] = AuditTrail(
                    trail_id=f"trail-{session_id}",
                    session_id=session_id,
                    started_at=datetime.now(),
                )
            self._trails[session_id].add_event(event)
        
        return AgentResult(
            success=True,
            output={
                "event_id": event.id,
                "compliance_status": event.compliance_status.value,
                "violations": event.violations,
            },
        )
    
    def _run_policy_checks(self, event: AuditEvent, payload: Dict[str, Any]):
        """Run compliance policy checks on an event."""
        content = payload.get("content", "")
        
        for policy in self._policies:
            if not policy.enabled:
                continue
            
            event.policy_checks.append(policy.id)
            
            # Run check based on policy
            violation = self._check_policy(policy, content, payload)
            
            if violation:
                event.violations.append(f"{policy.name}: {violation}")
                if policy.severity == "violation":
                    event.compliance_status = ComplianceStatus.VIOLATION
                elif event.compliance_status != ComplianceStatus.VIOLATION:
                    event.compliance_status = ComplianceStatus.WARNING
    
    def _check_policy(
        self, 
        policy: CompliancePolicy, 
        content: str,
        payload: Dict[str, Any],
    ) -> Optional[str]:
        """Check a specific policy. Returns violation message if failed."""
        content_lower = content.lower()
        
        if policy.id == "pii_detection":
            # Simple PII patterns
            pii_patterns = [
                "social security", "ssn", "credit card",
                "@", ".com",  # Email indicators
            ]
            for pattern in pii_patterns:
                if pattern in content_lower:
                    return f"Potential PII detected: {pattern}"
        
        elif policy.id == "content_safety":
            # Check for harmful content indicators
            unsafe_patterns = [
                "how to hack", "make a bomb", "illegal",
            ]
            for pattern in unsafe_patterns:
                if pattern in content_lower:
                    return f"Potentially unsafe content: {pattern}"
        
        elif policy.id == "rate_limit_compliance":
            rate_exceeded = payload.get("rate_limit_exceeded", False)
            if rate_exceeded:
                return "Rate limit was exceeded"
        
        elif policy.id == "model_attribution":
            models_used = payload.get("models_used", [])
            if not models_used:
                return "No model attribution provided"
        
        return None  # No violation
    
    def _get_trail(self, payload: Dict[str, Any]) -> AgentResult:
        """Get audit trail for a session."""
        session_id = payload.get("session_id")
        if not session_id:
            return AgentResult(success=False, error="No session_id provided")
        
        trail = self._trails.get(session_id)
        if not trail:
            return AgentResult(
                success=True,
                output={"message": "No audit trail found for session"},
            )
        
        return AgentResult(
            success=True,
            output=trail.to_dict(),
        )
    
    async def _check_compliance(self, payload: Dict[str, Any]) -> AgentResult:
        """Check compliance for specific content."""
        content = payload.get("content", "")
        
        violations = []
        warnings = []
        
        for policy in self._policies:
            if not policy.enabled:
                continue
            
            violation = self._check_policy(policy, content, payload)
            
            if violation:
                if policy.severity == "violation":
                    violations.append({
                        "policy": policy.name,
                        "message": violation,
                    })
                else:
                    warnings.append({
                        "policy": policy.name,
                        "message": violation,
                    })
        
        status = ComplianceStatus.COMPLIANT
        if violations:
            status = ComplianceStatus.VIOLATION
        elif warnings:
            status = ComplianceStatus.WARNING
        
        return AgentResult(
            success=True,
            output={
                "status": status.value,
                "violations": violations,
                "warnings": warnings,
                "policies_checked": len(self._policies),
            },
        )
    
    async def _generate_report(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate a compliance report."""
        time_range = payload.get("time_range", "24h")
        include_details = payload.get("include_details", False)
        
        # Calculate time filter
        now = datetime.now()
        if time_range == "1h":
            cutoff = now - timedelta(hours=1)
        elif time_range == "24h":
            cutoff = now - timedelta(hours=24)
        elif time_range == "7d":
            cutoff = now - timedelta(days=7)
        else:
            cutoff = now - timedelta(hours=24)
        
        # Filter events
        relevant_events = [
            e for e in self._audit_log 
            if e.timestamp >= cutoff
        ]
        
        # Calculate statistics
        violations = [e for e in relevant_events if e.compliance_status == ComplianceStatus.VIOLATION]
        warnings = [e for e in relevant_events if e.compliance_status == ComplianceStatus.WARNING]
        
        # Group by component
        by_component: Dict[str, int] = {}
        for event in relevant_events:
            by_component[event.component] = by_component.get(event.component, 0) + 1
        
        # Group by event type
        by_type: Dict[str, int] = {}
        for event in relevant_events:
            by_type[event.event_type.value] = by_type.get(event.event_type.value, 0) + 1
        
        report = {
            "time_range": time_range,
            "generated_at": now.isoformat(),
            "summary": {
                "total_events": len(relevant_events),
                "violations": len(violations),
                "warnings": len(warnings),
                "compliance_rate": (
                    (len(relevant_events) - len(violations)) / len(relevant_events)
                    if relevant_events else 1.0
                ),
            },
            "by_component": by_component,
            "by_event_type": by_type,
            "active_policies": len([p for p in self._policies if p.enabled]),
        }
        
        if include_details:
            report["violations"] = [e.to_dict() for e in violations]
            report["warnings"] = [e.to_dict() for e in warnings]
        
        return AgentResult(
            success=True,
            output=report,
        )
    
    def _get_policies(self, payload: Dict[str, Any]) -> AgentResult:
        """Get list of compliance policies."""
        category = payload.get("category")
        
        policies = self._policies
        if category:
            policies = [p for p in policies if p.category == category]
        
        return AgentResult(
            success=True,
            output={
                "total": len(policies),
                "policies": [p.to_dict() for p in policies],
            },
        )
    
    async def _explain_decision(self, payload: Dict[str, Any]) -> AgentResult:
        """Explain a system decision for transparency."""
        query_id = payload.get("query_id")
        session_id = payload.get("session_id")
        
        # Find relevant events
        events = []
        
        if query_id:
            events = [e for e in self._audit_log if e.query_id == query_id]
        elif session_id:
            trail = self._trails.get(session_id)
            if trail:
                events = trail.events
        
        if not events:
            return AgentResult(
                success=True,
                output={"message": "No events found for explanation"},
            )
        
        # Build explanation
        explanation = {
            "query_id": query_id or "N/A",
            "session_id": session_id or "N/A",
            "steps": [],
            "models_used": [],
            "tools_used": [],
            "compliance_checks": [],
        }
        
        for event in events:
            step = {
                "timestamp": event.timestamp.isoformat(),
                "action": event.action or event.description,
                "component": event.component,
            }
            explanation["steps"].append(step)
            
            if event.event_type == AuditEventType.MODEL_SELECTED:
                model = event.outputs.get("model", "unknown")
                if model not in explanation["models_used"]:
                    explanation["models_used"].append(model)
            
            if event.event_type == AuditEventType.TOOL_INVOKED:
                tool = event.action
                if tool not in explanation["tools_used"]:
                    explanation["tools_used"].append(tool)
            
            if event.policy_checks:
                for check in event.policy_checks:
                    if check not in explanation["compliance_checks"]:
                        explanation["compliance_checks"].append(check)
        
        explanation["total_steps"] = len(explanation["steps"])
        
        return AgentResult(
            success=True,
            output=explanation,
        )
    
    def _get_statistics(self) -> AgentResult:
        """Get overall audit statistics."""
        return AgentResult(
            success=True,
            output={
                "total_events": self._total_events,
                "total_violations": self._total_violations,
                "total_warnings": self._total_warnings,
                "active_trails": len(self._trails),
                "compliance_rate": (
                    (self._total_events - self._total_violations) / self._total_events
                    if self._total_events > 0 else 1.0
                ),
                "policies_count": len(self._policies),
            },
        )
    
    async def _get_summary(self) -> AgentResult:
        """Get audit summary (default action)."""
        return self._get_statistics()
    
    # Public methods for other components to use
    
    def log_query(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Log a query received event."""
        event_id = f"evt-{int(time.time() * 1000)}"
        event = AuditEvent(
            id=event_id,
            event_type=AuditEventType.QUERY_RECEIVED,
            timestamp=datetime.now(),
            session_id=session_id,
            user_id=user_id,
            description="Query received",
            component="orchestrator",
            action="receive_query",
            inputs={"query_length": len(query)},
        )
        self._audit_log.append(event)
        return event_id
    
    def log_model_selection(
        self,
        model: str,
        session_id: str,
        reason: str = "",
    ):
        """Log a model selection event."""
        event = AuditEvent(
            id=f"evt-{int(time.time() * 1000)}",
            event_type=AuditEventType.MODEL_SELECTED,
            timestamp=datetime.now(),
            session_id=session_id,
            description=f"Selected model: {model}",
            component="model_router",
            action="select_model",
            outputs={"model": model, "reason": reason},
        )
        self._audit_log.append(event)
    
    def log_tool_invocation(
        self,
        tool_name: str,
        session_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        latency_ms: float,
    ):
        """Log a tool invocation event."""
        event = AuditEvent(
            id=f"evt-{int(time.time() * 1000)}",
            event_type=AuditEventType.TOOL_INVOKED,
            timestamp=datetime.now(),
            session_id=session_id,
            description=f"Invoked tool: {tool_name}",
            component="tool_broker",
            action=tool_name,
            inputs=inputs,
            outputs=outputs,
            latency_ms=latency_ms,
        )
        self._audit_log.append(event)
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Audit & Compliance Agent",
            "type": "persistent",
            "purpose": "Monitor compliance and provide explainability",
            "task_types": [
                "log_event",
                "get_trail",
                "check_compliance",
                "generate_report",
                "get_policies",
                "explain_decision",
                "get_statistics",
            ],
            "policies_count": len(self._policies),
            "total_events_logged": self._total_events,
        }
