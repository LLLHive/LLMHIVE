"""Enhanced Answer Refiner Module for LLMHive Orchestrator.

This module implements the final polishing step that transforms verified
solutions into polished, user-ready deliverables.

Features:
- Coherence and clarity improvement
- Format enforcement (JSON, markdown, code, etc.)
- Verified content integration
- Citation formatting
- Confidence indication
- Style adaptation
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class OutputFormat(str, Enum):
    """Supported output formats."""
    PARAGRAPH = "paragraph"
    BULLET = "bullet"
    NUMBERED = "numbered"
    JSON = "json"
    MARKDOWN = "markdown"
    CODE = "code"
    TABLE = "table"
    ESSAY = "essay"


class ToneStyle(str, Enum):
    """Response tone styles."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    FORMAL = "formal"


class AudienceLevel(str, Enum):
    """Target audience expertise level."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"
    GENERAL = "general"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class RefinementConfig:
    """Configuration for answer refinement."""
    output_format: OutputFormat = OutputFormat.PARAGRAPH
    tone: ToneStyle = ToneStyle.PROFESSIONAL
    audience: AudienceLevel = AudienceLevel.GENERAL
    max_length: Optional[int] = None
    include_confidence: bool = True
    include_citations: bool = True
    preserve_structure: bool = True


@dataclass(slots=True)
class Citation:
    """A citation to include in the answer."""
    source: str
    content: str
    url: Optional[str] = None
    relevance_score: float = 1.0


@dataclass(slots=True)
class RefinedAnswer:
    """Result of the refinement process."""
    original_content: str
    refined_content: str
    format_applied: OutputFormat
    confidence_score: Optional[float]
    confidence_level: Optional[str]
    citations_included: List[Citation]
    improvements_made: List[str]
    final_length: int
    refinement_notes: List[str]


# ==============================================================================
# Answer Refiner Implementation
# ==============================================================================

class AnswerRefiner:
    """Enhanced answer refiner for final output polishing.
    
    This module takes verified responses and transforms them into
    polished, user-ready deliverables with appropriate formatting,
    tone, and supplementary information.
    """
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        default_config: Optional[RefinementConfig] = None,
    ) -> None:
        """
        Initialize the answer refiner.
        
        Args:
            providers: LLM providers for advanced refinement
            default_config: Default refinement configuration
        """
        self.providers = providers or {}
        self.default_config = default_config or RefinementConfig()
    
    async def refine(
        self,
        content: str,
        *,
        query: str,
        config: Optional[RefinementConfig] = None,
        verification_report: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Citation]] = None,
        model: str = "gpt-4o",
    ) -> RefinedAnswer:
        """
        Refine an answer into its final polished form.
        
        Args:
            content: The verified response content
            query: Original user query
            config: Refinement configuration
            verification_report: Results from verification
            citations: Citations to include
            model: Model to use for LLM refinement
            
        Returns:
            RefinedAnswer with polished content
        """
        config = config or self.default_config
        improvements_made: List[str] = []
        refinement_notes: List[str] = []
        
        # Step 1: Clean and normalize
        cleaned = self._clean_content(content)
        if cleaned != content:
            improvements_made.append("Cleaned whitespace and formatting")
        
        # Step 2: Apply format transformation
        formatted = self._apply_format(cleaned, config.output_format)
        if formatted != cleaned:
            improvements_made.append(f"Applied {config.output_format.value} format")
        
        # Step 3: Apply tone and style
        styled = self._apply_style(formatted, config.tone, config.audience)
        if styled != formatted:
            improvements_made.append(f"Adjusted tone to {config.tone.value}")
        
        # Step 4: Enforce length constraints
        if config.max_length and len(styled) > config.max_length:
            styled = self._enforce_length(styled, config.max_length)
            improvements_made.append(f"Trimmed to max length {config.max_length}")
        
        # Step 5: Integrate verified corrections
        if verification_report:
            corrected = self._integrate_corrections(styled, verification_report)
            if corrected != styled:
                improvements_made.append("Integrated verification corrections")
            styled = corrected
        
        # Step 6: Add citations
        citations_used: List[Citation] = []
        if config.include_citations and citations:
            styled, citations_used = self._add_citations(styled, citations)
            if citations_used:
                improvements_made.append(f"Added {len(citations_used)} citations")
        
        # Step 7: Calculate confidence
        confidence_score = None
        confidence_level = None
        if config.include_confidence and verification_report:
            confidence_score, confidence_level = self._compute_confidence(
                verification_report
            )
        
        # Step 8: Add confidence indicator
        if confidence_level and config.include_confidence:
            styled = self._add_confidence_indicator(styled, confidence_score, confidence_level)
            improvements_made.append("Added confidence indicator")
        
        # Step 9: Final polish with LLM (if available)
        if self.providers and len(styled) > 100:
            polished = await self._llm_polish(
                styled, query, config, model
            )
            if polished and polished != styled:
                styled = polished
                improvements_made.append("Applied LLM-based polish")
        
        refinement_notes.append(f"Final format: {config.output_format.value}")
        refinement_notes.append(f"Tone: {config.tone.value}")
        refinement_notes.append(f"Improvements: {len(improvements_made)}")
        
        return RefinedAnswer(
            original_content=content,
            refined_content=styled,
            format_applied=config.output_format,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            citations_included=citations_used,
            improvements_made=improvements_made,
            final_length=len(styled),
            refinement_notes=refinement_notes,
        )
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', content)
        
        # Fix spacing around punctuation
        cleaned = re.sub(r'\s+([.!?,;:])', r'\1', cleaned)
        cleaned = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', cleaned)
        
        # Remove excessive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def _apply_format(
        self,
        content: str,
        output_format: OutputFormat,
    ) -> str:
        """Apply the requested output format."""
        if output_format == OutputFormat.BULLET:
            return self._format_as_bullets(content)
        elif output_format == OutputFormat.NUMBERED:
            return self._format_as_numbered(content)
        elif output_format == OutputFormat.JSON:
            return self._format_as_json(content)
        elif output_format == OutputFormat.MARKDOWN:
            return self._format_as_markdown(content)
        elif output_format == OutputFormat.CODE:
            return self._format_as_code(content)
        elif output_format == OutputFormat.TABLE:
            return self._format_as_table(content)
        elif output_format == OutputFormat.ESSAY:
            return self._format_as_essay(content)
        else:
            return self._format_as_paragraph(content)
    
    def _format_as_bullets(self, content: str) -> str:
        """Format content as bullet points."""
        lines = content.split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # If already a bullet, keep it
            if re.match(r'^[-*•]\s+', line):
                bullets.append(line)
            # If numbered, convert to bullet
            elif re.match(r'^\d+[.)]\s+', line):
                bullets.append(re.sub(r'^\d+[.)]\s+', '• ', line))
            else:
                # Split sentences into bullets
                sentences = re.split(r'(?<=[.!?])\s+', line)
                for s in sentences:
                    s = s.strip()
                    if s and len(s) > 10:
                        bullets.append(f"• {s}")
        
        return '\n'.join(bullets) if bullets else f"• {content}"
    
    def _format_as_numbered(self, content: str) -> str:
        """Format content as numbered list."""
        lines = content.split('\n')
        numbered = []
        num = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove existing bullets/numbers
            line = re.sub(r'^[-*•]\s+', '', line)
            line = re.sub(r'^\d+[.)]\s+', '', line)
            
            if len(line) > 10:
                numbered.append(f"{num}. {line}")
                num += 1
        
        return '\n'.join(numbered) if numbered else f"1. {content}"
    
    def _format_as_json(self, content: str) -> str:
        """Attempt to format content as JSON."""
        # Try to parse existing JSON
        try:
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from content
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass
        
        # Create structured JSON from content
        return json.dumps({
            "response": content,
            "format": "structured",
        }, indent=2)
    
    def _format_as_markdown(self, content: str) -> str:
        """Format content as markdown."""
        # Add headers if not present
        if not content.startswith('#'):
            lines = content.split('\n\n')
            if len(lines) > 1:
                # First paragraph as header
                formatted = f"## Overview\n\n{lines[0]}"
                if len(lines) > 2:
                    formatted += "\n\n## Details\n\n" + "\n\n".join(lines[1:])
                else:
                    formatted += "\n\n" + "\n\n".join(lines[1:])
                return formatted
        
        return content
    
    def _format_as_code(self, content: str) -> str:
        """Format content as code block."""
        # If already in code block, return as is
        if content.strip().startswith('```'):
            return content
        
        # Detect language
        language = self._detect_code_language(content)
        
        return f"```{language}\n{content}\n```"
    
    def _format_as_table(self, content: str) -> str:
        """Attempt to format content as markdown table."""
        lines = content.split('\n')
        if len(lines) < 2:
            return content
        
        # Try to detect tabular data
        rows = []
        for line in lines:
            cells = re.split(r'\s{2,}|\t', line.strip())
            if len(cells) > 1:
                rows.append(cells)
        
        if len(rows) < 2:
            return content
        
        # Build markdown table
        max_cols = max(len(row) for row in rows)
        
        # Pad rows
        for row in rows:
            while len(row) < max_cols:
                row.append('')
        
        # Create table
        header = '| ' + ' | '.join(rows[0]) + ' |'
        separator = '| ' + ' | '.join(['---'] * max_cols) + ' |'
        body = '\n'.join('| ' + ' | '.join(row) + ' |' for row in rows[1:])
        
        return f"{header}\n{separator}\n{body}"
    
    def _format_as_essay(self, content: str) -> str:
        """Format content as essay with proper paragraphs."""
        # Split into paragraphs
        paragraphs = re.split(r'\n{2,}', content)
        
        # Ensure proper paragraph structure
        formatted_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para:
                # Ensure first letter is capitalized
                if para[0].islower():
                    para = para[0].upper() + para[1:]
                # Ensure ends with punctuation
                if not para.endswith(('.', '!', '?')):
                    para += '.'
                formatted_paragraphs.append(para)
        
        return '\n\n'.join(formatted_paragraphs)
    
    def _format_as_paragraph(self, content: str) -> str:
        """Format content as clean paragraphs."""
        # Remove excessive whitespace
        formatted = re.sub(r'\s+', ' ', content)
        
        # Restore paragraph breaks (after period + double newline)
        formatted = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', formatted)
        
        return formatted.strip()
    
    def _detect_code_language(self, content: str) -> str:
        """Detect programming language from code content."""
        indicators = {
            'python': ['def ', 'import ', 'class ', 'print(', 'async ', '    '],
            'javascript': ['function ', 'const ', 'let ', '=>', 'console.log'],
            'typescript': ['interface ', ': string', ': number', 'type '],
            'rust': ['fn ', 'let mut ', '&str', 'impl ', '::'],
            'go': ['func ', 'package ', 'import (', 'fmt.'],
            'java': ['public class', 'private ', 'void ', 'System.out'],
            'sql': ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'CREATE TABLE'],
        }
        
        for lang, keywords in indicators.items():
            if any(kw in content for kw in keywords):
                return lang
        
        return ''
    
    def _apply_style(
        self,
        content: str,
        tone: ToneStyle,
        audience: AudienceLevel,
    ) -> str:
        """Apply tone and style adjustments."""
        # For now, return content as-is
        # In production, this would use LLM for style transfer
        return content
    
    def _enforce_length(self, content: str, max_length: int) -> str:
        """Enforce maximum length constraint."""
        if len(content) <= max_length:
            return content
        
        # Try to cut at sentence boundary
        truncated = content[:max_length]
        
        # Find last sentence end
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclaim = truncated.rfind('!')
        
        best_cut = max(last_period, last_question, last_exclaim)
        
        if best_cut > max_length * 0.7:
            return truncated[:best_cut + 1] + "\n\n[Response truncated for length]"
        
        return truncated + "..."
    
    def _integrate_corrections(
        self,
        content: str,
        verification_report: Dict[str, Any],
    ) -> str:
        """Integrate corrections from verification."""
        corrected = content
        
        # Get corrections from report
        corrections = verification_report.get("corrections", {})
        issues = verification_report.get("issues_to_fix", [])
        
        for wrong, right in corrections.items():
            if wrong in corrected and right:
                corrected = corrected.replace(wrong, right)
        
        return corrected
    
    def _add_citations(
        self,
        content: str,
        citations: List[Citation],
    ) -> Tuple[str, List[Citation]]:
        """Add citations to the content."""
        if not citations:
            return content, []
        
        used_citations: List[Citation] = []
        cited_content = content
        
        # Add reference section
        references = []
        for i, cite in enumerate(citations, 1):
            if cite.relevance_score >= 0.5:
                used_citations.append(cite)
                if cite.url:
                    references.append(f"[{i}] {cite.source}: {cite.url}")
                else:
                    references.append(f"[{i}] {cite.source}")
        
        if references:
            cited_content += "\n\n---\n**References:**\n"
            cited_content += "\n".join(references)
        
        return cited_content, used_citations
    
    def _compute_confidence(
        self,
        verification_report: Dict[str, Any],
    ) -> Tuple[Optional[float], Optional[str]]:
        """Compute confidence from verification report."""
        # Extract verification score
        score = verification_report.get("verification_score")
        if score is None:
            result = verification_report.get("verification_result", {})
            score = result.get("confidence_score")
        
        if score is None:
            return None, None
        
        # Determine level
        if score >= 0.85:
            level = "High"
        elif score >= 0.65:
            level = "Medium"
        else:
            level = "Low"
        
        return score, level
    
    def _add_confidence_indicator(
        self,
        content: str,
        score: Optional[float],
        level: str,
    ) -> str:
        """Add confidence indicator to content."""
        if score is not None:
            indicator = f"\n\n---\n**Confidence: {level}** ({int(score * 100)}%)"
        else:
            indicator = f"\n\n---\n**Confidence: {level}**"
        
        return content + indicator
    
    async def _llm_polish(
        self,
        content: str,
        query: str,
        config: RefinementConfig,
        model: str,
    ) -> Optional[str]:
        """Use LLM for final polish."""
        if not self.providers:
            return None
        
        provider = self._select_provider(model)
        if not provider:
            return None
        
        polish_prompt = f"""Polish this response for clarity and coherence.

Original Query: {query}

Response to Polish:
{content}

Requirements:
- Maintain all factual content
- Improve flow and readability
- Use {config.tone.value} tone
- Target {config.audience.value} audience

Output ONLY the polished response, no commentary."""
        
        try:
            result = await provider.complete(polish_prompt, model=model)
            polished = result.content.strip()
            
            # Sanity check - should be similar length
            if 0.5 < len(polished) / len(content) < 2.0:
                return polished
        except Exception as e:
            logger.warning("LLM polish failed: %s", e)
        
        return None
    
    def _select_provider(self, model: str) -> Optional[Any]:
        """Select provider for a model."""
        model_lower = model.lower()
        
        provider_map = {
            "gpt": "openai",
            "claude": "anthropic",
            "grok": "grok",
            "gemini": "gemini",
            "deepseek": "deepseek",
        }
        
        for prefix, provider_name in provider_map.items():
            if model_lower.startswith(prefix) and provider_name in self.providers:
                return self.providers[provider_name]
        
        if self.providers:
            return next(iter(self.providers.values()))
        
        return None


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def refine_answer(
    content: str,
    query: str,
    *,
    format_style: str = "paragraph",
    providers: Optional[Dict[str, Any]] = None,
    verification_report: Optional[Dict[str, Any]] = None,
) -> RefinedAnswer:
    """Convenience function to refine an answer."""
    config = RefinementConfig(
        output_format=OutputFormat(format_style) if format_style else OutputFormat.PARAGRAPH,
    )
    
    refiner = AnswerRefiner(providers=providers)
    return await refiner.refine(
        content,
        query=query,
        config=config,
        verification_report=verification_report,
    )


def quick_format(
    content: str,
    format_style: str = "paragraph",
) -> str:
    """Quick formatting without LLM."""
    refiner = AnswerRefiner()
    output_format = OutputFormat(format_style) if format_style else OutputFormat.PARAGRAPH
    return refiner._apply_format(content, output_format)

