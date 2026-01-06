"""Quality Policies for LLMHive Orchestrator.

This module implements quality-focused policies that improve answer reliability:

1. Factoid Fast Path - Direct answers for simple factual questions
2. Consensus Verification Tie-Breaker - Resolve conflicts using fact-checking
3. Calibrated Confidence Scoring - Trustworthy uncertainty quantification
4. Self-Grader - Automatic quality improvement for high-accuracy modes

These policies prevent common failure modes like:
- Generic clarification requests for clear factoid questions
- Wrong consensus choices when models disagree on facts
- Missing confidence signals for uncertain answers
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Factoid Detection and Fast Path
# =============================================================================

class QueryType(str, Enum):
    """Classification of query types."""
    FACTOID = "factoid"           # Simple factual question with clear answer
    MATH = "math"                 # Mathematical calculation
    DEFINITION = "definition"     # What is X?
    COMPLEX = "complex"           # Multi-part or analytical
    AMBIGUOUS = "ambiguous"       # Genuinely unclear
    CREATIVE = "creative"         # Open-ended creative task
    CONVERSATIONAL = "conversational"  # Context-dependent chat


@dataclass
class QueryClassification:
    """Result of query classification."""
    query_type: QueryType
    confidence: float
    is_simple_factoid: bool
    allows_clarification: bool
    needs_verification: bool
    reasoning: str


# WH-words that typically indicate factoid questions
FACTOID_WH_WORDS = {
    "who", "what", "when", "where", "which",
    "how much", "how many", "how old", "how long", "how far"
}

# Patterns that indicate this is a simple factoid (no clarification needed)
SIMPLE_FACTOID_PATTERNS = [
    r"^who (?:is|was|discovered|invented|wrote|painted|created|founded|won)\b",
    r"^what (?:is|was|are|were) (?:the|a|an)?\s*\w+(?:\s+\w+){0,3}\??$",
    r"^what (?:is|are) (?:the )?\w+ (?:of|for|in) ",
    r"^when (?:did|was|is|were)\b",
    r"^where (?:is|was|are|were)\b",
    r"^which (?:is|was|are|were)\b",
    r"^how (?:much|many|old|long|far|tall|big|large)\b",
    r"^(?:what|who|when) .*(?:capital|discovered|invented|founded|born|died|wrote|painted)\b",
]

# Patterns that indicate complex/multi-part questions
COMPLEX_PATTERNS = [
    r"\band\s+\w+ly\b",  # "and additionally", "and comprehensively"
    r"\b(?:analyze|compare|explain|discuss|evaluate|assess)\b",
    r"\b(?:pros and cons|advantages and disadvantages)\b",
    r"\b(?:step by step|in detail|comprehensive)\b",
    r"[,;].*[,;]",  # Multiple clauses
    r"\b\d+\.\s+\w+",  # Numbered lists
]

# Patterns indicating truly ambiguous queries needing clarification
TRULY_AMBIGUOUS_PATTERNS = [
    r"^(?:it|this|that|they|them)\b",  # Dangling pronoun at start
    r"^tell me about it\b",
    r"^continue\b",
    r"^more\b",
    r"^what about\b",
    r"^how about\b",
]


def classify_query(query: str) -> QueryClassification:
    """Classify a query to determine appropriate handling strategy.
    
    This classification is critical for preventing generic clarification
    on factoid questions while still catching truly ambiguous queries.
    
    Args:
        query: The user's query
        
    Returns:
        QueryClassification with type and handling recommendations
    """
    query_lower = query.lower().strip()
    query_stripped = query.strip()
    
    # Check for math/calculation
    if _is_math_query(query_lower):
        return QueryClassification(
            query_type=QueryType.MATH,
            confidence=0.95,
            is_simple_factoid=True,  # Math is treated as factoid
            allows_clarification=False,
            needs_verification=True,
            reasoning="Mathematical calculation detected"
        )
    
    # Check for truly ambiguous queries FIRST
    for pattern in TRULY_AMBIGUOUS_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return QueryClassification(
                query_type=QueryType.AMBIGUOUS,
                confidence=0.9,
                is_simple_factoid=False,
                allows_clarification=True,
                needs_verification=False,
                reasoning=f"Ambiguous pattern matched: missing context"
            )
    
    # Check for simple factoid patterns
    for pattern in SIMPLE_FACTOID_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            # Additional check: short enough to be simple
            word_count = len(query_stripped.split())
            if word_count <= 12:
                return QueryClassification(
                    query_type=QueryType.FACTOID,
                    confidence=0.9,
                    is_simple_factoid=True,
                    allows_clarification=False,
                    needs_verification=word_count > 6,
                    reasoning=f"Simple factoid pattern matched"
                )
    
    # Check for complex patterns
    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return QueryClassification(
                query_type=QueryType.COMPLEX,
                confidence=0.85,
                is_simple_factoid=False,
                allows_clarification=False,  # Complex != ambiguous
                needs_verification=True,
                reasoning="Complex multi-part query detected"
            )
    
    # Check for definition queries
    if re.search(r"^what (?:is|are|was|were)\b", query_lower):
        return QueryClassification(
            query_type=QueryType.DEFINITION,
            confidence=0.85,
            is_simple_factoid=True,
            allows_clarification=False,
            needs_verification=False,
            reasoning="Definition query"
        )
    
    # Check word count for simplicity heuristic
    word_count = len(query_stripped.split())
    
    # Very short queries with WH-words are usually factoids
    if word_count <= 8:
        for wh in FACTOID_WH_WORDS:
            if query_lower.startswith(wh):
                return QueryClassification(
                    query_type=QueryType.FACTOID,
                    confidence=0.8,
                    is_simple_factoid=True,
                    allows_clarification=False,
                    needs_verification=False,
                    reasoning=f"Short WH-question: {wh}"
                )
    
    # Default: treat as conversational/general
    return QueryClassification(
        query_type=QueryType.CONVERSATIONAL,
        confidence=0.6,
        is_simple_factoid=False,
        allows_clarification=False,  # Default to not asking for clarification
        needs_verification=False,
        reasoning="General query - handle directly"
    )


def _is_math_query(query: str) -> bool:
    """Check if query is a math calculation request."""
    # Look for math operators and numbers
    if re.search(r'\d+\s*[\+\-\*\/\^]\s*\d+', query):
        return True
    if re.search(r'\b(?:calculate|compute|what is|solve)\b.*\d+', query, re.IGNORECASE):
        return True
    if re.search(r'\b(?:square root|factorial|percentage|percent)\b.*\d+', query, re.IGNORECASE):
        return True
    if re.search(r'\d+\s*(?:factorial|!)', query, re.IGNORECASE):
        return True
    return False


def should_skip_clarification(query: str) -> Tuple[bool, str]:
    """Determine if clarification should be skipped for this query.
    
    This is the main entry point for the factoid fast path.
    
    Returns:
        Tuple of (should_skip, reason)
    """
    classification = classify_query(query)
    
    if classification.is_simple_factoid:
        return True, f"Simple factoid: {classification.reasoning}"
    
    if not classification.allows_clarification:
        return True, f"Clarification not allowed: {classification.reasoning}"
    
    return False, ""


# =============================================================================
# Consensus Verification Tie-Breaker
# =============================================================================

@dataclass
class VerificationResult:
    """Result of verifying a claim or answer."""
    answer: str
    is_verified: bool
    confidence_score: float
    sources_found: int
    evidence: List[str] = field(default_factory=list)
    error: Optional[str] = None


async def verify_answer_claim(
    query: str,
    answer: str,
    providers: Dict[str, Any],
    fact_checker: Optional[Any] = None,
) -> VerificationResult:
    """Verify a specific answer claim using fact-checking.
    
    Args:
        query: The original question
        answer: The answer to verify
        providers: LLM providers
        fact_checker: Optional FactChecker instance
        
    Returns:
        VerificationResult with confidence and evidence
    """
    # If we have a fact checker, use it
    if fact_checker is not None:
        try:
            result = await fact_checker.verify(query, answer)
            return VerificationResult(
                answer=answer,
                is_verified=result.passed,
                confidence_score=result.score,
                sources_found=len(result.sources) if hasattr(result, 'sources') else 0,
                evidence=result.evidence if hasattr(result, 'evidence') else [],
            )
        except Exception as e:
            logger.debug("Fact check failed: %s", e)
    
    # Fallback: Use LLM-based verification
    return await _llm_verify_answer(query, answer, providers)


async def _llm_verify_answer(
    query: str,
    answer: str,
    providers: Dict[str, Any],
) -> VerificationResult:
    """Verify answer using LLM (fallback when no fact-checker)."""
    
    verification_prompt = f"""Verify this answer to the question.

Question: {query}
Answer: {answer}

Assess:
1. Is this factually correct based on established knowledge?
2. What is your confidence level (0-100)?
3. What evidence supports or contradicts this?

Respond in JSON format:
{{
  "is_correct": true/false,
  "confidence": 0-100,
  "reasoning": "brief explanation",
  "evidence": ["point 1", "point 2"]
}}"""
    
    provider = None
    if "openai" in providers:
        provider = providers["openai"]
    elif providers:
        provider = next(iter(providers.values()))
    
    if not provider:
        # No provider - return uncertain result
        return VerificationResult(
            answer=answer,
            is_verified=True,  # Assume correct if can't verify
            confidence_score=0.5,
            sources_found=0,
            error="No verification provider available"
        )
    
    try:
        result = await provider.complete(verification_prompt, model="gpt-4o-mini")
        content = getattr(result, 'content', '') or getattr(result, 'text', '')
        
        # Parse JSON response
        import json
        match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return VerificationResult(
                answer=answer,
                is_verified=data.get("is_correct", True),
                confidence_score=data.get("confidence", 50) / 100.0,
                sources_found=0,
                evidence=data.get("evidence", []),
            )
    except Exception as e:
        logger.debug("LLM verification failed: %s", e)
    
    # Fallback
    return VerificationResult(
        answer=answer,
        is_verified=True,
        confidence_score=0.5,
        sources_found=0,
        error="Verification parsing failed"
    )


async def resolve_consensus_conflict(
    query: str,
    candidate_answers: List[Tuple[str, str]],  # (model, answer)
    providers: Dict[str, Any],
    fact_checker: Optional[Any] = None,
) -> Tuple[str, str, float]:
    """Resolve conflicting answers using verification.
    
    When multiple models give different answers to a factual question,
    this function verifies each and selects the most likely correct one.
    
    Args:
        query: The original question
        candidate_answers: List of (model_name, answer) tuples
        providers: LLM providers
        fact_checker: Optional FactChecker instance
        
    Returns:
        Tuple of (winning_answer, winning_model, confidence)
    """
    if len(candidate_answers) == 0:
        return "", "", 0.0
    
    if len(candidate_answers) == 1:
        return candidate_answers[0][1], candidate_answers[0][0], 0.8
    
    # Verify each candidate
    verification_tasks = []
    for model, answer in candidate_answers:
        task = verify_answer_claim(query, answer, providers, fact_checker)
        verification_tasks.append(task)
    
    results = await asyncio.gather(*verification_tasks, return_exceptions=True)
    
    # Score each answer
    scored_answers = []
    for i, (model, answer) in enumerate(candidate_answers):
        result = results[i]
        if isinstance(result, Exception):
            score = 0.5
        else:
            score = result.confidence_score if result.is_verified else 0.3
        scored_answers.append((score, model, answer))
    
    # Sort by score descending
    scored_answers.sort(key=lambda x: x[0], reverse=True)
    
    best_score, best_model, best_answer = scored_answers[0]
    
    logger.info(
        "Consensus conflict resolved: chose %s (score %.2f) over %s",
        best_model,
        best_score,
        [m for s, m, a in scored_answers[1:]]
    )
    
    return best_answer, best_model, best_score


# =============================================================================
# Calibrated Confidence Scoring
# =============================================================================

@dataclass
class ConfidenceFactors:
    """Factors that contribute to confidence score."""
    ensemble_agreement: float = 0.5    # How much did models agree?
    verification_score: float = 0.5    # Did fact-check pass?
    source_presence: float = 0.0       # Are citations provided?
    tool_success: float = 0.5          # Did tools execute correctly?
    domain_safety: float = 1.0         # Is this a high-risk domain?


def calculate_confidence(
    factors: ConfidenceFactors,
    query: str = "",
) -> float:
    """Calculate calibrated confidence score from contributing factors.
    
    The confidence score is designed to be well-calibrated, meaning
    a 80% confidence should be correct ~80% of the time.
    
    Weights are tuned based on typical contribution to answer quality:
    - Ensemble agreement: 30% (strong signal when models agree)
    - Verification: 25% (fact-checking is highly informative)
    - Source presence: 20% (citations support reliability)
    - Tool success: 15% (tools provide external validation)
    - Domain safety: 10% (penalty for risky domains)
    
    Args:
        factors: ConfidenceFactors with individual scores
        query: Optional query for domain-based adjustments
        
    Returns:
        Calibrated confidence score 0-1
    """
    # Base weighted calculation
    confidence = (
        factors.ensemble_agreement * 0.30 +
        factors.verification_score * 0.25 +
        factors.source_presence * 0.20 +
        factors.tool_success * 0.15 +
        factors.domain_safety * 0.10
    )
    
    # Domain-specific caps
    if query:
        query_lower = query.lower()
        
        # Medical/health queries - cap confidence without verification
        if any(w in query_lower for w in ["symptom", "diagnos", "treatment", "disease", "medical"]):
            if factors.verification_score < 0.7:
                confidence = min(confidence, 0.6)
        
        # Legal queries - similar cap
        if any(w in query_lower for w in ["legal", "law", "lawsuit", "court", "attorney"]):
            if factors.verification_score < 0.7:
                confidence = min(confidence, 0.6)
        
        # Financial advice - require sources
        if any(w in query_lower for w in ["invest", "stock", "financial advice", "tax"]):
            if factors.source_presence < 0.5:
                confidence = min(confidence, 0.7)
    
    # Ensure 0-1 range
    return max(0.0, min(1.0, confidence))


def get_confidence_label(confidence: float) -> str:
    """Get human-readable confidence label."""
    if confidence >= 0.9:
        return "Very High"
    elif confidence >= 0.7:
        return "High"
    elif confidence >= 0.5:
        return "Moderate"
    elif confidence >= 0.3:
        return "Low"
    else:
        return "Very Low"


# =============================================================================
# Self-Grader
# =============================================================================

@dataclass
class SelfGradeResult:
    """Result of self-grading an answer."""
    correctness: float          # 0-1 likelihood answer is correct
    completeness: float         # 0-1 how complete is the answer
    hallucination_risk: float   # 0-1 risk of fabricated content
    composite_score: float      # Overall quality score
    needs_improvement: bool     # Should we try to improve?
    improvement_suggestions: List[str] = field(default_factory=list)


async def self_grade_answer(
    query: str,
    answer: str,
    providers: Dict[str, Any],
    threshold: float = 0.7,
) -> SelfGradeResult:
    """Self-grade an answer to determine if it needs improvement.
    
    This is used in Quality/Elite modes to catch low-quality answers
    before they reach the user.
    
    Args:
        query: Original question
        answer: Generated answer
        providers: LLM providers
        threshold: Score below which improvement is triggered
        
    Returns:
        SelfGradeResult with scores and recommendations
    """
    
    grading_prompt = f"""Grade this AI-generated answer objectively.

Question: {query}

Answer to grade:
{answer[:2000]}

Rate each dimension from 0-100:
1. CORRECTNESS: How likely is this factually accurate?
2. COMPLETENESS: Does it fully answer the question?
3. HALLUCINATION_RISK: Risk of fabricated/made-up content? (100=high risk)

Then list any specific improvements needed.

Respond in JSON:
{{
  "correctness": 0-100,
  "completeness": 0-100,
  "hallucination_risk": 0-100,
  "improvements": ["suggestion 1", "suggestion 2"]
}}"""
    
    provider = None
    if "openai" in providers:
        provider = providers["openai"]
    elif providers:
        provider = next(iter(providers.values()))
    
    if not provider:
        # No provider - return passing grade
        return SelfGradeResult(
            correctness=0.7,
            completeness=0.7,
            hallucination_risk=0.3,
            composite_score=0.7,
            needs_improvement=False,
        )
    
    try:
        result = await provider.complete(grading_prompt, model="gpt-4o-mini")
        content = getattr(result, 'content', '') or getattr(result, 'text', '')
        
        # Parse JSON
        import json
        match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            
            correctness = data.get("correctness", 70) / 100.0
            completeness = data.get("completeness", 70) / 100.0
            hallucination_risk = data.get("hallucination_risk", 30) / 100.0
            
            # Composite: high correctness and completeness, low hallucination risk
            composite = (correctness * 0.4 + completeness * 0.3 + (1 - hallucination_risk) * 0.3)
            
            return SelfGradeResult(
                correctness=correctness,
                completeness=completeness,
                hallucination_risk=hallucination_risk,
                composite_score=composite,
                needs_improvement=composite < threshold,
                improvement_suggestions=data.get("improvements", []),
            )
    except Exception as e:
        logger.debug("Self-grading failed: %s", e)
    
    # Fallback - assume OK
    return SelfGradeResult(
        correctness=0.7,
        completeness=0.7,
        hallucination_risk=0.3,
        composite_score=0.7,
        needs_improvement=False,
    )


# =============================================================================
# Stub Provider Detection
# =============================================================================

def detect_stub_provider(models_used: List[str], answer: str) -> bool:
    """Detect if a stub provider was used (configuration issue).
    
    Args:
        models_used: List of model names used
        answer: The generated answer
        
    Returns:
        True if stub provider detected
    """
    # Check model names
    for model in models_used:
        model_lower = model.lower() if model else ""
        if "stub" in model_lower or model_lower == "":
            return True
    
    # Check answer content
    answer_lower = answer.lower()
    stub_indicators = [
        "stub response",
        "this is a stub",
        "placeholder response",
        "[stub]",
    ]
    
    for indicator in stub_indicators:
        if indicator in answer_lower:
            return True
    
    return False


# =============================================================================
# Quality Metadata Builder
# =============================================================================

@dataclass
class QualityMetadata:
    """Complete quality metadata for a response."""
    trace_id: str
    confidence: float
    confidence_label: str
    models_used: List[str]
    strategy_used: str
    verification_status: str
    verification_score: Optional[float]
    tools_used: List[str]
    rag_used: bool
    memory_used: bool
    sources: List[Dict[str, str]]
    is_stub: bool = False
    self_graded: bool = False
    improvement_applied: bool = False


def build_quality_metadata(
    trace_id: str,
    confidence_factors: ConfidenceFactors,
    query: str = "",
    models_used: Optional[List[str]] = None,
    strategy_used: str = "direct",
    verification_status: str = "SKIPPED",
    verification_score: Optional[float] = None,
    tools_used: Optional[List[str]] = None,
    rag_used: bool = False,
    memory_used: bool = False,
    sources: Optional[List[Dict[str, str]]] = None,
    answer: str = "",
) -> QualityMetadata:
    """Build complete quality metadata for response.
    
    This should be called for every response to ensure consistent metadata.
    
    Args:
        trace_id: Unique request identifier
        confidence_factors: Individual confidence components
        query: Original query (for domain adjustments)
        models_used: Models that contributed
        strategy_used: hrm/consensus/tools/rag/direct
        verification_status: PASS/FAIL/PARTIAL/SKIPPED
        verification_score: Fact-check score if available
        tools_used: External tools invoked
        rag_used: Whether retrieval was used
        memory_used: Whether session memory was used
        sources: Citation sources
        answer: The generated answer (for stub detection)
        
    Returns:
        Complete QualityMetadata object
    """
    models = models_used or []
    confidence = calculate_confidence(confidence_factors, query)
    is_stub = detect_stub_provider(models, answer)
    
    return QualityMetadata(
        trace_id=trace_id,
        confidence=confidence,
        confidence_label=get_confidence_label(confidence),
        models_used=models,
        strategy_used=strategy_used,
        verification_status=verification_status,
        verification_score=verification_score,
        tools_used=tools_used or [],
        rag_used=rag_used,
        memory_used=memory_used,
        sources=sources or [],
        is_stub=is_stub,
    )

