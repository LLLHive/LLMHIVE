"""Proactive Suggestion Engine for LLMHive.

Generates and manages proactive suggestions and follow-ups:
- Parse [SUGGEST] tags from LLM output
- Generate contextual suggestions based on response
- Tier-based suggestion frequency control

Usage:
    engine = get_suggestion_engine()
    
    # Parse response for suggestions
    suggestions = engine.parse_suggestions(llm_output)
    
    # Generate suggestions based on context
    suggestions = engine.generate_suggestions(
        query="What's the weather in Tokyo?",
        response="The weather is sunny...",
        user_tier="pro",
    )
"""
from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class SuggestionType(str, Enum):
    """Types of suggestions."""
    FOLLOW_UP = "follow_up"  # Follow-up question
    RELATED_TOPIC = "related_topic"  # Related topic to explore
    ACTION = "action"  # Suggested action
    COMPARISON = "comparison"  # Offer to compare
    DETAIL = "detail"  # Offer more details
    EXAMPLE = "example"  # Offer examples
    EXPORT = "export"  # Offer to export/save


@dataclass(slots=True)
class Suggestion:
    """A proactive suggestion."""
    id: str
    text: str
    type: SuggestionType
    query_prompt: Optional[str] = None  # What to send if user clicks
    confidence: float = 0.8
    tier_required: str = "free"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type.value,
            "query_prompt": self.query_prompt,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class SuggestionConfig:
    """Configuration for suggestion generation."""
    enabled: bool = True
    max_suggestions: int = 3
    suggestion_probability: float = 0.7  # Probability of suggesting
    
    # Tier-based limits
    free_tier_enabled: bool = False
    pro_tier_enabled: bool = True
    enterprise_tier_enabled: bool = True
    
    # Cooldown (suggestions per session)
    max_per_session: int = 5


# ==============================================================================
# Suggestion Patterns
# ==============================================================================

# Pattern to match [SUGGEST] tags
SUGGEST_PATTERN = re.compile(
    r'\[SUGGEST\](.*?)\[/SUGGEST\]',
    re.DOTALL | re.IGNORECASE
)

SUGGEST_INLINE_PATTERN = re.compile(
    r'\[SUGGEST:\s*(.*?)\]',
    re.IGNORECASE
)

# Domain-specific suggestion templates
SUGGESTION_TEMPLATES: Dict[str, List[Tuple[str, SuggestionType]]] = {
    "weather": [
        ("Would you like a 5-day forecast?", SuggestionType.DETAIL),
        ("I can also check weather for other locations.", SuggestionType.RELATED_TOPIC),
        ("Want me to set up a daily weather notification?", SuggestionType.ACTION),
    ],
    "code": [
        ("Would you like me to explain this code in more detail?", SuggestionType.DETAIL),
        ("I can show alternative implementations.", SuggestionType.COMPARISON),
        ("Want me to add error handling to this code?", SuggestionType.ACTION),
    ],
    "math": [
        ("Would you like to see the step-by-step solution?", SuggestionType.DETAIL),
        ("I can solve similar problems if you have more.", SuggestionType.FOLLOW_UP),
        ("Want me to plot this function?", SuggestionType.ACTION),
    ],
    "explanation": [
        ("Would you like more examples?", SuggestionType.EXAMPLE),
        ("I can dive deeper into any specific aspect.", SuggestionType.DETAIL),
        ("Want me to compare this with similar concepts?", SuggestionType.COMPARISON),
    ],
    "search": [
        ("Would you like me to search for more recent information?", SuggestionType.ACTION),
        ("I can provide more sources on this topic.", SuggestionType.DETAIL),
        ("Want me to summarize the key points?", SuggestionType.ACTION),
    ],
    "general": [
        ("Is there anything specific you'd like me to elaborate on?", SuggestionType.FOLLOW_UP),
        ("I can provide more details if helpful.", SuggestionType.DETAIL),
        ("Would you like related information on this topic?", SuggestionType.RELATED_TOPIC),
    ],
}

# Keywords to detect domain
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "weather": ["weather", "temperature", "forecast", "rain", "sunny", "cloudy"],
    "code": ["code", "function", "class", "programming", "python", "javascript", "error"],
    "math": ["calculate", "equation", "solve", "math", "formula", "result"],
    "explanation": ["explain", "what is", "how does", "why", "definition"],
    "search": ["search", "find", "look up", "news", "latest"],
}


# ==============================================================================
# Suggestion Engine
# ==============================================================================

class SuggestionEngine:
    """Engine for generating and managing proactive suggestions.
    
    Features:
    - Parse [SUGGEST] tags from LLM output
    - Generate contextual suggestions
    - Tier-based access control
    - Session-based suggestion limiting
    
    Usage:
        engine = SuggestionEngine()
        
        # Parse from LLM output
        suggestions = engine.parse_suggestions(llm_output)
        
        # Generate based on context
        suggestions = engine.generate_suggestions(
            query="What's the weather?",
            response="It's sunny...",
            domain="weather",
        )
    """
    
    def __init__(self, config: Optional[SuggestionConfig] = None):
        self.config = config or SuggestionConfig()
        self._session_counts: Dict[str, int] = {}
        self._suggestion_id_counter = 0
    
    def _next_id(self) -> str:
        """Generate unique suggestion ID."""
        self._suggestion_id_counter += 1
        return f"suggest_{self._suggestion_id_counter}"
    
    def parse_suggestions(self, response: str) -> Tuple[str, List[Suggestion]]:
        """
        Parse suggestions from LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            (clean_response, suggestions)
        """
        suggestions = []
        clean_response = response
        
        # Parse [SUGGEST]...[/SUGGEST] tags
        for match in SUGGEST_PATTERN.finditer(response):
            suggestion_text = match.group(1).strip()
            suggestions.append(Suggestion(
                id=self._next_id(),
                text=suggestion_text,
                type=SuggestionType.FOLLOW_UP,
                query_prompt=suggestion_text,
            ))
        
        # Remove suggestion tags from response
        clean_response = SUGGEST_PATTERN.sub('', clean_response)
        
        # Parse [SUGGEST: ...] inline tags
        for match in SUGGEST_INLINE_PATTERN.finditer(clean_response):
            suggestion_text = match.group(1).strip()
            suggestions.append(Suggestion(
                id=self._next_id(),
                text=suggestion_text,
                type=SuggestionType.FOLLOW_UP,
                query_prompt=suggestion_text,
            ))
        
        clean_response = SUGGEST_INLINE_PATTERN.sub('', clean_response)
        
        return clean_response.strip(), suggestions
    
    def generate_suggestions(
        self,
        query: str,
        response: str,
        session_id: Optional[str] = None,
        user_tier: str = "free",
        domain: Optional[str] = None,
    ) -> List[Suggestion]:
        """
        Generate contextual suggestions.
        
        Args:
            query: User's original query
            response: Assistant's response
            session_id: Session ID for rate limiting
            user_tier: User's tier
            domain: Optional detected domain
            
        Returns:
            List of suggestions
        """
        # Check if enabled for tier
        if not self._is_enabled_for_tier(user_tier):
            return []
        
        # Check session limit
        if session_id:
            count = self._session_counts.get(session_id, 0)
            if count >= self.config.max_per_session:
                return []
        
        # Probability check
        if random.random() > self.config.suggestion_probability:
            return []
        
        # Detect domain if not provided
        if not domain:
            domain = self._detect_domain(query, response)
        
        # Get templates for domain
        templates = SUGGESTION_TEMPLATES.get(domain, SUGGESTION_TEMPLATES["general"])
        
        # Select suggestions
        suggestions = []
        selected_templates = random.sample(
            templates,
            min(self.config.max_suggestions, len(templates))
        )
        
        for text, stype in selected_templates:
            suggestions.append(Suggestion(
                id=self._next_id(),
                text=text,
                type=stype,
                query_prompt=text,
                confidence=0.7,
                tier_required="free" if user_tier == "free" else "pro",
            ))
        
        # Update session count
        if session_id and suggestions:
            self._session_counts[session_id] = self._session_counts.get(session_id, 0) + 1
        
        return suggestions[:self.config.max_suggestions]
    
    def _is_enabled_for_tier(self, tier: str) -> bool:
        """Check if suggestions are enabled for tier."""
        if not self.config.enabled:
            return False
        
        tier_lower = tier.lower()
        if tier_lower == "free":
            return self.config.free_tier_enabled
        elif tier_lower == "pro":
            return self.config.pro_tier_enabled
        elif tier_lower == "enterprise":
            return self.config.enterprise_tier_enabled
        
        return False
    
    def _detect_domain(self, query: str, response: str) -> str:
        """Detect domain from query and response."""
        combined = f"{query} {response}".lower()
        
        best_domain = "general"
        best_score = 0
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_domain = domain
        
        return best_domain
    
    def reset_session(self, session_id: str) -> None:
        """Reset suggestion count for a session."""
        self._session_counts.pop(session_id, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get suggestion statistics."""
        return {
            "total_sessions": len(self._session_counts),
            "total_suggestions_generated": self._suggestion_id_counter,
            "session_counts": dict(self._session_counts),
        }


# ==============================================================================
# Prompt Enhancement
# ==============================================================================

SUGGESTION_SYSTEM_PROMPT = """After providing your answer, you may optionally offer helpful follow-up suggestions using [SUGGEST][/SUGGEST] tags.

Suggestions should be:
- Relevant to the user's query
- Actionable and specific
- Not too frequent (only when genuinely helpful)

Format:
[SUGGEST]Would you like me to provide more details about X?[/SUGGEST]

Example response with suggestion:
"The weather in Tokyo is currently sunny with a temperature of 22°C.

[SUGGEST]Would you like a 5-day forecast for Tokyo?[/SUGGEST]"

Guidelines:
- Only suggest when it adds value
- Keep suggestions concise
- Maximum 1-2 suggestions per response
- Don't suggest for simple factual questions
"""


# ==============================================================================
# Global Instance
# ==============================================================================

_engine: Optional[SuggestionEngine] = None


def get_suggestion_engine() -> SuggestionEngine:
    """Get or create global suggestion engine."""
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine

