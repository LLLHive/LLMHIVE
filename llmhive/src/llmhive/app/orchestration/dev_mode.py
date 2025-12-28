"""Dev Mode and Collaboration Features for LLMHive Orchestrator.

Enhancement-3: Real-time trace emission for debugging orchestration flows.

Implements:
- Dev Mode toggle for agent debugging
- Answer explanation generation
- Collaboration session support
- Real-time trace event emission via WebSocket
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Environment variable to enable dev mode globally
DEV_MODE_ENABLED = os.environ.get("LLMHIVE_DEV_MODE", "false").lower() == "true"


# ==============================================================================
# Enhancement-3: Trace Event System
# ==============================================================================

@dataclass
class TraceEvent:
    """A single trace event for dev mode debugging."""
    timestamp: str
    event_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "timestamp": self.timestamp,
            "type": self.event_type,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        if self.session_id:
            result["session_id"] = self.session_id
        return result


def log_event(
    session_id: str,
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Enhancement-3: Emit a dev-mode trace event with timestamp, to be sent to clients.
    
    This function broadcasts trace events to:
    1. All connected WebSocket clients for the given session
    2. All dev trace subscribers (via /ws/dev/trace endpoint)
    
    Args:
        session_id: The session/chat ID to broadcast to
        event_type: Type of event (e.g., "strategy_selected", "model_call", "tool_invoked")
        message: Human-readable event description
        details: Optional structured details about the event
    """
    if not DEV_MODE_ENABLED and not session_id:
        # Skip if dev mode disabled globally and no session override
        return
    
    event = TraceEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type=event_type,
        message=message,
        details=details,
        session_id=session_id,
    )
    
    event_dict = {"trace_event": event.to_dict()}
    
    # Broadcast to session participants
    try:
        from ..routers.collab import CollabSessionManager
        CollabSessionManager.broadcast(session_id, event_dict)
    except ImportError:
        # Collab router not available yet
        pass
    except Exception as e:
        logger.debug(f"DevMode session broadcast failed: {e}")
    
    # Also broadcast to dev trace subscribers
    try:
        from ..routers.collab import broadcast_trace_event
        asyncio.create_task(broadcast_trace_event(event_dict))
    except RuntimeError:
        # No event loop available
        pass
    except Exception as e:
        logger.debug(f"DevMode trace broadcast failed: {e}")
    
    # Also log to server console for debugging
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"[DevMode] {event_type}: {message}")


def log_strategy_selected(session_id: str, strategy_name: str, reason: str = "") -> None:
    """Log when a strategy is selected."""
    log_event(
        session_id,
        "strategy_selected",
        f"Strategy chosen: {strategy_name}",
        {"strategy": strategy_name, "reason": reason}
    )


def log_model_call(session_id: str, model: str, prompt_preview: str = "") -> None:
    """Log when a model is being called."""
    preview = prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview
    log_event(
        session_id,
        "model_call",
        f"Calling model {model}",
        {"model": model, "prompt_preview": preview}
    )


def log_model_response(session_id: str, model: str, tokens_used: int = 0, latency_ms: float = 0) -> None:
    """Log when a model responds."""
    log_event(
        session_id,
        "model_response",
        f"Model {model} responded",
        {"model": model, "tokens": tokens_used, "latency_ms": round(latency_ms, 2)}
    )


def log_tool_invoked(session_id: str, tool_type: str, query: str = "") -> None:
    """Log when a tool is invoked."""
    query_preview = query[:100] + "..." if len(query) > 100 else query
    log_event(
        session_id,
        "tool_invoked",
        f"Tool invoked: {tool_type}",
        {"tool_type": tool_type, "query": query_preview}
    )


def log_tool_result(session_id: str, tool_type: str, success: bool, latency_ms: float = 0) -> None:
    """Log when a tool returns a result."""
    status = "succeeded" if success else "failed"
    log_event(
        session_id,
        "tool_result",
        f"Tool {tool_type} {status}",
        {"tool_type": tool_type, "success": success, "latency_ms": round(latency_ms, 2)}
    )


def log_verification_result(session_id: str, passed: bool, verdict: str = "") -> None:
    """Log verification/validation result."""
    status = "passed" if passed else "failed"
    log_event(
        session_id,
        "verification",
        f"Verification {status}",
        {"passed": passed, "verdict": verdict}
    )


def log_orchestration_step(session_id: str, step_name: str, description: str = "") -> None:
    """Log a generic orchestration step."""
    log_event(
        session_id,
        "orchestration_step",
        f"Step: {step_name}",
        {"step": step_name, "description": description}
    )


@dataclass
class AgentStep:
    """Record of a single agent execution step."""
    agent_name: str
    action: str
    input_summary: str
    output_summary: str
    duration_ms: float
    success: bool


@dataclass
class DebugSession:
    """Debug information for a dev mode session."""
    query: str
    steps: List[AgentStep] = field(default_factory=list)
    strategy_used: str = ""
    pipeline_used: str = ""
    technique_ids: List[str] = field(default_factory=list)
    total_duration_ms: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_step(self, step: AgentStep):
        """Add an agent step to the debug log."""
        self.steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query[:100] + "..." if len(self.query) > 100 else self.query,
            "strategy_used": self.strategy_used,
            "pipeline_used": self.pipeline_used,
            "technique_ids": self.technique_ids,
            "total_duration_ms": self.total_duration_ms,
            "step_count": len(self.steps),
            "tool_calls": len(self.tool_calls),
            "steps": [
                {
                    "agent": s.agent_name,
                    "action": s.action,
                    "success": s.success,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
        }


def is_dev_mode() -> bool:
    """Check if dev mode is enabled."""
    return DEV_MODE_ENABLED


def generate_explanation(
    final_answer: str,
    strategy: str,
    agents_used: List[str],
    tools_used: List[str],
    verification_passed: bool,
) -> str:
    """
    Generate a user-friendly explanation of how an answer was produced.
    
    Args:
        final_answer: The final answer text
        strategy: The orchestration strategy used
        agents_used: List of agent names that contributed
        tools_used: List of tools that were invoked
        verification_passed: Whether the answer passed verification
        
    Returns:
        A plain-English explanation of the orchestration process
    """
    parts = []
    
    parts.append("## How This Answer Was Generated\n")
    
    # Strategy
    strategy_names = {
        "automatic": "Automatic (AI-selected best approach)",
        "single_best": "Single Best Model",
        "parallel_race": "Parallel Race (fastest response wins)",
        "best_of_n": "Best of N (multiple attempts, best selected)",
        "fusion": "Fusion (multiple perspectives merged)",
        "expert_panel": "Expert Panel (domain specialists)",
        "challenge_and_refine": "Challenge & Refine (iterative improvement)",
    }
    strategy_desc = strategy_names.get(strategy, strategy)
    parts.append(f"**Strategy Used:** {strategy_desc}\n")
    
    # Agents
    if agents_used:
        parts.append(f"**Contributing Agents:** {', '.join(agents_used)}\n")
    
    # Tools
    if tools_used:
        parts.append(f"**Tools Invoked:** {', '.join(tools_used)}\n")
    
    # Verification
    if verification_passed:
        parts.append("**Verification:** ✅ Answer passed quality checks\n")
    else:
        parts.append("**Verification:** ⚠️ Limited verification performed\n")
    
    return "\n".join(parts)


@dataclass
class CollaborationSession:
    """A collaborative session that multiple users can join."""
    session_id: str
    owner_id: str
    participants: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = 0.0
    
    def add_participant(self, user_id: str) -> bool:
        """Add a participant to the session."""
        if user_id not in self.participants:
            self.participants.append(user_id)
            return True
        return False
    
    def remove_participant(self, user_id: str) -> bool:
        """Remove a participant from the session."""
        if user_id in self.participants:
            self.participants.remove(user_id)
            return True
        return False


# Session registry (in-memory for now)
_sessions: Dict[str, CollaborationSession] = {}


def create_session(session_id: str, owner_id: str) -> CollaborationSession:
    """Create a new collaboration session."""
    import time
    session = CollaborationSession(
        session_id=session_id,
        owner_id=owner_id,
        participants=[owner_id],
        created_at=time.time(),
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[CollaborationSession]:
    """Get an existing session by ID."""
    return _sessions.get(session_id)


def join_session(session_id: str, user_id: str) -> bool:
    """Join an existing session."""
    session = _sessions.get(session_id)
    if session:
        return session.add_participant(user_id)
    return False
