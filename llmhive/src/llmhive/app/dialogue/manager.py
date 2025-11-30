"""Dialogue Manager for LLMHive.

Central manager for all dialogue capabilities:
- Ambiguity detection and clarification
- Proactive suggestions
- Task scheduling
- Response processing

Usage:
    dm = get_dialogue_manager()
    
    # Pre-process query
    pre_result = await dm.pre_process_query(query, session_id)
    if pre_result.needs_clarification:
        return pre_result.clarification_response
    
    # Process LLM response
    result = await dm.process_response(llm_output, session_id)
    
    # Use result.final_response with result.suggestions
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .ambiguity import AmbiguityDetector, AmbiguityResult, detect_ambiguity
from .clarification import (
    ClarificationHandler,
    ClarificationRequest,
    ClarificationState,
    ParsedResponse,
    get_clarification_handler,
)
from .suggestions import (
    SuggestionEngine,
    Suggestion,
    SuggestionType,
    get_suggestion_engine,
)
from .scheduler import (
    TaskScheduler,
    ScheduledTask,
    parse_reminder_request,
    get_task_scheduler,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class DialogueState(str, Enum):
    """State of dialogue interaction."""
    NORMAL = "normal"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    PROCESSING_SCHEDULE = "processing_schedule"


@dataclass(slots=True)
class PreProcessResult:
    """Result of query pre-processing."""
    should_proceed: bool
    modified_query: str
    original_query: str
    
    # Clarification
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # Schedule detection
    is_schedule_request: bool = False
    schedule_info: Optional[Dict[str, Any]] = None
    
    # Context
    context_added: str = ""
    
    def get_response(self) -> Optional[str]:
        """Get response if processing should not proceed."""
        if self.needs_clarification:
            return self.clarification_question
        return None


@dataclass(slots=True)
class DialogueResult:
    """Result of dialogue processing."""
    final_response: str
    raw_response: str
    
    # Clarification
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # Suggestions
    suggestions: List[Suggestion] = field(default_factory=list)
    
    # Scheduled tasks
    scheduled_tasks: List[ScheduledTask] = field(default_factory=list)
    
    # State
    state: DialogueState = DialogueState.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.final_response,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "scheduled_tasks": [t.to_dict() for t in self.scheduled_tasks],
            "state": self.state.value,
        }


# ==============================================================================
# Dialogue Manager
# ==============================================================================

class DialogueManager:
    """Central manager for dialogue capabilities.
    
    Coordinates:
    - Ambiguity detection before processing
    - Clarification handling
    - Response processing for tags
    - Suggestion generation
    - Task scheduling
    
    Usage:
        dm = DialogueManager()
        
        # Pre-process query
        pre = await dm.pre_process_query(
            query="Tell me about Python",
            session_id="session123",
        )
        
        if not pre.should_proceed:
            return pre.get_response()
        
        # ... get LLM response ...
        
        # Post-process response
        result = await dm.process_response(
            response=llm_output,
            query=query,
            session_id="session123",
            user_tier="pro",
        )
        
        # Return result.final_response with result.suggestions
    """
    
    def __init__(
        self,
        clarification_handler: Optional[ClarificationHandler] = None,
        suggestion_engine: Optional[SuggestionEngine] = None,
        task_scheduler: Optional[TaskScheduler] = None,
        enable_clarification: bool = True,
        enable_suggestions: bool = True,
        enable_scheduling: bool = True,
    ):
        self.clarification_handler = clarification_handler or get_clarification_handler()
        self.suggestion_engine = suggestion_engine or get_suggestion_engine()
        self.task_scheduler = task_scheduler or get_task_scheduler()
        
        self.enable_clarification = enable_clarification
        self.enable_suggestions = enable_suggestions
        self.enable_scheduling = enable_scheduling
        
        # Session state
        self._session_states: Dict[str, DialogueState] = {}
    
    async def pre_process_query(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        check_ambiguity: bool = True,
        check_schedule: bool = True,
    ) -> PreProcessResult:
        """
        Pre-process a query before sending to LLM.
        
        Args:
            query: User's query
            session_id: Session ID
            user_id: User ID (for scheduling)
            check_ambiguity: Whether to check for ambiguity
            check_schedule: Whether to check for schedule requests
            
        Returns:
            PreProcessResult indicating how to proceed
        """
        modified_query = query
        context_added = ""
        
        # Check for pending clarification
        if self.clarification_handler.has_pending(session_id):
            # User is responding to clarification
            pending = self.clarification_handler.get_pending(session_id)
            if pending:
                self.clarification_handler.resolve_clarification(session_id, query)
                
                # Build clarified query
                modified_query = self.clarification_handler.build_clarified_query(
                    pending.original_query, query
                )
                context_added = "clarification"
                
                return PreProcessResult(
                    should_proceed=True,
                    modified_query=modified_query,
                    original_query=query,
                    context_added=context_added,
                )
        
        # Check for schedule request
        if check_schedule and self.enable_scheduling:
            schedule_result = await self._check_schedule_request(query, user_id, session_id)
            if schedule_result:
                return schedule_result
        
        # Check for ambiguity
        if check_ambiguity and self.enable_clarification:
            should_clarify, clarification = self.clarification_handler.should_request_clarification(
                query, session_id
            )
            
            if should_clarify and clarification:
                # Create clarification request
                self.clarification_handler.create_clarification(
                    session_id, query, clarification
                )
                self._session_states[session_id] = DialogueState.AWAITING_CLARIFICATION
                
                return PreProcessResult(
                    should_proceed=False,
                    modified_query=query,
                    original_query=query,
                    needs_clarification=True,
                    clarification_question=clarification,
                )
        
        return PreProcessResult(
            should_proceed=True,
            modified_query=modified_query,
            original_query=query,
            context_added=context_added,
        )
    
    async def _check_schedule_request(
        self,
        query: str,
        user_id: Optional[str],
        session_id: str,
    ) -> Optional[PreProcessResult]:
        """Check if query is a schedule/reminder request."""
        result = parse_reminder_request(query)
        
        if result and user_id:
            delay, task_message = result
            
            # Schedule the reminder
            task = await self.task_scheduler.schedule_reminder(
                user_id=user_id,
                message=task_message,
                delay_seconds=int(delay.total_seconds()),
                session_id=session_id,
            )
            
            # Format confirmation message
            if delay.total_seconds() < 3600:
                time_str = f"{int(delay.total_seconds() / 60)} minutes"
            elif delay.total_seconds() < 86400:
                time_str = f"{int(delay.total_seconds() / 3600)} hours"
            else:
                time_str = f"{int(delay.total_seconds() / 86400)} days"
            
            confirmation = f"✓ I'll remind you to '{task_message}' in {time_str}."
            
            return PreProcessResult(
                should_proceed=False,
                modified_query=query,
                original_query=query,
                is_schedule_request=True,
                schedule_info={
                    "task_id": task.id,
                    "message": task_message,
                    "run_at": task.run_at.isoformat(),
                    "confirmation": confirmation,
                },
            )
        
        return None
    
    async def process_response(
        self,
        response: str,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        user_tier: str = "free",
        generate_suggestions: bool = True,
    ) -> DialogueResult:
        """
        Process LLM response for dialogue elements.
        
        Args:
            response: LLM response
            query: Original user query
            session_id: Session ID
            user_id: User ID
            user_tier: User's tier
            generate_suggestions: Whether to generate suggestions
            
        Returns:
            DialogueResult with processed response
        """
        # Parse for [CLARIFY] tags
        parsed = self.clarification_handler.parse_response(response, session_id)
        
        if parsed.needs_clarification:
            # Create clarification request
            self.clarification_handler.create_clarification(
                session_id, query, parsed.clarification_question or ""
            )
            self._session_states[session_id] = DialogueState.AWAITING_CLARIFICATION
            
            return DialogueResult(
                final_response=parsed.clarification_question or "",
                raw_response=response,
                needs_clarification=True,
                clarification_question=parsed.clarification_question,
                clarification_options=parsed.clarification_options,
                state=DialogueState.AWAITING_CLARIFICATION,
            )
        
        # Parse for [SUGGEST] tags
        clean_response, suggestions_from_tags = self.suggestion_engine.parse_suggestions(
            parsed.clean_response
        )
        
        # Generate additional suggestions if enabled
        all_suggestions = list(suggestions_from_tags)
        if generate_suggestions and self.enable_suggestions:
            generated = self.suggestion_engine.generate_suggestions(
                query=query,
                response=clean_response,
                session_id=session_id,
                user_tier=user_tier,
            )
            all_suggestions.extend(generated)
        
        # Deduplicate suggestions
        seen_texts = set()
        unique_suggestions = []
        for s in all_suggestions:
            if s.text not in seen_texts:
                seen_texts.add(s.text)
                unique_suggestions.append(s)
        
        self._session_states[session_id] = DialogueState.NORMAL
        
        return DialogueResult(
            final_response=clean_response,
            raw_response=response,
            suggestions=unique_suggestions[:3],  # Limit to 3
            state=DialogueState.NORMAL,
        )
    
    def get_session_state(self, session_id: str) -> DialogueState:
        """Get current dialogue state for session."""
        return self._session_states.get(session_id, DialogueState.NORMAL)
    
    def clear_session(self, session_id: str) -> None:
        """Clear all dialogue state for a session."""
        self._session_states.pop(session_id, None)
        self.clarification_handler.clear_session(session_id)
        self.suggestion_engine.reset_session(session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dialogue system statistics."""
        return {
            "sessions_tracked": len(self._session_states),
            "clarification_stats": self.clarification_handler.get_stats(),
            "suggestion_stats": self.suggestion_engine.get_stats(),
            "scheduler_stats": self.task_scheduler.get_stats(),
        }


# ==============================================================================
# Combined System Prompt
# ==============================================================================

DIALOGUE_SYSTEM_PROMPT = """You are a helpful assistant with advanced dialogue capabilities.

## Clarification
When a query is ambiguous or unclear, ask for clarification using [CLARIFY] tags:
[CLARIFY]Your clarifying question here.
- Option 1
- Option 2[/CLARIFY]

Only ask when genuinely needed. Clear questions should be answered directly.

## Suggestions
After answering, you may offer helpful suggestions using [SUGGEST] tags:
[SUGGEST]Would you like more details about X?[/SUGGEST]

Keep suggestions relevant and concise. Don't suggest for simple questions.

## Reminders
If the user asks you to remind them of something, acknowledge and confirm:
"I'll remind you to [task] in [time]."

## Guidelines
- Be helpful but not overly verbose
- Ask clarifying questions only when necessary
- Offer suggestions sparingly (for complex topics)
- Always prioritize answering the user's actual question
"""


# ==============================================================================
# Global Instance
# ==============================================================================

_dialogue_manager: Optional[DialogueManager] = None


def get_dialogue_manager() -> DialogueManager:
    """Get or create global dialogue manager."""
    global _dialogue_manager
    if _dialogue_manager is None:
        _dialogue_manager = DialogueManager()
    return _dialogue_manager

