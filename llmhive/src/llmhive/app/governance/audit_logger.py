"""Audit Logger - Decision and action logging."""
from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """An entry in the audit log."""
    entry_id: str
    entry_type: str  # "decision", "action", "content_block", "error"
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Who
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    instance_id: Optional[str] = None
    
    # What
    action_type: Optional[str] = None
    action_details: Dict[str, Any] = field(default_factory=dict)
    
    # Why
    rationale: str = ""
    policies_applied: List[str] = field(default_factory=list)
    chain_of_thought: Optional[str] = None
    
    # Outcome
    decision: Optional[str] = None  # "approved", "denied", "modified"
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    parent_entry_id: Optional[str] = None  # For tracing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Comprehensive audit logging for governance.
    
    Features:
    - Decision logging with rationale
    - Action tracking with context
    - Content block logging
    - Queryable audit trail
    - Export capabilities
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """Initialize audit logger.
        
        Args:
            persist_path: Optional path to persist logs
        """
        self._entries: List[AuditEntry] = []
        self._persist_path = persist_path
        self._max_memory_entries = 10000
        
        logger.info("AuditLogger initialized")
    
    async def log_decision(
        self,
        decision_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        approved: bool,
        policies_applied: List[str],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        rationale: str = "",
        context: Optional[Dict] = None,
    ) -> AuditEntry:
        """Log a governance decision.
        
        Args:
            decision_id: Unique decision identifier
            action_type: Type of action being decided on
            action_details: Details of the action
            approved: Whether action was approved
            policies_applied: Policies that were checked
            user_id: Optional user identifier
            agent_id: Optional agent identifier
            rationale: Reason for decision
            context: Additional context
            
        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            entry_id=decision_id,
            entry_type="decision",
            user_id=user_id,
            agent_id=agent_id,
            action_type=action_type,
            action_details=action_details,
            rationale=rationale,
            policies_applied=policies_applied,
            decision="approved" if approved else "denied",
            context=context or {},
        )
        
        self._add_entry(entry)
        return entry
    
    async def log_action(
        self,
        action_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        result: Any,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        duration_ms: int = 0,
        error: Optional[str] = None,
    ) -> AuditEntry:
        """Log an executed action.
        
        Args:
            action_id: Unique action identifier
            action_type: Type of action
            action_details: Details of the action
            result: Result of the action
            agent_id: Agent that performed action
            user_id: User who initiated
            duration_ms: Execution duration
            error: Error if any
            
        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            entry_id=action_id,
            entry_type="action",
            agent_id=agent_id,
            user_id=user_id,
            action_type=action_type,
            action_details=action_details,
            result=str(result) if result else None,
            error=error,
            context={"duration_ms": duration_ms},
        )
        
        self._add_entry(entry)
        return entry
    
    async def log_content_block(
        self,
        decision_id: str,
        content_type: str,
        issues: List[str],
        user_id: Optional[str] = None,
    ) -> AuditEntry:
        """Log a content block event.
        
        Args:
            decision_id: Decision identifier
            content_type: Type of content blocked
            issues: Issues that caused the block
            user_id: User whose content was blocked
            
        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            entry_id=decision_id,
            entry_type="content_block",
            user_id=user_id,
            action_type=f"content_{content_type}",
            decision="blocked",
            rationale="; ".join(issues),
            policies_applied=["content_safety"],
        )
        
        self._add_entry(entry)
        return entry
    
    async def log_chain_of_thought(
        self,
        entry_id: str,
        agent_id: str,
        thought: str,
        parent_entry_id: Optional[str] = None,
    ) -> AuditEntry:
        """Log reasoning chain for explainability.
        
        Args:
            entry_id: Entry identifier
            agent_id: Agent doing the reasoning
            thought: The reasoning text
            parent_entry_id: Parent entry for tracing
            
        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            entry_id=entry_id,
            entry_type="reasoning",
            agent_id=agent_id,
            chain_of_thought=thought,
            parent_entry_id=parent_entry_id,
        )
        
        self._add_entry(entry)
        return entry
    
    def _add_entry(self, entry: AuditEntry) -> None:
        """Add entry to log and optionally persist."""
        self._entries.append(entry)
        
        # Persist if path configured
        if self._persist_path:
            self._persist_entry(entry)
        
        # Trim memory if too large
        if len(self._entries) > self._max_memory_entries:
            self._entries = self._entries[-self._max_memory_entries:]
    
    def _persist_entry(self, entry: AuditEntry) -> None:
        """Persist entry to file."""
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "a") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to persist audit entry: {e}")
    
    def query(
        self,
        entry_type: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        action_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Query audit entries.
        
        Args:
            entry_type: Filter by entry type
            user_id: Filter by user
            agent_id: Filter by agent
            action_type: Filter by action type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum entries to return
            
        Returns:
            Matching audit entries
        """
        results = []
        
        for entry in reversed(self._entries):
            if entry_type and entry.entry_type != entry_type:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            if action_type and entry.action_type != action_type:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            
            results.append(entry)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get specific entry by ID."""
        for entry in reversed(self._entries):
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def get_trace(self, entry_id: str) -> List[AuditEntry]:
        """Get full trace of entries related to a decision.
        
        Follows parent_entry_id links to build complete trace.
        """
        trace = []
        current_id = entry_id
        seen = set()
        
        while current_id and current_id not in seen:
            seen.add(current_id)
            entry = self.get_entry(current_id)
            if entry:
                trace.append(entry)
                current_id = entry.parent_entry_id
            else:
                break
        
        return list(reversed(trace))
    
    def export(
        self,
        format: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Export audit entries.
        
        Args:
            format: Export format ("json" or "csv")
            start_time: Filter start
            end_time: Filter end
            
        Returns:
            Exported data as string
        """
        entries = self.query(
            start_time=start_time,
            end_time=end_time,
            limit=100000,
        )
        
        if format == "json":
            return json.dumps([e.to_dict() for e in entries], indent=2, default=str)
        
        # CSV format
        if not entries:
            return ""
        
        headers = ["entry_id", "timestamp", "entry_type", "action_type", "decision", "user_id", "agent_id"]
        lines = [",".join(headers)]
        
        for entry in entries:
            row = [
                entry.entry_id,
                entry.timestamp.isoformat(),
                entry.entry_type or "",
                entry.action_type or "",
                entry.decision or "",
                entry.user_id or "",
                entry.agent_id or "",
            ]
            lines.append(",".join(f'"{v}"' for v in row))
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        type_counts: Dict[str, int] = {}
        decision_counts: Dict[str, int] = {}
        
        for entry in self._entries:
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1
            if entry.decision:
                decision_counts[entry.decision] = decision_counts.get(entry.decision, 0) + 1
        
        return {
            "total_entries": len(self._entries),
            "by_type": type_counts,
            "by_decision": decision_counts,
            "persist_path": self._persist_path,
        }


# Global audit logger
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger."""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger

