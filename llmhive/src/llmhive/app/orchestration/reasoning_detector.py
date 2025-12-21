"""Reasoning Model Detector - Intelligent routing to reasoning models.

This module implements reasoning model routing signal detection:
- Detects queries that require deep reasoning
- Routes to o1, Claude 4 with extended thinking, or similar
- Expected impact: 20-40% improvement on hard reasoning tasks

Based on orchestration pattern #2 from the intel memo.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReasoningType(str, Enum):
    """Types of reasoning that may require specialized models."""
    NONE = "none"                     # No special reasoning needed
    LOGICAL = "logical"               # Logical deduction
    MATHEMATICAL = "mathematical"     # Math proofs, calculations
    ANALYTICAL = "analytical"         # Deep analysis, comparisons
    VERIFICATION = "verification"     # Fact checking, validation
    PLANNING = "planning"             # Multi-step planning
    SCIENTIFIC = "scientific"         # Scientific reasoning, hypotheses
    CODING_COMPLEX = "coding_complex" # Complex code architecture


@dataclass
class ReasoningSignal:
    """A signal that suggests reasoning is needed."""
    pattern: str
    reasoning_type: ReasoningType
    weight: float = 1.0
    description: str = ""


@dataclass
class ReasoningAnalysis:
    """Analysis of a query's reasoning requirements."""
    needs_reasoning_model: bool
    reasoning_type: ReasoningType
    confidence: float
    detected_signals: List[str]
    recommended_models: List[str]
    recommended_effort: str  # "low", "medium", "high"
    explanation: str


class ReasoningDetector:
    """
    Detects queries requiring reasoning models.
    
    Uses pattern matching and heuristics to identify queries that would
    benefit from reasoning models like o1, o3-mini, or Claude with extended thinking.
    """
    
    # Reasoning models with their characteristics
    REASONING_MODELS = {
        "openai/o1": {
            "name": "o1",
            "reasoning_effort": ["low", "medium", "high"],
            "supports_tools": False,
            "best_for": ["mathematical", "scientific", "verification"],
            "cost_tier": "premium",
        },
        "openai/o1-mini": {
            "name": "o1-mini",
            "reasoning_effort": None,
            "supports_tools": False,
            "best_for": ["mathematical", "coding_complex"],
            "cost_tier": "standard",
        },
        "openai/o3-mini": {
            "name": "o3-mini",
            "reasoning_effort": ["low", "medium", "high"],
            "supports_tools": True,
            "best_for": ["coding_complex", "planning", "analytical"],
            "cost_tier": "standard",
        },
        "anthropic/claude-sonnet-4-20250514": {
            "name": "Claude 4 Sonnet",
            "reasoning_effort": None,  # Uses extended thinking
            "supports_tools": True,
            "best_for": ["analytical", "coding_complex", "planning"],
            "cost_tier": "standard",
            "extended_thinking": True,
        },
        "anthropic/claude-opus-4-20250514": {
            "name": "Claude 4 Opus",
            "reasoning_effort": None,
            "supports_tools": True,
            "best_for": ["scientific", "analytical", "verification"],
            "cost_tier": "premium",
            "extended_thinking": True,
        },
        "google/gemini-2.0-flash-thinking": {
            "name": "Gemini 2.0 Flash Thinking",
            "reasoning_effort": None,
            "supports_tools": True,
            "best_for": ["mathematical", "logical"],
            "cost_tier": "budget",
        },
        "deepseek/deepseek-reasoner": {
            "name": "DeepSeek R1",
            "reasoning_effort": None,
            "supports_tools": False,
            "best_for": ["mathematical", "coding_complex"],
            "cost_tier": "budget",
        },
    }
    
    # Signals that indicate reasoning is needed
    REASONING_SIGNALS: List[ReasoningSignal] = [
        # Mathematical reasoning
        ReasoningSignal(r"\bprove\b", ReasoningType.MATHEMATICAL, 1.0, "Mathematical proof"),
        ReasoningSignal(r"\bderive\b", ReasoningType.MATHEMATICAL, 1.0, "Mathematical derivation"),
        ReasoningSignal(r"\bcalculate\s+the\s+probability\b", ReasoningType.MATHEMATICAL, 0.9),
        ReasoningSignal(r"\bsolve\s+the\s+equation\b", ReasoningType.MATHEMATICAL, 0.8),
        ReasoningSignal(r"\bintegrate\b|\bdifferentiate\b", ReasoningType.MATHEMATICAL, 0.8),
        ReasoningSignal(r"\boptimize\b", ReasoningType.MATHEMATICAL, 0.7),
        
        # Logical reasoning
        ReasoningSignal(r"\bwhy\s+does\b", ReasoningType.LOGICAL, 0.7, "Causal reasoning"),
        ReasoningSignal(r"\bexplain\s+(step\s+by\s+step|in\s+detail)\b", ReasoningType.LOGICAL, 0.8),
        ReasoningSignal(r"\blogical(ly)?\s+(deduc|induc|reason)\b", ReasoningType.LOGICAL, 1.0),
        ReasoningSignal(r"\bif\s+and\s+only\s+if\b", ReasoningType.LOGICAL, 0.9),
        ReasoningSignal(r"\bnecessary\s+and\s+sufficient\b", ReasoningType.LOGICAL, 0.9),
        
        # Analytical reasoning
        ReasoningSignal(r"\bcompare\s+and\s+contrast\b", ReasoningType.ANALYTICAL, 0.8),
        ReasoningSignal(r"\bcritically\s+(assess|evaluate|analyze)\b", ReasoningType.ANALYTICAL, 0.9),
        ReasoningSignal(r"\bweigh\s+the\s+(pros|advantages)\b", ReasoningType.ANALYTICAL, 0.7),
        ReasoningSignal(r"\banalyze\s+in\s+depth\b", ReasoningType.ANALYTICAL, 0.8),
        ReasoningSignal(r"\bevaluate\s+the\s+implications\b", ReasoningType.ANALYTICAL, 0.8),
        
        # Verification
        ReasoningSignal(r"\bverify\b", ReasoningType.VERIFICATION, 0.8, "Verification needed"),
        ReasoningSignal(r"\bvalidate\b", ReasoningType.VERIFICATION, 0.7),
        ReasoningSignal(r"\bcheck\s+(if|whether)\b", ReasoningType.VERIFICATION, 0.6),
        ReasoningSignal(r"\bis\s+this\s+(correct|right|accurate)\b", ReasoningType.VERIFICATION, 0.7),
        ReasoningSignal(r"\bfact\s*check\b", ReasoningType.VERIFICATION, 0.9),
        
        # Planning
        ReasoningSignal(r"\bstep-by-step\s+plan\b", ReasoningType.PLANNING, 0.9),
        ReasoningSignal(r"\bdesign\s+a\s+strategy\b", ReasoningType.PLANNING, 0.8),
        ReasoningSignal(r"\bhow\s+would\s+you\s+approach\b", ReasoningType.PLANNING, 0.7),
        ReasoningSignal(r"\bcreate\s+a\s+(roadmap|timeline)\b", ReasoningType.PLANNING, 0.8),
        ReasoningSignal(r"\bbreak\s+(down|this)\s+into\s+steps\b", ReasoningType.PLANNING, 0.7),
        
        # Scientific reasoning
        ReasoningSignal(r"\bhypothesi[sz]e\b", ReasoningType.SCIENTIFIC, 0.9),
        ReasoningSignal(r"\bscientific(ally)?\s+(explain|reason)\b", ReasoningType.SCIENTIFIC, 0.9),
        ReasoningSignal(r"\bexperimental\s+design\b", ReasoningType.SCIENTIFIC, 0.8),
        ReasoningSignal(r"\bphd[\s\-]level\b", ReasoningType.SCIENTIFIC, 1.0),
        ReasoningSignal(r"\bresearch\s+question\b", ReasoningType.SCIENTIFIC, 0.7),
        
        # Complex coding
        ReasoningSignal(r"\barchitect(ure)?\s+(a|the)\s+system\b", ReasoningType.CODING_COMPLEX, 0.9),
        ReasoningSignal(r"\bdesign\s+pattern\b", ReasoningType.CODING_COMPLEX, 0.7),
        ReasoningSignal(r"\brefactor\s+(the\s+entire|completely)\b", ReasoningType.CODING_COMPLEX, 0.8),
        ReasoningSignal(r"\bdebug\s+(a\s+)?complex\b", ReasoningType.CODING_COMPLEX, 0.8),
        ReasoningSignal(r"\bcode\s+review\b", ReasoningType.CODING_COMPLEX, 0.6),
    ]
    
    # Threshold for recommending reasoning model
    # Lower threshold means more queries get reasoning models
    # A single strong signal (1.0) gives confidence 0.5
    REASONING_THRESHOLD = 0.4
    
    def __init__(self):
        """Initialize the reasoning detector."""
        # Compile regex patterns for efficiency
        self._compiled_patterns = [
            (re.compile(signal.pattern, re.IGNORECASE), signal)
            for signal in self.REASONING_SIGNALS
        ]
    
    def detect(self, query: str) -> ReasoningAnalysis:
        """
        Analyze a query for reasoning requirements.
        
        Args:
            query: User query text
            
        Returns:
            ReasoningAnalysis with recommendations
        """
        detected_signals: List[str] = []
        reasoning_scores: Dict[ReasoningType, float] = {rt: 0.0 for rt in ReasoningType}
        
        # Check each pattern
        for pattern, signal in self._compiled_patterns:
            if pattern.search(query):
                detected_signals.append(signal.description or signal.pattern)
                reasoning_scores[signal.reasoning_type] += signal.weight
        
        # Find dominant reasoning type
        max_score = max(reasoning_scores.values())
        dominant_type = max(reasoning_scores, key=reasoning_scores.get)
        
        # Normalize score
        confidence = min(1.0, max_score / 2.0)  # 2.0 signals = full confidence
        
        # Determine if reasoning model is needed
        needs_reasoning = confidence >= self.REASONING_THRESHOLD
        
        # Select recommended models
        recommended_models = self._get_recommended_models(
            dominant_type,
            needs_tools="function" in query.lower() or "tool" in query.lower(),
            budget_sensitive="cheap" in query.lower() or "budget" in query.lower(),
        )
        
        # Determine effort level
        if confidence >= 0.9:
            effort = "high"
        elif confidence >= 0.7:
            effort = "medium"
        else:
            effort = "low"
        
        # Generate explanation
        if needs_reasoning:
            explanation = (
                f"Query requires {dominant_type.value} reasoning. "
                f"Detected signals: {', '.join(detected_signals[:3])}. "
                f"Recommend using reasoning model with {effort} effort."
            )
        else:
            explanation = "No strong reasoning signals detected. Standard model should suffice."
        
        return ReasoningAnalysis(
            needs_reasoning_model=needs_reasoning,
            reasoning_type=dominant_type if needs_reasoning else ReasoningType.NONE,
            confidence=confidence,
            detected_signals=detected_signals,
            recommended_models=recommended_models,
            recommended_effort=effort,
            explanation=explanation,
        )
    
    def _get_recommended_models(
        self,
        reasoning_type: ReasoningType,
        needs_tools: bool = False,
        budget_sensitive: bool = False,
    ) -> List[str]:
        """Get recommended models for a reasoning type."""
        candidates: List[Tuple[str, int]] = []  # (model_id, priority)
        
        for model_id, info in self.REASONING_MODELS.items():
            priority = 0
            
            # Check if reasoning type matches
            if reasoning_type.value in info.get("best_for", []):
                priority += 3
            
            # Check tool support if needed
            if needs_tools and not info.get("supports_tools", True):
                continue  # Skip models without tool support
            
            # Check budget
            if budget_sensitive:
                if info.get("cost_tier") == "budget":
                    priority += 2
                elif info.get("cost_tier") == "premium":
                    priority -= 2
            
            # Prefer models with effort control for complex reasoning
            if info.get("reasoning_effort"):
                priority += 1
            
            candidates.append((model_id, priority))
        
        # Sort by priority and return top 3
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates[:3]]
    
    def get_effort_for_query(
        self,
        query: str,
        analysis: Optional[ReasoningAnalysis] = None,
    ) -> str:
        """
        Get recommended reasoning effort for a query.
        
        Args:
            query: User query
            analysis: Optional pre-computed analysis
            
        Returns:
            "low", "medium", or "high"
        """
        if analysis is None:
            analysis = self.detect(query)
        
        return analysis.recommended_effort
    
    def should_use_extended_thinking(
        self,
        query: str,
        model_id: str,
    ) -> bool:
        """
        Determine if extended thinking should be enabled.
        
        Args:
            query: User query
            model_id: Model being used
            
        Returns:
            True if extended thinking should be enabled
        """
        # Check if model supports extended thinking
        model_info = self.REASONING_MODELS.get(model_id, {})
        if not model_info.get("extended_thinking"):
            return False
        
        # Analyze query
        analysis = self.detect(query)
        return analysis.needs_reasoning_model


# Singleton instance
_reasoning_detector: Optional[ReasoningDetector] = None


def get_reasoning_detector() -> ReasoningDetector:
    """Get or create the singleton reasoning detector."""
    global _reasoning_detector
    if _reasoning_detector is None:
        _reasoning_detector = ReasoningDetector()
    return _reasoning_detector


def needs_reasoning_model(query: str) -> bool:
    """
    Quick check if a query needs a reasoning model.
    
    Args:
        query: User query text
        
    Returns:
        True if reasoning model is recommended
    """
    detector = get_reasoning_detector()
    analysis = detector.detect(query)
    return analysis.needs_reasoning_model


def get_reasoning_model_recommendation(
    query: str,
    needs_tools: bool = False,
) -> Tuple[str, str]:
    """
    Get recommended reasoning model and effort level.
    
    Args:
        query: User query
        needs_tools: Whether function/tool calling is needed
        
    Returns:
        Tuple of (model_id, effort_level)
    """
    detector = get_reasoning_detector()
    analysis = detector.detect(query)
    
    if not analysis.recommended_models:
        # Default fallback
        if needs_tools:
            return "openai/o3-mini", "medium"
        return "openai/o1", "medium"
    
    return analysis.recommended_models[0], analysis.recommended_effort

