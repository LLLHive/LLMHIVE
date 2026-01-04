"""Stage 4 Integration Module for LLMHive.

This module integrates all Stage 4 upgrades into a unified orchestrator
extension, providing a complete production-grade AI research platform.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Stage 4 module imports
from .stage4_upgrades import (
    TransformerCorefResolver,
    MemoryPruner,
    IterativeRefiner,
    LearnedWeightManager,
    EscalatingThresholdController,
    LiveDataAggregator,
    MultimodalTrialManager,
    SlidingWindowRateLimiter,
    AIInjectionDetector,
    MathNotationNormalizer,
    RefinementResult,
)

from .rag_upgrades import (
    DocumentChunker,
    ChunkRanker,
    OrderedAnswerMerger,
    MultiHopReasoner,
    RAGManager,
    MergedAnswer,
)

from .protocol_chain import (
    ChainExecutor,
    DAGVisualizer,
    ChainPlanner,
    ChainStep,
    ChainResult,
)

from .concurrency import (
    LockManager,
    ConcurrentMemoryStore,
    AccessControl,
    Role,
)

from .analytics import (
    MetricsCollector,
    AdaptiveTuner,
    InsightsDashboard,
)

from .connectivity import (
    ResilientSearchAggregator,
    ConnectivityMonitor,
    SearchResponse,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# STAGE 4 RESULT TYPES
# ==============================================================================

@dataclass
class Stage4Response:
    """Complete response from Stage 4 orchestrator."""
    answer: str
    query_id: str
    confidence: float
    sources: List[str] = field(default_factory=list)
    refinement_info: Optional[RefinementResult] = None
    chain_result: Optional[ChainResult] = None
    cache_info: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    
    def add_warning(self, warning: str):
        """Add a warning to the response."""
        self.warnings.append(warning)


# ==============================================================================
# STAGE 4 ORCHESTRATOR
# ==============================================================================

class Stage4Orchestrator:
    """Production-grade orchestrator with all Stage 4 enhancements.
    
    Integrates:
    - Transformer-based pronoun resolution
    - Memory TTL and summarization
    - Iterative refinement with diffs
    - Learned ensemble weights
    - RAG with chunking and multi-hop
    - Protocol chaining with partial results
    - Distributed locking
    - Analytics and auto-tuning
    - Resilient search providers
    - AI injection detection
    - Math notation handling
    - Multimodal trial system
    """
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        redis_url: Optional[str] = None,
        persistence_dir: Optional[str] = None,
    ):
        self._llm = llm_provider
        
        # Initialize all Stage 4 components
        self._init_components(redis_url, persistence_dir)
        
        logger.info("Stage 4 Orchestrator initialized")
    
    def _init_components(
        self,
        redis_url: Optional[str],
        persistence_dir: Optional[str],
    ):
        """Initialize all Stage 4 components."""
        # Section 1: Memory & Pronoun Resolution
        self._coref_resolver = TransformerCorefResolver(use_transformer=True)
        self._memory_pruner = MemoryPruner(llm_provider=self._llm)
        
        # Section 2: Prompt Refinement
        self._refiner = IterativeRefiner(max_rounds=3, llm_provider=self._llm)
        
        # Section 3: Consensus & Weights
        weights_path = f"{persistence_dir}/model_weights.json" if persistence_dir else None
        self._weight_manager = LearnedWeightManager(weights_path)
        
        # Section 4: RAG
        self._rag_manager = RAGManager()
        
        # Section 5: Loop Controls
        self._threshold_controller = EscalatingThresholdController()
        
        # Section 6: Live Data
        self._live_data = LiveDataAggregator()
        
        # Section 7: Multimodal
        self._multimodal_trials = MultimodalTrialManager()
        
        # Section 8: Rate Limiting
        self._rate_limiter = SlidingWindowRateLimiter()
        
        # Section 10: Analytics
        metrics_path = f"{persistence_dir}/metrics.json" if persistence_dir else None
        self._metrics = MetricsCollector(metrics_path)
        self._tuner = AdaptiveTuner(self._metrics)
        self._dashboard = InsightsDashboard(self._metrics, self._tuner)
        
        # Section 11: Concurrency
        self._lock_manager = LockManager(redis_url)
        self._memory_store = ConcurrentMemoryStore(self._lock_manager)
        
        # Section 12: Security
        self._injection_detector = AIInjectionDetector()
        
        # Section 13: Protocol Chaining
        self._chain_executor = ChainExecutor(continue_on_failure=True)
        self._dag_visualizer = DAGVisualizer()
        self._chain_planner = ChainPlanner()
        
        # Section 14: Math
        self._math_normalizer = MathNotationNormalizer()
        
        # Section 15: Connectivity
        self._search = ResilientSearchAggregator()
        self._connectivity = ConnectivityMonitor(self._search)
    
    async def process(
        self,
        query: str,
        user_id: str,
        context: Optional[str] = None,
        user_tier: str = "free",
    ) -> Stage4Response:
        """
        Process a query through the Stage 4 pipeline.
        
        Args:
            query: User query
            user_id: User identifier
            context: Optional conversation context
            user_tier: User's subscription tier
            
        Returns:
            Complete Stage4Response
        """
        start_time = time.time()
        query_id = str(uuid.uuid4())
        warnings = []
        
        logger.info("Processing query %s for user %s", query_id[:8], user_id)
        
        # Phase 0: Security Check
        is_injection, category, score = await self._injection_detector.detect(query)
        if is_injection:
            logger.warning("Injection detected in query %s: %s", query_id[:8], category)
            return Stage4Response(
                answer="I cannot process this request as it appears to contain a prompt injection attempt.",
                query_id=query_id,
                confidence=0.0,
                warnings=["Prompt injection detected"],
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # Phase 1: Rate Limiting
        allowed, wait_time = self._rate_limiter.check(user_id)
        if not allowed:
            return Stage4Response(
                answer=f"Rate limit exceeded. Please wait {wait_time:.0f} seconds.",
                query_id=query_id,
                confidence=0.0,
                warnings=["Rate limit exceeded"],
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # Phase 2: Normalize Query
        normalized_query = self._math_normalizer.normalize(query)
        is_math = self._math_normalizer.is_math_query(normalized_query)
        
        # Phase 3: Pronoun Resolution
        if context:
            resolutions = await self._coref_resolver.resolve(normalized_query, context)
            for pronoun, referent in resolutions.items():
                normalized_query = normalized_query.replace(pronoun, referent)
                logger.debug("Resolved pronoun '%s' → '%s'", pronoun, referent)
        
        # Phase 4: Detect Query Type
        if is_math:
            response = await self._process_math_query(
                normalized_query, query_id, user_id
            )
        elif self._is_live_data_query(normalized_query):
            response = await self._process_live_data_query(
                normalized_query, query_id, user_id
            )
        else:
            response = await self._process_general_query(
                normalized_query, query_id, user_id, context, user_tier
            )
        
        # Phase 5: Iterative Refinement
        if response.confidence < self._tuner.get_confidence_threshold():
            refinement = await self._refiner.refine(
                query, response.answer, context
            )
            response.answer = refinement.final_response
            response.confidence = refinement.final_confidence
            response.refinement_info = refinement
            
            if refinement.corrections_applied:
                logger.info(
                    "Applied %d corrections during refinement",
                    len(refinement.corrections_applied)
                )
        
        # Phase 6: Record Metrics
        self._metrics.record_query(
            query_id=query_id,
            query_text=query,
            model_used=response.metadata.get("model", "unknown"),
            latency_ms=response.latency_ms,
            confidence=response.confidence,
            success=response.confidence > 0.5,
            sources_count=len(response.sources),
        )
        
        # Phase 7: Add Connectivity Warnings
        connectivity_warning = self._connectivity.get_user_notification()
        if connectivity_warning:
            warnings.append(connectivity_warning)
        
        response.warnings.extend(warnings)
        response.latency_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Query %s completed in %.1fms (confidence=%.2f)",
            query_id[:8], response.latency_ms, response.confidence
        )
        
        return response
    
    async def _process_math_query(
        self,
        query: str,
        query_id: str,
        user_id: str,
    ) -> Stage4Response:
        """Process a mathematical query."""
        logger.debug("Processing as math query")
        
        # For math queries, we'd use a math-specialized model or tool
        # This is a placeholder for actual math solving
        
        return Stage4Response(
            answer=f"[Math Result] Query: {query}",
            query_id=query_id,
            confidence=0.7,
            metadata={"model": "math_solver", "query_type": "math"},
        )
    
    async def _process_live_data_query(
        self,
        query: str,
        query_id: str,
        user_id: str,
    ) -> Stage4Response:
        """Process a live data query."""
        logger.debug("Processing as live data query")
        
        result = await self._live_data.fetch(query)
        
        if result.error:
            return Stage4Response(
                answer=f"Unable to fetch live data: {result.error}",
                query_id=query_id,
                confidence=0.3,
                warnings=["Live data unavailable"],
                metadata={"model": "live_data", "query_type": "live_data"},
            )
        
        timestamp_str = result.retrieved_at.strftime("%Y-%m-%d %H:%M UTC")
        answer = f"{result.value}"
        if result.unit:
            answer += f" {result.unit}"
        answer += f" (as of {timestamp_str}) 【{result.source}†】"
        
        return Stage4Response(
            answer=answer,
            query_id=query_id,
            confidence=0.9 if not result.is_stale else 0.7,
            sources=[result.source],
            metadata={
                "model": "live_data",
                "query_type": "live_data",
                "retrieved_at": result.retrieved_at.isoformat(),
            },
        )
    
    async def _process_general_query(
        self,
        query: str,
        query_id: str,
        user_id: str,
        context: Optional[str],
        user_tier: str,
    ) -> Stage4Response:
        """Process a general query with RAG and search."""
        logger.debug("Processing as general query")
        
        # Search for relevant information
        search_response = await self._search.search(query, max_results=5)
        
        sources = []
        context_text = context or ""
        
        if search_response.results:
            # Build context from search results
            for i, result in enumerate(search_response.results[:3]):
                context_text += f"\n\nSource {i+1} ({result.url}):\n{result.snippet}"
                sources.append(result.url)
        
        # Generate answer using LLM
        if self._llm:
            try:
                prompt = f"""Based on the following context, answer the question.

Context:
{context_text}

Question: {query}

Answer:"""
                
                result = await self._llm.complete(prompt, model="gpt-4o-mini")
                answer = getattr(result, 'content', '') or str(result)
                
                # Add source citations
                if sources:
                    citations = " ".join(f"【source{i+1}†】" for i in range(len(sources)))
                    answer += f" {citations}"
                
                return Stage4Response(
                    answer=answer,
                    query_id=query_id,
                    confidence=0.8,
                    sources=sources,
                    metadata={"model": "gpt-4o-mini", "query_type": "general"},
                )
                
            except Exception as e:
                logger.warning("LLM call failed: %s", e)
        
        # Fallback to search results
        if search_response.results:
            answer = "\n\n".join(
                f"**{r.title}**\n{r.snippet}"
                for r in search_response.results[:3]
            )
            return Stage4Response(
                answer=answer,
                query_id=query_id,
                confidence=0.6,
                sources=sources,
                metadata={"model": "search_fallback", "query_type": "general"},
            )
        
        return Stage4Response(
            answer="I couldn't find relevant information to answer your question.",
            query_id=query_id,
            confidence=0.3,
            metadata={"model": "none", "query_type": "general"},
        )
    
    def _is_live_data_query(self, query: str) -> bool:
        """Check if query requires live data."""
        live_data_keywords = [
            "current", "today", "now", "latest", "price",
            "weather", "stock", "bitcoin", "crypto",
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in live_data_keywords)
    
    # =========================================================================
    # MULTIMODAL METHODS
    # =========================================================================
    
    async def process_image(
        self,
        image_data: bytes,
        prompt: str,
        user_id: str,
        user_tier: str = "free",
    ) -> Stage4Response:
        """Process an image with optional prompt."""
        query_id = str(uuid.uuid4())
        
        # Check trial usage for free tier
        allowed, message, remaining = self._multimodal_trials.check_trial(
            user_id, "image_analysis", user_tier
        )
        
        if not allowed:
            return Stage4Response(
                answer=message or "Image analysis not available for your tier.",
                query_id=query_id,
                confidence=0.0,
                warnings=["Upgrade required for image analysis"],
            )
        
        # Record trial usage
        if user_tier == "free":
            self._multimodal_trials.record_usage(user_id, "image_analysis")
        
        # Process image (placeholder)
        return Stage4Response(
            answer=f"[Image Analysis] {prompt}",
            query_id=query_id,
            confidence=0.7,
            warnings=[message] if message else [],
            metadata={"model": "vision", "remaining_trials": remaining},
        )
    
    async def process_audio(
        self,
        audio_data: bytes,
        user_id: str,
        user_tier: str = "free",
    ) -> Stage4Response:
        """Process audio for transcription."""
        query_id = str(uuid.uuid4())
        
        # Check trial usage for free tier
        allowed, message, remaining = self._multimodal_trials.check_trial(
            user_id, "audio_transcription", user_tier
        )
        
        if not allowed:
            return Stage4Response(
                answer=message or "Audio transcription not available for your tier.",
                query_id=query_id,
                confidence=0.0,
                warnings=["Upgrade required for audio transcription"],
            )
        
        # Record trial usage
        if user_tier == "free":
            self._multimodal_trials.record_usage(user_id, "audio_transcription")
        
        # Process audio (placeholder)
        return Stage4Response(
            answer="[Audio Transcription]",
            query_id=query_id,
            confidence=0.7,
            warnings=[message] if message else [],
            metadata={"model": "whisper", "remaining_trials": remaining},
        )
    
    # =========================================================================
    # ANALYTICS METHODS
    # =========================================================================
    
    def get_analytics_dashboard(self) -> InsightsDashboard:
        """Get the analytics dashboard."""
        return self._dashboard
    
    def get_model_insights(self) -> List[Dict[str, Any]]:
        """Get insights for all models."""
        insights = self._dashboard.get_model_insights()
        return [
            {
                "model_id": i.model_id,
                "success_rate": i.success_rate,
                "approval_rate": i.approval_rate,
                "avg_latency_ms": i.avg_latency_ms,
                "weight": i.weight,
                "recommendation": i.recommendation,
            }
            for i in insights
        ]
    
    def trigger_auto_tuning(self) -> Dict[str, Any]:
        """Trigger auto-tuning of parameters."""
        return self._tuner.tune()
    
    def record_user_feedback(self, query_id: str, feedback: str):
        """Record user feedback for a query."""
        self._metrics.record_user_feedback(query_id, feedback)
    
    # =========================================================================
    # PROTOCOL CHAINING METHODS
    # =========================================================================
    
    async def execute_chain(
        self,
        task: str,
        user_id: str,
    ) -> ChainResult:
        """Execute a task as a chain of steps."""
        # Plan the chain
        steps = self._chain_planner.plan(task)
        
        # Visualize for debugging
        dag_ascii = self._dag_visualizer.visualize_to_ascii(steps)
        logger.debug("Chain DAG:\n%s", dag_ascii)
        
        # Execute
        chain_id = str(uuid.uuid4())
        result = await self._chain_executor.execute(chain_id, steps)
        
        return result
    
    def visualize_chain(self, steps: List[ChainStep], format: str = "ascii") -> str:
        """Visualize a chain of steps."""
        if format == "dot":
            return self._dag_visualizer.visualize_to_dot(steps)
        elif format == "json":
            return self._dag_visualizer.visualize_to_json(steps)
        else:
            return self._dag_visualizer.visualize_to_ascii(steps)
    
    # =========================================================================
    # HEALTH & STATUS METHODS
    # =========================================================================
    
    async def check_health(self) -> Dict[str, Any]:
        """Check health of all services."""
        connectivity = await self._connectivity.check_connectivity()
        
        return {
            "status": connectivity["overall_status"],
            "connectivity": connectivity,
            "rate_limiter": {"type": "sliding_window"},
            "components": {
                "coref_resolver": "active",
                "memory_pruner": "active",
                "refiner": "active",
                "weight_manager": "active",
                "injection_detector": "active",
            },
        }
    
    def get_tuned_parameters(self) -> Dict[str, Any]:
        """Get current auto-tuned parameters."""
        return {
            "confidence_threshold": self._tuner.get_confidence_threshold(),
            "retry_threshold": self._tuner.get_retry_threshold(),
            "ensemble_weights": {
                m: self._weight_manager.get_weight(m)
                for m in ["gpt-4o", "gpt-4o-mini", "claude-3-opus", "claude-3-sonnet"]
            },
        }


# ==============================================================================
# FACTORY FUNCTION
# ==============================================================================

def create_stage4_orchestrator(
    llm_provider: Optional[Any] = None,
    redis_url: Optional[str] = None,
    persistence_dir: Optional[str] = None,
) -> Stage4Orchestrator:
    """Create a Stage 4 orchestrator with all enhancements."""
    return Stage4Orchestrator(
        llm_provider=llm_provider,
        redis_url=redis_url,
        persistence_dir=persistence_dir,
    )

