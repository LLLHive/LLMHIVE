"""Ambiguity Detection for LLMHive.

Detects when user queries are vague, incomplete, or have multiple
interpretations, enabling the system to ask for clarification.

Usage:
    detector = AmbiguityDetector()
    
    result = detector.detect("Tell me about the law")
    if result.is_ambiguous:
        print(result.ambiguity_types)  # [AmbiguityType.UNDERSPECIFIED]
        print(result.clarifying_questions)  # ["Which law...?"]
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class AmbiguityType(str, Enum):
    """Types of ambiguity in queries."""
    VAGUE_REFERENCE = "vague_reference"  # "it", "they", "that"
    UNDERSPECIFIED = "underspecified"  # Missing key details
    MULTIPLE_MEANINGS = "multiple_meanings"  # Word has multiple meanings
    INCOMPLETE_QUESTION = "incomplete_question"  # Sentence cut off
    MISSING_CONTEXT = "missing_context"  # Needs prior conversation context
    BROAD_TOPIC = "broad_topic"  # Topic too broad to answer well


@dataclass(slots=True)
class AmbiguityResult:
    """Result of ambiguity detection."""
    is_ambiguous: bool
    confidence: float
    ambiguity_types: List[AmbiguityType]
    clarifying_questions: List[str]
    original_query: str
    analysis: Dict[str, Any] = field(default_factory=dict)
    
    def get_best_question(self) -> Optional[str]:
        """Get the most relevant clarifying question."""
        if self.clarifying_questions:
            return self.clarifying_questions[0]
        return None


# ==============================================================================
# Patterns and Keywords
# ==============================================================================

# Vague reference pronouns that often need clarification
VAGUE_REFERENCES = {
    "it", "this", "that", "these", "those", "they", "them",
    "the thing", "the stuff", "the one", "that one",
}

# Words that often indicate incomplete questions
INCOMPLETE_INDICATORS = [
    r"^tell me about\s*$",
    r"^what about\s*$",
    r"^how about\s*$",
    r"^and\s*$",
    r"^also\s*$",
    r"^then\s*$",
]

# Broad topic patterns that need narrowing
BROAD_TOPICS = {
    "the law": "Which specific law or legal topic?",
    "the library": "Which library are you interested in?",
    "the book": "Which book are you referring to?",
    "python": "Are you asking about Python programming or pythons (snakes)?",
    "apple": "Are you asking about Apple Inc. or apples (the fruit)?",
    "java": "Are you asking about Java programming or Java (the island)?",
    "mercury": "Are you asking about Mercury (the planet), mercury (the element), or Mercury (the Roman god)?",
    "amazon": "Are you asking about Amazon.com, the Amazon rainforest, or the Amazon River?",
    "the article": "Which article are you referring to?",
    "the video": "Which video are you asking about?",
    "the movie": "Which movie are you interested in?",
    "the company": "Which company would you like to know about?",
    "the person": "Who specifically are you asking about?",
}

# Question words that often indicate need for more specifics
UNDERSPECIFIED_PATTERNS = [
    (r"^(what|how|why|when|where|who)\s+is\s+(\w+)\?*$", 
     "Could you be more specific about what aspect of {0} you'd like to know?"),
    (r"^tell me about\s+(\w+)\s*\?*$",
     "What specific aspect of {0} would you like to know about?"),
    (r"^explain\s+(\w+)\s*\?*$",
     "Would you like a general overview of {0}, or is there a specific aspect you're interested in?"),
]

# Context-dependent patterns
CONTEXT_DEPENDENT = [
    r"^(yes|no|maybe|sure|okay|ok)[\s.,!?]*$",
    r"^(the|that|this)\s+one[\s.,!?]*$",
    r"^(same|different|another)[\s.,!?]*$",
    r"^more[\s.,!?]*$",
    r"^less[\s.,!?]*$",
    r"^(first|second|third|last)\s+one[\s.,!?]*$",
]


# ==============================================================================
# Ambiguity Detector
# ==============================================================================

class AmbiguityDetector:
    """Detects ambiguity in user queries.
    
    Uses multiple heuristics to identify:
    - Vague references (pronouns without clear antecedents)
    - Underspecified queries (missing key details)
    - Multiple meaning words
    - Incomplete questions
    - Context-dependent responses
    - Overly broad topics
    
    Usage:
        detector = AmbiguityDetector()
        
        result = detector.detect("Tell me about Python")
        if result.is_ambiguous:
            print(result.clarifying_questions[0])
            # "Are you asking about Python programming or pythons (snakes)?"
    """
    
    def __init__(
        self,
        sensitivity: float = 0.5,
        min_query_length: int = 3,
    ):
        """
        Initialize detector.
        
        Args:
            sensitivity: Detection sensitivity (0-1, higher = more strict)
            min_query_length: Minimum query length to analyze
        """
        self.sensitivity = sensitivity
        self.min_query_length = min_query_length
        
        # Compile patterns
        self._incomplete_patterns = [
            re.compile(p, re.IGNORECASE) for p in INCOMPLETE_INDICATORS
        ]
        self._context_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONTEXT_DEPENDENT
        ]
        self._underspecified_patterns = [
            (re.compile(p, re.IGNORECASE), q) for p, q in UNDERSPECIFIED_PATTERNS
        ]
    
    def detect(
        self,
        query: str,
        conversation_context: Optional[List[str]] = None,
    ) -> AmbiguityResult:
        """
        Detect ambiguity in a query.
        
        Args:
            query: User query to analyze
            conversation_context: Previous messages for context
            
        Returns:
            AmbiguityResult with detection details
        """
        query = query.strip()
        
        # Very short queries are often ambiguous
        if len(query) < self.min_query_length:
            return AmbiguityResult(
                is_ambiguous=True,
                confidence=0.9,
                ambiguity_types=[AmbiguityType.INCOMPLETE_QUESTION],
                clarifying_questions=["Could you provide more detail about what you'd like to know?"],
                original_query=query,
            )
        
        ambiguity_types: List[AmbiguityType] = []
        clarifying_questions: List[str] = []
        analysis: Dict[str, Any] = {}
        
        # Check for vague references
        vague_refs = self._detect_vague_references(query)
        if vague_refs:
            ambiguity_types.append(AmbiguityType.VAGUE_REFERENCE)
            clarifying_questions.append(
                f"Could you clarify what you mean by '{vague_refs[0]}'?"
            )
            analysis["vague_references"] = vague_refs
        
        # Check for incomplete questions
        if self._is_incomplete(query):
            ambiguity_types.append(AmbiguityType.INCOMPLETE_QUESTION)
            clarifying_questions.append(
                "It looks like your question might be incomplete. Could you provide more details?"
            )
            analysis["incomplete"] = True
        
        # Check for context-dependent responses
        if self._needs_context(query, conversation_context):
            ambiguity_types.append(AmbiguityType.MISSING_CONTEXT)
            clarifying_questions.append(
                "I need a bit more context. What specifically are you referring to?"
            )
            analysis["needs_context"] = True
        
        # Check for broad topics / multiple meanings
        topic_question = self._check_broad_topic(query)
        if topic_question:
            ambiguity_types.append(AmbiguityType.MULTIPLE_MEANINGS)
            clarifying_questions.append(topic_question)
            analysis["broad_topic"] = True
        
        # Check for underspecified patterns
        underspec_question = self._check_underspecified(query)
        if underspec_question:
            ambiguity_types.append(AmbiguityType.UNDERSPECIFIED)
            clarifying_questions.append(underspec_question)
            analysis["underspecified"] = True
        
        # Calculate overall ambiguity
        is_ambiguous = len(ambiguity_types) > 0
        confidence = min(len(ambiguity_types) * 0.3 + 0.4, 1.0) if is_ambiguous else 0.0
        
        # Apply sensitivity threshold
        if confidence < self.sensitivity:
            is_ambiguous = False
            clarifying_questions = []
        
        return AmbiguityResult(
            is_ambiguous=is_ambiguous,
            confidence=confidence,
            ambiguity_types=ambiguity_types,
            clarifying_questions=clarifying_questions,
            original_query=query,
            analysis=analysis,
        )
    
    def _detect_vague_references(self, query: str) -> List[str]:
        """Detect vague pronoun references."""
        query_lower = query.lower()
        words = set(re.findall(r'\b\w+\b', query_lower))
        
        found = []
        for ref in VAGUE_REFERENCES:
            if ref in words or ref in query_lower:
                # Check if it's at the start (more likely to be vague)
                if query_lower.startswith(ref) or query_lower.startswith("what is " + ref):
                    found.append(ref)
        
        return found
    
    def _is_incomplete(self, query: str) -> bool:
        """Check if query appears incomplete."""
        for pattern in self._incomplete_patterns:
            if pattern.search(query):
                return True
        
        # Check for trailing conjunctions
        query_lower = query.lower().strip()
        if query_lower.endswith((' and', ' or', ' but', ' then', ' so')):
            return True
        
        return False
    
    def _needs_context(
        self,
        query: str,
        context: Optional[List[str]],
    ) -> bool:
        """Check if query needs conversation context."""
        for pattern in self._context_patterns:
            if pattern.match(query):
                # Only flag if no context provided
                return not context or len(context) == 0
        
        return False
    
    def _check_broad_topic(self, query: str) -> Optional[str]:
        """Check for broad topics that need clarification."""
        query_lower = query.lower()
        
        for topic, question in BROAD_TOPICS.items():
            if topic in query_lower:
                # Check if it's a simple mention without specifics
                words = len(query.split())
                if words <= 5:  # Short query with broad topic
                    return question
        
        return None
    
    def _check_underspecified(self, query: str) -> Optional[str]:
        """Check for underspecified question patterns."""
        for pattern, question_template in self._underspecified_patterns:
            match = pattern.match(query)
            if match:
                topic = match.group(1) if match.lastindex else "that"
                return question_template.format(topic)
        
        return None


# ==============================================================================
# Few-Shot Examples for LLM
# ==============================================================================

CLARIFICATION_FEW_SHOT = """When a user query is ambiguous or unclear, respond with a clarifying question inside [CLARIFY] tags.

Example 1:
User: Tell me about the law
Assistant: [CLARIFY]I'd be happy to help! Which specific law or legal topic are you interested in? For example:
- A specific legislation (like GDPR, HIPAA)
- A legal concept (like contract law, criminal law)
- Laws in a particular jurisdiction[/CLARIFY]

Example 2:
User: What is Python?
Assistant: [CLARIFY]Are you asking about Python the programming language, or pythons the snake family? Let me know which one you'd like to learn about.[/CLARIFY]

Example 3:
User: How do I fix it?
Assistant: [CLARIFY]Could you please clarify what you're trying to fix? I'd need to know:
- What system or application you're working with
- What problem or error you're experiencing[/CLARIFY]

Example 4:
User: What is the capital of France?
Assistant: The capital of France is Paris. It has been the country's capital since the 10th century and is its largest city.

Note: Only use [CLARIFY] when the query is genuinely ambiguous. Clear questions should be answered directly."""


# ==============================================================================
# Global Functions
# ==============================================================================

_detector: Optional[AmbiguityDetector] = None


def get_ambiguity_detector() -> AmbiguityDetector:
    """Get or create global ambiguity detector."""
    global _detector
    if _detector is None:
        _detector = AmbiguityDetector()
    return _detector


def detect_ambiguity(
    query: str,
    context: Optional[List[str]] = None,
) -> AmbiguityResult:
    """Quick helper to detect ambiguity."""
    detector = get_ambiguity_detector()
    return detector.detect(query, context)

