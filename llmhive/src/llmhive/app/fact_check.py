"""Enhanced fact-checking module with correction loop and multi-hop verification.

This module implements:
- Structured verification reports with per-fact status
- Automatic correction of unverified facts
- Multi-hop verification strategies
- Integration with memory and web search
- Feedback loop for iterative verification
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Import web research client (with fallback)
try:
    from .services.web_research import WebResearchClient, WebDocument
    WEB_RESEARCH_AVAILABLE = True
except ImportError:
    WEB_RESEARCH_AVAILABLE = False
    WebResearchClient = None  # type: ignore
    WebDocument = None  # type: ignore
    logger.warning("WebResearchClient not available")

# Import memory (with fallback)
try:
    from .memory.persistent_memory import get_persistent_memory, PersistentMemoryManager
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    get_persistent_memory = None  # type: ignore
    logger.warning("Memory module not available")


class VerificationStatus(str, Enum):
    """Status of a fact verification."""
    VERIFIED = "verified"
    CONTESTED = "contested"
    UNKNOWN = "unknown"
    CORRECTED = "corrected"
    UNVERIFIABLE = "unverifiable"


@dataclass(slots=True)
class FactCheckItem:
    """Represents a single factual claim and its verification status."""
    text: str
    verified: bool
    evidence: str = ""
    status: VerificationStatus = VerificationStatus.UNKNOWN
    evidence_urls: List[str] = field(default_factory=list)
    correction: Optional[str] = None  # Corrected fact if available
    confidence: float = 0.0  # 0.0-1.0 confidence in verification
    verification_source: str = ""  # "web", "memory", "llm"


@dataclass(slots=True)
class VerificationReport:
    """Aggregated verification results for an answer."""
    items: List[FactCheckItem] = field(default_factory=list)
    verification_score: float = 1.0
    needs_correction: bool = False
    is_valid: bool = True
    iteration: int = 0  # Which verification iteration this is
    corrections_made: int = 0
    
    def add_fact(
        self,
        fact_text: str,
        is_verified: bool,
        evidence: str = "",
        confidence: float = 0.0,
        source: str = "unknown",
    ) -> None:
        """Add a fact to the verification report."""
        status = (
            VerificationStatus.VERIFIED if is_verified 
            else VerificationStatus.UNKNOWN
        )
        item = FactCheckItem(
            text=fact_text,
            verified=is_verified,
            evidence=evidence,
            status=status,
            confidence=confidence,
            verification_source=source,
        )
        self.items.append(item)
        self._recalculate_scores()
    
    def _recalculate_scores(self) -> None:
        """Recalculate verification metrics."""
        if not self.items:
            self.verification_score = 1.0
            self.needs_correction = False
            self.is_valid = True
            return
        
        verified_count = sum(1 for i in self.items if i.verified)
        total_count = len(self.items)
        
        # Calculate weighted score based on confidence
        total_confidence = sum(i.confidence for i in self.items if i.verified)
        max_confidence = len(self.items)  # Max is 1.0 per item
        
        self.verification_score = (
            (verified_count / total_count) * 0.7 +
            (total_confidence / max(max_confidence, 1)) * 0.3
        )
        
        # Needs correction if any fact is not verified
        self.needs_correction = verified_count < total_count
        
        # Is valid if score >= 0.7 and no contested facts
        contested_count = sum(
            1 for i in self.items if i.status == VerificationStatus.CONTESTED
        )
        self.is_valid = self.verification_score >= 0.7 and contested_count == 0

    @property
    def verified_count(self) -> int:
        return sum(1 for i in self.items if i.verified)
    
    @property
    def unverified_count(self) -> int:
        return sum(1 for i in self.items if not i.verified)

    @property
    def contested_count(self) -> int:
        return sum(1 for i in self.items if i.status == VerificationStatus.CONTESTED)
    
    def get_failed_claims(self) -> List[FactCheckItem]:
        """Get all claims that failed verification."""
        return [i for i in self.items if not i.verified]
    
    def get_corrections(self) -> Dict[str, str]:
        """Get mapping of original facts to corrections."""
        return {
            item.text: item.correction
            for item in self.items
            if item.correction is not None
        }


class FactChecker:
    """Enhanced fact checker with multi-hop verification and correction loop.
    
    Features:
    - Structured verification reports
    - Multi-hop verification (try multiple strategies)
    - Integration with memory for known facts
    - Automatic correction of false facts
    - Iterative verification loop
    """
    
    def __init__(
        self,
        web_client: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        max_verification_iterations: int = 2,
        min_confidence_threshold: float = 0.6,
    ) -> None:
        """
        Initialize fact checker.
        
        Args:
            web_client: WebResearchClient for web searches
            memory_manager: PersistentMemoryManager for known facts
            max_verification_iterations: Max iterations for correction loop
            min_confidence_threshold: Minimum confidence to consider verified
        """
        self.web_client = web_client
        self.memory_manager = memory_manager
        self.max_iterations = max_verification_iterations
        self.min_confidence = min_confidence_threshold
        
        # Try to initialize defaults
        if self.memory_manager is None and MEMORY_AVAILABLE:
            try:
                self.memory_manager = get_persistent_memory()
            except Exception as e:
                logger.debug("Could not initialize memory: %s", e)
    
    async def verify(
        self,
        answer: str,
        *,
        prompt: str = "",
        web_documents: Optional[Sequence[Any]] = None,
        use_multihop: bool = True,
    ) -> VerificationReport:
        """
        Verify factual claims in an answer.
        
        Returns a structured VerificationReport with per-fact status.
        
        Args:
            answer: The answer text to verify
            prompt: Original prompt (for context)
            web_documents: Pre-retrieved web documents
            use_multihop: Whether to use multi-hop verification
            
        Returns:
            VerificationReport with detailed verification results
        """
        report = VerificationReport()
        
        # Extract factual statements from answer
        facts = self._extract_factual_statements(answer)
        
        if not facts:
            logger.debug("No factual claims extracted from answer")
            return report
        
        logger.info("Extracted %d factual claims for verification", len(facts))
        
        # Convert web_documents to list
        web_docs = list(web_documents or [])
        
        # Verify each fact
        for fact in facts:
            verified, evidence, confidence, source = await self._verify_fact(
                fact,
                web_documents=web_docs,
                use_multihop=use_multihop,
            )
            
            report.add_fact(
                fact_text=fact,
                is_verified=verified,
                evidence=evidence,
                confidence=confidence,
                source=source,
            )
        
        logger.info(
            "Verification complete: %d/%d verified (score: %.2f)",
            report.verified_count,
            len(report.items),
            report.verification_score,
        )
        
        return report
    
    async def _verify_fact(
        self,
        fact: str,
        *,
        web_documents: List[Any] = None,
        use_multihop: bool = True,
    ) -> Tuple[bool, str, float, str]:
        """
        Verify a single fact using multiple strategies.
        
        Returns:
            Tuple of (verified, evidence, confidence, source)
        """
        web_documents = web_documents or []
        
        # Strategy 1: Check against provided web documents
        verified, evidence, confidence = self._check_in_documents(fact, web_documents)
        if verified and confidence >= self.min_confidence:
            return True, evidence, confidence, "web"
        
        # Strategy 2: Check memory for known facts
        if self.memory_manager:
            mem_verified, mem_evidence, mem_confidence = await self._check_in_memory(fact)
            if mem_verified and mem_confidence >= self.min_confidence:
                return True, mem_evidence, mem_confidence, "memory"
        
        # Strategy 3: Multi-hop - try alternative queries if enabled
        if use_multihop and self.web_client:
            alt_verified, alt_evidence, alt_confidence = await self._multihop_verify(fact)
            if alt_verified:
                return True, alt_evidence, alt_confidence, "web_multihop"
        
        # Strategy 4: Break down complex facts
        if use_multihop and " and " in fact.lower():
            parts_verified, parts_evidence, parts_confidence = await self._verify_compound_fact(fact)
            if parts_verified:
                return True, parts_evidence, parts_confidence, "decomposed"
        
        # Return best evidence found even if not verified
        if evidence:
            return False, evidence, confidence, "web"
        
        return False, "", 0.0, "unknown"
    
    def _check_in_documents(
        self,
        fact: str,
        documents: List[Any],
    ) -> Tuple[bool, str, float]:
        """Check if fact is supported by web documents."""
        if not documents:
            return False, "", 0.0
        
        fact_lower = fact.lower()
        fact_words = set(fact_lower.split())
        
        best_match = ""
        best_score = 0.0
        
        for doc in documents:
            snippet = getattr(doc, 'snippet', '') or ""
            title = getattr(doc, 'title', '') or ""
            content = f"{title} {snippet}".lower()
            
            # Calculate word overlap
            content_words = set(content.split())
            overlap = len(fact_words.intersection(content_words))
            score = overlap / max(len(fact_words), 1)
            
            # Check for key terms
            # Extract potential key entities (capitalized words, numbers, dates)
            key_terms = re.findall(r'\b[A-Z][a-z]+\b|\b\d+\b', fact)
            key_matches = sum(1 for term in key_terms if term.lower() in content)
            key_score = key_matches / max(len(key_terms), 1) if key_terms else 0
            
            combined_score = (score * 0.6) + (key_score * 0.4)
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = snippet[:200] if snippet else title
        
        verified = best_score >= 0.5
        return verified, best_match, best_score
    
    async def _check_in_memory(
        self,
        fact: str,
    ) -> Tuple[bool, str, float]:
        """Check if fact exists in memory."""
        if not self.memory_manager:
            return False, "", 0.0
        
        try:
            hits = self.memory_manager.query_memory(
                query_text=fact,
                top_k=3,
                min_score=0.7,
                filter_verified=True,
            )
            
            if hits:
                best_hit = hits[0]
                # Higher confidence if it's a verified memory
                confidence = min(0.95, best_hit.score)
                return True, best_hit.text[:200], confidence
                
        except Exception as e:
            logger.debug("Memory check failed: %s", e)
        
        return False, "", 0.0
    
    async def _multihop_verify(
        self,
        fact: str,
    ) -> Tuple[bool, str, float]:
        """Try alternative queries for verification."""
        if not self.web_client:
            return False, "", 0.0
        
        # Generate alternative queries
        alt_queries = self._generate_alternative_queries(fact)
        
        for alt_query in alt_queries[:2]:  # Try up to 2 alternatives
            try:
                results = await self.web_client.search(alt_query)
                if results:
                    verified, evidence, confidence = self._check_in_documents(fact, results)
                    if verified:
                        return True, evidence, confidence
            except Exception as e:
                logger.debug("Alternative query failed: %s", e)
        
        return False, "", 0.0
    
    def _generate_alternative_queries(self, fact: str) -> List[str]:
        """Generate alternative search queries for a fact."""
        queries = []
        
        # Query 1: Direct fact
        queries.append(fact)
        
        # Query 2: Question form
        if not fact.endswith("?"):
            queries.append(f"Is it true that {fact.lower()}?")
        
        # Query 3: Key terms only
        key_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b\d+\b', fact)
        if key_terms:
            queries.append(" ".join(key_terms))
        
        # Query 4: Remove hedging words
        cleaned = re.sub(
            r'\b(approximately|about|roughly|nearly|almost|likely|probably)\b',
            '',
            fact,
            flags=re.IGNORECASE,
        )
        if cleaned != fact:
            queries.append(cleaned.strip())
        
        return queries
    
    async def _verify_compound_fact(
        self,
        fact: str,
    ) -> Tuple[bool, str, float]:
        """Verify a compound fact by breaking it into parts."""
        # Split on "and", "also", "additionally"
        parts = re.split(r'\band\b|\balso\b|\badditionally\b', fact, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if len(p.strip()) > 10]
        
        if len(parts) <= 1:
            return False, "", 0.0
        
        verified_parts = 0
        evidence_parts = []
        
        for part in parts:
            verified, evidence, confidence = await self._verify_fact(
                part,
                use_multihop=False,  # Avoid infinite recursion
            )
            if verified:
                verified_parts += 1
                evidence_parts.append(evidence[:100])
        
        # Compound fact is verified if majority of parts are verified
        all_verified = verified_parts >= (len(parts) * 0.7)
        combined_evidence = " | ".join(evidence_parts[:3])
        confidence = verified_parts / max(len(parts), 1)
        
        return all_verified, combined_evidence, confidence
    
    def _extract_factual_statements(
        self,
        answer: str,
        *,
        max_claims: int = 6,
    ) -> List[str]:
        """Extract factual statements from an answer."""
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        
        facts = []
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Skip short sentences
            if len(sentence.split()) < 5:
                continue
            
            # Skip questions
            if sentence.endswith("?"):
                continue
            
            # Skip opinions/hedged statements
            opinion_markers = [
                "I think", "I believe", "In my opinion", "Perhaps",
                "Maybe", "It might", "Could be", "Seems like",
            ]
            if any(marker.lower() in sentence.lower() for marker in opinion_markers):
                continue
            
            # Look for factual indicators
            factual_indicators = [
                r'\b(is|are|was|were|has|have|had)\b',  # State of being
                r'\b\d+\b',  # Numbers
                r'\b(in|on|at)\s+\d{4}\b',  # Dates
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',  # Proper nouns
            ]
            
            has_factual_indicator = any(
                re.search(pattern, sentence) for pattern in factual_indicators
            )
            
            if has_factual_indicator:
                facts.append(sentence)
        
        return facts[:max_claims]
    
    def correct_answer(
        self,
        answer: str,
        report: VerificationReport,
        corrections: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Correct unverified facts in an answer.
        
        Args:
            answer: Original answer text
            report: Verification report with failed claims
            corrections: Optional dict of {wrong_fact: correct_fact}
            
        Returns:
            Corrected answer text
        """
        corrected = answer
        corrections_made = 0
        
        # Get corrections from report or provided dict
        fact_corrections = corrections or {}
        
        for item in report.items:
            if not item.verified:
                fact = item.text
                
                if fact in fact_corrections and fact_corrections[fact]:
                    # Apply provided correction
                    correction = fact_corrections[fact]
                    corrected = corrected.replace(fact, correction)
                    item.correction = correction
                    item.status = VerificationStatus.CORRECTED
                    corrections_made += 1
                    logger.info("Corrected fact: '%s' -> '%s'", fact[:50], correction[:50])
                elif item.evidence:
                    # Try to infer correction from evidence
                    inferred = self._infer_correction(fact, item.evidence)
                    if inferred:
                        corrected = corrected.replace(fact, inferred)
                        item.correction = inferred
                        item.status = VerificationStatus.CORRECTED
                        corrections_made += 1
                else:
                    # Mark as unverified if no correction available
                    marked = f"[Note: This claim could not be verified: {fact}]"
                    corrected = corrected.replace(fact, marked)
                    item.status = VerificationStatus.UNVERIFIABLE
        
        report.corrections_made = corrections_made
        logger.info("Made %d corrections to answer", corrections_made)
        
        return corrected
    
    def _infer_correction(self, wrong_fact: str, evidence: str) -> Optional[str]:
        """Try to infer a correction from evidence."""
        # This is a simplified heuristic approach
        # In production, you might use an LLM to extract the correct fact
        
        if not evidence:
            return None
        
        # Extract key patterns that might indicate correct values
        # Look for "is" or "was" statements in evidence
        is_patterns = re.findall(
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is|was|are|were)\s+([^.]+)',
            evidence,
        )
        
        if is_patterns:
            # Find the pattern most relevant to the wrong fact
            wrong_words = set(wrong_fact.lower().split())
            for subject, predicate in is_patterns:
                if subject.lower() in wrong_fact.lower():
                    return f"{subject} is {predicate.strip()}."
        
        return None
    
    async def correct_with_search(
        self,
        answer: str,
        report: VerificationReport,
    ) -> str:
        """
        Correct unverified facts by searching for correct information.
        
        Args:
            answer: Original answer text
            report: Verification report with failed claims
            
        Returns:
            Corrected answer text
        """
        corrections: Dict[str, str] = {}
        
        for item in report.items:
            if not item.verified and self.web_client:
                # Search for correct information
                try:
                    query = f"{item.text} correct fact"
                    results = await self.web_client.search(query)
                    
                    if results:
                        # Extract potential correction from results
                        for doc in results[:2]:
                            snippet = getattr(doc, 'snippet', '') or ""
                            inferred = self._infer_correction(item.text, snippet)
                            if inferred:
                                corrections[item.text] = inferred
                                break
                except Exception as e:
                    logger.debug("Search for correction failed: %s", e)
        
        return self.correct_answer(answer, report, corrections)
    
    async def verify_and_correct_loop(
        self,
        answer: str,
        *,
        prompt: str = "",
        web_documents: Optional[Sequence[Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> Tuple[str, VerificationReport]:
        """
        Run verification and correction loop until answer passes or max iterations.
        
        This implements the feedback loop for verification:
        1. Verify answer
        2. If fails, attempt correction
        3. Re-verify corrected answer
        4. Repeat until passes or max iterations
        
        Args:
            answer: Initial answer to verify
            prompt: Original prompt
            web_documents: Pre-retrieved web documents
            max_iterations: Max correction iterations (default: self.max_iterations)
            
        Returns:
            Tuple of (final_answer, final_report)
        """
        max_iters = max_iterations or self.max_iterations
        current_answer = answer
        final_report = None
        
        for iteration in range(max_iters):
            logger.info("Verification iteration %d/%d", iteration + 1, max_iters)
            
            # Verify current answer
            report = await self.verify(
                current_answer,
                prompt=prompt,
                web_documents=web_documents,
            )
            report.iteration = iteration + 1
            final_report = report
            
            # Check if verification passed
            if not report.needs_correction:
                logger.info("Answer passed verification on iteration %d", iteration + 1)
                return current_answer, report
            
            # Check for improvement from previous iteration
            if iteration > 0:
                # Compare with previous report
                prev_unverified = sum(1 for i in final_report.items if not i.verified)
                curr_unverified = report.unverified_count
                
                if curr_unverified >= prev_unverified:
                    logger.info(
                        "No improvement after correction (still %d unverified), stopping",
                        curr_unverified,
                    )
                    break
            
            # Attempt correction
            logger.info(
                "Answer failed verification (%d unverified), attempting correction",
                report.unverified_count,
            )
            
            if self.web_client:
                current_answer = await self.correct_with_search(current_answer, report)
            else:
                current_answer = self.correct_answer(current_answer, report)
        
        logger.info(
            "Verification loop complete after %d iterations (score: %.2f)",
            final_report.iteration if final_report else 0,
            final_report.verification_score if final_report else 0,
        )
        
        return current_answer, final_report


# Convenience functions
async def verify(
    answer: str,
    *,
    prompt: str = "",
    web_documents: Optional[Sequence[Any]] = None,
) -> VerificationReport:
    """Verify factual claims in an answer."""
    checker = FactChecker()
    return await checker.verify(answer, prompt=prompt, web_documents=web_documents)


def correct_answer(
    answer: str,
    report: VerificationReport,
    corrections: Optional[Dict[str, str]] = None,
) -> str:
    """Correct unverified facts in an answer."""
    checker = FactChecker()
    return checker.correct_answer(answer, report, corrections)


async def verify_and_correct(
    answer: str,
    *,
    prompt: str = "",
    max_iterations: int = 2,
) -> Tuple[str, VerificationReport]:
    """Run verification and correction loop."""
    checker = FactChecker(max_verification_iterations=max_iterations)
    return await checker.verify_and_correct_loop(answer, prompt=prompt)


# Legacy compatibility
FactCheckClaim = FactCheckItem
FactCheckResult = VerificationReport
