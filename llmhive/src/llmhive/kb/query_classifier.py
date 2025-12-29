"""
LLMHive Query Classifier

Classifies user queries to determine:
- reasoning_type: What kind of reasoning is needed
- risk_level: How high-stakes is this query
- domain: What domain does this belong to
- citations_requested: Does the user want sources
- tools_needed: What tools might be needed

Usage:
    from llmhive.kb import get_query_classifier
    
    classifier = get_query_classifier()
    result = classifier.classify("Prove that sqrt(2) is irrational")
    print(result.reasoning_type)  # "mathematical_reasoning"
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Singleton instance
_classifier_instance: Optional["QueryClassifier"] = None
_classifier_lock = threading.Lock()


class ReasoningType(str, Enum):
    """Types of reasoning supported by the KB."""
    MATHEMATICAL_REASONING = "mathematical_reasoning"
    LOGICAL_DEDUCTIVE = "logical_deductive"
    PLANNING_MULTISTEP = "planning_multistep"
    TOOL_USE = "tool_use"
    RETRIEVAL_GROUNDING = "retrieval_grounding"
    CODING = "coding"
    ROBUSTNESS_ADVERSARIAL = "robustness_adversarial"
    CREATIVE = "creative"
    FACTUAL = "factual"
    GENERAL = "general"


class RiskLevel(str, Enum):
    """Risk levels for queries."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Domain(str, Enum):
    """Query domains."""
    MATH = "math"
    CODING = "coding"
    FACTUAL = "factual"
    PLANNING = "planning"
    TOOL_USE = "tool_use"
    CREATIVE = "creative"
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    GENERAL = "general"


@dataclass
class ClassificationResult:
    """Result of query classification."""
    reasoning_type: ReasoningType
    risk_level: RiskLevel
    domain: Domain
    citations_requested: bool = False
    tools_needed: List[str] = field(default_factory=list)
    confidence: float = 0.8
    heuristic_signals: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "reasoning_type": self.reasoning_type.value,
            "risk_level": self.risk_level.value,
            "domain": self.domain.value,
            "citations_requested": self.citations_requested,
            "tools_needed": self.tools_needed,
            "confidence": self.confidence,
            "heuristic_signals": self.heuristic_signals,
        }


# Keyword patterns for classification
MATH_PATTERNS = [
    r'\b(prove|proof|theorem|lemma|corollary)\b',
    r'\b(calculate|compute|solve|evaluate)\b',
    r'\b(equation|formula|integral|derivative)\b',
    r'\b(sqrt|sin|cos|tan|log|ln|exp)\b',
    r'\b(algebra|calculus|geometry|trigonometry)\b',
    r'\b(matrix|vector|eigenvalue|determinant)\b',
    r'\b(\d+\s*[\+\-\*\/\^]\s*\d+)',
    r'\b(sum|product|factorial|permutation|combination)\b',
]

CODING_PATTERNS = [
    r'\b(code|program|function|class|method)\b',
    r'\b(python|javascript|java|c\+\+|rust|go)\b',
    r'\b(algorithm|data structure|complexity)\b',
    r'\b(debug|fix|refactor|optimize)\b',
    r'\b(api|endpoint|request|response)\b',
    r'\b(compile|runtime|exception|error)\b',
    r'```[\s\S]*```',  # Code blocks
    r'\b(import|from|def|class|function)\b',
]

PLANNING_PATTERNS = [
    r'\b(plan|strategy|approach|steps)\b',
    r'\b(how (to|do|can|should))\b',
    r'\b(create|build|develop|implement)\b',
    r'\b(project|task|goal|objective)\b',
    r'\b(timeline|schedule|milestone)\b',
    r'\b(first|then|next|finally)\b',
]

TOOL_USE_PATTERNS = [
    r'\b(search|find|look up|google)\b',
    r'\b(browse|fetch|download|scrape)\b',
    r'\b(run|execute|call|invoke)\b',
    r'\b(api|tool|service|external)\b',
    r'\b(current|latest|today|now)\b',
    r'\b(real-time|live|up-to-date)\b',
]

FACTUAL_PATTERNS = [
    r'\b(what is|who is|when did|where is)\b',
    r'\b(explain|describe|define|tell me about)\b',
    r'\b(history|origin|background)\b',
    r'\b(fact|true|false|accurate)\b',
    r'\b(according to|based on|research shows)\b',
]

CREATIVE_PATTERNS = [
    r'\b(write|compose|create|generate)\b',
    r'\b(story|poem|essay|article|blog)\b',
    r'\b(creative|imaginative|original)\b',
    r'\b(brainstorm|ideas|concept)\b',
]

CITATION_PATTERNS = [
    r'\b(cite|citation|reference|source)\b',
    r'\b(according to|based on)\b',
    r'\b(provide sources|show references)\b',
    r'\b(academic|scholarly|peer-reviewed)\b',
]

HIGH_RISK_PATTERNS = [
    # Medical
    r'\b(symptom|diagnosis|treatment|medication|drug|dosage)\b',
    r'\b(disease|condition|illness|syndrome)\b',
    r'\b(doctor|physician|medical|health)\b',
    # Legal
    r'\b(law|legal|lawsuit|court|attorney|lawyer)\b',
    r'\b(contract|liability|sue|rights)\b',
    # Financial
    r'\b(invest|stock|portfolio|trading)\b',
    r'\b(tax|financial|retirement|loan)\b',
    r'\b(money|dollar|price|cost|fee)\b',
    # Safety
    r'\b(dangerous|safety|risk|harm)\b',
    r'\b(suicide|self-harm|abuse)\b',
]


class QueryClassifier:
    """
    Classifies queries to determine reasoning type and risk level.
    
    Uses heuristic pattern matching as the primary method.
    Can optionally use LLM-assisted classification for ambiguous cases.
    """
    
    def __init__(self, use_llm_assist: bool = False):
        """
        Initialize the classifier.
        
        Args:
            use_llm_assist: If True, use LLM for ambiguous cases
        """
        self.use_llm_assist = use_llm_assist
        
        # Compile patterns
        self._math_patterns = [re.compile(p, re.IGNORECASE) for p in MATH_PATTERNS]
        self._coding_patterns = [re.compile(p, re.IGNORECASE) for p in CODING_PATTERNS]
        self._planning_patterns = [re.compile(p, re.IGNORECASE) for p in PLANNING_PATTERNS]
        self._tool_patterns = [re.compile(p, re.IGNORECASE) for p in TOOL_USE_PATTERNS]
        self._factual_patterns = [re.compile(p, re.IGNORECASE) for p in FACTUAL_PATTERNS]
        self._creative_patterns = [re.compile(p, re.IGNORECASE) for p in CREATIVE_PATTERNS]
        self._citation_patterns = [re.compile(p, re.IGNORECASE) for p in CITATION_PATTERNS]
        self._high_risk_patterns = [re.compile(p, re.IGNORECASE) for p in HIGH_RISK_PATTERNS]
    
    def _count_matches(self, text: str, patterns: List[re.Pattern]) -> int:
        """Count how many patterns match in text."""
        count = 0
        for pattern in patterns:
            if pattern.search(text):
                count += 1
        return count
    
    def _detect_citations_requested(self, query: str) -> bool:
        """Detect if citations/sources are requested."""
        return any(p.search(query) for p in self._citation_patterns)
    
    def _detect_risk_level(self, query: str) -> RiskLevel:
        """Detect risk level of the query."""
        high_risk_matches = self._count_matches(query, self._high_risk_patterns)
        
        if high_risk_matches >= 2:
            return RiskLevel.HIGH
        elif high_risk_matches >= 1:
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _detect_domain(self, query: str) -> Domain:
        """Detect the domain of the query."""
        scores = {
            Domain.MATH: self._count_matches(query, self._math_patterns),
            Domain.CODING: self._count_matches(query, self._coding_patterns),
            Domain.PLANNING: self._count_matches(query, self._planning_patterns),
            Domain.TOOL_USE: self._count_matches(query, self._tool_patterns),
            Domain.FACTUAL: self._count_matches(query, self._factual_patterns),
            Domain.CREATIVE: self._count_matches(query, self._creative_patterns),
        }
        
        # Check for high-risk domains
        if any(p.search(query) for p in self._high_risk_patterns):
            # Determine specific high-risk domain
            query_lower = query.lower()
            if any(word in query_lower for word in ["symptom", "diagnosis", "treatment", "medication", "health"]):
                return Domain.MEDICAL
            elif any(word in query_lower for word in ["law", "legal", "lawsuit", "attorney"]):
                return Domain.LEGAL
            elif any(word in query_lower for word in ["invest", "stock", "tax", "financial"]):
                return Domain.FINANCIAL
        
        # Return domain with highest score
        max_domain = max(scores, key=scores.get)
        if scores[max_domain] > 0:
            return max_domain
        
        return Domain.GENERAL
    
    def _detect_reasoning_type(self, query: str, domain: Domain) -> ReasoningType:
        """Detect the type of reasoning needed."""
        # Domain-based mapping
        domain_to_reasoning = {
            Domain.MATH: ReasoningType.MATHEMATICAL_REASONING,
            Domain.CODING: ReasoningType.CODING,
            Domain.PLANNING: ReasoningType.PLANNING_MULTISTEP,
            Domain.TOOL_USE: ReasoningType.TOOL_USE,
            Domain.FACTUAL: ReasoningType.RETRIEVAL_GROUNDING,
            Domain.CREATIVE: ReasoningType.CREATIVE,
            Domain.MEDICAL: ReasoningType.RETRIEVAL_GROUNDING,
            Domain.LEGAL: ReasoningType.RETRIEVAL_GROUNDING,
            Domain.FINANCIAL: ReasoningType.RETRIEVAL_GROUNDING,
        }
        
        # Check for tool-use needs
        if self._count_matches(query, self._tool_patterns) >= 2:
            return ReasoningType.TOOL_USE
        
        # Check for logical/proof needs
        if "prove" in query.lower() or "proof" in query.lower():
            return ReasoningType.LOGICAL_DEDUCTIVE
        
        return domain_to_reasoning.get(domain, ReasoningType.GENERAL)
    
    def _detect_tools_needed(self, query: str, domain: Domain) -> List[str]:
        """Detect what tools might be needed."""
        tools = []
        
        # Web search for factual/current info
        if any(word in query.lower() for word in ["current", "latest", "today", "now", "2024", "2025"]):
            tools.append("web_search")
        
        # Citations need search
        if self._detect_citations_requested(query):
            tools.append("web_search")
        
        # Code execution for coding
        if domain == Domain.CODING:
            if any(word in query.lower() for word in ["run", "execute", "test", "output"]):
                tools.append("code_sandbox")
        
        # Calculator for math
        if domain == Domain.MATH:
            tools.append("calculator")
        
        return tools
    
    def classify(self, query: str) -> ClassificationResult:
        """
        Classify a query.
        
        Args:
            query: The user's query text
        
        Returns:
            ClassificationResult with reasoning_type, risk_level, etc.
        """
        if not query or not query.strip():
            return ClassificationResult(
                reasoning_type=ReasoningType.GENERAL,
                risk_level=RiskLevel.LOW,
                domain=Domain.GENERAL,
                confidence=0.5,
            )
        
        query = query.strip()
        
        # Detect all signals
        domain = self._detect_domain(query)
        reasoning_type = self._detect_reasoning_type(query, domain)
        risk_level = self._detect_risk_level(query)
        citations_requested = self._detect_citations_requested(query)
        tools_needed = self._detect_tools_needed(query, domain)
        
        # Compute confidence based on signal strength
        scores = {
            "math": self._count_matches(query, self._math_patterns),
            "coding": self._count_matches(query, self._coding_patterns),
            "planning": self._count_matches(query, self._planning_patterns),
            "tool_use": self._count_matches(query, self._tool_patterns),
            "factual": self._count_matches(query, self._factual_patterns),
            "creative": self._count_matches(query, self._creative_patterns),
        }
        max_score = max(scores.values()) if scores else 0
        confidence = min(0.95, 0.5 + (max_score * 0.1))
        
        return ClassificationResult(
            reasoning_type=reasoning_type,
            risk_level=risk_level,
            domain=domain,
            citations_requested=citations_requested,
            tools_needed=tools_needed,
            confidence=confidence,
            heuristic_signals=scores,
        )


def get_query_classifier(use_llm_assist: bool = False) -> QueryClassifier:
    """
    Get the singleton QueryClassifier instance.
    
    Thread-safe singleton pattern.
    """
    global _classifier_instance
    
    with _classifier_lock:
        if _classifier_instance is None:
            _classifier_instance = QueryClassifier(use_llm_assist=use_llm_assist)
        return _classifier_instance


def reset_classifier_instance() -> None:
    """Reset the singleton classifier instance (for testing)."""
    global _classifier_instance
    with _classifier_lock:
        _classifier_instance = None
