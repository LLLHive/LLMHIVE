"""LLMHive Orchestration Package - Stage 4 Production-Grade Upgrades.

This package contains all Stage 4 upgrades for the LLMHive AI research platform:

1. Shared Blackboard & Memory Enhancements
   - TransformerCorefResolver: Transformer-based pronoun resolution
   - MemoryPruner: TTL enforcement with summarization

2. Prompt Diffusion & Iterative Refinement
   - IterativeRefiner: Max rounds, logging, error diffs

3. Deep Consensus & Adaptive Ensemble
   - LearnedWeightManager: Dynamic learned model weights

4. RAG Upgrades
   - DocumentChunker: Chunked document retrieval
   - ChunkRanker: Query-aware chunk ranking
   - OrderedAnswerMerger: Order-preserving answer merging
   - MultiHopReasoner: Multi-hop reasoning with tracing

5. Loop-Back Self-Refinement Controls
   - EscalatingThresholdController: 3 iter limit, escalating thresholds

6. Live Data Integration
   - LiveDataAggregator: Real APIs with caching and fallback

7. Multimodal Support Extensions
   - MultimodalTrialManager: Trial uses for free tier

8. Plan Caching & Rate Limits
   - SlidingWindowRateLimiter: Adaptive rate limiting

9. Payments & Subscription
   - SubscriptionManager: Stripe integration (in payments module)

10. Adaptive Learning & Analytics
    - MetricsCollector: Performance metrics
    - AdaptiveTuner: Auto-tuning via RL signals
    - InsightsDashboard: Model insights UI

11. Roles & Concurrency
    - LockManager: Redis distributed locks
    - ConcurrentMemoryStore: Thread-safe memory
    - AccessControl: Granular permissions

12. Security & Injection Defense
    - AIInjectionDetector: AI-powered injection detection

13. Protocol Chaining Robustness
    - ChainExecutor: Atomic execution with partial results
    - DAGVisualizer: Execution plan visualization
    - ChainPlanner: Task planning

14. Math Query Handling
    - MathNotationNormalizer: Unicode normalization

15. Connectivity & Resilience
    - ResilientSearchAggregator: Multi-provider search with fallback
    - ConnectivityMonitor: Service health monitoring
"""
from __future__ import annotations

# Stage 4 Core Upgrades
from .stage4_upgrades import (
    TransformerCorefResolver,
    MemoryPruner,
    MemorySummary,
    IterativeRefiner,
    RefinementStep,
    RefinementResult,
    LearnedWeightManager,
    ModelWeight,
    EscalatingThresholdController,
    LiveDataAggregator,
    LiveDataResult,
    CryptoDataProvider,
    WeatherDataProvider,
    MultimodalTrialManager,
    SlidingWindowRateLimiter,
    AIInjectionDetector,
    MathNotationNormalizer,
    # Factory functions
    create_transformer_resolver,
    create_memory_pruner,
    create_iterative_refiner,
    create_weight_manager,
    create_threshold_controller,
    create_live_data_aggregator,
    create_multimodal_trial_manager,
    create_rate_limiter,
    create_ai_injection_detector,
    create_math_normalizer,
)

# RAG Upgrades
from .rag_upgrades import (
    DocumentChunk,
    DocumentChunker,
    ChunkRanker,
    SubAnswer,
    MergedAnswer,
    OrderedAnswerMerger,
    HopResult,
    MultiHopTrace,
    MultiHopReasoner,
    RAGManager,
    # Factory functions
    create_document_chunker,
    create_chunk_ranker,
    create_answer_merger,
    create_multi_hop_reasoner,
    create_rag_manager,
)

# Protocol Chaining
from .protocol_chain import (
    StepStatus,
    ChainStep,
    ChainResult,
    AtomicStepExecutor,
    ChainExecutor,
    DAGNode,
    DAGEdge,
    DAGBuilder,
    DAGVisualizer,
    ChainPlanner,
    # Factory functions
    create_step_executor,
    create_chain_executor,
    create_dag_visualizer,
    create_chain_planner,
)

# Concurrency
from .concurrency import (
    DistributedLock,
    LocalLock,
    RedisLock,
    LockManager,
    Role,
    Permission,
    AccessControl,
    MemoryEntry,
    PermissionChecker,
    ConcurrentMemoryStore,
    # Factory functions
    create_lock_manager,
    create_access_control,
    create_permission_checker,
    create_concurrent_memory_store,
)

# Analytics
from .analytics import (
    ModelMetrics,
    QueryMetrics,
    MetricsCollector,
    AdaptiveTuner,
    ModelInsight,
    InsightsDashboard,
    # Factory functions
    create_metrics_collector,
    create_adaptive_tuner,
    create_insights_dashboard,
)

# Connectivity
from .connectivity import (
    ProviderStatus,
    ProviderHealth,
    SearchResult,
    SearchResponse,
    SearchProvider,
    TavilyProvider,
    SerpAPIProvider,
    SerperProvider,
    ResilientSearchAggregator,
    ConnectivityMonitor,
    # Factory functions
    create_tavily_provider,
    create_serpapi_provider,
    create_serper_provider,
    create_resilient_search,
    create_connectivity_monitor,
)

# Stage 4 Integration
from .stage4_integration import (
    Stage4Response,
    Stage4Orchestrator,
    create_stage4_orchestrator,
    get_orchestrator,
)

# Category-Specific Optimization (January 2026)
from .category_optimization import (
    CategoryOptimizationEngine,
    QueryAnalyzer,
    OptimizationMode,
    OptimizationCategory,
    QueryComplexity,
    category_optimize,
    get_optimization_engine,
)

# Elite Orchestration
from .elite_orchestration import (
    EliteTier,
    EliteConfig,
    elite_orchestrate,
    elite_math_solve,
    elite_reasoning_solve,
    elite_rag_query,
    elite_multimodal_process,
    detect_elite_category,
    estimate_elite_cost,
)

__all__ = [
    # Stage 4 Core
    "TransformerCorefResolver",
    "MemoryPruner",
    "MemorySummary",
    "IterativeRefiner",
    "RefinementStep",
    "RefinementResult",
    "LearnedWeightManager",
    "ModelWeight",
    "EscalatingThresholdController",
    "LiveDataAggregator",
    "LiveDataResult",
    "CryptoDataProvider",
    "WeatherDataProvider",
    "MultimodalTrialManager",
    "SlidingWindowRateLimiter",
    "AIInjectionDetector",
    "MathNotationNormalizer",
    # RAG
    "DocumentChunk",
    "DocumentChunker",
    "ChunkRanker",
    "SubAnswer",
    "MergedAnswer",
    "OrderedAnswerMerger",
    "HopResult",
    "MultiHopTrace",
    "MultiHopReasoner",
    "RAGManager",
    # Protocol Chaining
    "StepStatus",
    "ChainStep",
    "ChainResult",
    "AtomicStepExecutor",
    "ChainExecutor",
    "DAGNode",
    "DAGEdge",
    "DAGBuilder",
    "DAGVisualizer",
    "ChainPlanner",
    # Concurrency
    "DistributedLock",
    "LocalLock",
    "RedisLock",
    "LockManager",
    "Role",
    "Permission",
    "AccessControl",
    "MemoryEntry",
    "PermissionChecker",
    "ConcurrentMemoryStore",
    # Analytics
    "ModelMetrics",
    "QueryMetrics",
    "MetricsCollector",
    "AdaptiveTuner",
    "ModelInsight",
    "InsightsDashboard",
    # Connectivity
    "ProviderStatus",
    "ProviderHealth",
    "SearchResult",
    "SearchResponse",
    "SearchProvider",
    "TavilyProvider",
    "SerpAPIProvider",
    "SerperProvider",
    "ResilientSearchAggregator",
    "ConnectivityMonitor",
    # Integration
    "Stage4Response",
    "Stage4Orchestrator",
    # Factory Functions
    "create_stage4_orchestrator",
    "get_orchestrator",
    "create_transformer_resolver",
    "create_memory_pruner",
    "create_iterative_refiner",
    "create_weight_manager",
    "create_threshold_controller",
    "create_live_data_aggregator",
    "create_multimodal_trial_manager",
    "create_rate_limiter",
    "create_ai_injection_detector",
    "create_math_normalizer",
    "create_document_chunker",
    "create_chunk_ranker",
    "create_answer_merger",
    "create_multi_hop_reasoner",
    "create_rag_manager",
    "create_step_executor",
    "create_chain_executor",
    "create_dag_visualizer",
    "create_chain_planner",
    "create_lock_manager",
    "create_access_control",
    "create_permission_checker",
    "create_concurrent_memory_store",
    "create_metrics_collector",
    "create_adaptive_tuner",
    "create_insights_dashboard",
    "create_tavily_provider",
    "create_serpapi_provider",
    "create_serper_provider",
    "create_resilient_search",
    "create_connectivity_monitor",
    # Category Optimization (January 2026)
    "CategoryOptimizationEngine",
    "QueryAnalyzer",
    "OptimizationMode",
    "OptimizationCategory",
    "QueryComplexity",
    "category_optimize",
    "get_optimization_engine",
    # Elite Orchestration
    "EliteTier",
    "EliteConfig",
    "elite_orchestrate",
    "elite_math_solve",
    "elite_reasoning_solve",
    "elite_rag_query",
    "elite_multimodal_process",
    "detect_elite_category",
    "estimate_elite_cost",
]
