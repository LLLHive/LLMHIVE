"""Autonomous Agent Framework for LLMHive Opus 5.0.

This module provides the infrastructure for persistent background agents
that continuously improve and monitor the system.

Agent Types:
- Persistent: Run continuously in background (R&D, QA, Audit)
- Scheduled: Run on a schedule (Benchmarking, Adversarial)
- On-demand: Triggered by queries (Vision, Audio, Code)

Architecture:
- AgentSupervisor: Manages agent lifecycle
- BaseAgent: Abstract base class for all agents
- AgentBlackboard: Shared memory for inter-agent communication
- AgentScheduler: Cron-like scheduling for background agents
"""
from __future__ import annotations

from .base import (
    BaseAgent,
    AgentConfig,
    AgentStatus,
    AgentResult,
    AgentPriority,
)

from .supervisor import (
    AgentSupervisor,
    get_agent_supervisor,
)

from .blackboard import (
    AgentBlackboard,
    BlackboardEntry,
    get_global_blackboard,
)

from .scheduler import (
    AgentScheduler,
    ScheduleConfig,
    get_agent_scheduler,
)

# Specialist Agents
from .research_agent import ResearchAgent
from .qa_agent import QualityAssuranceAgent
from .benchmark_agent import BenchmarkAgent
from .planning_agent import PlanningAgent
from .adversarial_agent import AdversarialAgent
from .audit_agent import AuditAgent
from .vision_agent import VisionAgent
from .audio_agent import AudioAgent
from .code_agent import CodeExecutionAgent
from .personalization_agent import PersonalizationAgent

__all__ = [
    # Core framework
    "BaseAgent",
    "AgentConfig",
    "AgentStatus",
    "AgentResult",
    "AgentPriority",
    "AgentSupervisor",
    "get_agent_supervisor",
    "AgentBlackboard",
    "BlackboardEntry",
    "get_global_blackboard",
    "AgentScheduler",
    "ScheduleConfig",
    "get_agent_scheduler",
    # Specialist agents
    "ResearchAgent",
    "QualityAssuranceAgent",
    "BenchmarkAgent",
    "PlanningAgent",
    "AdversarialAgent",
    "AuditAgent",
    "VisionAgent",
    "AudioAgent",
    "CodeExecutionAgent",
    "PersonalizationAgent",
]

