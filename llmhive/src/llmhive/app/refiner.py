"""Answer formatting and refinement utilities.

This module handles answer formatting based on user preferences including:
- Detail level (brief, standard, detailed, exhaustive)
- Format (paragraph, bullet points, numbered list, code, structured)
- Tone (formal, casual, technical, simplified, educational)

The AnswerRefiner class integrates with the ClarificationManager to apply
user-specified preferences to the final answer.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestration.clarification_manager import AnswerPreferences

logger = logging.getLogger(__name__)


def format_answer(
    answer_text: str,
    format_style: str = "paragraph",
    *,
    confidence_score: Optional[float] = None,
    confidence_level: Optional[str] = None,
) -> str:
    """
    Format the final answer according to user preferences.
    
    Args:
        answer_text: The raw answer text to format
        format_style: Format style - "bullet" or "paragraph" (default: "paragraph")
        confidence_score: Optional confidence score (0.0-1.0) for indicator
        confidence_level: Optional confidence level ("High", "Medium", "Low") for indicator
        
    Returns:
        Formatted answer text with optional confidence indicator
    """
    if not answer_text or not answer_text.strip():
        return answer_text
    
    # Clean up the answer text first
    formatted = answer_text.strip()
    
    # Apply format style
    if format_style == "bullet":
        formatted = _format_as_bullets(formatted)
    elif format_style == "paragraph":
        formatted = _format_as_paragraph(formatted)
    else:
        # Unknown format style, default to paragraph
        logger.warning("Unknown format_style '%s', defaulting to paragraph", format_style)
        formatted = _format_as_paragraph(formatted)
    
    # Add confidence indicator if provided
    if confidence_score is not None or confidence_level is not None:
        confidence_indicator = _format_confidence_indicator(confidence_score, confidence_level)
        if confidence_indicator:
            formatted = f"{formatted}\n\n---\n{confidence_indicator}"
    
    return formatted


def _format_as_bullets(text: str) -> str:
    """
    Format text as bullet points.
    
    Splits text into sentences or key points and prefixes each with "- ".
    For long sentences, attempts to create concise bullet points.
    """
    # First, try to split by existing bullet points or list markers
    lines = text.split("\n")
    bullet_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # If line already starts with a bullet marker, keep it
        if re.match(r'^[-*•]\s+', line):
            bullet_lines.append(line)
            continue
        
        # If line is a numbered list item, convert to bullet
        if re.match(r'^\d+[.)]\s+', line):
            bullet_lines.append(re.sub(r'^\d+[.)]\s+', '- ', line))
            continue
        
        # Split long lines into sentences and create bullets
        # Simple sentence splitting (period, exclamation, question mark followed by space)
        sentences = re.split(r'([.!?]\s+)', line)
        current_sentence = ""
        
        for part in sentences:
            current_sentence += part
            # If we have a complete sentence (ends with punctuation)
            if re.search(r'[.!?]\s*$', current_sentence.strip()):
                sentence = current_sentence.strip()
                if sentence:
                    # Make it concise - if too long, try to summarize
                    if len(sentence) > 150:
                        # For very long sentences, try to split by commas or semicolons
                        parts = re.split(r'[,;]\s+', sentence)
                        for part in parts:
                            part = part.strip()
                            if part:
                                # Remove trailing punctuation if it's not the last part
                                if part.endswith('.') and len(parts) > 1:
                                    part = part[:-1]
                                bullet_lines.append(f"- {part}")
                    else:
                        bullet_lines.append(f"- {sentence}")
                current_sentence = ""
        
        # Add any remaining text
        if current_sentence.strip():
            bullet_lines.append(f"- {current_sentence.strip()}")
    
    # If we didn't create any bullets, create one from the whole text
    if not bullet_lines:
        # Split by sentences
        sentences = re.split(r'([.!?]\s+)', text)
        current = ""
        for part in sentences:
            current += part
            if re.search(r'[.!?]\s*$', current.strip()):
                sentence = current.strip()
                if sentence and len(sentence) > 10:  # Only add substantial sentences
                    bullet_lines.append(f"- {sentence}")
                current = ""
        if current.strip() and len(current.strip()) > 10:
            bullet_lines.append(f"- {current.strip()}")
    
    return "\n".join(bullet_lines) if bullet_lines else f"- {text}"


def _format_as_paragraph(text: str) -> str:
    """
    Format text as a well-structured paragraph.
    
    Cleans up extra whitespace and ensures proper paragraph structure.
    """
    # Remove excessive whitespace
    formatted = re.sub(r'\s+', ' ', text)
    
    # Remove excessive newlines (more than 2 consecutive)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    # Ensure proper spacing around punctuation
    formatted = re.sub(r'\s+([.!?])', r'\1', formatted)
    formatted = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', formatted)
    
    # Clean up any remaining issues
    formatted = formatted.strip()
    
    return formatted


def _format_confidence_indicator(
    confidence_score: Optional[float] = None,
    confidence_level: Optional[str] = None,
) -> str:
    """
    Format a confidence indicator based on score or level.
    
    Args:
        confidence_score: Confidence score (0.0-1.0)
        confidence_level: Confidence level ("High", "Medium", "Low")
        
    Returns:
        Formatted confidence indicator string
    """
    if confidence_level:
        # Use provided level
        level = confidence_level
    elif confidence_score is not None:
        # Derive level from score
        if confidence_score >= 0.8:
            level = "High"
        elif confidence_score >= 0.6:
            level = "Medium"
        else:
            level = "Low"
    else:
        return ""
    
    # Format the indicator
    if confidence_score is not None:
        # Show both level and score
        score_out_of_10 = int(confidence_score * 10)
        return f"**Confidence: {level}** ({score_out_of_10}/10)"
    else:
        # Show only level
        return f"**Confidence: {level}**"


def compute_confidence_level(
    fact_check_result: Optional[object] = None,
    quality_assessments: Optional[dict] = None,
    consensus_score: Optional[float] = None,
    loopback_occurred: bool = False,
    verification_passed: bool = False,
) -> tuple[Optional[float], Optional[str]]:
    """
    Compute confidence score and level based on various metrics.
    
    Args:
        fact_check_result: Fact check result object (should have is_valid, verification_score)
        quality_assessments: Dictionary of quality assessments per model
        consensus_score: Consensus score from DeepConf (0.0-1.0)
        loopback_occurred: Whether loop-back refinement was needed
        verification_passed: Whether verification passed
        
    Returns:
        Tuple of (confidence_score, confidence_level)
        confidence_score: 0.0-1.0 or None
        confidence_level: "High", "Medium", "Low" or None
    """
    scores = []
    
    # Factor 1: Fact check verification
    if fact_check_result:
        if hasattr(fact_check_result, 'verification_score'):
            scores.append(fact_check_result.verification_score)
        elif hasattr(fact_check_result, 'is_valid'):
            scores.append(1.0 if fact_check_result.is_valid else 0.5)
    
    # Factor 2: Quality assessments
    if quality_assessments:
        quality_scores = [a.score for a in quality_assessments.values() if hasattr(a, 'score')]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            scores.append(avg_quality)
    
    # Factor 3: Consensus score
    if consensus_score is not None:
        scores.append(consensus_score)
    
    # Factor 4: Loop-back penalty (reduces confidence)
    if loopback_occurred:
        # Reduce confidence by 0.2 if loop-back was needed
        if scores:
            scores = [max(0.0, s - 0.2) for s in scores]
    
    # Factor 5: Verification passed bonus
    if verification_passed:
        scores.append(0.9)  # High confidence if verification passed
    
    # Compute final confidence
    if not scores:
        return None, None
    
    confidence_score = sum(scores) / len(scores)
    
    # Determine level
    if confidence_score >= 0.8:
        level = "High"
    elif confidence_score >= 0.6:
        level = "Medium"
    else:
        level = "Low"
    
    return confidence_score, level


# ==============================================================================
# AnswerRefiner Class - Preference-Aware Answer Formatting
# ==============================================================================

class AnswerRefiner:
    """Refines and formats answers based on user preferences.
    
    This class integrates with the ClarificationManager to apply
    user-specified preferences to the final answer, including:
    - Detail level adjustments
    - Format conversion (bullets, numbered, etc.)
    - Tone adjustments
    - Length constraints
    """
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        enable_llm_refinement: bool = True,
    ) -> None:
        """
        Initialize the AnswerRefiner.
        
        Args:
            providers: LLM providers for advanced refinement
            enable_llm_refinement: Use LLM for refinement (vs rule-based)
        """
        self.providers = providers or {}
        self.enable_llm_refinement = enable_llm_refinement
    
    async def refine_with_preferences(
        self,
        answer: str,
        preferences: Optional["AnswerPreferences"] = None,
        *,
        confidence_score: Optional[float] = None,
        confidence_level: Optional[str] = None,
        clarification_context: Optional[str] = None,
    ) -> str:
        """
        Refine an answer based on user preferences.
        
        Args:
            answer: The raw answer to refine
            preferences: User's answer preferences
            confidence_score: Optional confidence score
            confidence_level: Optional confidence level
            clarification_context: Context from clarification Q&A
            
        Returns:
            Refined and formatted answer
        """
        if not answer or not answer.strip():
            return answer
        
        # If no preferences, use defaults
        if preferences is None:
            # Import here to avoid circular import
            try:
                from .orchestration.clarification_manager import AnswerPreferences as AP
                preferences = AP()
            except ImportError:
                # Fallback to simple formatting
                return format_answer(
                    answer,
                    format_style="paragraph",
                    confidence_score=confidence_score,
                    confidence_level=confidence_level,
                )
        
        refined = answer.strip()
        
        # Step 1: Apply format transformation
        refined = self._apply_format(refined, preferences)
        
        # Step 2: Apply detail level adjustments
        refined = await self._apply_detail_level(refined, preferences)
        
        # Step 3: Apply tone adjustments (if LLM available)
        if self.enable_llm_refinement and self.providers:
            refined = await self._apply_tone(refined, preferences)
        
        # Step 4: Apply length constraints
        if preferences.max_length:
            refined = self._apply_length_limit(refined, preferences.max_length)
        
        # Step 5: Add examples if requested and not present
        if preferences.include_examples and "example" not in refined.lower():
            # This would need LLM to add examples, skip for now
            pass
        
        # Step 6: Add confidence indicator
        if confidence_score is not None or confidence_level is not None:
            confidence_indicator = _format_confidence_indicator(
                confidence_score, confidence_level
            )
            if confidence_indicator:
                refined = f"{refined}\n\n---\n{confidence_indicator}"
        
        return refined
    
    def _apply_format(self, text: str, preferences: "AnswerPreferences") -> str:
        """Apply format transformation based on preferences."""
        # Import format enum
        try:
            from .orchestration.clarification_manager import AnswerFormat
        except ImportError:
            return text
        
        format_pref = preferences.format
        
        if format_pref == AnswerFormat.BULLET_POINTS:
            return _format_as_bullets(text)
        elif format_pref == AnswerFormat.NUMBERED_LIST:
            return self._format_as_numbered(text)
        elif format_pref == AnswerFormat.STRUCTURED:
            return self._format_as_structured(text)
        elif format_pref == AnswerFormat.CONVERSATIONAL:
            # Add conversational elements
            return self._format_as_conversational(text)
        else:
            return _format_as_paragraph(text)
    
    def _format_as_numbered(self, text: str) -> str:
        """Format text as a numbered list."""
        # First convert to bullets
        bulleted = _format_as_bullets(text)
        
        # Then convert bullets to numbers
        lines = bulleted.split("\n")
        numbered_lines = []
        counter = 1
        
        for line in lines:
            if line.strip().startswith("- "):
                numbered_lines.append(f"{counter}. {line.strip()[2:]}")
                counter += 1
            elif line.strip().startswith("• "):
                numbered_lines.append(f"{counter}. {line.strip()[2:]}")
                counter += 1
            elif line.strip().startswith("* "):
                numbered_lines.append(f"{counter}. {line.strip()[2:]}")
                counter += 1
            else:
                numbered_lines.append(line)
        
        return "\n".join(numbered_lines)
    
    def _format_as_structured(self, text: str) -> str:
        """Format text with headers and sections."""
        # Split into paragraphs
        paragraphs = re.split(r'\n\n+', text)
        
        if len(paragraphs) <= 1:
            return text
        
        # Add headers to major sections
        structured = []
        section_count = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if it already has a header
            if para.startswith("#") or para.startswith("**"):
                structured.append(para)
            elif len(para) > 100:
                # Long paragraphs get headers
                section_count += 1
                # Try to extract a topic from first sentence
                first_sentence = para.split(".")[0]
                if len(first_sentence) < 50:
                    header = first_sentence
                else:
                    header = f"Section {section_count}"
                structured.append(f"### {header}\n\n{para}")
            else:
                structured.append(para)
        
        return "\n\n".join(structured)
    
    def _format_as_conversational(self, text: str) -> str:
        """Add conversational tone elements."""
        # Add casual opener if not present
        openers = ["Great question!", "Interesting topic!", "Let me explain.", "Here's what I know:"]
        
        text = text.strip()
        has_opener = any(text.lower().startswith(o.lower()[:5]) for o in openers)
        
        if not has_opener and not text[0].isupper():
            text = text[0].upper() + text[1:]
        
        # Make paragraph format friendlier
        text = _format_as_paragraph(text)
        
        return text
    
    async def _apply_detail_level(
        self,
        text: str,
        preferences: "AnswerPreferences",
    ) -> str:
        """Apply detail level adjustments."""
        try:
            from .orchestration.clarification_manager import DetailLevel
        except ImportError:
            return text
        
        detail = preferences.detail_level
        
        if detail == DetailLevel.BRIEF:
            # Shorten the response
            return self._shorten_text(text, target_ratio=0.5)
        elif detail == DetailLevel.EXHAUSTIVE:
            # Note: Adding detail would require LLM
            # For now, just ensure it's comprehensive
            pass
        
        return text
    
    def _shorten_text(self, text: str, target_ratio: float = 0.5) -> str:
        """Shorten text to target ratio of original length."""
        words = text.split()
        target_length = int(len(words) * target_ratio)
        
        if target_length >= len(words):
            return text
        
        # Try to keep complete sentences
        sentences = re.split(r'([.!?]\s+)', text)
        shortened = []
        word_count = 0
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= target_length:
                shortened.append(sentence)
                word_count += sentence_words
            else:
                break
        
        if shortened:
            return "".join(shortened).strip()
        else:
            # Fallback: just truncate
            return " ".join(words[:target_length]) + "..."
    
    async def _apply_tone(
        self,
        text: str,
        preferences: "AnswerPreferences",
    ) -> str:
        """Apply tone adjustments using LLM."""
        try:
            from .orchestration.clarification_manager import AnswerTone
        except ImportError:
            return text
        
        if preferences.tone == AnswerTone.FORMAL:
            return text  # Default is usually formal
        
        # For non-formal tones, we'd use LLM to rephrase
        # For now, make simple adjustments
        if preferences.tone == AnswerTone.CASUAL:
            # Add casual connectors
            text = text.replace(". Additionally,", ". Also,")
            text = text.replace(". Furthermore,", ". Plus,")
            text = text.replace(". However,", ". But,")
        elif preferences.tone == AnswerTone.SIMPLIFIED:
            # This would need LLM to simplify properly
            pass
        
        return text
    
    def _apply_length_limit(self, text: str, max_words: int) -> str:
        """Apply word length limit."""
        words = text.split()
        if len(words) <= max_words:
            return text
        
        # Truncate at sentence boundary
        return self._shorten_text(text, target_ratio=max_words / len(words))
    
    def get_style_instructions(
        self,
        preferences: Optional["AnswerPreferences"],
    ) -> str:
        """Get style instructions for LLM prompts based on preferences."""
        if preferences is None:
            return ""
        
        return preferences.to_style_guidelines()


# ==============================================================================
# Convenience function for preference-aware formatting
# ==============================================================================

async def refine_answer_with_preferences(
    answer: str,
    preferences: Optional[Any] = None,
    *,
    providers: Optional[Dict[str, Any]] = None,
    confidence_score: Optional[float] = None,
) -> str:
    """
    Convenience function to refine an answer with preferences.
    
    Args:
        answer: Raw answer text
        preferences: AnswerPreferences object
        providers: LLM providers
        confidence_score: Optional confidence score
        
    Returns:
        Refined answer
    """
    refiner = AnswerRefiner(providers=providers)
    
    confidence_level = None
    if confidence_score is not None:
        _, confidence_level = compute_confidence_level(
            consensus_score=confidence_score
        )
    
    return await refiner.refine_with_preferences(
        answer,
        preferences,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
    )

