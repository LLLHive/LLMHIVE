"""Stage 3 Production-Grade Upgrades for LLMHive.

This module implements the 8 Stage 3 upgrades:
1. Pronoun-Based Shared Memory Recall
2. Prompt Diffusion & Refinement Loop
3. Multi-Fact Retrieval and Answer Merging
4. Live Data Integration via Tavily
5. Protocol Chaining & Adaptive Learning
6. Prompt Injection Defense
7. Logging & Instrumentation
8. Multi-Modal Gating

These upgrades bring LLMHive to production-grade readiness with robust
pronoun resolution, iterative prompt refinement, parallel fact retrieval,
real-time data access, adaptive re-processing, injection prevention,
comprehensive logging, and tier-gated multimodal capabilities.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Pronoun Resolution Helper
# ==============================================================================

class PronounResolver:
    """Resolves pronouns using shared memory and conversation history.
    
    Implements Stage 3 Upgrade 1: Pronoun-Based Shared Memory Recall.
    """
    
    # Pronouns that may need resolution
    PRONOUNS = {"it", "they", "them", "he", "she", "this", "that", "these", "those"}
    
    def __init__(self, shared_memory: Optional[Any] = None):
        self.shared_memory = shared_memory
    
    def detect_pronouns(self, query: str) -> List[str]:
        """Detect pronouns in query that might need resolution."""
        words = query.lower().split()
        found = []
        
        for i, word in enumerate(words):
            # Clean word
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.PRONOUNS:
                # Check if it starts a sentence or follows question word
                if i == 0 or (i > 0 and words[i-1].rstrip('?') in {'what', 'where', 'when', 'who', 'how', 'does', 'is', 'are', 'was', 'were'}):
                    found.append(clean_word)
        
        return found
    
    async def resolve(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Resolve pronouns in query using shared memory.
        
        Returns:
            Tuple of (resolved_query, list of resolutions made)
        """
        pronouns = self.detect_pronouns(query)
        if not pronouns or not self.shared_memory:
            return query, []
        
        resolutions = []
        resolved_query = query
        
        # Build context from history
        context = ""
        if history:
            for msg in reversed(history[-5:]):
                context += " " + msg.get("content", "")
        
        for pronoun in pronouns:
            try:
                result = await self.shared_memory.resolve_pronoun(
                    user_id=user_id,
                    pronoun=pronoun,
                    session_id=session_id,
                    recent_context=context,
                )
                
                if result:
                    referent, fact = result
                    # Replace pronoun with referent
                    pattern = rf'\b{pronoun}\b'
                    resolved_query = re.sub(pattern, referent, resolved_query, count=1, flags=re.IGNORECASE)
                    resolutions.append(f"'{pronoun}' → '{referent}'")
                    logger.info(
                        "Pronoun '%s' resolved to '%s' from memory",
                        pronoun, referent
                    )
            except Exception as e:
                logger.warning("Pronoun resolution failed for '%s': %s", pronoun, e)
        
        return resolved_query, resolutions


# ==============================================================================
# 3. Compound Query Handler (Multi-Fact Retrieval)
# ==============================================================================

@dataclass(slots=True)
class SubQuery:
    """A sub-query extracted from a compound query."""
    query: str
    original_part: str
    index: int


@dataclass(slots=True)
class MergedAnswer:
    """Merged answer from multiple sub-queries."""
    answer: str
    sub_answers: List[Dict[str, Any]]
    sources: List[str]
    citation_map: Dict[int, str]


class CompoundQueryHandler:
    """Handles compound queries by splitting, parallel retrieval, and merging.
    
    Implements Stage 3 Upgrade 3: Multi-Fact Retrieval and Answer Merging.
    """
    
    # Patterns that indicate compound queries
    COMPOUND_PATTERNS = [
        r'\?.*?\band\b.*?\?',  # Multiple question marks with 'and'
        r'\?\s*\w+.*?\?',  # Multiple question marks
        r'\band\s+(?:what|where|when|who|how|why)\b',  # "and what/where/etc"
        r'\balso\s+(?:what|where|when|who|how|why)\b',  # "also what/where/etc"
    ]
    
    # Split patterns
    SPLIT_PATTERNS = [
        r'\s+and\s+(?=(?:what|where|when|who|how|why))',  # Split on "and what/where/etc"
        r'\?\s+(?=[A-Z])',  # Split on "? <Capital letter>"
        r'\.\s+(?=[A-Z])',  # Split on ". <Capital letter>" (for statements)
    ]
    
    def is_compound(self, query: str) -> bool:
        """Check if query is a compound query."""
        for pattern in self.COMPOUND_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        # Check for multiple question marks
        if query.count('?') > 1:
            return True
        
        return False
    
    def split_query(self, query: str) -> List[SubQuery]:
        """Split a compound query into sub-queries."""
        sub_queries = []
        
        # Try splitting on patterns
        parts = [query]
        for pattern in self.SPLIT_PATTERNS:
            new_parts = []
            for part in parts:
                split_parts = re.split(pattern, part)
                new_parts.extend([p.strip() for p in split_parts if p.strip()])
            if len(new_parts) > len(parts):
                parts = new_parts
                break
        
        # If no split patterns worked, try simple 'and' split for questions
        if len(parts) == 1 and ' and ' in query.lower():
            # Be careful not to split "pros and cons" type phrases
            match = re.search(r'(.+?)\s+and\s+((?:what|where|when|who|how|why|is|are|does|do).+)', query, re.IGNORECASE)
            if match:
                parts = [match.group(1).strip(), match.group(2).strip()]
        
        for i, part in enumerate(parts):
            sub_queries.append(SubQuery(
                query=part,
                original_part=part,
                index=i,
            ))
        
        logger.info("Split compound query into %d sub-queries", len(sub_queries))
        return sub_queries
    
    def merge_answers(
        self,
        sub_answers: List[Dict[str, Any]],
        original_query: str,
    ) -> MergedAnswer:
        """Merge answers from sub-queries into a coherent response."""
        if not sub_answers:
            return MergedAnswer(
                answer="I couldn't find an answer to your question.",
                sub_answers=[],
                sources=[],
                citation_map={},
            )
        
        answer_parts = []
        all_sources = []
        citation_map = {}
        
        for i, sub_answer in enumerate(sub_answers, 1):
            content = sub_answer.get("content", "")
            source = sub_answer.get("source", "")
            
            if content:
                # Add citation
                if source:
                    citation_map[i] = source
                    all_sources.append(source)
                    content_with_citation = f"{content}【source{i}†】"
                else:
                    content_with_citation = content
                
                answer_parts.append(content_with_citation)
        
        # Join with appropriate separator
        if len(answer_parts) == 2:
            merged = f"{answer_parts[0]} Additionally, {answer_parts[1].lower()}"
        else:
            merged = " ".join(answer_parts)
        
        return MergedAnswer(
            answer=merged,
            sub_answers=sub_answers,
            sources=all_sources,
            citation_map=citation_map,
        )


# ==============================================================================
# 5. Adaptive Retry Handler (Protocol Chaining)
# ==============================================================================

@dataclass(slots=True)
class RetryResult:
    """Result of an adaptive retry attempt."""
    answer: str
    model_used: str
    strategy_used: str
    confidence: float
    was_retry: bool
    retry_reason: Optional[str] = None


class AdaptiveRetryHandler:
    """Handles adaptive retry based on confidence/verification scores.
    
    Implements Stage 3 Upgrade 5: Protocol Chaining & Adaptive Learning.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        providers: Optional[Dict[str, Any]] = None,
        consensus_manager: Optional[Any] = None,
        high_accuracy_models: Optional[List[str]] = None,
    ):
        self.confidence_threshold = confidence_threshold
        self.providers = providers or {}
        self.consensus_manager = consensus_manager
        self.high_accuracy_models = high_accuracy_models or [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-pro",
        ]
    
    async def check_and_retry(
        self,
        answer: str,
        confidence: float,
        verification_passed: bool,
        original_prompt: str,
        **kwargs,
    ) -> RetryResult:
        """
        Check if answer needs retry and perform adaptive retry if needed.
        
        Args:
            answer: Initial answer
            confidence: Confidence score (0-1)
            verification_passed: Whether fact-check passed
            original_prompt: Original user prompt
            
        Returns:
            RetryResult with final answer
        """
        # Check if retry is needed
        needs_retry = (
            confidence < self.confidence_threshold or
            not verification_passed
        )
        
        if not needs_retry:
            return RetryResult(
                answer=answer,
                model_used=kwargs.get("model", "unknown"),
                strategy_used="single_pass",
                confidence=confidence,
                was_retry=False,
            )
        
        logger.info(
            "Low confidence detected (%.2f). Initiating adaptive retry.",
            confidence
        )
        
        # Try deep consensus if multiple models available
        if self.consensus_manager and len(self.providers) > 1:
            try:
                consensus_result = await self._try_deep_consensus(
                    original_prompt, **kwargs
                )
                if consensus_result:
                    return consensus_result
            except Exception as e:
                logger.warning("Deep consensus failed: %s", e)
        
        # Fallback: try high-accuracy model
        try:
            high_acc_result = await self._try_high_accuracy_model(
                original_prompt, **kwargs
            )
            if high_acc_result:
                return high_acc_result
        except Exception as e:
            logger.warning("High-accuracy retry failed: %s", e)
        
        # Return original if all retries fail
        return RetryResult(
            answer=answer,
            model_used=kwargs.get("model", "unknown"),
            strategy_used="single_pass_fallback",
            confidence=confidence,
            was_retry=True,
            retry_reason="All retry strategies failed",
        )
    
    async def _try_deep_consensus(
        self,
        prompt: str,
        **kwargs,
    ) -> Optional[RetryResult]:
        """Try deep consensus with multiple models."""
        if not self.consensus_manager:
            return None
        
        logger.info("Attempting deep consensus strategy")
        
        try:
            result = await self.consensus_manager.reach_consensus(
                prompt=prompt,
                models=self.high_accuracy_models[:3],
                max_rounds=2,
            )
            
            if result and result.consensus_reached:
                logger.info(
                    "Deep consensus achieved with %.2f agreement",
                    result.agreement_score
                )
                return RetryResult(
                    answer=result.final_answer,
                    model_used="consensus:" + ",".join(result.participating_models),
                    strategy_used="deep_consensus",
                    confidence=result.confidence,
                    was_retry=True,
                    retry_reason="Low initial confidence",
                )
        except Exception as e:
            logger.warning("Deep consensus error: %s", e)
        
        return None
    
    async def _try_high_accuracy_model(
        self,
        prompt: str,
        **kwargs,
    ) -> Optional[RetryResult]:
        """Try with a high-accuracy model."""
        for model_id in self.high_accuracy_models:
            provider_name = model_id.split("/")[0] if "/" in model_id else "openrouter"
            
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            
            logger.info("Retrying with high-accuracy model: %s", model_id)
            
            try:
                result = await provider.complete(prompt, model=model_id)
                content = getattr(result, 'content', '') or getattr(result, 'text', '')
                
                if content:
                    return RetryResult(
                        answer=content,
                        model_used=model_id,
                        strategy_used="high_accuracy_retry",
                        confidence=0.85,  # Assume higher confidence from better model
                        was_retry=True,
                        retry_reason="Low initial confidence",
                    )
            except Exception as e:
                logger.warning("High-accuracy model %s failed: %s", model_id, e)
        
        return None


# ==============================================================================
# 6. Prompt Injection Detector (Enhanced)
# ==============================================================================

@dataclass(slots=True)
class InjectionCheckResult:
    """Result of prompt injection check."""
    is_injection: bool
    threat_level: str  # "none", "low", "medium", "high", "critical"
    matched_patterns: List[str]
    should_block: bool
    sanitized_input: Optional[str] = None


class EnhancedInjectionDetector:
    """Enhanced prompt injection detection with blocking capability.
    
    Implements Stage 3 Upgrade 6: Prompt Injection Defense.
    """
    
    # Injection patterns with threat levels
    INJECTION_PATTERNS = {
        "critical": [
            r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|commands?)",
            r"disregard\s+(all\s+)?(previous|above|prior)",
            r"forget\s+(everything|all)\s+(you|i)\s+(said|told)",
            r"reveal\s+(your|the)\s+(system|initial|hidden)\s+prompt",
            r"show\s+(me\s+)?your\s+(initial|system)\s+instructions?",
            r"what\s+(is|are)\s+your\s+(system|base)\s+(prompt|instructions?)",
        ],
        "high": [
            r"you\s+are\s+(now|actually)\s+a",
            r"pretend\s+(to\s+be|you\s+are)",
            r"act\s+as\s+(if\s+you\s+(are|were)|a)",
            r"roleplay\s+as",
            r"dan\s+mode",
            r"developer\s+mode",
            r"jailbreak",
            r"bypass\s+(safety|filter|restriction)",
        ],
        "medium": [
            r"simulate\s+being",
            r"unlock\s+(hidden|secret)",
            r"repeat\s+(your\s+)?instructions",
            r"<\s*script",
            r"javascript\s*:",
        ],
        "low": [
            r"on(load|error|click)\s*=",
            r"\{\{\s*constructor",
            r"__proto__",
        ],
    }
    
    # Compiled patterns
    _compiled_patterns: Dict[str, List[re.Pattern]] = {}
    
    def __init__(self, block_threshold: str = "medium"):
        """
        Initialize detector.
        
        Args:
            block_threshold: Minimum threat level to block ("low", "medium", "high", "critical")
        """
        self.block_threshold = block_threshold
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all patterns for efficiency."""
        for level, patterns in self.INJECTION_PATTERNS.items():
            self._compiled_patterns[level] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]
    
    def check(self, text: str) -> InjectionCheckResult:
        """
        Check text for injection patterns.
        
        Args:
            text: Input text to check
            
        Returns:
            InjectionCheckResult with detection details
        """
        matched_patterns = []
        highest_threat = "none"
        threat_order = ["none", "low", "medium", "high", "critical"]
        
        for level in ["critical", "high", "medium", "low"]:
            for pattern in self._compiled_patterns.get(level, []):
                if pattern.search(text):
                    matched_patterns.append(pattern.pattern)
                    if threat_order.index(level) > threat_order.index(highest_threat):
                        highest_threat = level
        
        is_injection = len(matched_patterns) > 0
        should_block = (
            is_injection and
            threat_order.index(highest_threat) >= threat_order.index(self.block_threshold)
        )
        
        if is_injection:
            logger.warning(
                "Prompt injection detected: threat=%s, patterns=%d, blocked=%s",
                highest_threat, len(matched_patterns), should_block
            )
        
        return InjectionCheckResult(
            is_injection=is_injection,
            threat_level=highest_threat,
            matched_patterns=matched_patterns[:3],  # Limit for logging
            should_block=should_block,
        )
    
    def get_safe_refusal(self) -> str:
        """Get a safe refusal message without revealing details."""
        return "I'm sorry, but I cannot fulfill that request."


# ==============================================================================
# 7. Enhanced Logger (Instrumentation)
# ==============================================================================

class Stage3Logger:
    """Enhanced logging and instrumentation for Stage 3 features.
    
    Implements Stage 3 Upgrade 7: Logging & Instrumentation.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._event_counts: Dict[str, int] = {}
    
    def log_cache_hit(self, cache_type: str, key: str):
        """Log a cache hit event."""
        self._increment("cache_hits", cache_type)
        self.logger.info("Cache hit: type=%s, key=%s", cache_type, key[:20])
    
    def log_cache_miss(self, cache_type: str, key: str):
        """Log a cache miss event."""
        self._increment("cache_misses", cache_type)
        self.logger.debug("Cache miss: type=%s, key=%s", cache_type, key[:20])
    
    def log_pronoun_resolution(self, pronoun: str, referent: Optional[str], success: bool):
        """Log pronoun resolution attempt."""
        self._increment("pronoun_resolutions", "success" if success else "failed")
        if success:
            self.logger.info("Pronoun resolved: '%s' → '%s'", pronoun, referent)
        else:
            self.logger.info("Pronoun unresolved: '%s' (no matching context)", pronoun)
    
    def log_tool_blocked(self, tool_name: str, reason: str, user_tier: str):
        """Log blocked tool usage."""
        self._increment("tools_blocked", tool_name)
        self.logger.warning(
            "Tool blocked: tool=%s, tier=%s, reason=%s",
            tool_name, user_tier, reason
        )
    
    def log_tier_restriction(self, feature: str, user_tier: str, required_tier: str):
        """Log tier-based restriction."""
        self._increment("tier_restrictions", feature)
        self.logger.warning(
            "Tier restriction: feature=%s, user_tier=%s, required=%s",
            feature, user_tier, required_tier
        )
    
    def log_injection_attempt(self, threat_level: str, blocked: bool):
        """Log injection attempt."""
        self._increment("injection_attempts", threat_level)
        if blocked:
            self.logger.warning("Injection attempt BLOCKED: threat=%s", threat_level)
        else:
            self.logger.info("Injection attempt detected (not blocked): threat=%s", threat_level)
    
    def log_memory_operation(self, operation: str, category: str, success: bool):
        """Log memory operation."""
        self._increment("memory_ops", f"{operation}_{category}")
        self.logger.info("Memory %s: category=%s, success=%s", operation, category, success)
    
    def log_diffusion_step(self, round_num: int, role: str, score_before: float, score_after: float):
        """Log prompt diffusion step."""
        self._increment("diffusion_steps", role)
        improvement = score_after - score_before
        self.logger.info(
            "Diffusion round %d: role=%s, improvement=%.2f (%.2f → %.2f)",
            round_num, role, improvement, score_before, score_after
        )
    
    def log_adaptive_retry(self, strategy: str, original_confidence: float, new_confidence: float):
        """Log adaptive retry."""
        self._increment("adaptive_retries", strategy)
        self.logger.info(
            "Adaptive retry: strategy=%s, confidence=%.2f → %.2f",
            strategy, original_confidence, new_confidence
        )
    
    def log_consensus_attempt(self, models: List[str], success: bool, agreement: float):
        """Log consensus attempt."""
        self._increment("consensus_attempts", "success" if success else "failed")
        self.logger.info(
            "Consensus: models=%d, success=%s, agreement=%.2f",
            len(models), success, agreement
        )
    
    def _increment(self, category: str, subcategory: str):
        """Increment event counter."""
        key = f"{category}:{subcategory}"
        self._event_counts[key] = self._event_counts.get(key, 0) + 1
    
    def get_stats(self) -> Dict[str, int]:
        """Get event statistics."""
        return dict(self._event_counts)


# ==============================================================================
# 8. Multi-Modal Gating
# ==============================================================================

class MultiModalGate:
    """Gate for multi-modal features based on tier.
    
    Implements Stage 3 Upgrade 8: Multi-Modal Gating.
    """
    
    # Features and their required tiers
    FEATURE_TIERS = {
        "image_analysis": {"pro", "enterprise"},
        "audio_transcription": {"pro", "enterprise"},
        "image_generation": {"enterprise"},
        "video_analysis": {"enterprise"},
        "document_ocr": {"pro", "enterprise"},
    }
    
    # Feature names for user messages
    FEATURE_NAMES = {
        "image_analysis": "Image Analysis",
        "audio_transcription": "Audio Transcription",
        "image_generation": "Image Generation",
        "video_analysis": "Video Analysis",
        "document_ocr": "Document OCR",
    }
    
    def __init__(self, logger_instance: Optional[Stage3Logger] = None):
        self.s3_logger = logger_instance
    
    def check_access(self, feature: str, user_tier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user tier has access to a multimodal feature.
        
        Args:
            feature: Feature name (e.g., "image_analysis")
            user_tier: User's tier (e.g., "free", "pro")
            
        Returns:
            Tuple of (allowed, error_message if blocked)
        """
        allowed_tiers = self.FEATURE_TIERS.get(feature, {"enterprise"})
        user_tier_lower = user_tier.lower()
        
        if user_tier_lower in allowed_tiers:
            return True, None
        
        # Determine required tier
        required_tier = min(allowed_tiers) if allowed_tiers else "enterprise"
        feature_name = self.FEATURE_NAMES.get(feature, feature)
        
        error_msg = (
            f"{feature_name} is not available on your current plan. "
            f"Please upgrade to {required_tier.title()} to access this feature."
        )
        
        # Log the restriction
        if self.s3_logger:
            self.s3_logger.log_tier_restriction(feature, user_tier, required_tier)
        
        return False, error_msg
    
    def get_available_features(self, user_tier: str) -> List[str]:
        """Get list of multimodal features available for a tier."""
        available = []
        for feature, tiers in self.FEATURE_TIERS.items():
            if user_tier.lower() in tiers:
                available.append(feature)
        return available


# ==============================================================================
# Factory Functions
# ==============================================================================

def create_pronoun_resolver(shared_memory: Optional[Any] = None) -> PronounResolver:
    """Create a pronoun resolver instance."""
    return PronounResolver(shared_memory)


def create_compound_handler() -> CompoundQueryHandler:
    """Create a compound query handler instance."""
    return CompoundQueryHandler()


def create_injection_detector(block_threshold: str = "medium") -> EnhancedInjectionDetector:
    """Create an injection detector instance."""
    return EnhancedInjectionDetector(block_threshold)


def create_adaptive_retry_handler(
    providers: Optional[Dict[str, Any]] = None,
    consensus_manager: Optional[Any] = None,
) -> AdaptiveRetryHandler:
    """Create an adaptive retry handler instance."""
    return AdaptiveRetryHandler(
        providers=providers,
        consensus_manager=consensus_manager,
    )


def create_stage3_logger(name: str = "llmhive.stage3") -> Stage3Logger:
    """Create a Stage 3 logger instance."""
    return Stage3Logger(logging.getLogger(name))


def create_multimodal_gate(logger_instance: Optional[Stage3Logger] = None) -> MultiModalGate:
    """Create a multimodal gate instance."""
    return MultiModalGate(logger_instance)

