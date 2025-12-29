"""Clarification Manager for LLMHive Orchestrator.

This module implements the clarifying questions feature that:
1. Detects when a query is ambiguous or missing key details
2. Generates up to 3 focused clarifying questions about the query
3. Generates 3 questions about the user's preferred answer format
4. Processes user responses and refines the query accordingly

The clarification flow follows this pattern:
1. Analyze query for ambiguity/missing information
2. If clarification needed, generate query clarification questions
3. Present answer preference questions (detail level, format, tone)
4. Process responses and create refined query with preferences

This approach is inspired by ChatGPT's deep search mode and ensures
we fully understand the query before generating a response.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums
# ==============================================================================

class ClarificationStatus(str, Enum):
    """Status of the clarification process."""
    NOT_NEEDED = "not_needed"           # Query is clear, no clarification needed
    PENDING_QUERY = "pending_query"     # Waiting for query clarification answers
    PENDING_PREFERENCES = "pending_preferences"  # Waiting for format preferences
    COMPLETED = "completed"             # Clarification complete
    SKIPPED = "skipped"                 # User skipped clarification


class DetailLevel(str, Enum):
    """Level of detail for the answer."""
    BRIEF = "brief"         # Short, to-the-point answer
    STANDARD = "standard"   # Normal level of detail
    DETAILED = "detailed"   # Comprehensive, in-depth answer
    EXHAUSTIVE = "exhaustive"  # Maximum detail with examples


class AnswerFormat(str, Enum):
    """Format for the answer."""
    PARAGRAPH = "paragraph"       # Traditional prose
    BULLET_POINTS = "bullet_points"  # Bulleted list
    NUMBERED_LIST = "numbered_list"  # Numbered steps
    CODE_FOCUSED = "code_focused"    # Code with explanations
    TABLE = "table"                  # Tabular format
    STRUCTURED = "structured"        # Headers and sections
    CONVERSATIONAL = "conversational"  # Casual, chat-like


class AnswerTone(str, Enum):
    """Tone/style for the answer."""
    FORMAL = "formal"           # Professional, academic
    CASUAL = "casual"           # Friendly, informal
    TECHNICAL = "technical"     # Expert-level jargon
    SIMPLIFIED = "simplified"   # Layman-friendly
    EDUCATIONAL = "educational" # Teaching-focused


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class ClarificationQuestion:
    """A single clarification question."""
    id: str
    question: str
    category: str  # "query" or "preference"
    options: Optional[List[str]] = None  # Optional multiple choice options
    default_answer: Optional[str] = None
    required: bool = True


@dataclass
class AnswerPreferences:
    """User's preferences for answer format and style."""
    detail_level: DetailLevel = DetailLevel.STANDARD
    format: AnswerFormat = AnswerFormat.PARAGRAPH
    tone: AnswerTone = AnswerTone.FORMAL
    max_length: Optional[int] = None  # Optional word limit
    include_examples: bool = True
    include_citations: bool = False
    custom_instructions: Optional[str] = None
    
    def to_style_guidelines(self) -> List[str]:
        """Convert preferences to style guidelines for the refiner."""
        guidelines = []
        
        # Detail level
        if self.detail_level == DetailLevel.BRIEF:
            guidelines.append("Keep the response concise and to-the-point")
            guidelines.append("Focus only on the essential information")
        elif self.detail_level == DetailLevel.DETAILED:
            guidelines.append("Provide comprehensive coverage of the topic")
            guidelines.append("Include supporting details and context")
        elif self.detail_level == DetailLevel.EXHAUSTIVE:
            guidelines.append("Provide exhaustive coverage with all relevant details")
            guidelines.append("Include edge cases, exceptions, and nuances")
        
        # Format
        if self.format == AnswerFormat.BULLET_POINTS:
            guidelines.append("Structure the answer using bullet points")
        elif self.format == AnswerFormat.NUMBERED_LIST:
            guidelines.append("Use a numbered list format for clarity")
        elif self.format == AnswerFormat.CODE_FOCUSED:
            guidelines.append("Focus on code examples with explanations")
        elif self.format == AnswerFormat.TABLE:
            guidelines.append("Use tables where appropriate for comparison")
        elif self.format == AnswerFormat.STRUCTURED:
            guidelines.append("Use clear headers and sections to organize content")
        elif self.format == AnswerFormat.CONVERSATIONAL:
            guidelines.append("Use a conversational, approachable style")
        elif self.format == AnswerFormat.MARKDOWN:
            guidelines.append("Use markdown with headings and lists for readability")
        elif self.format == AnswerFormat.JSON:
            guidelines.append("Provide the answer as valid JSON without extra text")
        elif self.format == AnswerFormat.EXECUTIVE_SUMMARY:
            guidelines.append("Provide a brief executive summary followed by key bullets")
        elif self.format == AnswerFormat.QA:
            guidelines.append("Present the answer in a simple Q&A style")
        
        # Tone
        if self.tone == AnswerTone.CASUAL:
            guidelines.append("Use a friendly, casual tone")
        elif self.tone == AnswerTone.TECHNICAL:
            guidelines.append("Use precise technical terminology")
        elif self.tone == AnswerTone.SIMPLIFIED:
            guidelines.append("Explain in simple terms, avoid jargon")
        elif self.tone == AnswerTone.EDUCATIONAL:
            guidelines.append("Take an educational approach, building understanding step by step")
        
        # Additional preferences
        if self.include_examples:
            guidelines.append("Include concrete examples to illustrate points")
        if self.include_citations:
            guidelines.append("Cite sources where applicable")
        if self.max_length:
            guidelines.append(f"Keep response under {self.max_length} words")
        if self.custom_instructions:
            guidelines.append(f"Additional instruction: {self.custom_instructions}")
        
        return guidelines


@dataclass
class ClarificationRequest:
    """Request for clarification from the user."""
    query_questions: List[ClarificationQuestion] = field(default_factory=list)
    preference_questions: List[ClarificationQuestion] = field(default_factory=list)
    original_query: str = ""
    status: ClarificationStatus = ClarificationStatus.NOT_NEEDED
    ambiguity_summary: Optional[str] = None  # Why we're asking
    
    @property
    def total_questions(self) -> int:
        return len(self.query_questions) + len(self.preference_questions)
    
    @property
    def has_query_questions(self) -> bool:
        return len(self.query_questions) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "status": self.status.value,
            "original_query": self.original_query,
            "ambiguity_summary": self.ambiguity_summary,
            "query_questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "category": q.category,
                    "options": q.options,
                    "default_answer": q.default_answer,
                    "required": q.required,
                }
                for q in self.query_questions
            ],
            "preference_questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "category": q.category,
                    "options": q.options,
                    "default_answer": q.default_answer,
                    "required": q.required,
                }
                for q in self.preference_questions
            ],
        }


@dataclass
class ClarificationResponse:
    """User's responses to clarification questions."""
    query_answers: Dict[str, str] = field(default_factory=dict)  # question_id -> answer
    preference_answers: Dict[str, str] = field(default_factory=dict)
    skipped: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClarificationResponse":
        """Create from dictionary (API request)."""
        return cls(
            query_answers=data.get("query_answers", {}),
            preference_answers=data.get("preference_answers", {}),
            skipped=data.get("skipped", False),
        )


@dataclass
class RefinedQueryResult:
    """Result of processing clarification responses."""
    original_query: str
    refined_query: str
    answer_preferences: AnswerPreferences
    clarification_context: str  # Summary of clarifications for LLM context
    was_clarified: bool
    pending_clarification: bool = False  # If True, caller should trigger another round


# ==============================================================================
# LLM Prompts for Clarification Generation
# ==============================================================================

CLARIFICATION_DETECTION_PROMPT = """Analyze this user query to determine if clarification is TRULY needed.

Query: "{query}"

IMPORTANT GUIDELINES:
- Most queries are clear enough to answer directly. Default to NOT needing clarification.
- Simple factual questions (lists, rankings, "what is", "who is", etc.) almost NEVER need clarification.
- Only flag genuine ambiguity that would lead to completely different answers.
- "list 10 X" or "top 10 X" queries are clear - just provide the list.
- Do NOT ask about criteria unless the query is genuinely ambiguous about what's being asked.

Only flag these as TRUE ambiguities requiring clarification:
1. Pronouns without ANY clear referent ("fix it" with no context)
2. Query is genuinely incomprehensible or self-contradictory
3. Critical missing information that makes answering impossible

Do NOT flag as ambiguous:
- Simple ranking/list requests (even if "best" or "top" is used)
- Factual questions with clear scope
- Questions where a reasonable default interpretation exists
- Questions where the answer format is obvious from context

Respond in JSON format:
{{
    "needs_clarification": boolean (should be false for most queries),
    "ambiguity_score": 0.0 to 1.0 (keep below 0.5 for clear queries),
    "issues": [],
    "suggested_questions": []
}}

Be CONSERVATIVE - only suggest questions for genuinely incomprehensible queries.
Respond ONLY with JSON."""


CLARIFICATION_QUESTIONS_PROMPT = """Analyze this query and generate clarifying questions ONLY if genuinely needed.

Query: "{query}"
Detected Issues: {issues}

DECISION FRAMEWORK:
1. Can this query be answered with reasonable assumptions? → NO questions needed
2. Is there critical missing information that makes answering IMPOSSIBLE? → Ask SPECIFIC question

CLEAR QUERIES (NO questions needed):
- "list 10 fastest cars" → Answer directly (fastest = top speed is obvious)
- "best programming languages" → Provide a reasonable ranking
- "explain photosynthesis" → Just explain it
- "how to make pasta" → Provide the recipe

GENUINELY AMBIGUOUS (questions ARE needed):
- "fix it" with no context → "What would you like me to fix? Please share the content."
- "compare Python" with no target → "What would you like to compare Python with?"
- "continue" with no history → "What would you like me to continue? Please share the context."
- "help" alone → "What do you need help with? Please describe your situation."

RULES FOR QUESTIONS:
1. Questions MUST be specific to the query content
2. Questions MUST help us answer - not just be pedantic
3. Include helpful guidance in the question (e.g., "Please share..." or "For example...")
4. Maximum 2 questions - focus on the most critical missing information

Respond in JSON format:
{{
    "questions": [
        {{
            "id": "q1",
            "question": "Specific, helpful question that references the query",
            "why": "Brief explanation of why this is needed"
        }}
    ]
}}

Most queries are clear - return empty questions list unless clarification is ESSENTIAL.
Respond ONLY with JSON."""


QUERY_REFINEMENT_PROMPT = """Refine this query using the user's clarification answers.

Original Query: "{query}"

Clarification Q&A:
{clarifications}

Create a refined query that:
1. Incorporates all the clarified information
2. Is specific and unambiguous
3. Preserves the user's original intent
4. Can be directly answered by an AI assistant

Output ONLY the refined query, no other text."""


# ==============================================================================
# ClarificationManager Implementation
# ==============================================================================

class ClarificationManager:
    """Manages the clarification question flow.
    
    This class handles:
    - Detecting when clarification is needed
    - Generating query clarification questions (up to 3)
    - Generating answer preference questions (3 standard questions)
    - Processing user responses
    - Refining the query based on responses
    """
    
    # Standard preference questions (always asked)
    PREFERENCE_QUESTIONS = [
        ClarificationQuestion(
            id="pref_detail",
            question="How detailed of an answer would you like?",
            category="preference",
            options=[
                "Brief - Just the essentials",
                "Standard - Normal level of detail",
                "Detailed - Comprehensive coverage",
                "Exhaustive - Maximum detail with examples"
            ],
            default_answer="Standard - Normal level of detail",
            required=False,
        ),
        ClarificationQuestion(
            id="pref_format",
            question="Do you have a preferred format for the answer?",
            category="preference",
            options=[
                "Paragraph - Traditional prose",
                "Bullet Points - Easy to scan",
                "Numbered List - Step-by-step",
                "Code Focused - Code with explanations",
                "Structured - Headers and sections",
                "Conversational - Casual and friendly"
            ],
            default_answer="Paragraph - Traditional prose",
            required=False,
        ),
        ClarificationQuestion(
            id="pref_tone",
            question="Who is the intended audience, or what tone do you prefer?",
            category="preference",
            options=[
                "Formal - Professional and precise",
                "Casual - Friendly and approachable",
                "Technical - Expert-level terminology",
                "Simplified - Easy to understand, no jargon",
                "Educational - Teaching-focused, builds understanding"
            ],
            default_answer="Formal - Professional and precise",
            required=False,
        ),
    ]
    
    # Patterns that indicate the query is clear and should NOT trigger clarification
    CLEAR_QUERY_PATTERNS = [
        r'^list\s+(?:the\s+)?(?:top\s+)?\d+',  # "list 10 X", "list the top 10 X"
        r'^(?:what|who|when|where|which)\s+(?:is|are|was|were)',  # "what is X"
        r'^(?:name|give me|provide|tell me)\s+(?:the\s+)?\d+',  # "name 10 X"
        r'^how\s+(?:many|much|often|long)',  # "how many X"
        r'^(?:top|best|biggest|largest|smallest|fastest|slowest)\s+\d+',  # "top 10 X"
        r'^\d+\s+(?:best|top|biggest|largest)',  # "10 best X"
    ]
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        ambiguity_threshold: float = 0.7,  # Raised from 0.4 to be more conservative
        max_query_questions: int = 3,
        always_ask_preferences: bool = False,  # Changed: don't always ask preferences
        enable_llm_detection: bool = True,
    ) -> None:
        """
        Initialize the ClarificationManager.
        
        Args:
            providers: LLM providers for generating questions
            ambiguity_threshold: Threshold (0-1) above which to ask clarifying questions
            max_query_questions: Maximum number of query clarification questions (default 3)
            always_ask_preferences: Whether to always ask preference questions
            enable_llm_detection: Use LLM for ambiguity detection (vs rule-based)
        """
        self.providers = providers or {}
        self.ambiguity_threshold = ambiguity_threshold
        self.max_query_questions = max_query_questions
        self.always_ask_preferences = always_ask_preferences
        self.enable_llm_detection = enable_llm_detection
    
    async def analyze_and_generate_questions(
        self,
        query: str,
        *,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        skip_preferences: bool = False,
        clarification_round: int = 1,
    ) -> ClarificationRequest:
        """
        Analyze a query and generate clarification questions if needed.
        
        Args:
            query: The user's original query
            context: Optional conversation context
            history: Optional conversation history
            skip_preferences: Skip preference questions (useful for follow-ups)
            
        Returns:
            ClarificationRequest with questions (may be empty if not needed)
        """
        # Step 1: Detect if clarification is needed
        needs_clarification, issues, suggested_questions = await self._detect_ambiguity(
            query, context, history
        )
        
        # Step 2: Generate query clarification questions if needed
        query_questions: List[ClarificationQuestion] = []
        ambiguity_summary = None
        
        if needs_clarification and suggested_questions:
            query_questions = []
            lang = self._detect_language(query)
            localized_prefaces = {
                "es": ["", "Rápido chequeo: ", "Para asegurar: ", "Solo para confirmar: "],
                "fr": ["", "Vérification rapide : ", "Pour être sûr : ", "Juste pour confirmer : "],
                "de": ["", "Kurze Prüfung: ", "Um sicherzugehen: ", "Nur um zu bestätigen: "],
            }
            prefaces = localized_prefaces.get(lang, [
                "",
                "Quick check: ",
                "To be sure: ",
                "Just to confirm: ",
            ])
            for i, q in enumerate(suggested_questions[:self.max_query_questions]):
                prefix = prefaces[i % len(prefaces)]
                question_text = f"{prefix}{q}".strip()
                query_questions.append(
                    ClarificationQuestion(
                        id=f"q{i+1}",
                        question=question_text,
                        category="query",
                        required=True,
                    )
                )
            
            # Create summary of why we're asking
            ambiguity_summary = self._create_ambiguity_summary(issues)
        
        # Step 3: Add preference questions
        preference_questions: List[ClarificationQuestion] = []
        if not skip_preferences and self.always_ask_preferences:
            preference_questions = self.PREFERENCE_QUESTIONS.copy()
        
        # Determine status
        if query_questions:
            status = ClarificationStatus.PENDING_QUERY
        elif preference_questions:
            status = ClarificationStatus.PENDING_PREFERENCES
        else:
            status = ClarificationStatus.NOT_NEEDED
        
        return ClarificationRequest(
            query_questions=query_questions,
            preference_questions=preference_questions,
            original_query=query,
            status=status,
            ambiguity_summary=ambiguity_summary,
            clarification_round=clarification_round,
        )
    
    async def process_responses(
        self,
        request: ClarificationRequest,
        response: ClarificationResponse,
    ) -> RefinedQueryResult:
        """
        Process user's clarification responses and refine the query.
        
        Args:
            request: The original clarification request
            response: User's responses to the questions
            
        Returns:
            RefinedQueryResult with refined query and preferences
        """
        # Handle skipped clarification
        if response.skipped:
            return RefinedQueryResult(
                original_query=request.original_query,
                refined_query=request.original_query,
                answer_preferences=AnswerPreferences(),
                clarification_context="",
                was_clarified=False,
            )
        
        # Process query clarifications
        refined_query = request.original_query
        clarification_context = ""
        
        if response.query_answers:
            refined_query, clarification_context = await self._refine_query(
                request.original_query,
                request.query_questions,
                response.query_answers,
            )
            # Re-run ambiguity check to see if more clarification is needed
            try:
                needs_more, more_issues, _ = await self._detect_ambiguity(
                    refined_query, context=None, history=None
                )
                # If still ambiguous and user allows assumption, proceed with best guess
                if needs_more and response.proceed_with_assumption:
                    clarification_context += "\n[Assumed interpretation used due to remaining ambiguity]"
                    needs_more = False
                # If still ambiguous and round limit not reached, signal another round
                if needs_more and request.clarification_round < 2:
                    # Signal another round needed; caller can re-invoke analyze with round+1
                    clarification_context += "\n[Pending additional clarification]"
                    return RefinedQueryResult(
                        original_query=request.original_query,
                        refined_query=refined_query,
                        answer_preferences=AnswerPreferences(),
                        clarification_context=clarification_context,
                        was_clarified=False,
                        pending_clarification=True,
                    )
                if needs_more and more_issues:
                    clarification_context += "\n[Note] Some ambiguity may remain: " + "; ".join(
                        i.get("description", "") for i in more_issues[:2]
                    )
            except Exception as e:
                logger.debug("Follow-up ambiguity check failed: %s", e)
        
        # Process preference answers
        preferences = self._parse_preference_answers(response.preference_answers)
        
        return RefinedQueryResult(
            original_query=request.original_query,
            refined_query=refined_query,
            answer_preferences=preferences,
            clarification_context=clarification_context,
            was_clarified=bool(response.query_answers),
        )
    
    def _is_clear_query(self, query: str) -> bool:
        """Check if the query matches patterns that are clearly unambiguous."""
        query_lower = query.lower().strip()
        
        # Check against clear query patterns
        for pattern in self.CLEAR_QUERY_PATTERNS:
            if re.match(pattern, query_lower):
                return True
        
        # Simple factual patterns that don't need clarification
        if query_lower.startswith(('list ', 'name ', 'what are the ', 'who are the ')):
            return True
        
        # Numbered requests are always clear
        if re.search(r'\b\d+\s+(?:best|top|biggest|largest|fastest|slowest|most|least)\b', query_lower):
            return True
        if re.search(r'\b(?:top|best|biggest)\s+\d+\b', query_lower):
            return True
        
        return False
    
    async def _detect_ambiguity(
        self,
        query: str,
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """Detect if the query is ambiguous and needs clarification."""
        
        # FAST PATH: Check if query is clearly unambiguous
        if self._is_clear_query(query):
            logger.debug("Query matches clear pattern, skipping clarification: %s", query[:50])
            return False, [], []
        
        # Try LLM-based detection first
        if self.enable_llm_detection and self.providers:
            try:
                return await self._llm_detect_ambiguity(query, context, history)
            except Exception as e:
                logger.warning("LLM ambiguity detection failed: %s", e)
        
        # Fall back to rule-based detection
        return self._rule_based_detect_ambiguity(query, context, history)
    
    async def _llm_detect_ambiguity(
        self,
        query: str,
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """Use LLM to detect ambiguity."""
        provider = self.providers.get("openai") or next(iter(self.providers.values()), None)
        if not provider:
            return self._rule_based_detect_ambiguity(query, context, history)
        
        prompt = CLARIFICATION_DETECTION_PROMPT.format(query=query)
        
        try:
            result = await provider.complete(prompt, model="gpt-4o-mini")
            content = getattr(result, 'content', '') or getattr(result, 'text', '')
            
            # Clean up JSON response
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            data = json.loads(content.strip())
            
            needs_clarification = data.get("needs_clarification", False)
            ambiguity_score = data.get("ambiguity_score", 0.0)
            issues = data.get("issues", [])
            suggested_questions = data.get("suggested_questions", [])
            
            # Apply threshold
            if ambiguity_score < self.ambiguity_threshold:
                needs_clarification = False
            else:
                # Ensure we at least have one question
                if not suggested_questions and issues:
                    suggested_questions = [f"Could you clarify: {issues[0].get('description', '')}?"]
            
            return needs_clarification, issues, suggested_questions
            
        except Exception as e:
            logger.warning("Failed to parse LLM response: %s", e)
            return self._rule_based_detect_ambiguity(query, context, history)
    
    def _rule_based_detect_ambiguity(
        self,
        query: str,
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """
        Intelligent rule-based ambiguity detection.
        
        Key principle: Only ask clarifying questions when the query is GENUINELY
        ambiguous - meaning we truly cannot answer without more information.
        
        When questions ARE needed, they must be RELEVANT and SPECIFIC to the query.
        """
        query_lower = query.lower().strip()
        query_words = query.split()
        word_count = len(query_words)
        issues = []
        questions = []
        possible_interpretations: List[str] = []
        
        # =====================================================================
        # STEP 1: Check if query is CLEARLY unambiguous (fast path - no questions)
        # =====================================================================
        
        # Queries with specific numbers are almost always clear
        has_numbers = bool(re.search(r'\b\d+\b', query))
        
        # Standard factual question patterns that are clear
        # NOTE: These patterns should NOT match pronoun-based queries like "explain that"
        pronouns = {'it', 'this', 'that', 'these', 'those', 'they', 'them'}
        
        clear_patterns = [
            r'^list\s+(?:the\s+)?(?:top\s+)?\d+',  # "list 10 X"
            r'^(?:what|who|when|where|which)\s+(?:is|are|was|were)\s+\w+',  # "what is X"
            r'^how\s+(?:many|much|to|do|does|can|should)',  # "how many X"
            r'^(?:name|give me|provide|show me)\s+',  # "give me X"
        ]
        
        for pattern in clear_patterns:
            if re.match(pattern, query_lower):
                return False, [], []  # Clear query, no questions needed
        
        # Special handling for "explain/describe/define X" - clear ONLY if X is not a pronoun
        explain_match = re.match(r'^(?:explain|describe|define)\s+(\w+)', query_lower)
        if explain_match:
            target_word = explain_match.group(1)
            if target_word not in pronouns and len(target_word) >= 3:
                return False, [], []  # "explain photosynthesis" is clear
        
        # Sufficiently detailed queries (7+ words) are usually clear
        if word_count >= 7 and not self._has_critical_ambiguity(query_lower, history):
            return False, [], []
        
        # =====================================================================
        # STEP 2: Detect GENUINE ambiguities that require clarification
        # =====================================================================
        
        # Pattern 1: Action verbs with pronouns but NO context
        # "fix it", "explain this", "continue that", "describe it" - GENUINELY need clarification
        action_pronoun_pattern = r'^(fix|explain|describe|define|continue|analyze|review|check|update|change|modify|delete|remove|debug|test|run|execute)\s+(it|this|that)$'
        match = re.match(action_pronoun_pattern, query_lower)
        if match and not history and not context:
            action, pronoun = match.groups()
            issues.append({
                "type": "missing_referent",
                "description": f"'{pronoun}' has no referent - cannot determine what to {action}",
            })
            # Generate a RELEVANT question specific to this query
            questions.append(f"What would you like me to {action}? Please provide the content or describe what you're referring to.")
        
        # Pattern 2: "Compare X" without a comparison target
        compare_match = re.match(r'^compare\s+(.+?)(?:\s+and\s+|\s+vs\.?\s+|\s+versus\s+|\s+with\s+|\s+to\s+)?$', query_lower)
        if compare_match and 'and' not in query_lower and 'vs' not in query_lower and 'with' not in query_lower and 'to' not in query_lower:
            subject = compare_match.group(1).strip()
            if subject and not re.search(r'\s+(and|vs|versus|with|to)\s+', query_lower):
                issues.append({
                    "type": "incomplete_comparison",
                    "description": f"Comparison requested for '{subject}' but no comparison target specified",
                })
                questions.append(f"What would you like to compare {subject} with?")
        
        # Pattern 3: Very short queries with only vague words
        # "help", "problem", "question" alone are genuinely ambiguous
        single_word_vague = ["help", "problem", "question", "issue", "error", "bug", "stuck"]
        if word_count == 1 and query_lower in single_word_vague:
            issues.append({
                "type": "underspecified",
                "description": "Single vague word - need more context",
            })
            questions.append(f"Could you describe your {query_lower} in more detail? What specifically do you need help with?")
        
        # Pattern 4: "the X" or "my X" with action verb but no history/context
        # "fix the bug", "update my code" - need to know WHICH bug/code
        if word_count <= 4 and not history and not context:
            possessive_action = re.match(r'^(fix|update|change|modify|review|check|debug)\s+(the|my|our)\s+(\w+)$', query_lower)
            if possessive_action:
                action, possessive, item = possessive_action.groups()
                issues.append({
                    "type": "missing_context",
                    "description": f"Need to know which specific {item} to {action}",
                })
                questions.append(f"Could you share the {item} you'd like me to {action}? Please paste the content or provide more details.")
        
        # Pattern 5: Genuinely polysemous terms in SHORT queries only
        polysemous = {
            "bank": (["financial institution", "river bank"], ["money", "account", "loan", "river", "water", "shore"]),
            "python": (["programming language", "snake"], ["code", "program", "script", "pip", "snake", "reptile"]),
            "java": (["programming language", "coffee", "island"], ["code", "program", "jdk", "coffee", "beans"]),
            "mercury": (["planet", "chemical element", "car brand"], ["planet", "space", "metal", "thermometer", "car"]),
        }
        
        if word_count <= 3:  # Only for very short queries
            for term, (senses, disambiguators) in polysemous.items():
                if term in query_lower.split():
                    has_disambiguator = any(d in query_lower for d in disambiguators)
                    if not has_disambiguator:
                        issues.append({
                            "type": "semantic_ambiguity",
                            "description": f"'{term}' has multiple meanings",
                            "options": senses,
                        })
                        options_text = " or ".join(senses)
                        questions.append(f"When you say '{term}', do you mean {options_text}?")
                        possible_interpretations.extend(senses)
                    break
        
        # Pattern 6: Continuation requests with no history
        if any(kw in query_lower for kw in ["continue", "go on", "keep going", "next part", "resume"]) and not history:
            issues.append({
                "type": "missing_context",
                "description": "Continuation requested but no prior conversation",
            })
            questions.append("I don't have context from a previous conversation. What would you like me to continue? Please share the previous content or context.")
        
        # =====================================================================
        # STEP 3: Determine if clarification is TRULY needed
        # =====================================================================
        
        # We need clarification if we generated RELEVANT questions
        # Each question above was only added for genuine ambiguity cases
        needs_clarification = len(questions) > 0
        
        # Log for debugging
        if needs_clarification:
            logger.debug(
                "Clarification needed for query '%s': %d issues, %d questions",
                query[:50], len(issues), len(questions)
            )
        
        return needs_clarification, issues, questions[:self.max_query_questions]
    
    def _has_critical_ambiguity(self, query_lower: str, history: Optional[List[Dict[str, str]]]) -> bool:
        """
        Check if query has critical ambiguity that requires clarification.
        
        Used as a secondary check for longer queries that might still be ambiguous.
        """
        # Critical: pronouns at the start with action verbs
        if re.match(r'^(fix|explain|continue|analyze)\s+(it|this|that)\b', query_lower):
            return not history  # Ambiguous only if no history
        
        # Critical: "compare X" without "with/to/and/vs"
        if query_lower.startswith("compare ") and not re.search(r'\b(with|to|and|vs|versus)\b', query_lower):
            return True
        
        return False

    def _detect_language(self, text: str) -> str:
        """Very lightweight language hint (placeholder)."""
        try:
            import langdetect
            return langdetect.detect(text)
        except Exception:
            return "en"
    
    def _create_ambiguity_summary(self, issues: List[Dict[str, Any]]) -> str:
        """Create a human-readable summary of ambiguities."""
        if not issues:
            return "To provide the best answer, we'd like to clarify a few things."
        
        summaries = []
        for issue in issues[:3]:
            desc = issue.get("description", "")
            if desc:
                summaries.append(desc)
        
        if summaries:
            return "To ensure we understand your request correctly: " + "; ".join(summaries) + "."
        return "We have a few questions to make sure we give you the best answer."
    
    async def _refine_query(
        self,
        original_query: str,
        questions: List[ClarificationQuestion],
        answers: Dict[str, str],
    ) -> Tuple[str, str]:
        """Refine the query using clarification answers."""
        # Build Q&A context
        qa_pairs = []
        for q in questions:
            answer = answers.get(q.id, "")
            if answer:
                qa_pairs.append(f"Q: {q.question}\nA: {answer}")
        
        clarification_context = "\n".join(qa_pairs)
        
        if not qa_pairs:
            return original_query, ""
        
        # Try LLM-based refinement
        if self.providers:
            try:
                provider = self.providers.get("openai") or next(iter(self.providers.values()))
                
                prompt = QUERY_REFINEMENT_PROMPT.format(
                    query=original_query,
                    clarifications=clarification_context,
                )
                
                result = await provider.complete(prompt, model="gpt-4o-mini")
                content = getattr(result, 'content', '') or getattr(result, 'text', '')
                refined = content.strip()
                
                if refined and len(refined) > 10:
                    return refined, clarification_context
                    
            except Exception as e:
                logger.warning("LLM query refinement failed: %s", e)
        
        # Fallback: Append clarifications to query
        refined = f"{original_query}\n\nClarifications:\n{clarification_context}"
        return refined, clarification_context
    
    def _parse_preference_answers(
        self,
        answers: Dict[str, str],
    ) -> AnswerPreferences:
        """Parse preference answers into AnswerPreferences object."""
        preferences = AnswerPreferences()
        
        # Parse detail level
        detail_answer = answers.get("pref_detail", "").lower()
        if "brief" in detail_answer:
            preferences.detail_level = DetailLevel.BRIEF
        elif "exhaustive" in detail_answer or "maximum" in detail_answer:
            preferences.detail_level = DetailLevel.EXHAUSTIVE
        elif "detailed" in detail_answer or "comprehensive" in detail_answer:
            preferences.detail_level = DetailLevel.DETAILED
        else:
            preferences.detail_level = DetailLevel.STANDARD
        
        # Parse format
        format_answer = answers.get("pref_format", "").lower()
        if "bullet" in format_answer:
            preferences.format = AnswerFormat.BULLET_POINTS
        elif "number" in format_answer or "step" in format_answer:
            preferences.format = AnswerFormat.NUMBERED_LIST
        elif "code" in format_answer:
            preferences.format = AnswerFormat.CODE_FOCUSED
        elif "structured" in format_answer or "header" in format_answer:
            preferences.format = AnswerFormat.STRUCTURED
        elif "conversation" in format_answer or "casual" in format_answer:
            preferences.format = AnswerFormat.CONVERSATIONAL
        else:
            preferences.format = AnswerFormat.PARAGRAPH
        
        # Parse tone
        tone_answer = answers.get("pref_tone", "").lower()
        if "casual" in tone_answer or "friendly" in tone_answer:
            preferences.tone = AnswerTone.CASUAL
        elif "technical" in tone_answer or "expert" in tone_answer:
            preferences.tone = AnswerTone.TECHNICAL
        elif "simplified" in tone_answer or "easy" in tone_answer or "no jargon" in tone_answer:
            preferences.tone = AnswerTone.SIMPLIFIED
        elif "educational" in tone_answer or "teaching" in tone_answer:
            preferences.tone = AnswerTone.EDUCATIONAL
        else:
            preferences.tone = AnswerTone.FORMAL
        
        return preferences


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def check_needs_clarification(
    query: str,
    *,
    providers: Optional[Dict[str, Any]] = None,
    threshold: float = 0.4,
) -> Tuple[bool, List[str]]:
    """
    Quick check if a query needs clarification.
    
    Args:
        query: The user's query
        providers: Optional LLM providers
        threshold: Ambiguity threshold
        
    Returns:
        Tuple of (needs_clarification, suggested_questions)
    """
    manager = ClarificationManager(
        providers=providers,
        ambiguity_threshold=threshold,
        always_ask_preferences=False,
    )
    
    request = await manager.analyze_and_generate_questions(query)
    
    questions = [q.question for q in request.query_questions]
    return request.has_query_questions, questions


def get_default_preferences() -> AnswerPreferences:
    """Get default answer preferences."""
    return AnswerPreferences()


def preferences_to_prompt_instructions(preferences: AnswerPreferences) -> str:
    """Convert preferences to prompt instructions for the LLM."""
    guidelines = preferences.to_style_guidelines()
    
    if not guidelines:
        return ""
    
    instruction = "Format your response according to these guidelines:\n"
    instruction += "\n".join(f"- {g}" for g in guidelines)
    
    return instruction

