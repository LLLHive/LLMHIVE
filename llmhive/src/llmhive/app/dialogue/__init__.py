"""Proactive and Clarifying Dialogue System for LLMHive.

This module provides intelligent dialogue capabilities:
- Ambiguity detection in user queries
- Clarification request handling
- Proactive suggestions and follow-ups
- Task scheduling and reminders

Usage:
    from llmhive.app.dialogue import (
        DialogueManager,
        ClarificationDetector,
        SuggestionEngine,
        TaskScheduler,
    )
    
    # Process response for dialogue elements
    dm = get_dialogue_manager()
    result = dm.process_response(llm_output)
    
    if result.needs_clarification:
        return result.clarification_question
    
    if result.has_suggestions:
        # Include suggestions in response
        pass
"""
from __future__ import annotations

# Ambiguity detection
try:
    from .ambiguity import (
        AmbiguityDetector,
        AmbiguityResult,
        AmbiguityType,
        detect_ambiguity,
    )
    AMBIGUITY_AVAILABLE = True
except ImportError:
    AMBIGUITY_AVAILABLE = False
    AmbiguityDetector = None  # type: ignore

# Clarification handling
try:
    from .clarification import (
        ClarificationHandler,
        ClarificationRequest,
        ClarificationState,
        get_clarification_handler,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError:
    CLARIFICATION_AVAILABLE = False
    ClarificationHandler = None  # type: ignore

# Proactive suggestions
try:
    from .suggestions import (
        SuggestionEngine,
        Suggestion,
        SuggestionType,
        get_suggestion_engine,
    )
    SUGGESTIONS_AVAILABLE = True
except ImportError:
    SUGGESTIONS_AVAILABLE = False
    SuggestionEngine = None  # type: ignore

# Task scheduler
try:
    from .scheduler import (
        TaskScheduler,
        ScheduledTask,
        TaskStatus,
        get_task_scheduler,
    )
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    TaskScheduler = None  # type: ignore

# Dialogue manager
try:
    from .manager import (
        DialogueManager,
        DialogueResult,
        DialogueState,
        get_dialogue_manager,
    )
    MANAGER_AVAILABLE = True
except ImportError:
    MANAGER_AVAILABLE = False
    DialogueManager = None  # type: ignore


__all__ = []

if AMBIGUITY_AVAILABLE:
    __all__.extend([
        "AmbiguityDetector",
        "AmbiguityResult",
        "AmbiguityType",
        "detect_ambiguity",
    ])

if CLARIFICATION_AVAILABLE:
    __all__.extend([
        "ClarificationHandler",
        "ClarificationRequest",
        "ClarificationState",
        "get_clarification_handler",
    ])

if SUGGESTIONS_AVAILABLE:
    __all__.extend([
        "SuggestionEngine",
        "Suggestion",
        "SuggestionType",
        "get_suggestion_engine",
    ])

if SCHEDULER_AVAILABLE:
    __all__.extend([
        "TaskScheduler",
        "ScheduledTask",
        "TaskStatus",
        "get_task_scheduler",
    ])

if MANAGER_AVAILABLE:
    __all__.extend([
        "DialogueManager",
        "DialogueResult",
        "DialogueState",
        "get_dialogue_manager",
    ])

