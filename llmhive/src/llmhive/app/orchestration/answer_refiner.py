"""Enhanced Answer Refiner Module for LLMHive Orchestrator.

This module implements the final polishing step that transforms verified
solutions into polished, user-ready deliverables.

Enhanced Features:
- Dynamic tone/style based on user preferences and domain
- Verification result integration with "(verified)" annotations
- Multi-turn context awareness (avoids restating recent info)
- Edge case handling for formatting issues
- Citation/sources section with proper attribution
- Confidence indication based on verification
- Format completion for truncated/malformed content
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
    EXEC_SUMMARY = "executive_summary"
    QA = "qa"


class ToneStyle(str, Enum):
    """Response tone styles."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"


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
    max_length: Optional[int] = None  # Maximum characters
    max_words: Optional[int] = None   # Maximum words
    include_confidence: bool = True
    include_citations: bool = True
    preserve_structure: bool = True
    # New: domain-based style overrides
    domain: str = "general"
    # New: verification integration
    show_verified_annotations: bool = True
    tone_down_unverified: bool = True
    # New: multi-turn context
    avoid_repetition: bool = True
    recent_context: Optional[List[str]] = None
    # New: source attribution
    include_sources: bool = True


@dataclass(slots=True)
class Citation:
    """A citation to include in the answer."""
    source: str
    content: str
    url: Optional[str] = None
    relevance_score: float = 1.0
    tool_source: Optional[str] = None  # Which tool provided this


@dataclass(slots=True)
class VerificationInfo:
    """Information from verification to incorporate."""
    verified_claims: List[str] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)
    corrected_claims: Dict[str, str] = field(default_factory=dict)  # old -> new
    issues_found: List[str] = field(default_factory=list)
    confidence_score: float = 0.9
    verification_notes: List[str] = field(default_factory=list)


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
    # New: verification integration info
    verification_integrated: bool = False
    verified_claim_count: int = 0


# Domain to tone mappings
DOMAIN_TONE_MAP: Dict[str, ToneStyle] = {
    "coding": ToneStyle.TECHNICAL,
    "medical": ToneStyle.FORMAL,
    "legal": ToneStyle.FORMAL,
    "finance": ToneStyle.PROFESSIONAL,
    "marketing": ToneStyle.FRIENDLY,
    "research": ToneStyle.ACADEMIC,
    "education": ToneStyle.CONVERSATIONAL,
    "general": ToneStyle.PROFESSIONAL,
}


# ==============================================================================
# Answer Refiner Implementation
# ==============================================================================

class AnswerRefiner:
    """Enhanced answer refiner for final output polishing.
    
    This module takes verified responses and transforms them into
    polished, user-ready deliverables with appropriate formatting,
    tone, and supplementary information.
    
    Enhanced capabilities:
    - Dynamic tone based on domain and user preferences
    - Verification result integration
    - Multi-turn context awareness
    - Edge case handling for formatting
    - Citation and sources formatting
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
    
    def _strip_meta_commentary(self, content: str) -> str:
        """Strip meta-commentary and reasoning scaffold that may have leaked from orchestration.
        
        This removes patterns like:
        - "Here is the improved answer..."
        - "I have addressed the feedback..."
        - Self-critique sections
        - "Confidence Level: X/10" internal notes
        - Reasoning scaffold sections (=== PROBLEM ===, === UNDERSTANDING ===, etc.)
        """
        # FIRST: If content has "=== FINAL ANSWER ===" section, extract ONLY that
        if "=== FINAL ANSWER ===" in content:
            final_part = content.split("=== FINAL ANSWER ===")[-1].strip()
            # Remove any trailing scaffold if present
            for scaffold in ["=== ", "---", "***"]:
                if scaffold in final_part:
                    final_part = final_part.split(scaffold)[0].strip()
            if final_part and len(final_part) > 20:
                logger.info("Extracted final answer from reasoning scaffold")
                return final_part
        
        # Reasoning scaffold sections to remove entirely (with content up to next section)
        scaffold_sections = [
            r"===\s*PROBLEM\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*UNDERSTANDING\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*APPROACH\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*STEP-BY-STEP\s+SOLUTION\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*VERIFICATION\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*CONFIDENCE\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*SYNTHESIS\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*PERSPECTIVE\s+\d+.*?===.*?(?====\s*\w+\s*===|$)",
            r"===\s*PROPOSER\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*CRITIC\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*DEFENDER\s*===.*?(?====\s*\w+\s*===|$)",
            r"===\s*ATTEMPT\s+\d+\s*===.*?(?====\s*\w+\s*===|$)",
        ]
        
        cleaned = content
        for pattern in scaffold_sections:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Also strip any remaining "=== SOMETHING ===" headers
        cleaned = re.sub(r"===\s*[A-Z][A-Z\s]+===\s*\n?", "", cleaned, flags=re.IGNORECASE)
        
        # Patterns that indicate meta-commentary (case-insensitive)
        meta_patterns = [
            r"^```\w*\s*\n",  # Code fence at start with language tag
            r"The response is comprehensive.*?However,.*?refinement.*?:",
            r"Here is the improved answer[:\s]*",
            r"I have addressed the feedback.*?",
            r"Based on the feedback.*?here is.*?:",
            r"\*\*Improved Response\*\*[:\s]*",
            r"---\s*\n\s*\*\*Errors or Inaccuracies\*\*.*?---",
            r"\d+\.\s*\*\*(Completeness|Errors|Clarity|Missing Information)\*\*:.*?(?=\d+\.\s*\*\*|\Z)",
            r"\*\*Confidence Level\*\*:\s*\d+/\d+.*?$",
            r"Ultimately,\s*this response strives to.*?$",
            r"What is being asked:.*?$",
            r"Key constraints:.*?$",
            r"Type of problem:.*?$",
            r"Strategy:.*?(?=\n|$)",
            r"Why this approach:.*?(?=\n|$)",
            r"Step \d+:.*?(?=Step \d+:|===|$)",
            r"Check \d+:.*?(?=Check \d+:|===|$)",
            r"Confidence level:\s*\d+%.*?$",
            r"Most uncertain about:.*?$",
        ]
        
        for pattern in meta_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        # Remove orphaned closing code fences if we removed opening ones
        if not re.search(r"```\w*\s*\n", cleaned) and cleaned.strip().endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        
        # Clean up excessive whitespace/newlines left by removals
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"^\s*•\s*$", "", cleaned, flags=re.MULTILINE)  # Remove empty bullet points
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # If we stripped too much, return original
        if len(cleaned) < len(content) * 0.3:
            logger.warning("Meta-commentary stripping removed too much content, keeping original")
            return content
        
        return cleaned
    
    async def refine(
        self,
        content: str,
        *,
        query: str,
        config: Optional[RefinementConfig] = None,
        verification_report: Optional[Dict[str, Any]] = None,
        verification_info: Optional[VerificationInfo] = None,
        citations: Optional[List[Citation]] = None,
        model: str = "gpt-4o",
        recent_history: Optional[List[Dict[str, str]]] = None,
        tool_results: Optional[Dict[str, Any]] = None,
    ) -> RefinedAnswer:
        """
        Refine an answer into its final polished form.
        
        Args:
            content: The verified response content
            query: Original user query
            config: Refinement configuration
            verification_report: Results from verification (legacy format)
            verification_info: Structured verification results
            citations: Citations to include
            model: Model to use for LLM refinement
            recent_history: Recent conversation for context
            tool_results: Results from tool broker
            
        Returns:
            RefinedAnswer with polished content
        """
        config = config or self.default_config
        improvements_made: List[str] = []
        refinement_notes: List[str] = []
        
        # Strip meta-commentary and reasoning scaffold that may have leaked from orchestration
        original_content = content
        content = self._strip_meta_commentary(content)
        if content != original_content:
            improvements_made.append("Removed meta-commentary and reasoning scaffold from response")
        
        # Apply domain-based tone if not explicitly set
        if config.domain != "general" and config.tone == ToneStyle.PROFESSIONAL:
            suggested_tone = DOMAIN_TONE_MAP.get(config.domain, ToneStyle.PROFESSIONAL)
            config = RefinementConfig(
                output_format=config.output_format,
                tone=suggested_tone,
                audience=config.audience,
                max_length=config.max_length,
                include_confidence=config.include_confidence,
                include_citations=config.include_citations,
                preserve_structure=config.preserve_structure,
                domain=config.domain,
                show_verified_annotations=config.show_verified_annotations,
                tone_down_unverified=config.tone_down_unverified,
                avoid_repetition=config.avoid_repetition,
                recent_context=config.recent_context,
                include_sources=config.include_sources,
            )
            improvements_made.append(f"Applied {suggested_tone.value} tone for {config.domain} domain")
        
        # Convert legacy verification_report to VerificationInfo
        if verification_report and not verification_info:
            verification_info = self._extract_verification_info(verification_report)
        
        # Step 1: Clean and normalize
        cleaned = self._clean_content(content)
        if cleaned != content:
            improvements_made.append("Cleaned whitespace and formatting")
        
        # Step 2: Fix formatting edge cases
        cleaned = self._fix_format_edge_cases(cleaned)
        
        # Step 3: Apply format transformation
        formatted = self._apply_format(cleaned, config.output_format)
        if formatted != cleaned:
            improvements_made.append(f"Applied {config.output_format.value} format")
        
        # Step 4: Remove repetition from recent context
        if config.avoid_repetition and recent_history:
            formatted, removed = self._remove_repetition(formatted, recent_history)
            if removed:
                improvements_made.append(f"Removed {removed} redundant references")
        
        # Step 5: Apply tone and style with LLM
        styled = await self._apply_style_llm(formatted, config.tone, config.audience, query)
        if styled != formatted:
            improvements_made.append(f"Adjusted tone to {config.tone.value}")
        else:
            styled = formatted
        
        # Step 6: Integrate verification results
        verified_count = 0
        if verification_info:
            styled, verified_count = self._integrate_verification(
                styled, verification_info, config
            )
            if verified_count > 0:
                improvements_made.append(f"Integrated {verified_count} verification annotations")
        
        # Step 7: Enforce length constraints (characters)
        if config.max_length and len(styled) > config.max_length:
            styled = self._enforce_length(styled, config.max_length)
            improvements_made.append(f"Trimmed to max length {config.max_length}")
        
        # Step 7b: Enforce word limit constraints
        if config.max_words:
            word_count = len(styled.split())
            if word_count > config.max_words:
                styled = self._enforce_word_limit(styled, config.max_words)
                improvements_made.append(f"Trimmed to max {config.max_words} words")
        
        # Step 8: Add tool sources if available
        if tool_results and config.include_sources:
            styled = self._add_tool_sources(styled, tool_results)
            improvements_made.append("Added tool source attributions")
        
        # Step 9: Add citations
        citations_used: List[Citation] = []
        if config.include_citations and citations:
            styled, citations_used = self._add_citations(styled, citations)
            if citations_used:
                improvements_made.append(f"Added {len(citations_used)} citations")
        
        # Step 10: Calculate confidence
        confidence_score = None
        confidence_level = None
        if config.include_confidence:
            if verification_info:
                confidence_score = verification_info.confidence_score
            elif verification_report:
                confidence_score, confidence_level = self._compute_confidence(
                    verification_report
                )
            
            if confidence_score is not None and confidence_level is None:
                confidence_level = self._score_to_level(confidence_score)
        
        # Step 11: Add confidence indicator
        if confidence_level and config.include_confidence:
            styled = self._add_confidence_indicator(styled, confidence_score, confidence_level, config.output_format)
            improvements_made.append("Added confidence indicator")
        
        # Step 12: Final formatting check
        styled = self._final_format_check(styled, config.output_format)
        
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
            verification_integrated=verified_count > 0,
            verified_claim_count=verified_count,
        )
    
    def _extract_verification_info(
        self,
        report: Dict[str, Any],
    ) -> VerificationInfo:
        """Extract VerificationInfo from legacy report format."""
        info = VerificationInfo()
        
        if "verified_claims" in report:
            info.verified_claims = report["verified_claims"]
        if "unverified_claims" in report:
            info.unverified_claims = report["unverified_claims"]
        if "corrections" in report:
            info.corrected_claims = report["corrections"]
        if "issues" in report or "issues_to_fix" in report:
            info.issues_found = report.get("issues", report.get("issues_to_fix", []))
        if "verification_score" in report:
            info.confidence_score = report["verification_score"]
        elif "confidence_score" in report:
            info.confidence_score = report["confidence_score"]
        
        return info
    
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
    
    def _fix_format_edge_cases(self, content: str) -> str:
        """Fix common formatting edge cases."""
        fixed = content
        
        # Fix truncated ending
        if fixed.endswith("...") and len(fixed) > 100:
            # Remove trailing ellipsis if it seems like truncation
            pass  # Keep as is, user may want to know it's truncated
        
        # Fix abrupt ending (no punctuation)
        if fixed and fixed[-1] not in '.!?)"\'`:':
            # Try to complete the sentence
            last_sentence_start = max(
                fixed.rfind('. '),
                fixed.rfind('? '),
                fixed.rfind('! ')
            )
            if last_sentence_start > len(fixed) * 0.8:
                # Just add period
                fixed = fixed + "."
        
        # Fix markdown artifacts (unclosed code blocks)
        open_code_blocks = fixed.count('```')
        if open_code_blocks % 2 != 0:
            fixed = fixed + "\n```"
        
        # Fix unclosed parentheses/brackets
        open_parens = fixed.count('(') - fixed.count(')')
        if open_parens > 0:
            fixed = fixed + ')' * open_parens
        
        open_brackets = fixed.count('[') - fixed.count(']')
        if open_brackets > 0:
            fixed = fixed + ']' * open_brackets
        
        return fixed
    
    def _remove_repetition(
        self,
        content: str,
        history: List[Dict[str, str]],
    ) -> Tuple[str, int]:
        """Remove content that repeats recent history."""
        if not history:
            return content, 0
        
        removed = 0
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Get recent content from history
        recent_content = ""
        for msg in history[-3:]:
            recent_content += " " + msg.get("content", "")
        recent_content = recent_content.lower()
        
        # Filter out sentences that are nearly identical to recent content
        filtered = []
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            
            # Skip very short sentences
            if len(sentence_lower) < 20:
                filtered.append(sentence)
                continue
            
            # Check if sentence is largely repeated
            if sentence_lower in recent_content:
                removed += 1
                continue
            
            filtered.append(sentence)
        
        return ' '.join(filtered), removed
    
    async def _apply_style_llm(
        self,
        content: str,
        tone: ToneStyle,
        audience: AudienceLevel,
        query: str,
    ) -> str:
        """Apply tone and style adjustments using LLM."""
        if not self.providers or len(content) < 50:
            return content
        
        # Only apply for significant tone changes
        if tone == ToneStyle.PROFESSIONAL:
            return content  # Default, no change needed
        
        provider = self._select_provider("gpt-4o-mini")
        if not provider:
            return content
        
        tone_instructions = {
            ToneStyle.CASUAL: "Make this sound natural and conversational",
            ToneStyle.ACADEMIC: "Make this sound scholarly and well-researched",
            ToneStyle.TECHNICAL: "Use precise technical terminology",
            ToneStyle.FRIENDLY: "Make this warm and approachable",
            ToneStyle.FORMAL: "Make this sound formal and official",
            ToneStyle.CONVERSATIONAL: "Make this flow like natural speech",
            ToneStyle.AUTHORITATIVE: "Make this sound confident and expert",
        }
        
        instruction = tone_instructions.get(tone, "")
        if not instruction:
            return content
        
        prompt = f"""{instruction}. Target audience: {audience.value}.

Original:
{content[:2000]}

Output ONLY the refined text, no commentary."""
        
        try:
            result = await provider.complete(prompt, model="gpt-4o-mini")
            # Safely extract content - handle None values
            raw = getattr(result, 'content', None) or getattr(result, 'text', None)
            refined = raw.strip() if raw else ""
            
            # Sanity check - should be similar length and not empty
            if refined and 0.5 < len(refined) / len(content) < 2.0 and len(refined) > 50:
                return refined
        except Exception as e:
            logger.debug("Style LLM failed: %s", e)
        
        return content
    
    def _integrate_verification(
        self,
        content: str,
        info: VerificationInfo,
        config: RefinementConfig,
    ) -> Tuple[str, int]:
        """Integrate verification results into content."""
        integrated = content
        count = 0
        
        # Apply corrections
        for old, new in info.corrected_claims.items():
            if old in integrated:
                integrated = integrated.replace(old, new)
                count += 1
        
        # Add verified annotations if enabled
        if config.show_verified_annotations and info.verified_claims:
            for claim in info.verified_claims[:5]:  # Limit annotations
                # Find claim in text and add subtle marker
                claim_pattern = re.escape(claim[:50]) if len(claim) > 50 else re.escape(claim)
                if re.search(claim_pattern, integrated, re.IGNORECASE):
                    # Could add "(verified)" but it can be distracting
                    # Instead, we just count verified claims
                    count += 1
        
        # Tone down unverified claims if configured
        if config.tone_down_unverified and info.unverified_claims:
            hedging_prefixes = [
                ("It is the case that", "It appears that"),
                ("definitely", "likely"),
                ("certainly", "probably"),
                ("always", "often"),
                ("never", "rarely"),
            ]
            
            for old, new in hedging_prefixes:
                if old in integrated:
                    # Check if this is near an unverified claim
                    for claim in info.unverified_claims:
                        if claim[:30] in integrated:
                            integrated = integrated.replace(old, new, 1)
                            break
        
        # Add verification notes at end if there were issues
        if info.issues_found and len(info.issues_found) > 0:
            issues_note = "\n\n*Note: Some claims in this response could not be fully verified.*"
            # Only add if not already present
            if "could not be fully verified" not in integrated:
                integrated = integrated + issues_note
        
        return integrated, count
    
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
        elif output_format == OutputFormat.EXEC_SUMMARY:
            return self._format_as_exec_summary(content)
        elif output_format == OutputFormat.QA:
            return self._format_as_qa(content)
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
        # First, check if content has inline numbered items (e.g., "1. Item 2. Item 3. Item")
        # This handles cases where the model outputs everything on one line
        inline_pattern = r'(\d+)\.\s*([^0-9]+?)(?=\s*\d+\.|$)'
        inline_matches = re.findall(inline_pattern, content)
        
        if len(inline_matches) >= 3:  # If we found at least 3 inline numbered items
            numbered = []
            for i, (_, item) in enumerate(inline_matches, 1):
                item = item.strip().rstrip('.,;')
                if item and len(item) > 3:
                    numbered.append(f"{i}. {item}")
            if numbered:
                return '\n'.join(numbered)
        
        # Fall back to line-by-line processing
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
    
    def _format_as_exec_summary(self, content: str) -> str:
        """Executive summary: brief lead + bullets."""
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        summary = sentences[0] if sentences else content
        bullets = []
        for s in sentences[1:5]:
            s = s.strip()
            if s:
                bullets.append(f"- {s}")
        bullet_block = "\n".join(bullets) if bullets else ""
        return f"**Executive Summary:** {summary}\n\n{bullet_block}".strip()
    
    def _format_as_qa(self, content: str) -> str:
        """Simple Q&A style."""
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            return content
        if len(lines) == 1:
            return f"Q: (original question)\nA: {lines[0]}"
        return "Q: (original question)\nA:\n" + "\n".join(f"- {l}" for l in lines)
    
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
            'python': ['def ', 'import ', 'class ', 'print(', 'async ', '    ', 'elif '],
            'javascript': ['function ', 'const ', 'let ', '=>', 'console.log', 'async '],
            'typescript': ['interface ', ': string', ': number', 'type ', 'export '],
            'rust': ['fn ', 'let mut ', '&str', 'impl ', '::', '->'],
            'go': ['func ', 'package ', 'import (', 'fmt.', ':= '],
            'java': ['public class', 'private ', 'void ', 'System.out', '@Override'],
            'sql': ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'CREATE TABLE'],
            'bash': ['#!/bin/bash', 'echo ', 'export ', '$(', 'if ['],
        }
        
        for lang, keywords in indicators.items():
            if any(kw in content for kw in keywords):
                return lang
        
        return ''
    
    def _enforce_length(self, content: str, max_length: int) -> str:
        """Enforce maximum character length constraint."""
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
    
    def _enforce_word_limit(self, content: str, max_words: int) -> str:
        """Enforce maximum word count constraint."""
        words = content.split()
        if len(words) <= max_words:
            return content
        
        # Truncate to max_words
        truncated_words = words[:max_words]
        truncated = ' '.join(truncated_words)
        
        # Try to end at sentence boundary
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclaim = truncated.rfind('!')
        
        best_cut = max(last_period, last_question, last_exclaim)
        
        if best_cut > len(truncated) * 0.7:
            return truncated[:best_cut + 1]
        
        return truncated + "..."
    
    def _add_tool_sources(
        self,
        content: str,
        tool_results: Dict[str, Any],
    ) -> str:
        """Add source attribution for tool results."""
        sources = []
        
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                source = result.get("source") or result.get("url")
                if source:
                    sources.append(f"- {tool_name}: {source}")
            elif hasattr(result, 'source') and result.source:
                sources.append(f"- {tool_name}: {result.source}")
        
        if sources:
            content += "\n\n---\n**Sources Used:**\n" + "\n".join(sources)
        
        return content
    
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
        
        level = self._score_to_level(score)
        return score, level
    
    def _score_to_level(self, score: float) -> str:
        """Convert numeric score to level."""
        if score >= 0.85:
            return "High"
        elif score >= 0.65:
            return "Medium"
        else:
            return "Low"
    
    def _add_confidence_indicator(
        self,
        content: str,
        score: Optional[float],
        level: str,
        output_format: OutputFormat = OutputFormat.PARAGRAPH,
    ) -> str:
        """Add confidence indicator to content. Skips JSON to avoid invalid syntax."""
        if output_format == OutputFormat.JSON:
            return content
        if score is not None:
            indicator = f"\n\n---\n**Confidence: {level}** ({int(score * 100)}%)"
        else:
            indicator = f"\n\n---\n**Confidence: {level}**"
        
        return content + indicator
    
    def _final_format_check(
        self,
        content: str,
        output_format: OutputFormat,
    ) -> str:
        """Final check to ensure content doesn't have formatting issues."""
        # Check for abrupt ending
        content = content.rstrip()
        
        # Ensure doesn't end mid-sentence
        if content and content[-1] not in '.!?)"\'`:—':
            # Check if it's a code block (may end with })
            if not content.endswith('}') and not content.endswith('```'):
                content += "."
        
        # Ensure no trailing markdown artifacts
        if content.endswith('**'):
            content = content[:-2]
        if content.endswith('__'):
            content = content[:-2]
        
        return content
    
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
    tone: str = "professional",
    domain: str = "general",
    providers: Optional[Dict[str, Any]] = None,
    verification_report: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Citation]] = None,
) -> RefinedAnswer:
    """Convenience function to refine an answer with full configuration."""
    config = RefinementConfig(
        output_format=OutputFormat(format_style) if format_style else OutputFormat.PARAGRAPH,
        tone=ToneStyle(tone) if tone else ToneStyle.PROFESSIONAL,
        domain=domain,
    )
    
    refiner = AnswerRefiner(providers=providers)
    return await refiner.refine(
        content,
        query=query,
        config=config,
        verification_report=verification_report,
        citations=citations,
    )


def quick_format(
    content: str,
    format_style: str = "paragraph",
) -> str:
    """Quick formatting without LLM."""
    refiner = AnswerRefiner()
    try:
        output_format = OutputFormat(format_style) if format_style else OutputFormat.PARAGRAPH
    except ValueError:
        output_format = OutputFormat.PARAGRAPH
    return refiner._apply_format(content, output_format)
