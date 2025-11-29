"""Answer formatting and refinement utilities."""
from __future__ import annotations

import logging
import re
from typing import Optional

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

