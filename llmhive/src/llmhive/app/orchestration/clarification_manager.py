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

CLARIFICATION_DETECTION_PROMPT = """Analyze this user query to determine if clarification is needed.

Query: "{query}"

Identify issues that make the query unclear:
1. Ambiguous terms or pronouns (e.g., "it", "this", "they")
2. Vague scope (e.g., "tell me about X" without specifics)
3. Missing context (e.g., which version, time period, platform)
4. Unclear intent (e.g., could be answered multiple ways)
5. Implicit assumptions that need confirmation

Respond in JSON format:
{{
    "needs_clarification": boolean,
    "ambiguity_score": 0.0 to 1.0 (higher = more ambiguous),
    "issues": [
        {{
            "type": "ambiguous_term|vague_scope|missing_context|unclear_intent|implicit_assumption",
            "description": "what is unclear",
            "example_interpretations": ["interpretation 1", "interpretation 2"]
        }}
    ],
    "suggested_questions": [
        "Question 1 to resolve ambiguity?",
        "Question 2 to clarify scope?",
        "Question 3 to confirm intent?"
    ]
}}

Only suggest questions for significant ambiguities. Limit to 3 most important questions.
Respond ONLY with JSON."""


CLARIFICATION_QUESTIONS_PROMPT = """Generate clarifying questions for this query.

Query: "{query}"
Detected Issues: {issues}

Generate up to 3 focused, specific questions that will help us:
1. Understand exactly what the user is asking for
2. Narrow down the scope if too broad
3. Resolve any ambiguities in terminology or reference

Rules:
- Each question should address a distinct aspect
- Questions should be concise and specific
- Offer example answers when helpful
- Avoid yes/no questions when possible

Respond in JSON format:
{{
    "questions": [
        {{
            "id": "q1",
            "question": "The clarifying question",
            "why": "Why this clarification helps",
            "example_answers": ["Example answer 1", "Example answer 2"]
        }}
    ]
}}

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
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        ambiguity_threshold: float = 0.4,
        max_query_questions: int = 3,
        always_ask_preferences: bool = True,
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
    
    async def _detect_ambiguity(
        self,
        query: str,
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """Detect if the query is ambiguous and needs clarification."""
        
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
        """Rule-based ambiguity detection (fallback)."""
        query_lower = query.lower()
        issues = []
        questions = []
        possible_interpretations: List[str] = []
        language_hint = self._detect_language(query_lower)
        
        # Check for pronouns without clear referents
        pronouns = re.findall(r'\b(it|this|that|these|those|they|them)\b', query_lower)
        if pronouns and not history:  # Pronouns without history context
            issues.append({
                "type": "ambiguous_term",
                "description": f"Pronoun '{pronouns[0]}' without clear referent",
            })
            questions.append(f"What does '{pronouns[0]}' refer to in your question?")
        
        # Check for vague terms
        vague_terms = ["best", "good", "better", "improve", "optimize", "thing", "stuff"]
        for term in vague_terms:
            if term in query_lower.split():
                issues.append({
                    "type": "vague_scope",
                    "description": f"Vague term '{term}' needs context",
                })
                if term in ["best", "better"]:
                    questions.append(f"When you say '{term}', what criteria are most important to you?")
                break
        
        # Semantic ambiguity (polysemous terms)
        polysemous = {
            "bank": ["financial institution", "river bank"],
            "python": ["programming language", "the snake"],
            "java": ["programming language", "coffee"],
            "mercury": ["planet", "metal", "car brand", "medicine"],
            "apple": ["company", "fruit"],
        }
        for term, senses in polysemous.items():
            if term in query_lower.split():
                issues.append({
                    "type": "semantic_ambiguity",
                    "description": f"Term '{term}' can mean multiple things",
                    "options": senses,
                })
                possible_interpretations.extend(senses)
                questions.append(f"Do you mean {', '.join(senses[:-1])} or {senses[-1]}?")
                break
        
        # Temporal ambiguity
        temporal_patterns = ["next monday", "next tuesday", "next week", "next month", "tomorrow", "yesterday"]
        for t in temporal_patterns:
            if t in query_lower:
                issues.append({
                    "type": "temporal_ambiguity",
                    "description": f"'{t}' is time-relative; please specify an exact date/time or timezone",
                })
                questions.append("Which exact date/time (with timezone) do you mean?")
                break
        
        # Continuation without context
        if any(kw in query_lower for kw in ["continue", "next part", "keep going", "resume"]) and not history:
            issues.append({
                "type": "missing_context",
                "description": "Continuation requested but no prior conversation provided",
            })
            questions.append("What should I continue from? Please paste the prior content or summary.")
        
        # Extremely short / numeric / symbol-only queries
        if len(query.strip()) <= 3 or re.fullmatch(r"[\\d\\W]+", query.strip()):
            issues.append({
                "type": "underspecified",
                "description": "Very short query may have multiple meanings",
            })
            questions.append("Could you add a few words about what you want to know?")
        
        # Check for very broad queries
        broad_indicators = [
            "tell me about", "what is", "explain", "describe", 
            "how does", "what are"
        ]
        for indicator in broad_indicators:
            if query_lower.startswith(indicator) and len(query.split()) < 8:
                issues.append({
                    "type": "vague_scope",
                    "description": "Query may be too broad",
                })
                questions.append("Could you be more specific about what aspect you're most interested in?")
                break
        
        # Check for missing context
        context_needed_patterns = [
            (r'\b(my|our)\s+\w+', "Specific context about 'your' item may be needed"),
            (r'\bthe\s+\w+\s+(project|system|app|code)', "Which specific project/system?"),
        ]
        for pattern, msg in context_needed_patterns:
            if re.search(pattern, query_lower):
                issues.append({
                    "type": "missing_context",
                    "description": msg,
                })
                questions.append("Can you provide the specific name or link for that item?")
        
        # Compound/multi-part detection
        if " and " in query_lower and "?" in query_lower and len(query.split()) > 12:
            issues.append({
                "type": "compound_question",
                "description": "Multiple sub-questions detected; need priority",
            })
            questions.append("Which part should I address first, or should I cover all parts?")
        
        # If we built possible interpretations, add a guided choice question
        if possible_interpretations and len(possible_interpretations) >= 2:
            opts = ", ".join(possible_interpretations[:3])
            questions.append(f"To confirm, did you mean: {opts}?")
        
        # Determine if clarification is needed
        ambiguity_score = min(1.0, 0.2 * len(issues) + (0.1 if possible_interpretations else 0))
        needs_clarification = ambiguity_score >= self.ambiguity_threshold or (
            len(issues) >= 2 or (len(issues) >= 1 and len(query.split()) < 10)
        )
        
        # If we have language hint, prepend a localized nudge (lightweight)
        if language_hint and language_hint != "en":
            questions = [q for q in questions]  # placeholder for future localization
        
        return needs_clarification, issues, questions[:self.max_query_questions]

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

