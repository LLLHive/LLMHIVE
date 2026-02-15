"""Orchestrator module for LLMHive - provides unified interface for LLM orchestration.

This module implements the main orchestration logic including:
- Hierarchical Role Management (HRM) for complex queries
- Adaptive model routing based on performance metrics
- Multi-model ensemble orchestration
- Deep consensus through multi-round debate
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Import feature flags for controlling partial implementations
try:
    from .feature_flags import is_feature_enabled, FeatureFlags
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False
    def is_feature_enabled(flag): return False  # type: ignore
    logger.warning("Feature flags module not available, all flags disabled")

# Import orchestration components
try:
    from .orchestration.hierarchical_planning import (
        HierarchicalPlanner,
        HierarchicalPlan,
        HierarchicalPlanStep,
        TaskComplexity,
        is_complex_query,
        decompose_query,
    )
    from .orchestration.hierarchical_executor import (
        HierarchicalPlanExecutor,
        HRMBlackboard,
        ExecutionResult as HRMExecutionResult,
        StepResult,
        StepStatus,
        execute_hierarchical_plan,
    )
    HRM_AVAILABLE = True
except ImportError:
    HRM_AVAILABLE = False
    HierarchicalPlanner = None  # type: ignore
    HierarchicalPlanExecutor = None  # type: ignore
    HRMBlackboard = None  # type: ignore
    execute_hierarchical_plan = None  # type: ignore
    logger.warning("Hierarchical planning module not available")

try:
    from .orchestration.adaptive_router import (
        AdaptiveModelRouter,
        get_adaptive_router,
        select_models_adaptive,
        infer_domain,
    )
    ADAPTIVE_ROUTING_AVAILABLE = True
except ImportError:
    ADAPTIVE_ROUTING_AVAILABLE = False
    AdaptiveModelRouter = None  # type: ignore
    logger.warning("Adaptive routing module not available")

try:
    from .performance_tracker import performance_tracker
    PERFORMANCE_TRACKER_AVAILABLE = True
except ImportError:
    PERFORMANCE_TRACKER_AVAILABLE = False
    performance_tracker = None  # type: ignore

# Import memory components
try:
    from .memory.persistent_memory import (
        PersistentMemoryManager,
        Scratchpad,
        get_persistent_memory,
        get_scratchpad,
        query_scratchpad,
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    PersistentMemoryManager = None  # type: ignore
    Scratchpad = None  # type: ignore
    logger.warning("Memory module not available")

# Import fact-checking components
try:
    from .fact_check import (
        FactChecker,
        VerificationReport,
        verify_and_correct,
    )
    FACT_CHECK_AVAILABLE = True
except ImportError:
    FACT_CHECK_AVAILABLE = False
    FactChecker = None  # type: ignore
    VerificationReport = None  # type: ignore
    logger.warning("Fact check module not available")

# Import guardrails components
try:
    from .guardrails import (
        SafetyValidator,
        TierAccessController,
        redact_sensitive_info,
        check_output_policy,
        enforce_output_policy,
        assess_query_risk,
        filter_query,
        filter_output,
        security_check,
        get_safety_validator,
        get_tier_controller,
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    SafetyValidator = None  # type: ignore
    TierAccessController = None  # type: ignore
    logger.warning("Guardrails module not available")

# Import tool broker components
try:
    from .tool_broker import (
        ToolBroker,
        ToolResult,
        ToolType,
        ToolAnalysis,
        ToolRequest,
        RAGConfig,
        RetrievalMode,
        get_tool_broker,
        configure_tool_broker,
        check_and_execute_tools,
    )
    TOOL_BROKER_AVAILABLE = True
except ImportError:
    TOOL_BROKER_AVAILABLE = False
    ToolBroker = None  # type: ignore
    ToolResult = None  # type: ignore
    ToolType = None  # type: ignore
    ToolAnalysis = None  # type: ignore
    RAGConfig = None  # type: ignore
    RetrievalMode = None  # type: ignore
    logger.warning("Tool broker module not available")

# Import agent executor for autonomous tasks
try:
    from .agent_executor import (
        AgentExecutor,
        AgentExecutionResult,
        AgentStep,
        AgentAction,
        AgentStatus,
        AGENT_TIER_LIMITS,
    )
    AGENT_EXECUTOR_AVAILABLE = True
except ImportError:
    AGENT_EXECUTOR_AVAILABLE = False
    AgentExecutor = None  # type: ignore
    AgentExecutionResult = None  # type: ignore
    logger.warning("Agent executor module not available")

# Import RLHF feedback store for RAG context enhancement
try:
    from .rlhf.pinecone_feedback import (
        PineconeFeedbackStore,
        get_pinecone_feedback_store,
    )
    RLHF_FEEDBACK_AVAILABLE = True
except ImportError:
    RLHF_FEEDBACK_AVAILABLE = False
    PineconeFeedbackStore = None  # type: ignore
    get_pinecone_feedback_store = None  # type: ignore
    logger.debug("RLHF feedback store not available")

# Import local model provider and registry
try:
    from .providers import (
        LOCAL_MODEL_AVAILABLE,
        MODEL_REGISTRY_AVAILABLE,
    )
    if LOCAL_MODEL_AVAILABLE:
        from .providers.local_model import (
            LocalModelProvider,
            ChatLocalModelProvider,
            get_local_provider,
        )
    if MODEL_REGISTRY_AVAILABLE:
        from .providers.model_registry import (
            ModelRegistry,
            ModelInfo,
            ModelType,
            get_model_registry,
        )
except ImportError:
    LOCAL_MODEL_AVAILABLE = False
    MODEL_REGISTRY_AVAILABLE = False
    LocalModelProvider = None  # type: ignore
    ModelRegistry = None  # type: ignore
    logger.warning("Local model provider not available")

# Import prompt diffusion components
try:
    from .orchestration.prompt_diffusion import (
        PromptDiffusion,
        DiffusionResult,
        RefinerRole,
    )
    PROMPT_DIFFUSION_AVAILABLE = True
except ImportError:
    PROMPT_DIFFUSION_AVAILABLE = False
    PromptDiffusion = None  # type: ignore
    DiffusionResult = None  # type: ignore
    logger.warning("Prompt diffusion module not available")

# Optional knowledge base for prompt enrichment (gated by feature flag)
KNOWLEDGE_BASE_AVAILABLE = False
get_knowledge_base = None  # type: ignore
RecordType = None  # type: ignore

if FEATURE_FLAGS_AVAILABLE and is_feature_enabled(FeatureFlags.VECTOR_MEMORY):
    try:
        from .knowledge.pinecone_kb import get_knowledge_base, RecordType
        KNOWLEDGE_BASE_AVAILABLE = True
        logger.info("Pinecone knowledge base enabled via feature flag")
    except Exception as e:
        logger.warning("Knowledge base import failed: %s", e)
else:
    logger.debug("Vector memory feature disabled or feature flags unavailable")

# Import answer store for cross-session reuse
ANSWER_STORE_AVAILABLE = False
try:
    if FEATURE_FLAGS_AVAILABLE and is_feature_enabled(FeatureFlags.CROSS_SESSION_REUSE):
        from .learning.answer_store import get_answer_store, StoredAnswer
        ANSWER_STORE_AVAILABLE = True
        logger.info("Answer store enabled for cross-session reuse")
except ImportError as e:
    logger.debug("Answer store not available: %s", e)

# Import consensus manager components
try:
    from .orchestration.consensus_manager import (
        ConsensusManager,
        ConsensusResult,
        ConsensusStrategy,
    )
    CONSENSUS_AVAILABLE = True
except ImportError:
    CONSENSUS_AVAILABLE = False
    ConsensusManager = None  # type: ignore
    ConsensusResult = None  # type: ignore
    logger.warning("Consensus manager module not available")

# Import refinement loop components
try:
    from .orchestration.refinement_loop import (
        RefinementLoopController,
        RefinementResult,
        RefinementConfig,
        RefinementStrategy,
        LoopStatus,
    )
    REFINEMENT_LOOP_AVAILABLE = True
except ImportError:
    REFINEMENT_LOOP_AVAILABLE = False
    RefinementLoopController = None  # type: ignore
    RefinementResult = None  # type: ignore
    logger.warning("Refinement loop module not available")

# Import shared memory components
try:
    from .memory.shared_memory import (
        SharedMemoryManager,
        SharedMemoryEntry,
        AccessLevel,
        MemoryCategory,
        get_shared_memory_manager,
    )
    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    SHARED_MEMORY_AVAILABLE = False
    SharedMemoryManager = None  # type: ignore
    get_shared_memory_manager = None  # type: ignore
    logger.warning("Shared memory module not available")

# Import live data components
try:
    from .services.live_data import (
        LiveDataManager,
        LiveDataTool,
        get_live_data_manager,
    )
    LIVE_DATA_AVAILABLE = True
except ImportError:
    LIVE_DATA_AVAILABLE = False
    LiveDataManager = None  # type: ignore
    LiveDataTool = None  # type: ignore
    logger.warning("Live data module not available")

# Import billing enforcement components
try:
    from .billing.enforcement import (
        SubscriptionEnforcer,
        EnforcementResult,
        create_enforcement_error,
    )
    from .billing.metering import (
        UsageMeter,
        UsageType,
        get_usage_meter,
        get_cost_estimator,
    )
    from .billing.usage import UsageTracker
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
    SubscriptionEnforcer = None  # type: ignore
    EnforcementResult = None  # type: ignore
    UsageMeter = None  # type: ignore
    get_usage_meter = None  # type: ignore
    logger.warning("Billing module not available")

# Import dialogue system components
try:
    from .dialogue import (
        DialogueManager,
        DialogueResult,
        DialogueState,
        get_dialogue_manager,
    )
    from .dialogue.ambiguity import AmbiguityDetector, detect_ambiguity
    from .dialogue.clarification import ClarificationHandler, CLARIFICATION_SYSTEM_PROMPT
    from .dialogue.suggestions import SuggestionEngine, SUGGESTION_SYSTEM_PROMPT
    from .dialogue.scheduler import TaskScheduler, get_task_scheduler
    DIALOGUE_AVAILABLE = True
except ImportError:
    DIALOGUE_AVAILABLE = False
    DialogueManager = None  # type: ignore
    get_dialogue_manager = None  # type: ignore
    logger.warning("Dialogue system module not available")

# Import Stage 3 upgrades
try:
    from .orchestration.stage3_upgrades import (
        PronounResolver,
        CompoundQueryHandler,
        AdaptiveRetryHandler,
        EnhancedInjectionDetector,
        Stage3Logger,
        MultiModalGate,
        create_pronoun_resolver,
        create_compound_handler,
        create_injection_detector,
        create_adaptive_retry_handler,
        create_stage3_logger,
        create_multimodal_gate,
    )
    STAGE3_AVAILABLE = True
except ImportError:
    STAGE3_AVAILABLE = False
    PronounResolver = None  # type: ignore
    CompoundQueryHandler = None  # type: ignore
    AdaptiveRetryHandler = None  # type: ignore
    EnhancedInjectionDetector = None  # type: ignore
    Stage3Logger = None  # type: ignore
    MultiModalGate = None  # type: ignore
    logger.warning("Stage 3 upgrades module not available")

# Import prompt injection defense
try:
    from .security.hardening import check_prompt_injection
    INJECTION_DEFENSE_AVAILABLE = True
except ImportError:
    INJECTION_DEFENSE_AVAILABLE = False
    check_prompt_injection = None  # type: ignore
    logger.warning("Prompt injection defense not available")

# Import provider types
try:
    from .providers.gemini import GeminiProvider
    GEMINI_AVAILABLE = True
except ImportError as e:
    GEMINI_AVAILABLE = False
    GeminiProvider = None  # type: ignore
    logger.warning("Gemini provider not available: %s", e)

# Import stub provider as fallback
STUB_AVAILABLE = False
StubProvider = None
try:
    # Try various import paths for stub provider
    from .models.stub_provider import StubProvider
    STUB_AVAILABLE = True
except ImportError:
    try:
        from ..models.stub_provider import StubProvider
        STUB_AVAILABLE = True
    except ImportError:
        try:
            # Create a minimal stub provider class
            class StubProvider:
                def __init__(self):
                    self.name = 'stub'
                def generate(self, prompt, **kwargs):
                    class Result:
                        text = f'Stub response for: {prompt[:50]}...'
                        content = f'Stub response for: {prompt[:50]}...'
                        model = 'stub'
                    return Result()
                async def complete(self, prompt, **kwargs):
                    """Async complete method for compatibility with refinement loop."""
                    return self.generate(prompt, **kwargs)
            STUB_AVAILABLE = True
        except Exception:
            pass

# Import orchestration artifacts
try:
    from .models.orchestration import OrchestrationArtifacts
except ImportError:
    OrchestrationArtifacts = None  # type: ignore


# Module-level LLMResult class for use across methods
class LLMResult:
    """Result from an LLM generation request."""
    
    def __init__(
        self,
        content: str,
        model: str,
        tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        cost_info: Optional[Dict[str, Any]] = None,
        generation_id: Optional[str] = None,
    ):
        self.content = content
        self.model = model
        self.tokens_used = tokens
        self.metadata = metadata or {}
        self.cost_info = cost_info or {}
        self.generation_id = generation_id
    
    def __repr__(self):
        return f"LLMResult(model={self.model}, tokens={self.tokens_used}, content_len={len(self.content)}, cost_info={bool(self.cost_info)})"


class Orchestrator:
    """
    Main orchestrator class for LLMHive.
    
    Provides unified interface for LLM provider management and orchestration.
    Supports:
    - Hierarchical Role Management (HRM) for complex queries
    - Adaptive model routing based on performance
    - Multi-model ensemble orchestration
    - Deep consensus through debate
    """
    
    def __init__(self):
        """Initialize orchestrator with available providers."""
        self.providers: Dict[str, Any] = {}
        self.mcp_client = None  # MCP client (optional)
        
        # Initialize HRM planner and executor if available
        self.hrm_planner: Optional[Any] = None
        self.hrm_executor: Optional[Any] = None
        if HRM_AVAILABLE and HierarchicalPlanner:
            self.hrm_planner = HierarchicalPlanner()
            logger.info("HRM planner initialized")
            # Executor will be initialized later when providers are available
        
        # Initialize adaptive router if available
        self.adaptive_router: Optional[Any] = None
        if ADAPTIVE_ROUTING_AVAILABLE:
            self.adaptive_router = get_adaptive_router()
            logger.info("Adaptive router initialized")
        
        # Initialize memory manager if available
        self.memory_manager: Optional[Any] = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = get_persistent_memory()
                logger.info("Memory manager initialized")
            except Exception as e:
                logger.warning("Failed to initialize memory manager: %s", e)
        
        # Initialize fact checker if available and enabled
        self.fact_checker: Optional[Any] = None
        if FACT_CHECK_AVAILABLE and FactChecker and is_feature_enabled(FeatureFlags.FACT_VERIFICATION):
            try:
                self.fact_checker = FactChecker(
                    memory_manager=self.memory_manager,
                    max_verification_iterations=2,
                )
                logger.info("Fact checker initialized (FACT_VERIFICATION enabled)")
            except Exception as e:
                logger.warning("Failed to initialize fact checker: %s", e)
        elif FACT_CHECK_AVAILABLE and FactChecker:
            logger.debug("Fact checker available but FACT_VERIFICATION feature disabled")
        
        # Initialize guardrails if available
        self.safety_validator: Optional[Any] = None
        self.tier_controller: Optional[Any] = None
        if GUARDRAILS_AVAILABLE:
            try:
                self.safety_validator = get_safety_validator()
                self.tier_controller = get_tier_controller()
                logger.info("Security guardrails initialized")
            except Exception as e:
                logger.warning("Failed to initialize guardrails: %s", e)
        
        # Initialize tool broker if available
        self.tool_broker: Optional[Any] = None
        if TOOL_BROKER_AVAILABLE:
            try:
                self.tool_broker = get_tool_broker()
                # Set memory manager for knowledge lookup
                if self.memory_manager:
                    self.tool_broker.memory_manager = self.memory_manager
                
                # PR4: Configure external APIs from environment
                import os
                self.tool_broker.configure_external_apis(
                    serpapi_key=os.getenv("SERPAPI_API_KEY"),
                    tavily_key=os.getenv("TAVILY_API_KEY"),
                    browserless_key=os.getenv("BROWSERLESS_API_KEY"),
                    wolframalpha_key=os.getenv("WOLFRAMALPHA_API_KEY"),
                )
                
                logger.info("Tool broker initialized with %d tools", len(self.tool_broker.list_tools()))
            except Exception as e:
                logger.warning("Failed to initialize tool broker: %s", e)
        
        # Initialize agent executor for autonomous tasks
        self.agent_executor: Optional[Any] = None
        if AGENT_EXECUTOR_AVAILABLE and AgentExecutor:
            try:
                # Will be fully initialized when providers are available
                self.agent_executor = None  # Lazy init with providers
                logger.info("Agent executor module available")
            except Exception as e:
                logger.warning("Failed to initialize agent executor: %s", e)
        
        # Prompt diffusion will be initialized after providers
        self.prompt_diffusion: Optional[Any] = None
        
        # Initialize providers from environment variables
        self._initialize_providers()
        
        # Initialize prompt diffusion after providers are ready
        if PROMPT_DIFFUSION_AVAILABLE and PromptDiffusion:
            try:
                kb = get_knowledge_base() if KNOWLEDGE_BASE_AVAILABLE and get_knowledge_base else None
                self.prompt_diffusion = PromptDiffusion(
                    providers=self.providers,
                    max_rounds=5,
                    convergence_threshold=0.9,
                    knowledge_base=kb,
                )
                logger.info("Prompt diffusion initialized")
            except Exception as e:
                logger.warning("Failed to initialize prompt diffusion: %s", e)
        
        # Initialize consensus manager after providers are ready
        self.consensus_manager: Optional[Any] = None
        if CONSENSUS_AVAILABLE and ConsensusManager:
            try:
                self.consensus_manager = ConsensusManager(
                    providers=self.providers,
                    performance_tracker=performance_tracker if PERFORMANCE_TRACKER_AVAILABLE else None,
                    max_debate_rounds=3,
                    consensus_threshold=0.75,
                )
                logger.info("Consensus manager initialized")
            except Exception as e:
                logger.warning("Failed to initialize consensus manager: %s", e)
        
        # Initialize refinement loop controller after providers are ready
        self.refinement_controller: Optional[Any] = None
        if REFINEMENT_LOOP_AVAILABLE and RefinementLoopController:
            try:
                refinement_config = RefinementConfig(
                    max_iterations=3,
                    convergence_threshold=0.90,
                    min_improvement_threshold=0.05,
                    enable_prompt_refinement=True,
                    enable_model_switching=True,
                )
                self.refinement_controller = RefinementLoopController(
                    fact_checker=self.fact_checker,
                    prompt_diffusion=self.prompt_diffusion if hasattr(self, 'prompt_diffusion') else None,
                    providers=self.providers,
                    memory_manager=self.memory_manager,
                    config=refinement_config,
                )
                logger.info("Refinement loop controller initialized")
            except Exception as e:
                logger.warning("Failed to initialize refinement controller: %s", e)
        
        # Initialize shared memory manager
        self.shared_memory: Optional[Any] = None
        if SHARED_MEMORY_AVAILABLE and get_shared_memory_manager:
            try:
                self.shared_memory = get_shared_memory_manager()
                logger.info("Shared memory manager initialized")
            except Exception as e:
                logger.warning("Failed to initialize shared memory: %s", e)
        
        # Initialize answer store for cross-session reuse
        self.answer_store: Optional[Any] = None
        if ANSWER_STORE_AVAILABLE:
            try:
                self.answer_store = get_answer_store()
                logger.info("Answer store initialized for cross-session reuse")
            except Exception as e:
                logger.warning("Failed to initialize answer store: %s", e)
        
        # Initialize live data manager
        self.live_data: Optional[Any] = None
        if LIVE_DATA_AVAILABLE and get_live_data_manager:
            try:
                self.live_data = get_live_data_manager()
                logger.info("Live data manager initialized")
            except Exception as e:
                logger.warning("Failed to initialize live data manager: %s", e)
        
        # Initialize dialogue manager for clarifications and suggestions
        self.dialogue_manager: Optional[Any] = None
        if DIALOGUE_AVAILABLE and get_dialogue_manager:
            try:
                self.dialogue_manager = get_dialogue_manager()
                logger.info("Dialogue manager initialized")
            except Exception as e:
                logger.warning("Failed to initialize dialogue manager: %s", e)
        
        # Initialize Stage 3 components
        self.pronoun_resolver: Optional[Any] = None
        self.compound_handler: Optional[Any] = None
        self.injection_detector: Optional[Any] = None
        self.adaptive_retry: Optional[Any] = None
        self.stage3_logger: Optional[Any] = None
        self.multimodal_gate: Optional[Any] = None
        
        if STAGE3_AVAILABLE:
            try:
                # Pronoun resolver with shared memory
                self.pronoun_resolver = create_pronoun_resolver(self.shared_memory)
                
                # Compound query handler for multi-fact retrieval
                self.compound_handler = create_compound_handler()
                
                # Enhanced injection detector
                self.injection_detector = create_injection_detector(block_threshold="medium")
                
                # Adaptive retry handler with consensus manager
                self.adaptive_retry = create_adaptive_retry_handler(
                    providers=self.providers,
                    consensus_manager=self.consensus_manager,
                )
                
                # Stage 3 logger for instrumentation
                self.stage3_logger = create_stage3_logger()
                
                # Multimodal gate for tier-based feature access
                self.multimodal_gate = create_multimodal_gate(self.stage3_logger)
                
                logger.info("Stage 3 production upgrades initialized")
            except Exception as e:
                logger.warning("Failed to initialize Stage 3 components: %s", e)
        
        logger.info(f"Orchestrator initialized with {len(self.providers)} provider(s)")
    
    def _initialize_providers(self) -> None:
        """Initialize LLM providers based on available API keys.
        
        Provider Priority (Dec 2025):
        1. OpenRouter (PRIMARY) - Access to 400+ models with single API key
        2. Direct providers (FALLBACK) - OpenAI, Anthropic, etc. as backup
        """
        import os
        
        # =================================================================
        # 1. OPENROUTER PROVIDER (PRIMARY - Access to ALL 400+ models)
        # =================================================================
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                from .openrouter.client import OpenRouterClient, OpenRouterConfig
                
                openrouter_config = OpenRouterConfig.from_env()
                openrouter_client = OpenRouterClient(openrouter_config)
                
                class OpenRouterProvider:
                    """OpenRouter provider - PRIMARY provider for all model inference.
                    
                    Routes requests to 400+ models through OpenRouter's unified API.
                    """
                    
                    ORCHESTRATION_KWARGS = {
                        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
                        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
                        'session_id', 'user_id', 'user_tier', 'enable_tools',
                        'knowledge_snippets', 'context', 'plan', 'db_session',
                        'skip_injection_check', 'history',  # Internal orchestration params
                    }
                    
                    def __init__(self, client: OpenRouterClient):
                        self.name = 'openrouter'
                        self.client = client
                        self._initialized = False
                    
                    async def _ensure_client(self):
                        if not self._initialized:
                            await self.client._ensure_client()
                            self._initialized = True
                    
                    # System prompt to prevent models from asking clarifying questions
                    SYSTEM_PROMPT = """You are a helpful assistant that answers questions directly and completely.

CRITICAL RULES:
1. NEVER ask clarifying questions. Answer directly with your best interpretation.
2. If the user asks for a list/ranking (e.g., "top 10 fastest"), provide that list immediately.
3. Do NOT ask about criteria, preferences, or alternatives. Just answer.
4. "Fastest" means top speed. "Best" means a reasonable ranking. "Top 10" means provide 10 items.
5. If you're unsure about interpretation, pick the most reasonable one and answer.

The user wants an answer, not questions. Provide helpful, direct responses."""

                    async def generate(self, prompt: str, model: str = "openai/gpt-4o", **kwargs):
                        """Generate response using OpenRouter API."""
                        try:
                            await self._ensure_client()
                            
                            api_kwargs = {
                                k: v for k, v in kwargs.items() 
                                if k not in self.ORCHESTRATION_KWARGS
                            }
                            
                            # Include system prompt to prevent clarifying questions
                            messages = [
                                {"role": "system", "content": self.SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ]
                            
                            response = await self.client.chat_completion(
                                model=model,
                                messages=messages,
                                **api_kwargs
                            )
                            
                            class Result:
                                def __init__(self, text, model_name, tokens, cost_info=None, generation_id=None):
                                    self.content = text
                                    self.text = text
                                    self.model = model_name
                                    self.tokens_used = tokens
                                    self.cost_info = cost_info or {}
                                    self.generation_id = generation_id
                            
                            content = ""
                            if response.get("choices") and len(response["choices"]) > 0:
                                choice = response["choices"][0]
                                if choice.get("message"):
                                    # Handle both missing key and null value
                                    raw_content = choice["message"].get("content")
                                    content = raw_content if raw_content is not None else ""
                            
                            usage = response.get("usage", {})
                            total_tokens = usage.get("total_tokens", 0)
                            prompt_tokens = usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("completion_tokens", 0)
                            if not total_tokens:
                                total_tokens = prompt_tokens + completion_tokens
                            
                            # Extract cost tracking information from OpenRouter response
                            # OpenRouter includes cost in the usage section
                            generation_id = response.get("id")
                            cost_info = {
                                "generation_id": generation_id,
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": total_tokens,
                                "model_used": response.get("model", model),
                                "provider": "openrouter",
                            }
                            
                            # OpenRouter may include direct cost data
                            if "native_tokens_prompt" in usage:
                                cost_info["native_prompt_tokens"] = usage.get("native_tokens_prompt", 0)
                            if "native_tokens_completion" in usage:
                                cost_info["native_completion_tokens"] = usage.get("native_tokens_completion", 0)
                            
                            # Calculate estimated cost in USD using OpenRouter pricing
                            # Typical rates (per 1M tokens):
                            # - Premium models: $2-15 prompt, $5-30 completion
                            # - Free models: $0 (subsidized)
                            # For accurate costs, we estimate based on model tier
                            model_lower = model.lower()
                            if any(x in model_lower for x in ["deepseek", "qwen", "gemma", "llama", "gemini-flash"]):
                                # Free tier models - $0 cost
                                estimated_cost_usd = 0.0
                            elif any(x in model_lower for x in ["gpt-5", "claude-opus", "o3", "gpt-4"]):
                                # Premium models - estimate ~$10/1M average
                                estimated_cost_usd = (prompt_tokens * 5 + completion_tokens * 15) / 1_000_000
                            elif any(x in model_lower for x in ["claude-sonnet", "gpt-4o"]):
                                # Mid-tier models - estimate ~$3/1M average
                                estimated_cost_usd = (prompt_tokens * 1 + completion_tokens * 3) / 1_000_000
                            else:
                                # Default estimate
                                estimated_cost_usd = (prompt_tokens * 2 + completion_tokens * 8) / 1_000_000
                            
                            cost_info["total_cost"] = estimated_cost_usd
                            cost_info["cost_usd"] = estimated_cost_usd
                            
                            return Result(
                                text=content,
                                model_name=response.get("model", model),
                                tokens=total_tokens,
                                cost_info=cost_info,
                                generation_id=generation_id
                            )
                            
                        except Exception as e:
                            error_str = str(e).lower()
                            is_rate_limit = (
                                "429" in error_str
                                or "rate limit" in error_str
                                or "rate limited" in error_str
                                or "request failed after retries" in error_str
                            )
                            logger.error(f"OpenRouter API error for model {model}: {e}")
                            # Fallback to Together.ai only on rate limit (backup path)
                            if is_rate_limit:
                                try:
                                    from .providers.together_client import get_together_client
                                    together_client = get_together_client()
                                    if together_client:
                                        model_lower = model.lower()
                                        if "qwen" in model_lower:
                                            together_model = "together/Qwen/Qwen2.5-72B-Instruct-Turbo"
                                        elif "405" in model_lower:
                                            together_model = "together/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
                                        elif "8b" in model_lower:
                                            together_model = "together/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
                                        else:
                                            together_model = "together/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
                                        logger.warning(
                                            "OpenRouter rate limit; falling back to Together.ai model %s",
                                            together_model,
                                        )
                                        fallback_text = await together_client.generate_with_retry(
                                            prompt,
                                            model=together_model,
                                            temperature=kwargs.get("temperature", 0.7),
                                            max_tokens=kwargs.get("max_tokens", 2048),
                                        )
                                        if fallback_text:
                                            return Result(
                                                text=fallback_text,
                                                model_name=together_model,
                                                tokens=0,
                                                cost_info={"provider": "together", "fallback": True},
                                                generation_id=None,
                                            )
                                except Exception as fallback_error:
                                    logger.warning("Together.ai fallback failed: %s", fallback_error)
                            raise
                    
                    async def complete(self, prompt: str, model: str = "openai/gpt-4o", **kwargs):
                        return await self.generate(prompt, model=model, **kwargs)
                    
                    def supports_model(self, model_id: str) -> bool:
                        return "/" in model_id
                
                self.providers["openrouter"] = OpenRouterProvider(openrouter_client)
                logger.info("✓ OpenRouter provider initialized (PRIMARY - 400+ models)")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenRouter provider: {e}")
        else:
            logger.warning("⚠️ OPENROUTER_API_KEY not set - using direct providers only")
        
        # =================================================================
        # 2. DIRECT PROVIDERS (FALLBACK)
        # =================================================================
        
        # Initialize OpenAI provider (FALLBACK)
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                class OpenAIProvider:
                    # Orchestration kwargs to filter out (not valid for OpenAI API)
                    ORCHESTRATION_KWARGS = {
                        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
                        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
                        'session_id', 'user_id', 'user_tier', 'enable_tools',
                        'knowledge_snippets', 'context', 'plan', 'db_session',
                        'skip_injection_check', 'history',  # Internal orchestration params
                    }
                    
                    # System prompt to prevent models from asking clarifying questions
                    SYSTEM_PROMPT = """You are a helpful assistant that answers questions directly and completely.

CRITICAL RULES:
1. NEVER ask clarifying questions. Answer directly with your best interpretation.
2. If the user asks for a list/ranking (e.g., "top 10 fastest"), provide that list immediately.
3. Do NOT ask about criteria, preferences, or alternatives. Just answer.
4. "Fastest" means top speed. "Best" means a reasonable ranking. "Top 10" means provide 10 items.
5. If you're unsure about interpretation, pick the most reasonable one and answer.

The user wants an answer, not questions. Provide helpful, direct responses."""
                    
                    def __init__(self, client):
                        self.name = 'openai'
                        self.client = client
                    
                    async def generate(self, prompt, model="gpt-4o-mini", **kwargs):
                        """Generate response using OpenAI API."""
                        try:
                            # Strip provider prefix (e.g., "openai/gpt-4o" -> "gpt-4o")
                            api_model = model.split("/")[-1] if "/" in model else model
                            
                            # Filter out orchestration-specific kwargs
                            api_kwargs = {
                                k: v for k, v in kwargs.items() 
                                if k not in self.ORCHESTRATION_KWARGS
                            }
                            response = self.client.chat.completions.create(
                                model=api_model,
                                messages=[
                                    {"role": "system", "content": self.SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt}
                                ],
                                **api_kwargs
                            )
                            class Result:
                                def __init__(self, text, model, tokens):
                                    self.content = text
                                    self.text = text
                                    self.model = model
                                    self.tokens_used = tokens
                            
                            return Result(
                                text=response.choices[0].message.content,
                                model=response.model,
                                tokens=response.usage.total_tokens if hasattr(response, 'usage') else 0
                            )
                        except Exception as e:
                            logger.error(f"OpenAI API error: {e}")
                            raise
                    
                    async def complete(self, prompt, model="gpt-4o-mini", **kwargs):
                        """Alias for generate() - used by orchestration components."""
                        return await self.generate(prompt, model=model, **kwargs)
                
                self.providers["openai"] = OpenAIProvider(client)
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Initialize Grok provider
        if os.getenv("GROK_API_KEY"):
            try:
                import httpx
                api_key = os.getenv("GROK_API_KEY")
                
                class GrokProvider:
                    # Orchestration kwargs to filter out (not valid for Grok API)
                    ORCHESTRATION_KWARGS = {
                        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
                        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
                        'session_id', 'user_id', 'user_tier', 'enable_tools',
                        'knowledge_snippets', 'context', 'plan', 'db_session',
                        'skip_injection_check', 'history',  # Internal orchestration params
                    }
                    
                    # System prompt to prevent models from asking clarifying questions
                    SYSTEM_PROMPT = """You are a helpful assistant that answers questions directly and completely.

CRITICAL RULES:
1. NEVER ask clarifying questions. Answer directly with your best interpretation.
2. If the user asks for a list/ranking (e.g., "top 10 fastest"), provide that list immediately.
3. Do NOT ask about criteria, preferences, or alternatives. Just answer.
4. "Fastest" means top speed. "Best" means a reasonable ranking. "Top 10" means provide 10 items.
5. If you're unsure about interpretation, pick the most reasonable one and answer.

The user wants an answer, not questions. Provide helpful, direct responses."""
                    
                    def __init__(self, api_key):
                        self.name = 'grok'
                        self.api_key = api_key
                        self.base_url = "https://api.x.ai/v1"
                    
                    async def generate(self, prompt, model="grok-2", **kwargs):
                        """Generate response using Grok (xAI) API."""
                        try:
                            # Strip provider prefix (e.g., "x-ai/grok-4" -> "grok-4")
                            api_model = model.split("/")[-1] if "/" in model else model
                            
                            # Filter out orchestration-specific kwargs
                            api_kwargs = {
                                k: v for k, v in kwargs.items() 
                                if k not in self.ORCHESTRATION_KWARGS
                            }
                            async with httpx.AsyncClient() as client:
                                response = await client.post(
                                    f"{self.base_url}/chat/completions",
                                    headers={
                                        "Authorization": f"Bearer {self.api_key}",
                                        "Content-Type": "application/json"
                                    },
                                    json={
                                        "model": api_model,
                                        "messages": [
                                            {"role": "system", "content": self.SYSTEM_PROMPT},
                                            {"role": "user", "content": prompt}
                                        ],
                                        **api_kwargs
                                    },
                                    timeout=30.0
                                )
                                response.raise_for_status()
                                data = response.json()
                                
                                class Result:
                                    def __init__(self, text, model, tokens):
                                        self.content = text
                                        self.text = text
                                        self.model = model
                                        self.tokens_used = tokens
                                
                                return Result(
                                    text=data["choices"][0]["message"]["content"],
                                    model=data.get("model", model),
                                    tokens=data.get("usage", {}).get("total_tokens", 0)
                                )
                        except Exception as e:
                            logger.error(f"Grok API error: {e}")
                            raise
                    
                    async def complete(self, prompt, model="grok-2", **kwargs):
                        """Alias for generate() - used by orchestration components."""
                        return await self.generate(prompt, model=model, **kwargs)
                
                self.providers["grok"] = GrokProvider(api_key)
                logger.info("Grok provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok provider: {e}")
        
        # Initialize Gemini provider
        if os.getenv("GEMINI_API_KEY") and GEMINI_AVAILABLE:
            try:
                self.providers["gemini"] = GeminiProvider(api_key=os.getenv("GEMINI_API_KEY"))
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")
        
        # Initialize Anthropic provider using httpx directly (SDK has connection issues in Cloud Run)
        # Support both ANTHROPIC_API_KEY and CLAUDE_API_KEY
        claude_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if claude_key:
            try:
                import httpx
                
                # Strip any whitespace/newlines from the API key (secrets sometimes have trailing newlines)
                anthropic_api_key = claude_key.strip()
                
                class AnthropicProvider:
                    """Anthropic provider using httpx for reliable async connections."""
                    
                    # Model mapping for Claude models (handles all formats)
                    MODEL_MAPPING = {
                        # Full OpenRouter IDs
                        "anthropic/claude-sonnet-4": "claude-sonnet-4-20250514",
                        "anthropic/claude-opus-4": "claude-opus-4-20250514",
                        "anthropic/claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
                        "anthropic/claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
                        # Short names
                        "claude-sonnet-4.5": "claude-sonnet-4-20250514",
                        "claude-sonnet-4": "claude-sonnet-4-20250514",
                        "claude-opus-4": "claude-opus-4-20250514",
                        "claude-haiku-4": "claude-3-5-haiku-20241022",
                        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
                        "claude-3-5-haiku": "claude-3-5-haiku-20241022",
                        "claude-3-sonnet": "claude-3-5-sonnet-20241022",
                        "claude-3-haiku": "claude-3-5-haiku-20241022",
                        "claude-sonnet": "claude-3-5-sonnet-20241022",
                        "claude-haiku": "claude-3-5-haiku-20241022",
                    }
                    
                    # Kwargs to filter out
                    ORCHESTRATION_KWARGS = {
                        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
                        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
                        'session_id', 'user_id', 'user_tier', 'enable_tools',
                        'knowledge_snippets', 'context', 'plan', 'db_session',
                        'skip_injection_check', 'history',  # Internal orchestration params
                    }
                    
                    # System prompt to prevent models from asking clarifying questions
                    SYSTEM_PROMPT = """You are a helpful assistant that answers questions directly and completely.

CRITICAL RULES:
1. NEVER ask clarifying questions. Answer directly with your best interpretation.
2. If the user asks for a list/ranking (e.g., "top 10 fastest"), provide that list immediately.
3. Do NOT ask about criteria, preferences, or alternatives. Just answer.
4. "Fastest" means top speed. "Best" means a reasonable ranking. "Top 10" means provide 10 items.
5. If you're unsure about interpretation, pick the most reasonable one and answer.

The user wants an answer, not questions. Provide helpful, direct responses."""
                    
                    def __init__(self, api_key):
                        self.name = 'anthropic'
                        self.api_key = api_key
                        self.base_url = "https://api.anthropic.com/v1/messages"
                    
                    def _map_model(self, model):
                        """Map UI model names to actual Claude model names."""
                        return self.MODEL_MAPPING.get(model.lower(), model)
                    
                    async def generate(self, prompt, model="claude-3-5-haiku-20241022", **kwargs):
                        """Generate response using Anthropic API via httpx."""
                        # Filter out orchestration kwargs
                        api_kwargs = {k: v for k, v in kwargs.items() if k not in self.ORCHESTRATION_KWARGS}
                        
                        # Map model name
                        actual_model = self._map_model(model)
                        logger.info("Anthropic calling model: %s (mapped from %s)", actual_model, model)
                        
                        try:
                            async with httpx.AsyncClient(timeout=60.0) as client:
                                response = await client.post(
                                    self.base_url,
                                    headers={
                                        "x-api-key": self.api_key,
                                        "anthropic-version": "2023-06-01",
                                        "content-type": "application/json",
                                    },
                                    json={
                                        "model": actual_model,
                                        "max_tokens": api_kwargs.get('max_tokens', 2048),
                                        "system": self.SYSTEM_PROMPT,  # Anthropic uses 'system' field
                                        "messages": [{"role": "user", "content": prompt}]
                                    }
                                )
                                response.raise_for_status()
                                data = response.json()
                                
                            class Result:
                                def __init__(self, text, model, tokens):
                                    self.content = text
                                    self.text = text
                                    self.model = model
                                    self.tokens_used = tokens
                            
                            return Result(
                                text=data["content"][0]["text"],
                                model=data.get("model", actual_model),
                                tokens=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                            )
                        except Exception as e:
                            logger.error(f"Anthropic API error: {e}")
                            raise
                    
                    async def complete(self, prompt, model="claude-3-5-haiku-20241022", **kwargs):
                        """Alias for generate() - used by orchestration components."""
                        return await self.generate(prompt, model=model, **kwargs)
                
                self.providers["anthropic"] = AnthropicProvider(anthropic_api_key)
                logger.info("Anthropic provider initialized (httpx)")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        # Initialize DeepSeek provider
        if os.getenv("DEEPSEEK_API_KEY"):
            try:
                import httpx
                
                # Strip any whitespace/newlines from the API key
                deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
                
                class DeepSeekProvider:
                    """DeepSeek provider using httpx (OpenAI-compatible API)."""
                    
                    # Model mapping (handles all formats)
                    MODEL_MAPPING = {
                        # Full OpenRouter IDs
                        "deepseek/deepseek-v3.2": "deepseek-chat",
                        "deepseek/deepseek-chat": "deepseek-chat",
                        "deepseek/deepseek-r1-0528": "deepseek-reasoner",
                        # Short names
                        "deepseek-v3.2": "deepseek-chat",
                        "deepseek-v3": "deepseek-chat",
                        "deepseek-chat": "deepseek-chat",
                        "deepseek-coder": "deepseek-coder",
                        "deepseek-reasoner": "deepseek-reasoner",
                        "deepseek-r1-0528": "deepseek-reasoner",
                    }
                    
                    # Kwargs to filter out
                    ORCHESTRATION_KWARGS = {
                        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
                        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
                        'session_id', 'user_id', 'user_tier', 'enable_tools',
                        'knowledge_snippets', 'context', 'plan', 'db_session',
                        'skip_injection_check', 'history',  # Internal orchestration params
                    }
                    
                    # System prompt to prevent models from asking clarifying questions
                    SYSTEM_PROMPT = """You are a helpful assistant that answers questions directly and completely.

CRITICAL RULES:
1. NEVER ask clarifying questions. Answer directly with your best interpretation.
2. If the user asks for a list/ranking (e.g., "top 10 fastest"), provide that list immediately.
3. Do NOT ask about criteria, preferences, or alternatives. Just answer.
4. "Fastest" means top speed. "Best" means a reasonable ranking. "Top 10" means provide 10 items.
5. If you're unsure about interpretation, pick the most reasonable one and answer.

The user wants an answer, not questions. Provide helpful, direct responses."""
                    
                    def __init__(self, api_key):
                        self.name = 'deepseek'
                        self.api_key = api_key
                        self.base_url = "https://api.deepseek.com/chat/completions"
                    
                    def _map_model(self, model):
                        """Map UI model names to actual DeepSeek model names."""
                        return self.MODEL_MAPPING.get(model.lower(), "deepseek-chat")
                    
                    async def generate(self, prompt, model="deepseek-chat", **kwargs):
                        """Generate response using DeepSeek API."""
                        # Filter out orchestration kwargs
                        api_kwargs = {k: v for k, v in kwargs.items() if k not in self.ORCHESTRATION_KWARGS}
                        
                        # Map model name
                        actual_model = self._map_model(model)
                        logger.info("DeepSeek calling model: %s", actual_model)
                        
                        try:
                            async with httpx.AsyncClient(timeout=60.0) as client:
                                response = await client.post(
                                    self.base_url,
                                    headers={
                                        "Authorization": f"Bearer {self.api_key}",
                                        "Content-Type": "application/json",
                                    },
                                    json={
                                        "model": actual_model,
                                        "messages": [
                                            {"role": "system", "content": self.SYSTEM_PROMPT},
                                            {"role": "user", "content": prompt}
                                        ],
                                        "max_tokens": api_kwargs.get('max_tokens', 2048),
                                    }
                                )
                                response.raise_for_status()
                                data = response.json()
                                
                            class Result:
                                def __init__(self, text, model, tokens):
                                    self.content = text
                                    self.text = text
                                    self.model = model
                                    self.tokens_used = tokens
                            
                            return Result(
                                text=data["choices"][0]["message"]["content"],
                                model=data.get("model", actual_model),
                                tokens=data.get("usage", {}).get("total_tokens", 0)
                            )
                        except Exception as e:
                            logger.error(f"DeepSeek API error: {e}")
                            raise
                    
                    async def complete(self, prompt, model="deepseek-chat", **kwargs):
                        """Alias for generate() - used by orchestration components."""
                        return await self.generate(prompt, model=model, **kwargs)
                
                self.providers["deepseek"] = DeepSeekProvider(deepseek_api_key)
                logger.info("DeepSeek provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek provider: {e}")

        # Initialize Together.ai provider
        if os.getenv("TOGETHERAI_API_KEY") or os.getenv("TOGETHER_API_KEY"):
            try:
                from .providers.together_client import get_together_client, TogetherClient
                together_client = get_together_client()

                if together_client:
                    class TogetherProvider:
                        """Together.ai direct provider (backup/complement)."""

                        ORCHESTRATION_KWARGS = {
                            'use_hrm', 'use_adaptive_routing', 'use_deep_consensus',
                            'use_prompt_diffusion', 'use_memory', 'accuracy_level',
                            'session_id', 'user_id', 'user_tier', 'enable_tools',
                            'knowledge_snippets', 'context', 'plan', 'db_session',
                            'skip_injection_check', 'history',
                        }

                        def __init__(self, client: TogetherClient):
                            self.name = 'together'
                            self.client = client

                        async def generate(self, prompt: str, model: str = TogetherClient.DEFAULT_MODEL, **kwargs):
                            api_kwargs = {
                                k: v for k, v in kwargs.items()
                                if k not in self.ORCHESTRATION_KWARGS
                            }
                            text = await self.client.generate(prompt, model=model, **api_kwargs)
                            class Result:
                                def __init__(self, text, model_name):
                                    self.content = text
                                    self.text = text
                                    self.model = model_name
                                    self.tokens_used = 0
                            return Result(text=text, model_name=model)

                        async def complete(self, prompt: str, model: str = TogetherClient.DEFAULT_MODEL, **kwargs):
                            return await self.generate(prompt, model=model, **kwargs)

                        def supports_model(self, model_id: str) -> bool:
                            return "meta-llama/" in model_id or "Qwen/" in model_id

                    self.providers["together"] = TogetherProvider(together_client)
                    logger.info("Together.ai provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Together.ai provider: {e}")
        
        # Always add stub provider as fallback
        if STUB_AVAILABLE and StubProvider:
            try:
                self.providers["stub"] = StubProvider()
                logger.info("Stub provider initialized (fallback)")
            except Exception as e:
                logger.warning(f"Failed to instantiate StubProvider: {e}, creating minimal stub")
                self._create_minimal_stub()
        else:
            # Create minimal stub if import failed
            self._create_minimal_stub()
        
        # Initialize local model provider if configured
        self._initialize_local_models()
    
    def _initialize_local_models(self) -> None:
        """Initialize local model provider if configured."""
        if not LOCAL_MODEL_AVAILABLE:
            logger.info("Local model provider not available")
            return
        
        local_model = os.getenv("LLMHIVE_LOCAL_MODEL")
        if local_model:
            try:
                use_4bit = os.getenv("LLMHIVE_LOCAL_USE_4BIT", "true").lower() == "true"
                
                local_provider = ChatLocalModelProvider(
                    model_name=local_model,
                    use_4bit=use_4bit,
                )
                
                self.providers["local"] = local_provider
                logger.info("Local model provider initialized: %s (4bit=%s)", local_model, use_4bit)
            except Exception as e:
                logger.warning(f"Failed to initialize local model provider: {e}")
        
        # Initialize model registry
        self.model_registry: Optional[Any] = None
        if MODEL_REGISTRY_AVAILABLE:
            try:
                self.model_registry = get_model_registry()
                logger.info("Model registry initialized with %d models", len(self.model_registry._models))
            except Exception as e:
                logger.warning(f"Failed to initialize model registry: {e}")
    
    def register_local_model(
        self,
        model_id: str,
        model_path: str,
        *,
        domains: Optional[List[str]] = None,
        use_4bit: bool = True,
        preload: bool = False,
    ) -> bool:
        """
        Register and optionally load a local/fine-tuned model.
        
        Args:
            model_id: Unique identifier for the model
            model_path: HuggingFace model ID or local path
            domains: List of domains the model specializes in
            use_4bit: Use 4-bit quantization
            preload: Load model immediately
            
        Returns:
            True if successful
        """
        if not LOCAL_MODEL_AVAILABLE:
            logger.error("Local model provider not available")
            return False
        
        try:
            # Register in model registry
            if self.model_registry:
                self.model_registry.register(
                    model_id=model_id,
                    model_name=model_path,
                    model_type=ModelType.FINE_TUNED if os.path.isdir(model_path) else ModelType.LOCAL,
                    provider="local",
                    model_path=model_path,
                    domains=domains or ["general"],
                    use_4bit=use_4bit,
                )
            
            # Create provider
            provider = ChatLocalModelProvider(
                model_name=model_path,
                use_4bit=use_4bit,
            )
            
            if preload:
                provider.load_model()
            
            self.providers[model_id] = provider
            logger.info("Registered local model: %s", model_id)
            return True
            
        except Exception as e:
            logger.error("Failed to register local model %s: %s", model_id, e)
            return False
    
    async def generate_with_local(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Generate using a local model (for sensitive/offline queries).
        
        Args:
            prompt: Input prompt
            model_id: Specific local model ID (uses default if not specified)
            **kwargs: Generation parameters
            
        Returns:
            LLMResult-like object
        """
        # Find local provider
        provider = None
        
        if model_id and model_id in self.providers:
            provider = self.providers[model_id]
        elif "local" in self.providers:
            provider = self.providers["local"]
        else:
            # Try to find any local provider
            for name, p in self.providers.items():
                if hasattr(p, 'model_name') and hasattr(p, 'load_model'):
                    provider = p
                    break
        
        if not provider:
            raise ValueError("No local model provider available")
        
        # Generate
        result = await provider.generate(prompt, **kwargs)
        
        return LLMResult(
            content=result.content,
            model=result.model,
            tokens=result.tokens_used,
            metadata={
                "provider": "local",
                "generation_time_ms": result.generation_time_ms,
            },
        )
    
    def get_models_for_domain(
        self,
        domain: str,
        include_local: bool = True,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get best models for a domain.
        
        Args:
            domain: Domain name (e.g., "coding", "medical")
            include_local: Include local/fine-tuned models
            limit: Maximum models to return
            
        Returns:
            List of model info dicts
        """
        if not self.model_registry:
            return []
        
        models = self.model_registry.get_models_for_domain(
            domain,
            limit=limit,
            include_local=include_local,
        )
        
        return [
            {
                "id": m.model_id,
                "name": m.model_name,
                "type": m.model_type.value,
                "provider": m.provider,
                "priority": m.priority,
                "domains": m.domains,
            }
            for m in models
        ]
    
    def _create_minimal_stub(self) -> None:
        """Create a minimal stub provider."""
        class MinimalStub:
            def __init__(self):
                self.name = 'stub'
            def generate(self, prompt, **kwargs):
                class Result:
                    def __init__(self):
                        self.text = f'Stub response for: {prompt[:50]}...'
                        self.model = 'stub'
                return Result()
        
        self.providers["stub"] = MinimalStub()
        logger.warning("Using minimal stub provider (StubProvider import failed)")
    
    # =========================================================================
    # PR3: Verification Fallback Logic
    # =========================================================================
    
    # High-accuracy models ordered by preference.
    # NOTE: These are fallback defaults only. The orchestrator now dynamically
    # fetches high-accuracy models from the OpenRouter rankings DB for categories:
    # science, health, legal, finance, academia.
    # This list is used only when the dynamic catalog is unavailable.
    FALLBACK_HIGH_ACCURACY_MODELS = [
        ("openai", "gpt-4o"),           # General accuracy
        ("openai", "gpt-4o-2024-11-20"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openai", "o1"),                # Reasoning model
        ("openai", "o3"),                # Latest reasoning
        ("deepseek", "deepseek-chat"),
        ("google", "gemini-2.5-pro"),
    ]
    
    # Cached dynamic high-accuracy models
    _cached_high_accuracy_models: Optional[List[Tuple[str, str]]] = None
    _high_accuracy_models_fetched_at: Optional[float] = None
    HIGH_ACCURACY_CACHE_TTL = 3600  # 1 hour cache
    
    async def retry_with_high_accuracy(
        self,
        prompt: str,
        previous_response: str,
        verification_report: Optional[Any] = None,
        *,
        context: Optional[str] = None,
        excluded_models: Optional[List[str]] = None,
        max_retries: int = 2,
    ) -> Tuple[Any, bool]:
        """
        PR3: Retry with a high-accuracy model when verification fails.
        
        This method is called when initial verification fails. It:
        1. Selects a high-accuracy model different from the one that failed
        2. Constructs an enhanced prompt with verification feedback
        3. Generates a new response with stricter accuracy instructions
        4. Re-verifies the new response
        
        Args:
            prompt: Original user prompt
            previous_response: Response that failed verification
            verification_report: VerificationReport from the failed attempt
            context: Additional context to include
            excluded_models: Models to exclude (e.g., the one that failed)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (LLMResult, verification_passed: bool)
        """
        excluded_models = excluded_models or []
        
        # Construct enhanced prompt with verification feedback
        enhanced_prompt = self._build_high_accuracy_prompt(
            prompt=prompt,
            previous_response=previous_response,
            verification_report=verification_report,
            context=context,
        )
        
        # Find available high-accuracy model (use async version for fresh data)
        selected_model, selected_provider = await self._select_high_accuracy_model_async(
            excluded_models=excluded_models
        )
        
        if not selected_model or not selected_provider:
            logger.warning("No high-accuracy model available for retry")
            # Return original result with failed verification
            return LLMResult(
                content=previous_response,
                model="unknown",
                tokens=0,
                metadata={"retry_failed": True, "reason": "no_high_accuracy_model_available"},
            ), False
        
        logger.info(
            "PR3: Retrying with high-accuracy model %s after verification failure",
            selected_model
        )
        
        # Retry with high-accuracy model
        try:
            result = await selected_provider.generate(
                enhanced_prompt,
                model=selected_model,
            )
            
            new_result = LLMResult(
                content=result.content if hasattr(result, 'content') else result.text,
                model=selected_model,
                tokens=getattr(result, 'tokens_used', 0),
                metadata={
                    "retry_with_high_accuracy": True,
                    "original_response_length": len(previous_response),
                },
            )
            
            # Re-verify the new response
            new_verification_passed = True
            
            if FACT_CHECK_AVAILABLE and self.fact_checker:
                try:
                    new_verification_report = await self.fact_checker.verify(
                        new_result.content,
                        prompt=prompt,
                    )
                    new_verification_passed = (
                        new_verification_report.is_valid if hasattr(new_verification_report, 'is_valid') 
                        else new_verification_report.verification_score >= 0.7
                    )
                    
                    logger.info(
                        "PR3: High-accuracy retry verification: passed=%s, score=%.2f",
                        new_verification_passed,
                        new_verification_report.verification_score,
                    )
                    
                    # If still failing and have retries left, use refinement loop
                    if not new_verification_passed and max_retries > 1:
                        logger.info("PR3: Triggering refinement loop for further improvement")
                        
                        if REFINEMENT_LOOP_AVAILABLE and self.refinement_controller:
                            refinement_result = await self.refinement_controller.run_refinement_loop(
                                answer=new_result.content,
                                prompt=prompt,
                                model=selected_model,
                                context=context,
                                available_models=[m for p, m in self.HIGH_ACCURACY_MODELS 
                                                  if p in self.providers and m not in excluded_models][:3],
                            )
                            
                            if refinement_result.final_answer != new_result.content:
                                new_result = LLMResult(
                                    content=refinement_result.final_answer,
                                    model=selected_model,
                                    tokens=getattr(result, 'tokens_used', 0),
                                    metadata={
                                        "retry_with_high_accuracy": True,
                                        "refinement_iterations": len(refinement_result.iterations),
                                        "final_score": refinement_result.final_verification_score,
                                    },
                                )
                            
                            new_verification_passed = (
                                refinement_result.final_status == LoopStatus.PASSED or
                                refinement_result.final_verification_score >= 0.7
                            )
                            
                except Exception as e:
                    logger.warning("PR3: Re-verification failed: %s", e)
            
            return new_result, new_verification_passed
            
        except Exception as e:
            logger.error("PR3: High-accuracy retry failed: %s", e)
            return LLMResult(
                content=previous_response,
                model="unknown",
                tokens=0,
                metadata={"retry_failed": True, "reason": str(e)},
            ), False
    
    def _build_high_accuracy_prompt(
        self,
        prompt: str,
        previous_response: str,
        verification_report: Optional[Any],
        context: Optional[str],
    ) -> str:
        """Build an enhanced prompt for high-accuracy retry."""
        
        # Extract verification issues if available
        issues_text = ""
        if verification_report:
            items = getattr(verification_report, 'items', [])
            failed_claims = [
                f"- {item.text[:100]}: {item.evidence[:100] if item.evidence else 'unverified'}"
                for item in items
                if not getattr(item, 'verified', True)
            ][:5]
            
            if failed_claims:
                issues_text = "\n".join(failed_claims)
        
        enhanced_prompt = f"""IMPORTANT: A previous response to this query failed fact-checking verification.
Please provide a highly accurate, well-researched response. Be especially careful about:
1. Factual accuracy - verify all claims before including them
2. Avoiding speculation or unverified information
3. Citing sources or acknowledging uncertainty where appropriate
4. Correcting any errors from the previous attempt

"""
        
        if issues_text:
            enhanced_prompt += f"""The following specific claims from the previous response could not be verified:
{issues_text}

"""
        
        if context:
            enhanced_prompt += f"""Context:
{context}

"""
        
        enhanced_prompt += f"""Original question:
{prompt}

Please provide an accurate, well-verified response."""
        
        return enhanced_prompt
    
    async def _get_high_accuracy_models(self) -> List[Tuple[str, str]]:
        """Get high-accuracy models from rankings DB or cache.
        
        Fetches top models from high-stakes categories:
        - science, health, legal, finance, academia
        
        Returns list of (provider, model_id) tuples ordered by rank.
        Falls back to FALLBACK_HIGH_ACCURACY_MODELS if DB unavailable.
        """
        import time
        
        # Check cache
        now = time.time()
        if (self._cached_high_accuracy_models is not None and 
            self._high_accuracy_models_fetched_at is not None and
            now - self._high_accuracy_models_fetched_at < self.HIGH_ACCURACY_CACHE_TTL):
            return self._cached_high_accuracy_models
        
        try:
            from .openrouter.dynamic_catalog import get_high_accuracy_models
            
            # Fetch from dynamic catalog (use task_type and max_count params)
            models = await get_high_accuracy_models(task_type="general", max_count=10)
            
            if models:
                result = []
                for m in models:
                    # FIX 1.3: Handle both string (model_id) and dict formats
                    # get_high_accuracy_models returns List[str] of model IDs
                    if isinstance(m, str):
                        model_id = m
                    elif isinstance(m, dict):
                        model_id = m.get("id", "")
                    else:
                        logger.warning("Unexpected model type in catalog: %s", type(m))
                        continue
                    
                    # Extract provider from model_id (e.g., "openai/gpt-4o" -> "openai")
                    if "/" in model_id:
                        provider = model_id.split("/")[0]
                        result.append((provider, model_id))
                    else:
                        # Try to infer provider from model_id pattern
                        model_lower = model_id.lower()
                        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower or "o4" in model_lower:
                            result.append(("openai", model_id))
                        elif "claude" in model_lower:
                            result.append(("anthropic", model_id))
                        elif "gemini" in model_lower:
                            result.append(("google", model_id))
                        else:
                            result.append(("openrouter", model_id))
                
                # Cache result
                self._cached_high_accuracy_models = result
                self._high_accuracy_models_fetched_at = now
                logger.debug("Fetched %d high-accuracy models from dynamic catalog", len(result))
                return result
        
        except Exception as e:
            logger.warning("Failed to fetch high-accuracy models from catalog: %s", e)
        
        # Fallback to static list
        return self.FALLBACK_HIGH_ACCURACY_MODELS
    
    def _select_high_accuracy_model(
        self,
        excluded_models: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Optional[Any]]:
        """Select the best available high-accuracy model (sync version).
        
        Note: This method is synchronous for backward compatibility.
        For async usage, call _get_high_accuracy_models() directly.
        """
        excluded_models = excluded_models or []
        
        # Use cached models if available, otherwise fallback
        models_to_try = (
            self._cached_high_accuracy_models 
            if self._cached_high_accuracy_models 
            else self.FALLBACK_HIGH_ACCURACY_MODELS
        )
        
        for provider_name, model_name in models_to_try:
            if model_name in excluded_models:
                continue
            
            provider = self.providers.get(provider_name)
            if provider:
                return model_name, provider
            
            # Also try openrouter for non-local providers
            openrouter = self.providers.get("openrouter")
            if openrouter:
                return model_name, openrouter
        
        # Fallback: try any available provider with their default model
        for provider_name, provider in self.providers.items():
            if provider_name == "stub":
                continue
            
            # Return with provider's default high-accuracy model
            if provider_name == "openai":
                return "gpt-4o", provider
            elif provider_name == "anthropic":
                return "claude-3-5-sonnet-20241022", provider
            elif provider_name == "google":
                return "gemini-2.5-pro", provider
            elif provider_name == "openrouter":
                return "openai/gpt-4o", provider
        
        return None, None
    
    async def _select_high_accuracy_model_async(
        self,
        excluded_models: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Optional[Any]]:
        """Async version of _select_high_accuracy_model.
        
        Fetches fresh models from the dynamic catalog before selecting.
        """
        # Refresh cache
        await self._get_high_accuracy_models()
        
        # Use sync version with fresh cache
        return self._select_high_accuracy_model(excluded_models)
    
    async def invoke_refinement_loop(
        self,
        answer: str,
        prompt: str,
        *,
        model: str = "default",
        context: Optional[str] = None,
        max_iterations: int = 3,
        convergence_threshold: float = 0.9,
    ) -> Tuple[str, bool, Optional[Any]]:
        """
        PR3: Programmatically invoke the refinement loop.
        
        This is a convenience method for external callers who want to
        trigger the refinement loop directly (e.g., from the API layer).
        
        Args:
            answer: Initial answer to refine
            prompt: Original prompt
            model: Model that generated the answer
            context: Additional context
            max_iterations: Maximum refinement iterations
            convergence_threshold: Score threshold for passing
            
        Returns:
            Tuple of (final_answer, passed, RefinementResult)
        """
        if not REFINEMENT_LOOP_AVAILABLE or not self.refinement_controller:
            logger.warning("PR3: Refinement loop not available")
            return answer, False, None
        
        try:
            # Update controller config for this call
            original_max_iters = self.refinement_controller.config.max_iterations
            original_threshold = self.refinement_controller.config.convergence_threshold
            
            self.refinement_controller.config.max_iterations = max_iterations
            self.refinement_controller.config.convergence_threshold = convergence_threshold
            
            # Run the loop
            refinement_result = await self.refinement_controller.run_refinement_loop(
                answer=answer,
                prompt=prompt,
                model=model,
                context=context,
            )
            
            # Restore config
            self.refinement_controller.config.max_iterations = original_max_iters
            self.refinement_controller.config.convergence_threshold = original_threshold
            
            passed = (
                refinement_result.final_status == LoopStatus.PASSED or
                refinement_result.final_verification_score >= convergence_threshold
            )
            
            return refinement_result.final_answer, passed, refinement_result
            
        except Exception as e:
            logger.error("PR3: Refinement loop invocation failed: %s", e)
            return answer, False, None
    
    async def orchestrate(
        self,
        prompt: str,
        models: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate LLM calls across multiple models.
        
        Args:
            prompt: The prompt to send to models
            models: List of model names to use (optional)
            **kwargs: Additional orchestration parameters including:
                - use_hrm: Enable hierarchical role management
                - use_adaptive_routing: Enable adaptive model selection
                - use_deep_consensus: Enable multi-round debate
                - use_prompt_diffusion: Enable prompt refinement
                - accuracy_level: 1-5 slider for accuracy vs speed
            
        Returns:
            ProtocolResult-like object with final_response, initial_responses, etc.
        """
        # Extract orchestration settings
        use_hrm = kwargs.get("use_hrm", False)
        use_adaptive_routing = kwargs.get("use_adaptive_routing", False)
        use_deep_consensus = kwargs.get("use_deep_consensus", False)
        use_prompt_diffusion = kwargs.get("use_prompt_diffusion", False)
        use_memory = kwargs.get("use_memory", True)  # Memory enabled by default
        accuracy_level = kwargs.get("accuracy_level", 3)
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id", "default")
        
        logger.info(
            "Orchestrating request: hrm=%s, adaptive=%s, consensus=%s, memory=%s, accuracy=%d",
            use_hrm, use_adaptive_routing, use_deep_consensus, use_memory, accuracy_level
        )
        
        # Initialize scratchpad for this query
        scratchpad = Scratchpad() if MEMORY_AVAILABLE and Scratchpad else None
        
        # Import/define ProtocolResult early for use in early returns
        # LLMResult is already defined at module level (line ~407)
        try:
            from .protocols.base import ProtocolResult as _ProtocolResult
            ProtocolResult = _ProtocolResult
        except ImportError:
            ProtocolResult = None
        
        # Define ProtocolResult fallback if import failed
        if ProtocolResult is None:
            class ProtocolResult:
                def __init__(self, final_response, initial_responses=None, critiques=None, 
                           improvements=None, consensus_notes=None, step_outputs=None,
                           supporting_notes=None, quality_assessments=None, suggestions=None):
                    self.final_response = final_response
                    self.initial_responses = initial_responses or []
                    self.critiques = critiques or []
                    self.improvements = improvements or []
                    self.consensus_notes = consensus_notes or []
                    self.step_outputs = step_outputs or {}
                    self.supporting_notes = supporting_notes or []
                    self.quality_assessments = quality_assessments or {}
                    self.suggestions = suggestions or []
        
        # Helper function to wrap early returns in ProtocolResult
        def _make_early_return(result: Any, notes: List[str] = None) -> Any:
            """Wrap an LLMResult in a ProtocolResult for consistent return structure."""
            return ProtocolResult(
                final_response=result,
                initial_responses=[result],
                critiques=[],
                improvements=[],
                consensus_notes=notes or [],
                step_outputs={"answer": [result]},
                supporting_notes=[],
                suggestions=[],
                quality_assessments={},
            )
        
        # Stage 3: Enhanced Prompt Injection Defense (Phase -1.5)
        # Note: skip_injection_check may be set to True if the caller (e.g., orchestrator_adapter)
        # has already checked the RAW user prompt. This is important because 'prompt' here may
        # be an enhanced/system prompt containing instructions like "act as a planner" which
        # would falsely trigger injection detection.
        skip_injection_check = kwargs.get("skip_injection_check", False)
        if self.injection_detector and STAGE3_AVAILABLE and not skip_injection_check:
            try:
                injection_check = self.injection_detector.check(prompt)
                if injection_check.should_block:
                    logger.warning(
                        "Prompt injection BLOCKED: threat=%s",
                        injection_check.threat_level
                    )
                    if self.stage3_logger:
                        self.stage3_logger.log_injection_attempt(
                            injection_check.threat_level, blocked=True
                        )
                    
                    early_result = LLMResult(
                        content=self.injection_detector.get_safe_refusal(),
                        model="security_filter",
                        tokens=0,
                    )
                    return _make_early_return(early_result, ["Prompt injection blocked"])
                elif injection_check.is_injection:
                    # Log but don't block lower-threat injections
                    if self.stage3_logger:
                        self.stage3_logger.log_injection_attempt(
                            injection_check.threat_level, blocked=False
                        )
            except Exception as e:
                logger.warning("Injection detection failed: %s", e)
        
        # Stage 3: Pronoun Resolution (Phase -1.3)
        pronoun_resolutions = []
        if self.pronoun_resolver and STAGE3_AVAILABLE and user_id:
            try:
                history = kwargs.get("history", [])
                resolved_prompt, resolutions = await self.pronoun_resolver.resolve(
                    query=prompt,
                    user_id=user_id,
                    session_id=session_id,
                    history=history,
                )
                if resolutions:
                    pronoun_resolutions = resolutions
                    prompt = resolved_prompt
                    logger.info("Resolved %d pronouns: %s", len(resolutions), resolutions)
                    if scratchpad:
                        scratchpad.write("pronoun_resolutions", resolutions)
                    if self.stage3_logger:
                        for res in resolutions:
                            parts = res.split(" → ")
                            if len(parts) == 2:
                                self.stage3_logger.log_pronoun_resolution(
                                    parts[0].strip("'"), parts[1].strip("'"), True
                                )
            except Exception as e:
                logger.warning("Pronoun resolution failed: %s", e)
        
        # Phase -1: Security - Input validation and tier checks
        use_guardrails = kwargs.get("use_guardrails", True)
        is_external_model = kwargs.get("is_external_model", True)
        security_issues: List[str] = []
        
        if use_guardrails and GUARDRAILS_AVAILABLE and self.safety_validator:
            try:
                # Check tier-based restrictions
                if self.tier_controller:
                    tier_allowed, tier_reason = self.tier_controller.enforce_tier_restrictions(
                        prompt, user_tier=kwargs.get("user_tier", "free")
                    )
                    if not tier_allowed:
                        logger.warning("Tier restriction: %s", tier_reason)
                        # Return early with tier restriction message
                        early_result = LLMResult(
                            content=tier_reason or "This query is not available for your tier.",
                            model="guardrails",
                            tokens=0,
                        )
                        return _make_early_return(early_result, ["Tier restriction applied"])
                
                # Validate input and sanitize
                sanitized_query, is_allowed, rejection_reason = self.safety_validator.validate_input(
                    prompt, user_tier=kwargs.get("user_tier", "free")
                )
                
                if not is_allowed:
                    logger.warning("Query blocked by guardrails: %s", rejection_reason)
                    early_result = LLMResult(
                        content=rejection_reason or "I cannot process this request due to safety policies.",
                        model="guardrails",
                        tokens=0,
                    )
                    return _make_early_return(early_result, ["Query blocked by guardrails"])
                
                # Use sanitized query if external model
                if is_external_model and sanitized_query != prompt:
                    logger.info("Input sanitized for external model (redacted PII)")
                    prompt = sanitized_query
                    if scratchpad:
                        scratchpad.write("original_prompt", kwargs.get("original_prompt", prompt))
                        scratchpad.write("sanitized_prompt", prompt)
                        scratchpad.write("input_sanitized", True)
                
            except Exception as e:
                logger.warning("Security validation failed: %s", e)
                security_issues.append(f"Security check error: {e}")
        
        # Phase -0.5: Billing Enforcement - Check subscription limits
        user_tier = kwargs.get("user_tier", "free")
        enforcement_passed = True
        
        if BILLING_AVAILABLE and user_id:
            try:
                # Get database session for enforcement check
                from .database import SessionLocal
                
                with SessionLocal() as db_session:
                    enforcer = SubscriptionEnforcer(db_session)
                    
                    # Estimate tokens for this request
                    estimated_tokens = len(prompt) // 4 + 500  # Rough estimate
                    
                    # Check enforcement
                    enforcement_result = enforcer.enforce_request(
                        user_id=user_id,
                        requested_models=len(models_to_use) if models_to_use else 1,
                        estimated_tokens=estimated_tokens,
                        protocol=kwargs.get("protocol"),
                        feature=kwargs.get("feature"),
                    )
                    
                    if not enforcement_result.allowed:
                        enforcement_passed = False
                        logger.warning(
                            "Billing enforcement blocked request: user=%s, reason=%s",
                            user_id,
                            enforcement_result.reason,
                        )
                        
                        # Return billing error response
                        error_message = enforcement_result.upgrade_message or enforcement_result.reason
                        early_result = LLMResult(
                            content=f"⚠️ {error_message}\n\nTo continue using LLMHive, please upgrade your subscription.",
                            model="billing_enforcement",
                            tokens=0,
                        )
                        return _make_early_return(early_result, ["Billing enforcement: subscription limit reached"])
                    
                    # Update user tier from subscription
                    user_tier = enforcement_result.tier_name
                    
                    if scratchpad:
                        scratchpad.write("user_tier", user_tier)
                        scratchpad.write("enforcement_passed", True)
                        
            except Exception as e:
                logger.warning("Billing enforcement check failed: %s", e)
                # Continue without enforcement on error (fail open)
        
        # Phase -0.3: Dialogue Pre-processing (clarification and schedule detection)
        use_dialogue = kwargs.get("use_dialogue", True)
        dialogue_result: Optional[Any] = None
        
        if use_dialogue and self.dialogue_manager and DIALOGUE_AVAILABLE:
            try:
                pre_result = await self.dialogue_manager.pre_process_query(
                    query=prompt,
                    session_id=session_id,
                    user_id=user_id,
                    check_ambiguity=True,
                    check_schedule=True,
                )
                
                if scratchpad:
                    scratchpad.write("dialogue_pre_processed", True)
                
                # Handle schedule requests
                if pre_result.is_schedule_request and pre_result.schedule_info:
                    logger.info("Schedule request detected: %s", pre_result.schedule_info.get("message"))
                    
                    # Return schedule confirmation directly
                    early_result = LLMResult(
                        content=pre_result.schedule_info.get("confirmation", "Reminder scheduled."),
                        model="dialogue_scheduler",
                        tokens=0,
                    )
                    return _make_early_return(early_result, ["Schedule request processed"])
                
                # Handle clarification requests
                if not pre_result.should_proceed and pre_result.needs_clarification:
                    logger.info("Clarification needed for query")
                    
                    # Return clarification question to user
                    early_result = LLMResult(
                        content=pre_result.clarification_question or "Could you please clarify your question?",
                        model="dialogue_clarification",
                        tokens=0,
                    )
                    return _make_early_return(early_result, ["Clarification requested"])
                
                # Use modified query if clarification was resolved
                if pre_result.context_added:
                    prompt = pre_result.modified_query
                    if scratchpad:
                        scratchpad.write("query_clarified", True)
                        scratchpad.write("clarified_query", prompt)
                
            except Exception as e:
                logger.warning("Dialogue pre-processing failed: %s", e)
        
        # Phase 0: Prompt Diffusion (optional pre-processing)
        # Auto-activate for complex/ambiguous queries when feature is enabled
        diffusion_result: Optional[Any] = None
        original_prompt = prompt  # Store original for transparency
        
        # Auto-detect if prompt diffusion should be activated
        auto_diffusion_reasons: List[str] = []
        if not use_prompt_diffusion and self.prompt_diffusion and PROMPT_DIFFUSION_AVAILABLE:
            # Check if query complexity warrants automatic diffusion
            prompt_lower = prompt.lower()
            word_count = len(prompt.split())
            
            # High complexity indicators (auto-activate)
            complexity_indicators = [
                word_count > 80,  # Long queries often need refinement
                prompt_lower.count("?") >= 3,  # Multiple questions
                "compare" in prompt_lower and "vs" in prompt_lower,  # Comparison queries
                any(kw in prompt_lower for kw in ["analyze", "evaluate", "assess", "critique"]),
                prompt_lower.count(",") >= 5,  # Multiple clauses
                accuracy_level >= 4,  # User wants high accuracy
            ]
            
            # Ambiguity indicators (needs clarification refinement)
            ambiguity_indicators = [
                "it" in prompt_lower.split()[:5] and "?" in prompt,  # Pronoun-heavy start
                any(vague in prompt_lower for vague in ["something like", "kind of", "maybe", "probably"]),
                "this" in prompt_lower.split()[:3] and len(prompt.split()) > 10,
            ]
            
            complexity_score = sum(complexity_indicators)
            ambiguity_score = sum(ambiguity_indicators)
            
            if complexity_score >= 2:
                use_prompt_diffusion = True
                auto_diffusion_reasons.append(f"high_complexity({complexity_score}/6)")
                logger.info("Auto-activating prompt diffusion: high complexity score %d", complexity_score)
            elif ambiguity_score >= 1 and word_count > 15:
                use_prompt_diffusion = True
                auto_diffusion_reasons.append(f"ambiguity_detected({ambiguity_score})")
                logger.info("Auto-activating prompt diffusion: ambiguity detected")
        
        if use_prompt_diffusion and self.prompt_diffusion and PROMPT_DIFFUSION_AVAILABLE:
            try:
                logger.info("Running prompt diffusion refinement")
                
                # Determine models for refinement
                diffusion_models = models_to_use[:2] if models_to_use else ["gpt-4o-mini"]
                
                # Run diffusion
                diffusion_result = await self.prompt_diffusion.diffuse(
                    initial_prompt=prompt,
                    models=diffusion_models,
                    context=kwargs.get("context"),
                    domain=kwargs.get("domain"),
                    analyze_ambiguity=kwargs.get("analyze_ambiguity", True),
                )
                
                # Use refined prompt
                if diffusion_result and diffusion_result.final_prompt != prompt:
                    logger.info(
                        "Prompt refined: %d rounds, convergence=%.2f, score=%.2f",
                        diffusion_result.rounds_completed,
                        diffusion_result.convergence_score,
                        diffusion_result.best_version.score,
                    )
                    prompt = diffusion_result.final_prompt
                    
                    if scratchpad:
                        scratchpad.write("original_prompt", original_prompt)
                        scratchpad.write("refined_prompt", prompt)
                        scratchpad.write("diffusion_rounds", diffusion_result.rounds_completed)
                        scratchpad.write("diffusion_convergence", diffusion_result.convergence_score)
                        scratchpad.write("diffusion_improvements", [
                            imp for v in diffusion_result.versions for imp in v.improvements
                        ])
                        if auto_diffusion_reasons:
                            scratchpad.write("auto_diffusion_reasons", auto_diffusion_reasons)
                
            except Exception as e:
                logger.warning("Prompt diffusion failed: %s", e)
                # Continue with original prompt
        
        # Phase 0.5: Shared Memory Retrieval (cross-session context)
        shared_memory_context = ""
        if self.shared_memory and SHARED_MEMORY_AVAILABLE and user_id:
            try:
                shared_memory_context = await self.shared_memory.build_context_string(
                    user_id=user_id,
                    session_id=session_id,
                    max_length=1000,
                )
                if shared_memory_context:
                    logger.info("Retrieved shared memory context (%d chars)", len(shared_memory_context))
                    if scratchpad:
                        scratchpad.write("shared_memory_used", True)
            except Exception as e:
                logger.warning("Shared memory retrieval failed: %s", e)
        
        # Phase 0.6: Live Data Retrieval (real-time information)
        live_data_context = ""
        use_live_data = kwargs.get("use_live_data", True)
        
        if use_live_data and self.live_data and LIVE_DATA_AVAILABLE:
            try:
                live_data_context = await self.live_data.get_context_for_query(
                    prompt,
                    max_feeds=3,
                )
                if live_data_context:
                    logger.info("Retrieved live data context (%d chars)", len(live_data_context))
                    if scratchpad:
                        scratchpad.write("live_data_used", True)
            except Exception as e:
                logger.warning("Live data retrieval failed: %s", e)
        
        # Phase 0.5: Cross-Session Reuse Check
        # Check if we have a high-quality cached answer for a similar query
        enable_cross_session = kwargs.get("enable_cross_session_reuse", True)
        if (enable_cross_session and ANSWER_STORE_AVAILABLE and 
            self.answer_store and FEATURE_FLAGS_AVAILABLE and 
            is_feature_enabled(FeatureFlags.CROSS_SESSION_REUSE)):
            try:
                similar_answers = self.answer_store.search_similar(
                    query=prompt,
                    user_id=user_id,
                    top_k=3,
                    min_relevance=0.85,  # High threshold for reuse
                )
                
                if similar_answers:
                    best_match = similar_answers[0]
                    if best_match.relevance_score >= 0.9:
                        logger.info(
                            "Cross-session reuse: Found cached answer (score=%.2f, reused=%d times)",
                            best_match.relevance_score,
                            best_match.times_reused,
                        )
                        
                        # Update reuse count
                        self.answer_store.mark_reused(best_match.id)
                        
                        if scratchpad:
                            scratchpad.write("cross_session_reuse", True)
                            scratchpad.write("cached_answer_id", best_match.id)
                            scratchpad.write("cached_relevance_score", best_match.relevance_score)
                        
                        # Return the cached answer
                        cached_result = LLMResult(
                            content=best_match.answer_text,
                            model="cached:" + (best_match.models_used[0] if best_match.models_used else "unknown"),
                            tokens=0,  # No tokens used for cached response
                        )
                        
                        return _make_early_return(
                            cached_result,
                            [f"Cross-session reuse: Answer from {best_match.created_at}"]
                        )
                        
            except Exception as e:
                logger.warning("Cross-session reuse check failed: %s", e)
        
        # Phase 1: Memory Retrieval (before model dispatch)
        memory_context = ""
        memory_hits = []
        if use_memory and self.memory_manager and MEMORY_AVAILABLE:
            try:
                memory_context, memory_hits = self.memory_manager.get_relevant_context(
                    query=prompt,
                    user_id=user_id,
                    max_context_length=2000,
                    top_k=3,
                )
                if memory_context:
                    logger.info(
                        "Memory retrieval: Found %d relevant memories (context: %d chars)",
                        len(memory_hits),
                        len(memory_context),
                    )
                    # Store memory hits in scratchpad for other agents
                    if scratchpad:
                        scratchpad.write("memory_hits", memory_hits)
                        scratchpad.write("memory_context", memory_context)
            except Exception as e:
                logger.warning("Memory retrieval failed: %s", e)
        
        # =====================================================================
        # PR4: Tool Analysis and Early Execution
        # =====================================================================
        # Analyze tool needs BEFORE model dispatch to get data for augmentation
        tool_context = ""
        early_tool_results: Dict[Any, Any] = {}
        enable_tools = kwargs.get("enable_tools", True)
        
        if enable_tools and self.tool_broker and TOOL_BROKER_AVAILABLE:
            try:
                # Analyze what tools the query needs
                tool_analysis = self.tool_broker.analyze_tool_needs(
                    query=prompt,
                    context=memory_context,
                    task_type=domain,
                )
                
                if tool_analysis.requires_tools:
                    logger.info(
                        "PR4: Tool analysis detected %d tool(s) needed: %s",
                        len(tool_analysis.tool_requests),
                        tool_analysis.trace,
                    )
                    
                    if scratchpad:
                        scratchpad.write("tool_analysis", {
                            "requires_tools": True,
                            "tools_identified": tool_analysis.trace,
                            "reasoning": tool_analysis.reasoning,
                        })
                    
                    # Execute tools in parallel (or sequential if dependencies)
                    early_tool_results = await self.tool_broker.execute_tools(
                        tool_analysis.tool_requests,
                        parallel=not tool_analysis.has_dependencies,
                    )
                    
                    # Format tool results for context augmentation
                    tool_context = self.tool_broker.format_tool_results(
                        early_tool_results,
                        include_failures=False,
                    )
                    
                    if tool_context:
                        logger.info(
                            "PR4: Tool execution complete. Context: %d chars",
                            len(tool_context)
                        )
                        
                        if scratchpad:
                            scratchpad.write("early_tool_execution", {
                                "tools_executed": list(early_tool_results.keys()),
                                "success_count": sum(1 for r in early_tool_results.values() if r.success),
                                "context_length": len(tool_context),
                            })
                
                # PR4: RAG retrieval mode decision
                rag_config = self.tool_broker.decide_retrieval_mode(
                    query=prompt,
                    context=memory_context,
                    accuracy_level=accuracy_level,
                )
                
                if rag_config.mode != RetrievalMode.NONE and self.tool_broker.memory_manager:
                    rag_chunks = await self.tool_broker.perform_rag_retrieval(
                        query=prompt,
                        config=rag_config,
                        namespace=user_id,
                    )
                    
                    if rag_chunks:
                        rag_context = "\n".join([
                            f"[Knowledge: {c.get('source', 'KB')}] {c['text']}"
                            for c in rag_chunks[:5]
                        ])
                        if tool_context:
                            tool_context = f"{tool_context}\n\n{rag_context}"
                        else:
                            tool_context = rag_context
                        
                        logger.info(
                            "PR4: RAG retrieval (mode=%s) returned %d chunks",
                            rag_config.mode.value,
                            len(rag_chunks),
                        )
                
                # PR5: RLHF Feedback Context - Learn from past successful answers
                if RLHF_FEEDBACK_AVAILABLE and is_feature_enabled(FeatureFlags.RLHF_FEEDBACK):
                    try:
                        feedback_store = get_pinecone_feedback_store()
                        # Get similar positive feedback examples
                        positive_examples = await feedback_store.find_similar_feedback(
                            query=prompt,
                            positive_only=True,
                            limit=2,
                            min_score=0.7,
                        )
                        
                        if positive_examples:
                            feedback_context = "[SIMILAR SUCCESSFUL ANSWERS - Use as reference style]\n"
                            for ex in positive_examples:
                                feedback_context += f"Q: {ex.query[:200]}...\nA: {ex.answer[:500]}...\n---\n"
                            
                            if tool_context:
                                tool_context = f"{tool_context}\n\n{feedback_context}"
                            else:
                                tool_context = feedback_context
                            
                            logger.info(
                                "PR5: RLHF feedback context added (%d positive examples)",
                                len(positive_examples),
                            )
                    except Exception as e:
                        logger.debug("PR5: RLHF feedback retrieval skipped: %s", e)
                    
            except Exception as e:
                logger.warning("PR4: Tool analysis/execution failed: %s", e)
                if scratchpad:
                    scratchpad.write("tool_analysis_error", str(e))
        
        # Build augmented prompt with all context sources
        context_parts = []
        
        # Add shared memory context (cross-session)
        if shared_memory_context:
            context_parts.append(shared_memory_context)
        
        # Add live data context (real-time)
        if live_data_context:
            context_parts.append(live_data_context)
        
        # Add memory context (session-specific)
        if memory_context:
            context_parts.append(memory_context)
        
        # PR4: Add tool context from early execution
        if tool_context:
            context_parts.append(f"[TOOL RESULTS]\n{tool_context}")
        
        # Build final augmented prompt
        augmented_prompt = prompt
        if context_parts:
            context_str = "\n".join(context_parts)
            augmented_prompt = f"{context_str}\nUser Query: {prompt}"
        
        # NOTE: ProtocolResult and LLMResult are defined at the start of this method
        # to ensure they're available for all early returns
        
        # Phase 1: Hierarchical Planning (if HRM enabled)
        hierarchical_plan = None
        if use_hrm and self.hrm_planner and HRM_AVAILABLE:
            try:
                hierarchical_plan = self.hrm_planner.plan_with_hierarchy(
                    augmented_prompt,  # Use augmented prompt with memory context
                    use_full_hierarchy=(accuracy_level >= 4)
                )
                logger.info(
                    "HRM plan created: %d steps, strategy=%s",
                    len(hierarchical_plan.steps),
                    hierarchical_plan.strategy
                )
                # Store plan in scratchpad
                if scratchpad:
                    scratchpad.write("hrm_plan", hierarchical_plan.strategy)
                    scratchpad.write("hrm_steps", len(hierarchical_plan.steps))
            except Exception as e:
                logger.warning("HRM planning failed, falling back to flat plan: %s", e)
        
        # Phase 2: Adaptive Model Selection
        # NEVER default to stub - use a real model as fallback
        default_fallback = ["openai/gpt-4o-mini"] if "openrouter" in self.providers else ["gpt-4o-mini"]
        selected_models = models or default_fallback
        model_assignments: Dict[str, str] = {}
        
        if use_adaptive_routing and self.adaptive_router and ADAPTIVE_ROUTING_AVAILABLE:
            try:
                # Get roles from HRM plan or use default
                if hierarchical_plan:
                    roles = [step.role.name for step in hierarchical_plan.steps]
                else:
                    roles = ["executor"]
                
                # Run adaptive selection (exclude stub - it's only a last resort fallback)
                available_models = [p for p in self.providers.keys() if p != "stub"]
                routing_result = self.adaptive_router.select_models_adaptive(
                    prompt,
                    roles,
                    accuracy_level,
                    available_models=available_models,
                )
                
                model_assignments = routing_result.role_assignments
                selected_models = [routing_result.primary_model] + routing_result.secondary_models
                
                logger.info(
                    "Adaptive routing: primary=%s, secondary=%s",
                    routing_result.primary_model,
                    routing_result.secondary_models,
                )
            except Exception as e:
                logger.warning("Adaptive routing failed, using default models: %s", e)
                selected_models = models or default_fallback
        else:
            selected_models = models or default_fallback
        
        # Ensure we have at least one model
        if not selected_models:
            selected_models = default_fallback
        
        models_to_use = selected_models
        
        # Map model names to provider names
        # PRIORITY: OpenRouter FIRST (400+ models), direct APIs as FALLBACK
        model_to_provider = {}
        openrouter_available = "openrouter" in self.providers
        
        for model in models_to_use:
            model_lower = model.lower()
            
            # Use OpenRouter for ALL models if available (PRIMARY)
            if openrouter_available:
                if "/" in model:
                    # Already in OpenRouter format (e.g., "openai/gpt-4o")
                    model_to_provider[model] = "openrouter"
                else:
                    # Route through OpenRouter regardless of model type
                    model_to_provider[model] = "openrouter"
            else:
                # FALLBACK: Direct providers only when OpenRouter unavailable
                if "gpt" in model_lower or "openai" in model_lower:
                    model_to_provider[model] = "openai"
                elif "claude" in model_lower or "anthropic" in model_lower:
                    model_to_provider[model] = "anthropic"
                elif "grok" in model_lower:
                    model_to_provider[model] = "grok"
                elif "gemini" in model_lower:
                    model_to_provider[model] = "gemini"
                elif "deepseek" in model_lower:
                    model_to_provider[model] = "deepseek"
                else:
                    model_to_provider[model] = model
        
        if openrouter_available:
            logger.info("Using OpenRouter as PRIMARY provider for %d models", len(models_to_use))
        
        # Consensus result tracking
        consensus_result: Optional[Any] = None
        hrm_execution_result: Optional[Any] = None
        
        # Phase 2.4: Critique-and-Improve Protocol for Complex Queries
        # If the query is complex and the feature is enabled, use multi-model critique
        use_critique_protocol = False
        if (is_feature_enabled(FeatureFlags.CRITIQUE_AND_IMPROVE) 
            and HRM_AVAILABLE 
            and is_complex_query 
            and accuracy_level >= 4):
            try:
                query_complexity = is_complex_query(augmented_prompt)
                if query_complexity:
                    use_critique_protocol = True
                    logger.info("Query identified as complex - enabling Critique-and-Improve protocol")
            except Exception as e:
                logger.debug("Complexity check failed: %s", e)
        
        # Execute Critique-and-Improve if triggered
        if use_critique_protocol:
            try:
                from .protocols import CritiqueAndImproveProtocol
                
                critique_protocol = CritiqueAndImproveProtocol(
                    providers=self.providers,
                    model_registry=self,  # Use self as a simple registry
                    planner=self.hrm_planner if use_hrm else None,
                    max_critique_rounds=2,
                    min_models=2,
                    max_models=min(len(models_to_use), 3),
                )
                
                protocol_result = await critique_protocol.execute(
                    prompt=prompt,
                    context=memory_context,
                    knowledge_snippets=None,
                    models=models_to_use[:3],
                    mode="accuracy" if accuracy_level >= 4 else "speed",
                )
                
                if protocol_result and protocol_result.final_response:
                    logger.info(
                        "Critique-and-Improve protocol completed: %d drafts, %d critiques",
                        len(protocol_result.initial_responses or []),
                        len(protocol_result.critiques or []),
                    )
                    
                    # Update scratchpad
                    if scratchpad:
                        scratchpad.write("protocol_used", "critique_and_improve")
                        scratchpad.write("critique_rounds", len(protocol_result.critiques or []))
                    
                    return protocol_result
            except Exception as e:
                logger.warning("Critique-and-Improve protocol failed, falling back: %s", e)
        
        # Phase 2.5: Hierarchical Plan Execution (if HRM enabled and plan exists)
        # This executes the multi-step reasoning chain before consensus or single model
        if hierarchical_plan and len(hierarchical_plan.steps) > 1 and HRM_AVAILABLE and execute_hierarchical_plan:
            logger.info(
                "Executing hierarchical plan: %d steps, strategy=%s",
                len(hierarchical_plan.steps),
                hierarchical_plan.strategy,
            )
            
            try:
                # Assign models to roles if we have model assignments
                if model_assignments and hasattr(self.hrm_planner, 'assign_models_to_roles'):
                    hierarchical_plan = self.hrm_planner.assign_models_to_roles(
                        hierarchical_plan,
                        model_assignments,
                    )
                
                # Execute the hierarchical plan
                hrm_execution_result = await execute_hierarchical_plan(
                    plan=hierarchical_plan,
                    providers=self.providers,
                    context=memory_context if memory_context else None,
                    accuracy_level=accuracy_level,
                    model_assignments=model_assignments,
                )
                
                # Check if execution was successful
                if hrm_execution_result and hrm_execution_result.success:
                    result = LLMResult(
                        content=hrm_execution_result.final_answer,
                        model=hrm_execution_result.final_model,
                        tokens=hrm_execution_result.total_tokens,
                    )
                    
                    # Store HRM execution info in scratchpad
                    if scratchpad:
                        scratchpad.write("hrm_execution_success", True)
                        scratchpad.write("hrm_steps_completed", hrm_execution_result.steps_completed)
                        scratchpad.write("hrm_total_latency_ms", hrm_execution_result.total_latency_ms)
                        scratchpad.write("hrm_transparency_notes", hrm_execution_result.transparency_notes)
                        
                        # Store step details
                        step_details = []
                        for step_result in hrm_execution_result.step_results:
                            step_details.append({
                                "step_id": step_result.step_id,
                                "role": step_result.role_name,
                                "model": step_result.model_used,
                                "status": step_result.status.value if hasattr(step_result.status, 'value') else str(step_result.status),
                                "tokens": step_result.tokens_used,
                                "latency_ms": step_result.latency_ms,
                            })
                        scratchpad.write("hrm_step_details", step_details)
                        
                        # Store blackboard summary
                        if hrm_execution_result.blackboard:
                            scratchpad.write("hrm_blackboard_summary", hrm_execution_result.blackboard.get_summary())
                    
                    # Store sub-answers for learning reuse
                    if KNOWLEDGE_BASE_AVAILABLE and get_knowledge_base and RecordType:
                        try:
                            kb = get_knowledge_base()
                            step_map = {s.step_id: s for s in getattr(hierarchical_plan, "steps", [])}
                            for step_result in hrm_execution_result.step_results:
                                status_val = getattr(step_result, "status", None)
                                status_str = getattr(status_val, "value", str(status_val))
                                if status_str not in {"COMPLETED", "StepStatus.COMPLETED"}:
                                    continue
                                if not getattr(step_result, "output", ""):
                                    continue
                                step_def = step_map.get(step_result.step_id)
                                sub_query = (
                                    step_def.goal
                                    or step_def.description
                                    or f"{step_result.role_name} sub-task"
                                    if step_def
                                    else f"{step_result.role_name} sub-task"
                                )
                                await kb.store_answer(
                                    query=sub_query[:500],
                                    answer=step_result.output,
                                    models_used=[step_result.model_used] if step_result.model_used else [],
                                    record_type=RecordType.PARTIAL_ANSWER,
                                    quality_score=getattr(step_result, "confidence", 0.0) or 0.0,
                                    domain=domain or "default",
                                    user_id=user_id,
                                )
                            
                            # Distill multi-agent outputs into reusable knowledge
                            distilled = []
                            for step_result in hrm_execution_result.step_results:
                                if getattr(step_result, "output", ""):
                                    distilled.append(f"{step_result.role_name}: {step_result.output}")
                            if distilled:
                                distilled_text = "\n".join(distilled[:6])
                                await kb.store_answer(
                                    query=f"Distilled knowledge for {original_prompt[:80]}",
                                    answer=distilled_text[:2000],
                                    models_used=[r.model_used for r in hrm_execution_result.step_results if r.model_used],
                                    record_type=RecordType.DOMAIN_KNOWLEDGE,
                                    quality_score=0.6,
                                    domain=domain or "default",
                                    user_id=user_id,
                                    metadata={"multi_agent_distilled": True},
                                )
                        except Exception as e:
                            logger.debug("Failed to store HRM sub-answers: %s", e)
                    
                    logger.info(
                        "Hierarchical execution complete: %d/%d steps, %d tokens, %.1fms",
                        hrm_execution_result.steps_completed,
                        len(hrm_execution_result.step_results),
                        hrm_execution_result.total_tokens,
                        hrm_execution_result.total_latency_ms,
                    )
                else:
                    logger.warning(
                        "Hierarchical execution incomplete, falling back to consensus/single model"
                    )
                    hrm_execution_result = None
                    
            except Exception as e:
                logger.error("Hierarchical execution failed: %s, falling back", e)
                hrm_execution_result = None
                if scratchpad:
                    scratchpad.write("hrm_execution_error", str(e))
        
        # Deep Consensus: Run multiple models in parallel and build consensus
        # Skip if hierarchical execution already succeeded
        if hrm_execution_result is None and use_deep_consensus and self.consensus_manager and CONSENSUS_AVAILABLE and len(models_to_use) > 1:
            logger.info("Using Deep Consensus with %d models", len(models_to_use))
            
            try:
                # Build consensus from multiple models
                consensus_result = await self.consensus_manager.build_consensus(
                    prompt=augmented_prompt,
                    models=models_to_use,
                    context=memory_context if memory_context else None,
                    accuracy_level=accuracy_level,
                )
                
                # Use consensus result
                result = LLMResult(
                    content=consensus_result.final_answer,
                    model=f"consensus({','.join(consensus_result.participating_models[:3])}...)" if len(consensus_result.participating_models) > 3 else f"consensus({','.join(consensus_result.participating_models)})",
                    tokens=sum(r.tokens for r in consensus_result.responses),
                )
                
                # Store consensus info in scratchpad
                if scratchpad:
                    scratchpad.write("consensus_strategy", consensus_result.strategy_used.value)
                    scratchpad.write("consensus_score", consensus_result.consensus_score.overall_score)
                    scratchpad.write("consensus_models", consensus_result.participating_models)
                    scratchpad.write("model_contributions", consensus_result.model_contributions)
                    if consensus_result.debate_rounds:
                        scratchpad.write("debate_rounds", len(consensus_result.debate_rounds))
                    if consensus_result.key_agreements:
                        scratchpad.write("key_agreements", consensus_result.key_agreements[:3])
                
                logger.info(
                    "Consensus built: strategy=%s, score=%.2f, models=%d",
                    consensus_result.strategy_used.value,
                    consensus_result.consensus_score.overall_score,
                    len(consensus_result.participating_models),
                )
                
            except Exception as e:
                logger.error("Deep consensus failed, falling back to single model: %s", e)
                consensus_result = None
                # Fall through to single model execution
        
        # Single model execution (when HRM and consensus not used or failed)
        if hrm_execution_result is None and consensus_result is None:
            # Get the provider for the first model
            first_model = models_to_use[0]
            provider_name = model_to_provider.get(first_model, first_model)
            # Try to get the provider, fallback to openrouter if available (NEVER fall back to stub)
            provider = self.providers.get(provider_name)
            if not provider:
                # Try real providers only - stub should NEVER be used for actual API calls
                provider = self.providers.get("openrouter") or self.providers.get("openai") or self.providers.get("anthropic") or self.providers.get("google")
            if not provider:
                # Create minimal stub response
                result = LLMResult(
                    content="I apologize, but no LLM providers are configured. Please configure at least one API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, GROK_API_KEY, or GEMINI_API_KEY).",
                    model="stub",
                    tokens=0
                )
            else:
                # Try to generate a response using the provider
                try:
                    # Check if provider has a generate method
                    if hasattr(provider, 'generate'):
                        # Pass the actual model name to the provider
                        model_name = first_model if first_model != provider_name else (models_to_use[0] if models_to_use else "default")
                        # Check if generate is async
                        import asyncio
                        import inspect
                        if inspect.iscoroutinefunction(provider.generate):
                            provider_result = await provider.generate(augmented_prompt, model=model_name, **kwargs)
                        else:
                            provider_result = provider.generate(augmented_prompt, model=model_name, **kwargs)
                        # Extract content from result
                        if hasattr(provider_result, 'text'):
                            content = provider_result.text
                        elif hasattr(provider_result, 'content'):
                            content = provider_result.content
                        elif isinstance(provider_result, str):
                            content = provider_result
                        else:
                            content = str(provider_result)
                        
                        model_name = getattr(provider_result, 'model', models_to_use[0])
                        tokens = getattr(provider_result, 'tokens_used', 0)
                        # Extract cost tracking info if available
                        cost_info = getattr(provider_result, 'cost_info', None)
                        generation_id = getattr(provider_result, 'generation_id', None)
                    else:
                        # Fallback for providers without generate method
                        content = f"Stub response: {augmented_prompt[:100]}..."
                        model_name = "stub"
                        tokens = 0
                        cost_info = None
                        generation_id = None
                    
                    result = LLMResult(
                        content=content,
                        model=model_name,
                        tokens=tokens,
                        cost_info=cost_info,
                        generation_id=generation_id,
                    )
                    
                    # Store model output and cost info in scratchpad
                    if scratchpad:
                        scratchpad.write("model_output", content)
                        scratchpad.write("model_name", model_name)
                        if cost_info:
                            scratchpad.write("cost_info", cost_info)
                        
                except Exception as e:
                    logger.error(f"Error generating response from provider: {e}")
                    
                    # FALLBACK: Try Together.ai before giving up
                    # This catches OpenRouter 403/429/5xx and retries via Together.ai
                    fallback_result = None
                    
                    # Method 1: Try via provider router
                    try:
                        from .providers import get_provider_router
                        router = get_provider_router()
                        if router:
                            fallback_result = await router._try_together_fallback(
                                first_model, augmented_prompt
                            )
                    except Exception as fb_err:
                        logger.warning(f"Together.ai router fallback failed: {fb_err}")
                    
                    # Method 2: Direct httpx call if router failed
                    if not fallback_result:
                        try:
                            import os, httpx as _fb_httpx
                            _fb_key = os.getenv("TOGETHERAI_API_KEY") or os.getenv("TOGETHER_API_KEY")
                            if _fb_key:
                                async with _fb_httpx.AsyncClient(timeout=60.0) as _fb_client:
                                    _fb_resp = await _fb_client.post(
                                        "https://api.together.ai/v1/chat/completions",
                                        headers={"Authorization": f"Bearer {_fb_key}", "Content-Type": "application/json"},
                                        json={"model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                                              "messages": [{"role": "user", "content": augmented_prompt}],
                                              "max_tokens": 2048},
                                    )
                                    if _fb_resp.status_code == 200:
                                        _fb_data = _fb_resp.json()
                                        _fb_choices = _fb_data.get("choices", [])
                                        if _fb_choices:
                                            fallback_result = _fb_choices[0].get("message", {}).get("content", "")
                                            logger.info("Direct Together.ai fallback succeeded")
                        except Exception as direct_err:
                            logger.warning(f"Direct Together.ai fallback failed: {direct_err}")
                    
                    if fallback_result:
                        logger.info(f"Together.ai fallback succeeded for {first_model}")
                        result = LLMResult(
                            content=fallback_result,
                            model=f"together-fallback-for-{first_model}",
                            tokens=0,
                            cost_info=None,
                            generation_id=None,
                        )
                    else:
                        # No fallback available — raise the error
                        from .errors import ProviderError, ErrorCode
                        raise ProviderError(
                            message=f"Provider error: {str(e)}",
                            provider=provider_name,
                            model=first_model,
                            code=ErrorCode.PROVIDER_ERROR,
                            original_error=e,
                            details={"models_attempted": models_to_use},
                            recoverable=True,
                        ) from e
        
        # Infer domain for later use
        domain = None
        if ADAPTIVE_ROUTING_AVAILABLE:
            try:
                domain = infer_domain(prompt)
            except Exception:
                pass
        
        # Output security check - sanitize before verification
        if use_guardrails and GUARDRAILS_AVAILABLE and self.safety_validator:
            try:
                sanitized_output, is_safe = self.safety_validator.validate_output(result.content)
                if sanitized_output != result.content:
                    logger.info("Output sanitized by guardrails")
                    result = LLMResult(
                        content=sanitized_output,
                        model=result.model,
                        tokens=getattr(result, 'tokens_used', 0),
                    )
                    if scratchpad:
                        scratchpad.write("output_sanitized", True)
                        scratchpad.write("output_was_safe", is_safe)
                        security_issues.append("Output sanitized")
            except Exception as e:
                logger.warning("Output security check failed: %s", e)
        
        # Tool execution - process any tool calls in model output
        use_tools = kwargs.get("use_tools", True)
        tool_results: List[Any] = []
        
        if use_tools and self.tool_broker and TOOL_BROKER_AVAILABLE:
            try:
                # Check if model output contains tool requests
                if self.tool_broker.is_tool_request(result.content):
                    logger.info("Detected tool request in model output")
                    
                    # Process tool calls
                    user_tier = kwargs.get("user_tier", "free")
                    processed_output, tool_results = await self.tool_broker.process_model_output_with_tools(
                        result.content,
                        user_tier=user_tier,
                        max_tool_calls=kwargs.get("max_tool_calls", 5),
                    )
                    
                    if processed_output != result.content:
                        result = LLMResult(
                            content=processed_output,
                            model=result.model,
                            tokens=getattr(result, 'tokens_used', 0),
                        )
                        
                        if scratchpad:
                            scratchpad.write("tool_calls_executed", len(tool_results))
                            scratchpad.write("tool_results", [
                                {"tool": r.tool_name, "success": r.success, "result": str(r.result)[:200]}
                                for r in tool_results
                            ])
                        
                        logger.info("Executed %d tool calls", len(tool_results))
                        
            except Exception as e:
                logger.warning("Tool execution failed: %s", e)
        
        # Fact verification and iterative refinement loop
        # NOTE: Refinement loop disabled for accuracy_level <= 3 due to system prompt leakage issues
        use_verification = kwargs.get("use_verification", True) and accuracy_level >= 4
        use_refinement_loop = kwargs.get("use_refinement_loop", True) and accuracy_level >= 4
        verification_report = None
        refinement_result: Optional[Any] = None
        verification_passed = True
        
        if use_verification and FACT_CHECK_AVAILABLE:
            try:
                logger.info("Running fact verification on response")
                
                # Use advanced refinement loop if available and enabled
                if use_refinement_loop and self.refinement_controller and REFINEMENT_LOOP_AVAILABLE:
                    logger.info("Using iterative refinement loop for self-correction")
                    
                    # Configure max iterations based on accuracy level
                    max_iters = 2 if accuracy_level <= 3 else 3
                    
                    # Run the iterative refinement loop
                    refinement_result = await self.refinement_controller.run_refinement_loop(
                        answer=result.content,
                        prompt=prompt,
                        model=result.model,
                        context=memory_context if memory_context else None,
                        available_models=models_to_use if len(models_to_use) > 1 else None,
                    )
                    
                    # Update result with refined answer
                    if refinement_result.final_answer != result.content:
                        logger.info(
                            "Answer refined after %d iterations (final score: %.2f, status: %s)",
                            len(refinement_result.iterations),
                            refinement_result.final_verification_score,
                            refinement_result.final_status.value,
                        )
                        result = LLMResult(
                            content=refinement_result.final_answer,
                            model=result.model,
                            tokens=getattr(result, 'tokens_used', 0),
                        )
                    
                    verification_passed = (
                        refinement_result.final_status == LoopStatus.PASSED or
                        refinement_result.final_verification_score >= 0.7
                    )
                    
                    # Store refinement result in scratchpad
                    if scratchpad:
                        scratchpad.write("refinement_iterations", len(refinement_result.iterations))
                        scratchpad.write("refinement_status", refinement_result.final_status.value)
                        scratchpad.write("verification_score", refinement_result.final_verification_score)
                        scratchpad.write("issues_found", refinement_result.total_issues_found)
                        scratchpad.write("issues_resolved", refinement_result.issues_resolved)
                        scratchpad.write("strategies_used", [s.value for s in refinement_result.strategies_used])
                        scratchpad.write("convergence_history", refinement_result.convergence_history)
                        if refinement_result.transparency_notes:
                            scratchpad.write("refinement_notes", refinement_result.transparency_notes)
                    
                else:
                    # Fallback to basic fact checker loop
                    corrected_answer, verification_report = await self.fact_checker.verify_and_correct_loop(
                        result.content,
                        prompt=prompt,
                        max_iterations=2,
                    )
                    
                    # Update result if corrections were made
                    if corrected_answer != result.content:
                        logger.info(
                            "Answer corrected after verification (score: %.2f, corrections: %d)",
                            verification_report.verification_score if verification_report else 0,
                            verification_report.corrections_made if verification_report else 0,
                        )
                        result = LLMResult(
                            content=corrected_answer,
                            model=result.model,
                            tokens=getattr(result, 'tokens_used', 0),
                        )
                    
                    verification_passed = (
                        verification_report.is_valid if verification_report else True
                    )
                    
                    # Store verification result in scratchpad
                    if scratchpad and verification_report:
                        scratchpad.write("verification_score", verification_report.verification_score)
                        scratchpad.write("verification_passed", verification_passed)
                        scratchpad.write("corrections_made", verification_report.corrections_made)
                    
            except Exception as e:
                logger.warning("Fact verification failed: %s", e)
        
        # =====================================================================
        # PR3: Verification Fallback Logic - Retry with high-accuracy model
        # =====================================================================
        use_verification_fallback = kwargs.get("use_verification_fallback", True)
        
        if not verification_passed and use_verification_fallback:
            logger.info("PR3: Verification failed, initiating high-accuracy retry")
            
            try:
                # Get the original model that failed
                failed_model = result.model if result else "unknown"
                
                # Attempt high-accuracy retry
                retry_result, retry_passed = await self.retry_with_high_accuracy(
                    prompt=prompt,
                    previous_response=result.content if result else "",
                    verification_report=verification_report if 'verification_report' in locals() else None,
                    context=memory_context if 'memory_context' in locals() else None,
                    excluded_models=[failed_model],
                    max_retries=2,
                )
                
                if retry_passed:
                    logger.info(
                        "PR3: High-accuracy retry succeeded (switched from %s to %s)",
                        failed_model,
                        retry_result.model,
                    )
                    result = retry_result
                    verification_passed = True
                    
                    # Update scratchpad with retry info
                    if scratchpad:
                        scratchpad.write("verification_fallback_used", True)
                        scratchpad.write("fallback_model", retry_result.model)
                        scratchpad.write("fallback_success", True)
                else:
                    logger.warning(
                        "PR3: High-accuracy retry did not improve verification"
                    )
                    
                    # Optionally use the retry result if it's longer/better
                    if len(retry_result.content) > len(result.content) * 0.8:
                        result = retry_result
                    
                    if scratchpad:
                        scratchpad.write("verification_fallback_used", True)
                        scratchpad.write("fallback_model", retry_result.model)
                        scratchpad.write("fallback_success", False)
                        
            except Exception as e:
                logger.warning("PR3: Verification fallback failed: %s", e)
                if scratchpad:
                    scratchpad.write("verification_fallback_error", str(e))
        
        # Log performance feedback if available
        # Strategy Memory (PR2): Extended logging with strategy information
        if PERFORMANCE_TRACKER_AVAILABLE and performance_tracker:
            try:
                # Determine strategy from request mode
                strategy = "single_best"  # Default for simple orchestration
                if hasattr(request, "mode"):
                    mode_to_strategy = {
                        "simple": "single_best",
                        "balanced": "quality_weighted_fusion",
                        "quality": "best_of_n",
                        "elite": "expert_panel",
                    }
                    strategy = mode_to_strategy.get(str(request.mode).lower(), "single_best")
                
                # Get quality score if available
                quality_score = None
                if "verification_report" in locals() and verification_report:
                    quality_score = getattr(verification_report, "verification_score", None)
                
                performance_tracker.log_run(
                    models_used=[result.model],
                    success_flag=verification_passed,
                    latency_ms=getattr(result, "latency_ms", None),
                    domain=domain,
                    # Strategy Memory (PR2) extended fields
                    strategy=strategy,
                    task_type=domain,  # Use domain as task type for now
                    primary_model=result.model,
                    quality_score=quality_score,
                    total_tokens=getattr(result, "tokens_used", 0),
                )
            except Exception as e:
                logger.debug("Failed to log performance: %s", e)
        
        # Update registry performance for routing (learning loop)
        try:
            if MODEL_REGISTRY_AVAILABLE and self.model_registry:
                latency_ms = getattr(result, "latency_ms", 0.0) or 0.0
                quality_score = (
                    getattr(verification_report, "verification_score", None)
                    if "verification_report" in locals()
                    else None
                )
                self.model_registry.update_performance(
                    model_id=result.model,
                    latency_ms=latency_ms,
                    success=verification_passed,
                    quality=quality_score,
                )
        except Exception as e:
            logger.debug("Failed to update registry performance: %s", e)
        
        # Store insights to shared memory for cross-session use
        if self.shared_memory and SHARED_MEMORY_AVAILABLE and verification_passed and user_id:
            try:
                # Store as a verified insight
                await self.shared_memory.store_conversation_insight(
                    user_id=user_id,
                    session_id=session_id,
                    insight=f"Q: {prompt[:200]}\nA: {result.content[:500]}",
                    verified=True,
                    tags=[domain] if domain else None,
                )
                logger.debug("Stored verified insight to shared memory")
                
                # Stage 3: Save factual responses for pronoun resolution
                # Only save if this looks like a factual Q&A (not creative writing etc.)
                factual_domains = {"general", "science", "history", "factual_question", "research"}
                if domain in factual_domains or domain is None:
                    try:
                        # Extract and save the key fact from the answer
                        fact_content = result.content[:500]  # First 500 chars as fact
                        await self.shared_memory.save_fact(
                            user_id=user_id,
                            fact=fact_content,
                            session_id=session_id,
                            verified=True,
                        )
                        logger.debug("Saved factual response for pronoun resolution")
                        if self.stage3_logger:
                            self.stage3_logger.log_memory_operation("save", "fact", True)
                    except Exception as e:
                        logger.debug("Failed to save fact: %s", e)
                        
            except Exception as e:
                logger.debug("Failed to store shared memory insight: %s", e)
        
        # Store verified answer in memory only if verification passed
        if use_memory and self.memory_manager and MEMORY_AVAILABLE and verification_passed:
            try:
                # Store the Q&A pair
                record_id = self.memory_manager.store_verified_answer(
                    session_id=session_id,
                    query=prompt,
                    answer=result.content,
                    domain=domain,
                    user_id=user_id,
                    additional_metadata={
                        "verification_score": verification_report.verification_score if verification_report else 1.0,
                        "corrections_made": verification_report.corrections_made if verification_report else 0,
                    },
                )
                logger.info("Stored verified answer in memory: %s", record_id[:8] if record_id else "failed")
            except Exception as e:
                logger.warning("Failed to store answer in memory: %s", e)
        
        # Store high-quality answer for cross-session reuse
        if (ANSWER_STORE_AVAILABLE and self.answer_store and verification_passed and
            FEATURE_FLAGS_AVAILABLE and is_feature_enabled(FeatureFlags.CROSS_SESSION_REUSE)):
            try:
                # Calculate quality score based on verification and consensus
                quality_score = 0.8  # Base score for verified answers
                if verification_report and hasattr(verification_report, 'verification_score'):
                    quality_score = max(quality_score, verification_report.verification_score)
                
                stored_id = self.answer_store.store(
                    query=prompt,
                    answer=result.content,
                    quality_score=quality_score,
                    domain=domain,
                    complexity="moderate",
                    models_used=[result.model] if result.model else [],
                    consensus_method=protocol_name if protocol_name else "single",
                    session_id=session_id,
                    user_id=user_id,
                )
                logger.info("Stored answer for cross-session reuse: %s (score=%.2f)", 
                           stored_id[:8] if stored_id else "failed", quality_score)
            except Exception as e:
                logger.warning("Failed to store answer for cross-session reuse: %s", e)
        
        # Build consensus notes
        consensus_notes = [f"Response generated using {result.model}"]
        if hierarchical_plan:
            consensus_notes.append(f"HRM strategy: {hierarchical_plan.strategy}")
        if use_adaptive_routing:
            consensus_notes.append("Adaptive routing enabled")
        if memory_context:
            consensus_notes.append(f"Memory context used ({len(memory_hits)} hits)")
        if shared_memory_context:
            consensus_notes.append("Cross-session shared memory used")
        if live_data_context:
            consensus_notes.append("Real-time live data integrated")
        # Add refinement loop info to consensus notes
        if refinement_result:
            consensus_notes.append(
                f"Refinement loop: {len(refinement_result.iterations)} iterations, "
                f"status={refinement_result.final_status.value}, "
                f"score={refinement_result.final_verification_score:.2f}"
            )
            if refinement_result.issues_resolved > 0:
                consensus_notes.append(
                    f"Issues resolved: {refinement_result.issues_resolved}/{refinement_result.total_issues_found}"
                )
            if refinement_result.strategies_used:
                consensus_notes.append(
                    f"Strategies used: {', '.join(s.value for s in refinement_result.strategies_used[:3])}"
                )
        elif verification_report:
            consensus_notes.append(
                f"Fact verification: score={verification_report.verification_score:.2f}, "
                f"verified={verification_report.verified_count}/{len(verification_report.items)}"
            )
            if verification_report.corrections_made > 0:
                consensus_notes.append(f"Corrections applied: {verification_report.corrections_made}")
        
        # Build supporting notes from scratchpad
        supporting_notes = []
        if scratchpad:
            scratchpad_context = scratchpad.get_context_string()
            if scratchpad_context:
                supporting_notes.append(f"Scratchpad data: {scratchpad_context[:500]}")
        
        # Add verification details to supporting notes
        if verification_report and verification_report.items:
            for item in verification_report.items[:3]:  # Include top 3 verified facts
                if item.verified:
                    supporting_notes.append(f"Verified: {item.text[:100]}...")
        
        # Add security info to consensus notes
        if security_issues:
            consensus_notes.append(f"Security actions: {len(security_issues)}")
        if use_guardrails and GUARDRAILS_AVAILABLE:
            consensus_notes.append("Guardrails: active")
        
        # Add tool execution info to consensus notes
        if tool_results:
            successful_tools = [r.tool_name for r in tool_results if r.success]
            failed_tools = [r.tool_name for r in tool_results if not r.success]
            if successful_tools:
                consensus_notes.append(f"Tools used: {', '.join(successful_tools)}")
            if failed_tools:
                consensus_notes.append(f"Tool errors: {', '.join(failed_tools)}")
        
        # Add prompt diffusion info to consensus notes
        if diffusion_result:
            consensus_notes.append(
                f"Prompt refined: {diffusion_result.rounds_completed} rounds, "
                f"score={diffusion_result.best_version.score:.2f}"
            )
            if diffusion_result.clarifications_added:
                consensus_notes.append(
                    f"Clarifications added: {len(diffusion_result.clarifications_added)}"
                )
        
        # Add deep consensus info to consensus notes
        if consensus_result:
            consensus_notes.append(
                f"Deep consensus: {consensus_result.strategy_used.value}, "
                f"score={consensus_result.consensus_score.overall_score:.2f}, "
                f"models={len(consensus_result.participating_models)}"
            )
            if consensus_result.debate_rounds:
                consensus_notes.append(
                    f"Debate rounds: {len(consensus_result.debate_rounds)}"
                )
            if consensus_result.key_agreements:
                consensus_notes.append(
                    f"Key agreements: {len(consensus_result.key_agreements)}"
                )
        
        # Record usage metering
        if BILLING_AVAILABLE and user_id and get_usage_meter:
            try:
                from .database import SessionLocal
                
                meter = get_usage_meter()
                tokens_used = getattr(result, 'tokens_used', 0)
                
                # Record token usage
                if tokens_used > 0:
                    # Estimate input/output split
                    input_tokens = tokens_used // 3
                    output_tokens = tokens_used - input_tokens
                    
                    meter.record_usage(
                        user_id=user_id,
                        usage_type=UsageType.TOKEN_INPUT,
                        amount=input_tokens,
                        model=result.model,
                    )
                    meter.record_usage(
                        user_id=user_id,
                        usage_type=UsageType.TOKEN_OUTPUT,
                        amount=output_tokens,
                        model=result.model,
                    )
                
                # Record request
                meter.record_usage(
                    user_id=user_id,
                    usage_type=UsageType.REQUEST,
                    amount=1,
                    model=result.model,
                )
                
                # Also record in database for persistence
                with SessionLocal() as db_session:
                    from .billing.usage import UsageTracker
                    tracker = UsageTracker(db_session)
                    tracker.record_usage(
                        user_id=user_id,
                        tokens=tokens_used,
                        requests=1,
                        models_used=[result.model],
                        metadata={
                            "session_id": session_id,
                            "verification_passed": verification_passed,
                            "user_tier": user_tier,
                        },
                    )
                    db_session.commit()
                
                logger.debug(
                    "Recorded usage: user=%s, tokens=%d, model=%s",
                    user_id,
                    tokens_used,
                    result.model,
                )
                
            except Exception as e:
                logger.warning("Failed to record usage metering: %s", e)
        
        # Phase Final: Dialogue Post-processing (suggestions)
        suggestions = []
        if use_dialogue and self.dialogue_manager and DIALOGUE_AVAILABLE:
            try:
                response_text = result.content if hasattr(result, 'content') else str(result)
                
                dialogue_result = await self.dialogue_manager.process_response(
                    response=response_text,
                    query=original_prompt,
                    session_id=session_id,
                    user_id=user_id,
                    user_tier=user_tier,
                    generate_suggestions=True,
                )
                
                # Update response if it was cleaned of tags
                if dialogue_result.final_response != response_text:
                    result.content = dialogue_result.final_response
                
                # Collect suggestions
                suggestions = dialogue_result.suggestions
                
                if suggestions:
                    logger.info("Generated %d suggestions", len(suggestions))
                    if scratchpad:
                        scratchpad.write("suggestions_generated", len(suggestions))
                        scratchpad.write("suggestion_texts", [s.text for s in suggestions])
                
                # Add suggestion info to consensus notes
                if suggestions:
                    consensus_notes.append(f"Suggestions offered: {len(suggestions)}")
                    
            except Exception as e:
                logger.warning("Dialogue post-processing failed: %s", e)
        
        # Return ProtocolResult structure expected by orchestrator_adapter
        return ProtocolResult(
            final_response=result,
            initial_responses=[result],
            critiques=[],
            improvements=[],
            consensus_notes=consensus_notes,
            step_outputs={"answer": [result]},
            supporting_notes=supporting_notes,
            suggestions=suggestions if suggestions else [],
            quality_assessments={},
        )
    
    async def orchestrate_with_memory(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        session_id: str = "default",
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate with full memory integration.
        
        This method:
        1. Queries memory for relevant prior knowledge
        2. Augments the prompt with memory context
        3. Generates response
        4. Stores verified answer in memory
        
        Args:
            prompt: The prompt to process
            user_id: User ID for memory namespace
            session_id: Session ID for memory storage
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with memory-augmented response
        """
        return await self.orchestrate(
            prompt,
            use_memory=True,
            user_id=user_id,
            session_id=session_id,
            **kwargs
        )
    
    async def orchestrate_with_hrm(
        self,
        prompt: str,
        accuracy_level: int = 3,
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate with full HRM hierarchy.
        
        This method implements the hierarchical role management pattern:
        1. Executive coordinates overall strategy
        2. Managers delegate to specialists
        3. Specialists execute with assistant support
        4. Quality manager validates
        5. Executive synthesizes final response
        
        Args:
            prompt: The prompt to process
            accuracy_level: 1-5 slider value
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with full HRM artifacts
        """
        return await self.orchestrate(
            prompt,
            use_hrm=True,
            use_adaptive_routing=True,
            accuracy_level=accuracy_level,
            **kwargs
        )
    
    async def orchestrate_ensemble(
        self,
        prompt: str,
        models: List[str],
        accuracy_level: int = 3,
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate with adaptive ensemble voting.
        
        Multiple models process the query in parallel, and their responses
        are weighted and voted on based on performance metrics.
        
        Args:
            prompt: The prompt to process
            models: List of models for ensemble
            accuracy_level: 1-5 slider value
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with ensemble voting results
        """
        return await self.orchestrate(
            prompt,
            models=models,
            use_adaptive_routing=True,
            accuracy_level=accuracy_level,
            **kwargs
        )
    
    async def orchestrate_autonomous(
        self,
        task: str,
        *,
        user_tier: str = "free",
        model: Optional[str] = None,
        max_iterations: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        on_step: Optional[Callable] = None,
        **kwargs: Any
    ) -> Any:
        """
        Execute a task autonomously using the AgentExecutor.
        
        This method enables AutoGPT-like behavior where the agent:
        1. Plans a sequence of tool calls
        2. Executes tools and integrates results
        3. Iterates until answer is found or limits reached
        
        Example tasks:
        - "Calculate 5! + sqrt(16)" -> Uses calculator tool
        - "Research population of France in 1900, 1950, 2000" -> Multiple searches
        
        Args:
            task: The task/question to solve autonomously
            user_tier: User's tier (affects limits)
            model: Model to use for agent reasoning
            max_iterations: Override tier max iterations
            max_tool_calls: Override tier max tool calls
            on_step: Optional callback for each step (for streaming updates)
            **kwargs: Additional parameters
            
        Returns:
            AgentExecutionResult or LLMResult-like object
        """
        if not AGENT_EXECUTOR_AVAILABLE or not AgentExecutor:
            logger.warning("Agent executor not available, falling back to regular orchestration")
            return await self.orchestrate(task, **kwargs)
        
        if not self.tool_broker:
            logger.warning("Tool broker not available, falling back to regular orchestration")
            return await self.orchestrate(task, **kwargs)
        
        # Create or get agent executor
        if self.agent_executor is None:
            self.agent_executor = AgentExecutor(
                providers=self.providers,
                tool_broker=self.tool_broker,
                default_model=model or "gpt-4o",
            )
        
        # Execute task
        result = await self.agent_executor.execute(
            task,
            user_tier=user_tier,
            model=model,
            max_iterations=max_iterations,
            max_tool_calls=max_tool_calls,
            on_step=on_step,
        )
        
        # Convert to LLMResult-like format for consistency
        if hasattr(result, 'final_answer'):
            return LLMResult(
                content=result.final_answer,
                model=f"agent({model or 'default'})",
                tokens=result.total_tokens,
                metadata={
                    "agent_status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "iterations": result.total_iterations,
                    "tool_calls": result.total_tool_calls,
                    "steps": [
                        {
                            "step": s.step_number,
                            "action": s.action.value if hasattr(s.action, 'value') else str(s.action),
                            "tool": s.tool_name,
                            "result": s.tool_result[:200] if s.tool_result else None,
                        }
                        for s in result.steps
                    ],
                },
            )
        
        return result
    
    async def orchestrate_multi_step(
        self,
        goal: str,
        *,
        steps: Optional[List[str]] = None,
        user_tier: str = "pro",
        **kwargs: Any
    ) -> Any:
        """
        Execute a multi-step goal, optionally with predefined steps.
        
        If steps are provided, executes them in order.
        Otherwise, lets the agent plan its own steps.
        
        Args:
            goal: The overall goal to achieve
            steps: Optional list of steps to execute
            user_tier: User's tier
            **kwargs: Additional parameters
            
        Returns:
            Combined result of all steps
        """
        if steps:
            # Execute predefined steps
            results = []
            context = f"Goal: {goal}\n"
            
            for i, step in enumerate(steps):
                logger.info("Executing step %d/%d: %s", i+1, len(steps), step[:50])
                
                result = await self.orchestrate_autonomous(
                    f"{step}\n\nContext: {context}",
                    user_tier=user_tier,
                    **kwargs
                )
                
                if hasattr(result, 'content'):
                    results.append(result.content)
                    context += f"\nStep {i+1} result: {result.content[:500]}"
            
            # Synthesize final answer
            synthesis_prompt = f"""
Goal: {goal}

Step results:
{chr(10).join(f'{i+1}. {r}' for i, r in enumerate(results))}

Synthesize these results into a final comprehensive answer:
"""
            return await self.orchestrate(synthesis_prompt, **kwargs)
        
        else:
            # Let agent plan its own steps
            return await self.orchestrate_autonomous(
                goal,
                user_tier=user_tier,
                **kwargs
            )

