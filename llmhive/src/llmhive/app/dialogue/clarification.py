"""Clarification Handling for LLMHive.

Manages the clarification dialogue flow:
- Parsing [CLARIFY] tags from LLM output
- Tracking clarification state per session
- Handling user responses to clarifications

Usage:
    handler = get_clarification_handler()
    
    # Check if response needs clarification
    result = handler.parse_response(llm_output)
    if result.needs_clarification:
        # Return clarification question to user
        return result.clarification_question
    
    # Resume after user provides clarification
    clarified_query = handler.build_clarified_query(
        original_query, user_response
    )
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

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class ClarificationState(str, Enum):
    """State of clarification dialogue."""
    NONE = "none"  # No clarification needed
    AWAITING_RESPONSE = "awaiting_response"  # Waiting for user
    RECEIVED = "received"  # User responded
    RESOLVED = "resolved"  # Clarification complete
    SKIPPED = "skipped"  # User skipped/cancelled


@dataclass(slots=True)
class ClarificationRequest:
    """A clarification request."""
    id: str
    session_id: str
    original_query: str
    clarification_question: str
    state: ClarificationState
    created_at: datetime
    options: List[str] = field(default_factory=list)
    user_response: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "original_query": self.original_query,
            "clarification_question": self.clarification_question,
            "state": self.state.value,
            "options": self.options,
            "user_response": self.user_response,
        }


@dataclass(slots=True)
class ParsedResponse:
    """Parsed LLM response with clarification elements."""
    needs_clarification: bool
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    clean_response: str = ""
    raw_response: str = ""
    
    # Suggestions (from [SUGGEST] tags)
    suggestions: List[str] = field(default_factory=list)


# ==============================================================================
# Clarification Patterns
# ==============================================================================

# Pattern to match [CLARIFY] tags
CLARIFY_PATTERN = re.compile(
    r'\[CLARIFY\](.*?)\[/CLARIFY\]',
    re.DOTALL | re.IGNORECASE
)

# Alternative patterns
CLARIFY_INLINE_PATTERN = re.compile(
    r'\[CLARIFY:\s*(.*?)\]',
    re.IGNORECASE
)

# Pattern to extract bullet options from clarification
OPTIONS_PATTERN = re.compile(
    r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)',
    re.MULTILINE
)


# ==============================================================================
# Clarification Handler
# ==============================================================================

class ClarificationHandler:
    """Handles clarification dialogue flow.
    
    Responsibilities:
    - Parse LLM responses for [CLARIFY] tags
    - Track clarification state per session
    - Build clarified queries from user responses
    - Support multi-turn clarification if needed
    
    Usage:
        handler = ClarificationHandler()
        
        # Parse LLM output
        parsed = handler.parse_response(llm_output, session_id)
        
        if parsed.needs_clarification:
            # Send clarification_question to user
            # Store the pending clarification
            handler.create_clarification(
                session_id, original_query, parsed.clarification_question
            )
        
        # When user responds
        handler.resolve_clarification(session_id, user_response)
    """
    
    def __init__(
        self,
        ambiguity_detector: Optional[AmbiguityDetector] = None,
        max_clarification_attempts: int = 3,
    ):
        self.ambiguity_detector = ambiguity_detector
        self.max_clarification_attempts = max_clarification_attempts
        
        # Session state
        self._pending_clarifications: Dict[str, ClarificationRequest] = {}
        self._clarification_history: Dict[str, List[ClarificationRequest]] = {}
        self._attempt_counts: Dict[str, int] = {}
    
    def parse_response(
        self,
        response: str,
        session_id: Optional[str] = None,
    ) -> ParsedResponse:
        """
        Parse LLM response for clarification requests.
        
        Args:
            response: Raw LLM response
            session_id: Session ID for state tracking
            
        Returns:
            ParsedResponse with clarification info
        """
        # Check for [CLARIFY]...[/CLARIFY] tags
        clarify_match = CLARIFY_PATTERN.search(response)
        if clarify_match:
            clarification_text = clarify_match.group(1).strip()
            
            # Extract options if present
            options = OPTIONS_PATTERN.findall(clarification_text)
            
            # Clean the response (remove clarify tags)
            clean_response = CLARIFY_PATTERN.sub('', response).strip()
            
            return ParsedResponse(
                needs_clarification=True,
                clarification_question=clarification_text,
                clarification_options=options,
                clean_response=clean_response,
                raw_response=response,
            )
        
        # Check for [CLARIFY: ...] inline tags
        inline_match = CLARIFY_INLINE_PATTERN.search(response)
        if inline_match:
            clarification_text = inline_match.group(1).strip()
            clean_response = CLARIFY_INLINE_PATTERN.sub('', response).strip()
            
            return ParsedResponse(
                needs_clarification=True,
                clarification_question=clarification_text,
                clarification_options=[],
                clean_response=clean_response,
                raw_response=response,
            )
        
        # No clarification needed
        return ParsedResponse(
            needs_clarification=False,
            clean_response=response,
            raw_response=response,
        )
    
    def should_request_clarification(
        self,
        query: str,
        session_id: str,
        force_check: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if clarification should be requested before processing.
        
        Args:
            query: User query
            session_id: Session ID
            force_check: Force ambiguity check even if at limit
            
        Returns:
            (should_clarify, clarification_question)
        """
        # Check attempt limit
        attempts = self._attempt_counts.get(session_id, 0)
        if attempts >= self.max_clarification_attempts and not force_check:
            return False, None
        
        # Check for pending clarification
        if session_id in self._pending_clarifications:
            # Already awaiting clarification
            return False, None
        
        # Use ambiguity detector
        if self.ambiguity_detector:
            result = self.ambiguity_detector.detect(query)
            if result.is_ambiguous and result.confidence > 0.6:
                return True, result.get_best_question()
        
        return False, None
    
    def create_clarification(
        self,
        session_id: str,
        original_query: str,
        clarification_question: str,
        options: Optional[List[str]] = None,
    ) -> ClarificationRequest:
        """
        Create and track a clarification request.
        
        Args:
            session_id: Session ID
            original_query: Original user query
            clarification_question: Question to ask user
            options: Optional list of choices
            
        Returns:
            ClarificationRequest object
        """
        request_id = f"clarify_{session_id}_{datetime.now().timestamp()}"
        
        request = ClarificationRequest(
            id=request_id,
            session_id=session_id,
            original_query=original_query,
            clarification_question=clarification_question,
            state=ClarificationState.AWAITING_RESPONSE,
            created_at=datetime.now(timezone.utc),
            options=options or [],
        )
        
        self._pending_clarifications[session_id] = request
        self._attempt_counts[session_id] = self._attempt_counts.get(session_id, 0) + 1
        
        logger.info(
            "Created clarification request for session %s: %s",
            session_id, clarification_question[:50],
        )
        
        return request
    
    def resolve_clarification(
        self,
        session_id: str,
        user_response: str,
    ) -> Optional[ClarificationRequest]:
        """
        Resolve a pending clarification with user's response.
        
        Args:
            session_id: Session ID
            user_response: User's clarifying response
            
        Returns:
            Resolved ClarificationRequest or None
        """
        request = self._pending_clarifications.pop(session_id, None)
        
        if request:
            request.state = ClarificationState.RESOLVED
            request.user_response = user_response
            request.resolved_at = datetime.now(timezone.utc)
            
            # Store in history
            if session_id not in self._clarification_history:
                self._clarification_history[session_id] = []
            self._clarification_history[session_id].append(request)
            
            logger.info(
                "Resolved clarification for session %s",
                session_id,
            )
        
        return request
    
    def skip_clarification(self, session_id: str) -> Optional[ClarificationRequest]:
        """Skip/cancel pending clarification."""
        request = self._pending_clarifications.pop(session_id, None)
        
        if request:
            request.state = ClarificationState.SKIPPED
            
            # Store in history
            if session_id not in self._clarification_history:
                self._clarification_history[session_id] = []
            self._clarification_history[session_id].append(request)
        
        return request
    
    def get_pending(self, session_id: str) -> Optional[ClarificationRequest]:
        """Get pending clarification for a session."""
        return self._pending_clarifications.get(session_id)
    
    def has_pending(self, session_id: str) -> bool:
        """Check if session has pending clarification."""
        return session_id in self._pending_clarifications
    
    def build_clarified_query(
        self,
        original_query: str,
        clarification_response: str,
        include_context: bool = True,
    ) -> str:
        """
        Build a clarified query combining original and clarification.
        
        Args:
            original_query: The original ambiguous query
            clarification_response: User's clarifying response
            include_context: Whether to include context note
            
        Returns:
            Combined query string
        """
        if include_context:
            return f"""Original question: {original_query}
User clarification: {clarification_response}

Please answer the question with this clarification in mind."""
        else:
            # Simple combination
            return f"{original_query} - {clarification_response}"
    
    def clear_session(self, session_id: str) -> None:
        """Clear all clarification state for a session."""
        self._pending_clarifications.pop(session_id, None)
        self._clarification_history.pop(session_id, None)
        self._attempt_counts.pop(session_id, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get clarification statistics."""
        total_requests = sum(
            len(history) for history in self._clarification_history.values()
        )
        resolved = sum(
            1 for history in self._clarification_history.values()
            for req in history if req.state == ClarificationState.RESOLVED
        )
        
        return {
            "pending_count": len(self._pending_clarifications),
            "total_requests": total_requests,
            "resolved_count": resolved,
            "sessions_with_history": len(self._clarification_history),
        }


# ==============================================================================
# Prompt Enhancement
# ==============================================================================

CLARIFICATION_SYSTEM_PROMPT = """You are a helpful assistant that asks clarifying questions when needed.

When a user's query is ambiguous, unclear, or could have multiple interpretations:
1. Identify what information is missing or unclear
2. Ask a helpful clarifying question using [CLARIFY][/CLARIFY] tags
3. If possible, offer options to make it easier for the user

Format for clarification:
[CLARIFY]Your clarifying question here.
- Option 1
- Option 2
- Option 3[/CLARIFY]

Only ask for clarification when genuinely needed. Clear questions should be answered directly.

Examples of when to clarify:
- "Tell me about Python" → Clarify: programming language or snake?
- "How do I fix it?" → Clarify: what specifically needs fixing?
- "What about the other one?" → Clarify: which other one?

Examples of when NOT to clarify:
- "What is the capital of France?" → Answer directly
- "How do I make a HTTP request in Python?" → Answer directly (context is clear)
"""


# ==============================================================================
# Global Instance
# ==============================================================================

_handler: Optional[ClarificationHandler] = None


def get_clarification_handler() -> ClarificationHandler:
    """Get or create global clarification handler."""
    global _handler
    if _handler is None:
        from .ambiguity import get_ambiguity_detector
        _handler = ClarificationHandler(
            ambiguity_detector=get_ambiguity_detector()
        )
    return _handler

