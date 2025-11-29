"""Clarification loop for handling ambiguous queries."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ClarificationRequest:
    """Represents a request for user clarification."""
    
    original_query: str
    clarification_question: str
    possible_interpretations: List[str]
    ambiguity_reasons: List[str]
    query_id: Optional[str] = None  # For tracking clarification sessions


@dataclass
class AmbiguityAnalysis:
    """Result of ambiguity analysis for a query."""
    
    is_ambiguous: bool
    ambiguity_score: float  # 0.0-1.0, higher = more ambiguous
    reasons: List[str]
    possible_interpretations: List[str]
    suggested_clarification: Optional[str] = None


class AmbiguityDetector:
    """Detects ambiguous or underspecified queries."""
    
    # Common ambiguous terms that need context
    AMBIGUOUS_TERMS = {
        "it", "this", "that", "these", "those", "they", "them",
        "here", "there", "now", "then", "recent", "latest", "current",
        "better", "best", "good", "bad", "important", "relevant",
        "tell me about", "what is", "explain", "how does", "why",
    }
    
    # Very short queries are often ambiguous
    MIN_QUERY_LENGTH = 10
    
    # Queries with only numbers or very generic terms
    GENERIC_PATTERNS = [
        r'^\d+$',  # Just a number like "42"
        r'^[a-z]{1,3}$',  # Very short words
        r'^(what|how|why|when|where|who)\s*\?*$',  # Just question words
    ]
    
    def analyze(self, query: str, context: Optional[str] = None) -> AmbiguityAnalysis:
        """
        Analyze a query for ambiguity.
        
        Args:
            query: The user query to analyze
            context: Optional conversation context
            
        Returns:
            AmbiguityAnalysis with ambiguity detection results
        """
        query_lower = query.lower().strip()
        reasons: List[str] = []
        interpretations: List[str] = []
        score = 0.0
        
        # Check 1: Query too short
        if len(query_lower) < self.MIN_QUERY_LENGTH:
            reasons.append(f"Query is too short ({len(query_lower)} characters)")
            score += 0.3
            interpretations.append("Query may be incomplete or need more detail")
        
        # Check 2: Generic patterns (just numbers, very short words, etc.)
        for pattern in self.GENERIC_PATTERNS:
            if re.match(pattern, query_lower):
                reasons.append(f"Query matches generic pattern: {pattern}")
                score += 0.4
                if re.match(r'^\d+$', query_lower):
                    # Number-only queries are highly ambiguous
                    interpretations.append(f"Could refer to the number {query_lower} in mathematics")
                    interpretations.append(f"Could refer to '{query_lower}' as a cultural reference")
                    interpretations.append(f"Could refer to '{query_lower}' as an identifier or code")
                break
        
        # Check 3: Ambiguous pronouns or references without context
        ambiguous_refs = [term for term in self.AMBIGUOUS_TERMS if term in query_lower]
        if ambiguous_refs and not context:
            reasons.append(f"Contains ambiguous references: {', '.join(ambiguous_refs[:3])}")
            score += 0.2
            interpretations.append("Query contains pronouns or references that need context")
        
        # Check 4: Very broad question words without specifics
        broad_questions = ["what is", "tell me about", "explain"]
        if any(broad in query_lower for broad in broad_questions):
            # Check if there's a specific subject after the question word
            words = query_lower.split()
            if len(words) <= 3:  # Very short after question word
                reasons.append("Broad question without specific subject")
                score += 0.3
                interpretations.append("Query lacks specific subject or topic")
        
        # Check 5: Multiple possible interpretations based on common ambiguous queries
        if query_lower == "42" or query_lower.strip() == "42":
            reasons.append("Number-only query with multiple cultural meanings")
            score = 1.0  # Maximum ambiguity
            interpretations.append("The number 42 in mathematics (answer to life, universe, everything)")
            interpretations.append("The number 42 as a pop culture reference (Hitchhiker's Guide)")
            interpretations.append("The number 42 as a sports jersey number")
        
        # Normalize score to 0.0-1.0
        score = min(1.0, score)
        
        # Determine if ambiguous (threshold: 0.4)
        is_ambiguous = score >= 0.4
        
        # Generate suggested clarification if ambiguous
        suggested_clarification = None
        if is_ambiguous:
            suggested_clarification = self._generate_clarification_question(
                query, reasons, interpretations
            )
        
        return AmbiguityAnalysis(
            is_ambiguous=is_ambiguous,
            ambiguity_score=score,
            reasons=reasons,
            possible_interpretations=interpretations[:3],  # Limit to top 3
            suggested_clarification=suggested_clarification,
        )
    
    def _generate_clarification_question(
        self,
        query: str,
        reasons: List[str],
        interpretations: List[str],
    ) -> str:
        """
        Generate a clarifying question based on ambiguity analysis.
        
        Args:
            query: Original ambiguous query
            reasons: List of ambiguity reasons
            interpretations: List of possible interpretations
            
        Returns:
            Clarifying question string
        """
        # Special handling for number-only queries
        if re.match(r'^\d+$', query.strip()):
            if len(interpretations) >= 2:
                return (
                    f"I see you asked about '{query}'. Could you clarify what you mean? "
                    f"For example: {interpretations[0]}, {interpretations[1]}, "
                    f"or something else?"
                )
            else:
                return (
                    f"Could you provide more context about '{query}'? "
                    f"What specifically would you like to know?"
                )
        
        # Handle very short queries
        if len(query.strip()) < self.MIN_QUERY_LENGTH:
            return (
                f"Your query seems incomplete. Could you provide more details about "
                f"what you're looking for? For example, what specific aspect of "
                f"'{query}' would you like to know about?"
            )
        
        # Handle ambiguous references
        if "ambiguous references" in str(reasons):
            return (
                f"Your query contains some references that could mean different things. "
                f"Could you provide more context or be more specific about what you're asking?"
            )
        
        # Generic clarification
        if interpretations:
            if len(interpretations) == 1:
                return (
                    f"To provide the best answer, could you clarify: {interpretations[0]}?"
                )
            else:
                options = " or ".join([f"'{i}'" for i in interpretations[:2]])
                return (
                    f"Your query could mean several things. Are you asking about "
                    f"{options}, or something else? Please provide more details."
                )
        
        # Fallback
        return (
            f"Could you provide more details about your question? "
            f"What specific information are you looking for regarding '{query}'?"
        )


class ClarificationGenerator:
    """Generates clarification questions using LLM or templates."""
    
    def __init__(self, providers: Optional[dict] = None):
        """
        Initialize clarification generator.
        
        Args:
            providers: Optional dict of LLM providers for generating clarifications
        """
        self.providers = providers or {}
        self.detector = AmbiguityDetector()
    
    def generate_clarification(
        self,
        query: str,
        context: Optional[str] = None,
        use_llm: bool = False,
    ) -> Optional[ClarificationRequest]:
        """
        Generate a clarification request for an ambiguous query.
        
        Args:
            query: The ambiguous query
            context: Optional conversation context
            use_llm: Whether to use LLM for generating clarification (default: False, uses templates)
            
        Returns:
            ClarificationRequest if query is ambiguous, None otherwise
        """
        # Analyze for ambiguity
        analysis = self.detector.analyze(query, context)
        
        if not analysis.is_ambiguous:
            return None
        
        # Generate clarification question
        if use_llm and self.providers:
            clarification_question = self._generate_with_llm(query, analysis, context)
        else:
            clarification_question = analysis.suggested_clarification or self._generate_template(query, analysis)
        
        return ClarificationRequest(
            original_query=query,
            clarification_question=clarification_question,
            possible_interpretations=analysis.possible_interpretations,
            ambiguity_reasons=analysis.reasons,
        )
    
    def _generate_template(
        self,
        query: str,
        analysis: AmbiguityAnalysis,
    ) -> str:
        """Generate clarification using template (fallback)."""
        return analysis.suggested_clarification or (
            f"To provide the best answer, could you clarify what you mean by '{query}'? "
            f"Please provide more specific details or context."
        )
    
    def _generate_with_llm(
        self,
        query: str,
        analysis: AmbiguityAnalysis,
        context: Optional[str] = None,
    ) -> str:
        """
        Generate clarification question using LLM.
        
        Args:
            query: Original query
            analysis: Ambiguity analysis results
            context: Optional context
            
        Returns:
            Generated clarification question
        """
        # Try to use a lightweight model for clarification generation
        try:
            # Use gpt-4o-mini or similar lightweight model if available
            provider = None
            model = "gpt-4o-mini"
            
            for prov_name, prov in self.providers.items():
                if "openai" in prov_name.lower() or "gpt" in prov_name.lower():
                    provider = prov
                    break
            
            if not provider:
                # Fallback to first available provider
                provider = next(iter(self.providers.values())) if self.providers else None
            
            if not provider:
                return self._generate_template(query, analysis)
            
            # Build prompt for clarification generation
            prompt = f"""The user asked: "{query}"

This query is ambiguous because:
{chr(10).join(f"- {reason}" for reason in analysis.reasons)}

Possible interpretations:
{chr(10).join(f"- {interp}" for interp in analysis.possible_interpretations)}

Generate a friendly, concise clarifying question (1-2 sentences) to help the user specify what they mean. 
Be conversational and helpful. Do not include the original query in your response, just the clarifying question."""

            if context:
                prompt += f"\n\nContext from conversation: {context[:200]}"
            
            # Generate clarification
            result = provider.complete(prompt, model=model)
            if result and hasattr(result, 'content'):
                return result.content.strip()
            elif isinstance(result, str):
                return result.strip()
            else:
                return self._generate_template(query, analysis)
                
        except Exception as exc:
            logger.warning("Failed to generate clarification with LLM: %s", exc)
            return self._generate_template(query, analysis)
    
    def incorporate_clarification(
        self,
        original_query: str,
        clarification_response: str,
    ) -> str:
        """
        Incorporate user's clarification into the original query.
        
        Args:
            original_query: The original ambiguous query
            clarification_response: User's response to clarification question
            
        Returns:
            Enhanced query with clarification incorporated
        """
        # Simple approach: append clarification to original query
        # More sophisticated: could use LLM to merge intelligently
        enhanced = f"{original_query}\n\nContext: {clarification_response}"
        return enhanced

