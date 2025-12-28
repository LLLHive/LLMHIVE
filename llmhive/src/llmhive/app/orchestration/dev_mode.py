"""Dev Mode and Collaboration Features for LLMHive Orchestrator.

Implements:
- Dev Mode toggle for agent debugging
- Answer explanation generation
- Collaboration session support
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Environment variable to enable dev mode globally
DEV_MODE_ENABLED = os.environ.get("LLMHIVE_DEV_MODE", "false").lower() == "true"


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
