"""Orchestration modules for LLMHive."""

from .blackboard import Blackboard
from .hrm import (
    HRMRegistry,
    HRMRole,
    RoleLevel,
    RolePermission,
    get_hrm_registry,
)

# Hierarchical Planning
try:
    from .hierarchical_planning import (
        HierarchicalPlanner,
        HierarchicalPlan,
        HierarchicalPlanStep,
        HierarchicalRole,
        TaskComplexity,
        is_complex_query,
        decompose_query,
    )
    HIERARCHICAL_PLANNING_AVAILABLE = True
except ImportError:
    HIERARCHICAL_PLANNING_AVAILABLE = False
    HierarchicalPlanner = None  # type: ignore
    HierarchicalPlan = None  # type: ignore
    HierarchicalPlanStep = None  # type: ignore
    HierarchicalRole = None  # type: ignore
    TaskComplexity = None  # type: ignore

# Hierarchical Executor
try:
    from .hierarchical_executor import (
        HierarchicalPlanExecutor,
        HRMBlackboard,
        HRMBlackboardEntry,
        ExecutionResult as HRMExecutionResult,
        StepResult,
        StepStatus,
        ExecutionMode,
        execute_hierarchical_plan,
    )
    HIERARCHICAL_EXECUTOR_AVAILABLE = True
except ImportError:
    HIERARCHICAL_EXECUTOR_AVAILABLE = False
    HierarchicalPlanExecutor = None  # type: ignore
    HRMBlackboard = None  # type: ignore
    HRMBlackboardEntry = None  # type: ignore
    HRMExecutionResult = None  # type: ignore
    StepResult = None  # type: ignore
    StepStatus = None  # type: ignore
    ExecutionMode = None  # type: ignore
    execute_hierarchical_plan = None  # type: ignore

# Adaptive Router
try:
    from .adaptive_router import (
        AdaptiveModelRouter,
        AdaptiveRoutingResult,
        ModelScore,
        get_adaptive_router,
        select_models_adaptive,
        select_models_dynamic,
        infer_domain,
        # PR5: Budget-aware routing
        BudgetConstraints,
        DEFAULT_MAX_COST_USD,
        DEFAULT_COST_WEIGHT,
    )
    ADAPTIVE_ROUTING_AVAILABLE = True
except ImportError:
    ADAPTIVE_ROUTING_AVAILABLE = False
    AdaptiveModelRouter = None  # type: ignore
    AdaptiveRoutingResult = None  # type: ignore
    ModelScore = None  # type: ignore
    BudgetConstraints = None  # type: ignore

# Prompt Diffusion
try:
    from .prompt_diffusion import PromptDiffusion, DiffusionResult, PromptVersion
    PROMPT_DIFFUSION_AVAILABLE = True
except ImportError:
    PROMPT_DIFFUSION_AVAILABLE = False
    PromptDiffusion = None  # type: ignore
    DiffusionResult = None  # type: ignore
    PromptVersion = None  # type: ignore

# PromptOps Layer
try:
    from .prompt_ops import (
        PromptOps,
        PromptSpecification,
        QueryAnalysis,
        TaskSegment,
        TaskType,
        QueryComplexity,
        preprocess_query,
        analyze_query,
    )
    PROMPT_OPS_AVAILABLE = True
except ImportError:
    PROMPT_OPS_AVAILABLE = False
    PromptOps = None  # type: ignore
    PromptSpecification = None  # type: ignore
    QueryAnalysis = None  # type: ignore

# Answer Refiner
try:
    from .answer_refiner import (
        AnswerRefiner,
        RefinedAnswer,
        RefinementConfig,
        OutputFormat,
        refine_answer,
        quick_format,
    )
    ANSWER_REFINER_AVAILABLE = True
except ImportError:
    ANSWER_REFINER_AVAILABLE = False
    AnswerRefiner = None  # type: ignore
    RefinedAnswer = None  # type: ignore

# Prompt Templates
try:
    from .prompt_templates import (
        PLANNER_SYSTEM_PROMPT,
        VERIFIER_SYSTEM_PROMPT,
        REFINER_SYSTEM_PROMPT,
        build_planner_prompt,
        build_verifier_prompt,
        build_refiner_prompt,
        build_solver_prompt,
        build_debate_prompt,
        build_fact_check_prompt,
        get_prompt_template,
    )
    PROMPT_TEMPLATES_AVAILABLE = True
except ImportError:
    PROMPT_TEMPLATES_AVAILABLE = False
    PLANNER_SYSTEM_PROMPT = ""  # type: ignore
    VERIFIER_SYSTEM_PROMPT = ""  # type: ignore
    REFINER_SYSTEM_PROMPT = ""  # type: ignore

__all__ = [
    "Blackboard",
    "HRMRegistry",
    "HRMRole",
    "RoleLevel",
    "RolePermission",
    "get_hrm_registry",
]

if HIERARCHICAL_PLANNING_AVAILABLE:
    __all__.extend([
        "HierarchicalPlanner",
        "HierarchicalPlan",
        "HierarchicalPlanStep",
        "HierarchicalRole",
        "TaskComplexity",
        "is_complex_query",
        "decompose_query",
    ])

if HIERARCHICAL_EXECUTOR_AVAILABLE:
    __all__.extend([
        "HierarchicalPlanExecutor",
        "HRMBlackboard",
        "HRMBlackboardEntry",
        "HRMExecutionResult",
        "StepResult",
        "StepStatus",
        "ExecutionMode",
        "execute_hierarchical_plan",
    ])

if ADAPTIVE_ROUTING_AVAILABLE:
    __all__.extend([
        "AdaptiveModelRouter",
        "AdaptiveRoutingResult",
        "ModelScore",
        "get_adaptive_router",
        "select_models_adaptive",
        "select_models_dynamic",
        "infer_domain",
        # PR5: Budget-aware routing
        "BudgetConstraints",
        "DEFAULT_MAX_COST_USD",
        "DEFAULT_COST_WEIGHT",
    ])

if PROMPT_DIFFUSION_AVAILABLE:
    __all__.extend(["PromptDiffusion", "DiffusionResult", "PromptVersion"])

if PROMPT_OPS_AVAILABLE:
    __all__.extend([
        "PromptOps",
        "PromptSpecification",
        "QueryAnalysis",
        "TaskSegment",
        "TaskType",
        "QueryComplexity",
        "preprocess_query",
        "analyze_query",
    ])

if ANSWER_REFINER_AVAILABLE:
    __all__.extend([
        "AnswerRefiner",
        "RefinedAnswer",
        "RefinementConfig",
        "OutputFormat",
        "refine_answer",
        "quick_format",
    ])

if PROMPT_TEMPLATES_AVAILABLE:
    __all__.extend([
        "PLANNER_SYSTEM_PROMPT",
        "VERIFIER_SYSTEM_PROMPT",
        "REFINER_SYSTEM_PROMPT",
        "build_planner_prompt",
        "build_verifier_prompt",
        "build_refiner_prompt",
        "build_solver_prompt",
        "build_debate_prompt",
        "build_fact_check_prompt",
        "get_prompt_template",
    ])

# Elite Orchestrator
try:
    from .elite_orchestrator import (
        EliteOrchestrator,
        EliteResult,
        ModelCapability,
        MODEL_CAPABILITIES,
        TASK_CAPABILITIES,
        elite_orchestrate,
        get_best_model_for_task,
    )
    ELITE_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ELITE_ORCHESTRATOR_AVAILABLE = False
    EliteOrchestrator = None  # type: ignore
    EliteResult = None  # type: ignore

# Quality Booster
try:
    from .quality_booster import (
        QualityBooster,
        QualityResult,
        FactualQualityBooster,
        CodeQualityBooster,
        boost_response,
        generate_high_quality,
    )
    QUALITY_BOOSTER_AVAILABLE = True
except ImportError:
    QUALITY_BOOSTER_AVAILABLE = False
    QualityBooster = None  # type: ignore
    QualityResult = None  # type: ignore

if ELITE_ORCHESTRATOR_AVAILABLE:
    __all__.extend([
        "EliteOrchestrator",
        "EliteResult",
        "ModelCapability",
        "MODEL_CAPABILITIES",
        "TASK_CAPABILITIES",
        "elite_orchestrate",
        "get_best_model_for_task",
    ])

if QUALITY_BOOSTER_AVAILABLE:
    __all__.extend([
        "QualityBooster",
        "QualityResult",
        "FactualQualityBooster",
        "CodeQualityBooster",
        "boost_response",
        "generate_high_quality",
    ])

# Elite Prompts
try:
    from .elite_prompts import (
        OrchestratorRole,
        META_CONTROLLER_SYSTEM_PROMPT,
        PLANNER_SYSTEM_PROMPT as ELITE_PLANNER_PROMPT,
        VERIFIER_SYSTEM_PROMPT as ELITE_VERIFIER_PROMPT,
        CHALLENGER_SYSTEM_PROMPT,
        REFINER_SYSTEM_PROMPT as ELITE_REFINER_PROMPT,
        ROUTER_SYSTEM_PROMPT,
        TOOL_BROKER_SYSTEM_PROMPT,
        get_system_prompt,
        get_all_prompts,
        SELF_CONSISTENCY_TEMPLATE,
        DEBATE_TEMPLATE,
        FACT_CHECK_TEMPLATE,
        SYNTHESIS_TEMPLATE,
        REFLECTION_TEMPLATE,
    )
    ELITE_PROMPTS_AVAILABLE = True
except ImportError:
    ELITE_PROMPTS_AVAILABLE = False
    OrchestratorRole = None  # type: ignore

# Tool Broker
try:
    from .tool_broker import (
        ToolBroker,
        ToolType,
        ToolPriority,
        ToolStatus,
        ToolRequest,
        ToolResult,
        ToolAnalysis,
        WebSearchTool,
        CalculatorTool,
        CodeExecutionTool,
        KnowledgeBaseTool,
        WebBrowserTool,
        DocumentQATool,
        DatabaseQueryTool,
        ImageGenerationTool,
        get_tool_broker,
        configure_tool_broker,
        check_and_execute_tools,
        # PR4: New exports
        RAGConfig,
        RetrievalMode,
    )
    TOOL_BROKER_AVAILABLE = True
except ImportError:
    TOOL_BROKER_AVAILABLE = False
    ToolBroker = None  # type: ignore
    RAGConfig = None  # type: ignore
    RetrievalMode = None  # type: ignore

# Industry Dominance Controller
try:
    from .dominance_controller import (
        IndustryDominanceController,
        OrchestrationStrategy,
        QueryComplexity as DominanceQueryComplexity,
        QueryType as DominanceQueryType,
        QualityMetrics,
        OrchestrationResult,
        ExecutionPlan,
        QueryAnalyzer,
        StrategySelector,
        create_dominance_controller,
    )
    DOMINANCE_CONTROLLER_AVAILABLE = True
except ImportError:
    DOMINANCE_CONTROLLER_AVAILABLE = False
    IndustryDominanceController = None  # type: ignore

if ELITE_PROMPTS_AVAILABLE:
    __all__.extend([
        "OrchestratorRole",
        "META_CONTROLLER_SYSTEM_PROMPT",
        "ELITE_PLANNER_PROMPT",
        "ELITE_VERIFIER_PROMPT",
        "CHALLENGER_SYSTEM_PROMPT",
        "ELITE_REFINER_PROMPT",
        "ROUTER_SYSTEM_PROMPT",
        "TOOL_BROKER_SYSTEM_PROMPT",
        "get_system_prompt",
        "get_all_prompts",
        "SELF_CONSISTENCY_TEMPLATE",
        "DEBATE_TEMPLATE",
        "FACT_CHECK_TEMPLATE",
        "SYNTHESIS_TEMPLATE",
        "REFLECTION_TEMPLATE",
    ])

if TOOL_BROKER_AVAILABLE:
    __all__.extend([
        "ToolBroker",
        "ToolType",
        "ToolPriority",
        "ToolStatus",
        "ToolRequest",
        "ToolResult",
        "ToolAnalysis",
        "WebSearchTool",
        "CalculatorTool",
        "CodeExecutionTool",
        "KnowledgeBaseTool",
        "WebBrowserTool",
        "DocumentQATool",
        "DatabaseQueryTool",
        "ImageGenerationTool",
        "get_tool_broker",
        "configure_tool_broker",
        "check_and_execute_tools",
        # PR4: New exports
        "RAGConfig",
        "RetrievalMode",
    ])

if DOMINANCE_CONTROLLER_AVAILABLE:
    __all__.extend([
        "IndustryDominanceController",
        "OrchestrationStrategy",
        "DominanceQueryComplexity",
        "DominanceQueryType",
        "QualityMetrics",
        "OrchestrationResult",
        "ExecutionPlan",
        "QueryAnalyzer",
        "StrategySelector",
        "create_dominance_controller",
    ])

# ==================== PERFORMANCE OPTIMIZATION MODULES ====================

# Advanced Reasoning Engine
try:
    from .advanced_reasoning import (
        AdvancedReasoningEngine,
        ReasoningStrategy,
        ReasoningResult,
        ThoughtNode,
        get_reasoning_engine,
    )
    ADVANCED_REASONING_AVAILABLE = True
except ImportError:
    ADVANCED_REASONING_AVAILABLE = False
    AdvancedReasoningEngine = None  # type: ignore
    ReasoningStrategy = None  # type: ignore
    ReasoningResult = None  # type: ignore

# Smart Ensemble
try:
    from .smart_ensemble import (
        SmartEnsemble,
        TaskCategory,
        ModelProfile,
        EnsembleResult,
        get_smart_ensemble,
    )
    SMART_ENSEMBLE_AVAILABLE = True
except ImportError:
    SMART_ENSEMBLE_AVAILABLE = False
    SmartEnsemble = None  # type: ignore
    TaskCategory = None  # type: ignore

# Tool Verification
try:
    from .tool_verification import (
        ToolVerifier,
        VerificationPipeline,
        VerificationType,
        VerificationResult,
        get_verification_pipeline,
    )
    TOOL_VERIFICATION_AVAILABLE = True
except ImportError:
    TOOL_VERIFICATION_AVAILABLE = False
    ToolVerifier = None  # type: ignore
    VerificationPipeline = None  # type: ignore

# Benchmark Strategies
try:
    from .benchmark_strategies import (
        BenchmarkOptimizer,
        BenchmarkType,
        BenchmarkConfig,
        BenchmarkResult,
        BenchmarkRunner,
    )
    BENCHMARK_STRATEGIES_AVAILABLE = True
except ImportError:
    BENCHMARK_STRATEGIES_AVAILABLE = False
    BenchmarkOptimizer = None  # type: ignore
    BenchmarkType = None  # type: ignore

# Performance Controller - The Brain
try:
    from .performance_controller import (
        PerformanceController,
        PerformanceMode,
        PerformanceConfig,
        PerformanceResult,
        create_performance_controller,
        get_performance_controller,
    )
    PERFORMANCE_CONTROLLER_AVAILABLE = True
except ImportError:
    PERFORMANCE_CONTROLLER_AVAILABLE = False
    PerformanceController = None  # type: ignore
    PerformanceMode = None  # type: ignore

# Export performance modules
if ADVANCED_REASONING_AVAILABLE:
    __all__.extend([
        "AdvancedReasoningEngine",
        "ReasoningStrategy",
        "ReasoningResult",
        "ThoughtNode",
        "get_reasoning_engine",
    ])

if SMART_ENSEMBLE_AVAILABLE:
    __all__.extend([
        "SmartEnsemble",
        "TaskCategory",
        "ModelProfile",
        "EnsembleResult",
        "get_smart_ensemble",
    ])

if TOOL_VERIFICATION_AVAILABLE:
    __all__.extend([
        "ToolVerifier",
        "VerificationPipeline",
        "VerificationType",
        "VerificationResult",
        "get_verification_pipeline",
    ])

if BENCHMARK_STRATEGIES_AVAILABLE:
    __all__.extend([
        "BenchmarkOptimizer",
        "BenchmarkType",
        "BenchmarkConfig",
        "BenchmarkResult",
        "BenchmarkRunner",
    ])

if PERFORMANCE_CONTROLLER_AVAILABLE:
    __all__.extend([
        "PerformanceController",
        "PerformanceMode",
        "PerformanceConfig",
        "PerformanceResult",
        "create_performance_controller",
        "get_performance_controller",
    ])

# ==================== NEW ENHANCEMENT MODULES ====================

# Model Config (Data-Driven Model Selection)
try:
    from .model_config import (
        ModelConfigManager,
        ModelCapability as ConfigModelCapability,
        ModelProfile as ConfigModelProfile,
        StrategyConfig,
        get_config_manager,
        get_model_capabilities,
        get_best_models_for_task as config_get_best_models,
    )
    MODEL_CONFIG_AVAILABLE = True
except ImportError:
    MODEL_CONFIG_AVAILABLE = False
    ModelConfigManager = None  # type: ignore
    ConfigModelCapability = None  # type: ignore

# Hierarchical Planning (Enhanced)
try:
    from .hierarchical_planning import (
        HierarchicalPlanner as NewHierarchicalPlanner,
        HierarchicalPlanExecutor as NewHierarchicalPlanExecutor,
        PlanStep,
        ExecutionPlan as NewExecutionPlan,
        PlanResult,
        PlanRole,
        plan_and_execute,
        should_use_hrm,
    )
    NEW_HIERARCHICAL_PLANNING_AVAILABLE = True
except ImportError:
    NEW_HIERARCHICAL_PLANNING_AVAILABLE = False
    NewHierarchicalPlanner = None  # type: ignore
    PlanStep = None  # type: ignore
    PlanRole = None  # type: ignore

# Consensus Manager (Multi-Model Synthesis)
try:
    from .consensus_manager import (
        ConsensusManager,
        ConsensusMethod,
        ConsensusResult,
        ModelResponse as ConsensusModelResponse,
        synthesize_responses,
        calculate_agreement,
    )
    CONSENSUS_MANAGER_AVAILABLE = True
except ImportError:
    CONSENSUS_MANAGER_AVAILABLE = False
    ConsensusManager = None  # type: ignore
    ConsensusMethod = None  # type: ignore

# Export new modules
if MODEL_CONFIG_AVAILABLE:
    __all__.extend([
        "ModelConfigManager",
        "ConfigModelCapability",
        "ConfigModelProfile",
        "StrategyConfig",
        "get_config_manager",
        "get_model_capabilities",
        "config_get_best_models",
    ])

if NEW_HIERARCHICAL_PLANNING_AVAILABLE:
    __all__.extend([
        "NewHierarchicalPlanner",
        "NewHierarchicalPlanExecutor",
        "PlanStep",
        "NewExecutionPlan",
        "PlanResult",
        "PlanRole",
        "plan_and_execute",
        "should_use_hrm",
    ])

if CONSENSUS_MANAGER_AVAILABLE:
    __all__.extend([
        "ConsensusManager",
        "ConsensusMethod",
        "ConsensusResult",
        "ConsensusModelResponse",
        "synthesize_responses",
        "calculate_agreement",
    ])

# ==================== OPENROUTER INTEGRATION ====================

# OpenRouter Model Selector (Dynamic Rankings)
try:
    from .openrouter_selector import (
        OpenRouterModelSelector,
        SelectionStrategy,
        TaskDomain,
        SelectedModel,
        SelectionResult,
        get_openrouter_selector,
        select_models_dynamic,
    )
    OPENROUTER_SELECTOR_AVAILABLE = True
except ImportError:
    OPENROUTER_SELECTOR_AVAILABLE = False
    OpenRouterModelSelector = None  # type: ignore
    SelectionStrategy = None  # type: ignore
    TaskDomain = None  # type: ignore

# Dynamic model selection via adaptive router
try:
    from .adaptive_router import select_models_dynamic as adaptive_select_dynamic
    DYNAMIC_ROUTING_AVAILABLE = True
except ImportError:
    DYNAMIC_ROUTING_AVAILABLE = False
    adaptive_select_dynamic = None  # type: ignore

if OPENROUTER_SELECTOR_AVAILABLE:
    __all__.extend([
        "OpenRouterModelSelector",
        "SelectionStrategy",
        "TaskDomain",
        "SelectedModel",
        "SelectionResult",
        "get_openrouter_selector",
        "select_models_dynamic",
    ])

if DYNAMIC_ROUTING_AVAILABLE:
    __all__.extend([
        "adaptive_select_dynamic",
    ])

# ==================== STRATEGY MEMORY (PR2) ====================

# Strategy Memory Module
try:
    from .strategy_memory import (
        StrategyMemory,
        StrategyProfile,
        ModelTeamRecord,
        get_strategy_memory,
        record_strategy_outcome,
        recommend_strategy,
    )
    STRATEGY_MEMORY_AVAILABLE = True
except ImportError:
    STRATEGY_MEMORY_AVAILABLE = False
    StrategyMemory = None  # type: ignore
    StrategyProfile = None  # type: ignore
    ModelTeamRecord = None  # type: ignore
    get_strategy_memory = None  # type: ignore
    record_strategy_outcome = None  # type: ignore
    recommend_strategy = None  # type: ignore

if STRATEGY_MEMORY_AVAILABLE:
    __all__.extend([
        "StrategyMemory",
        "StrategyProfile",
        "ModelTeamRecord",
        "get_strategy_memory",
        "record_strategy_outcome",
        "recommend_strategy",
    ])

# ==================== REFINEMENT LOOP (PR3) ====================

# Refinement Loop Controller
try:
    from .refinement_loop import (
        RefinementLoopController,
        RefinementResult,
        RefinementConfig,
        RefinementStrategy,
        RefinementIteration,
        LoopStatus,
        IssueType,
        VerificationIssue,
        run_refinement_loop,
        create_refinement_controller,
        refine_on_failure,
        RefinementOnFailure,
    )
    REFINEMENT_LOOP_AVAILABLE = True
except ImportError:
    REFINEMENT_LOOP_AVAILABLE = False
    RefinementLoopController = None  # type: ignore
    RefinementResult = None  # type: ignore
    RefinementConfig = None  # type: ignore
    RefinementStrategy = None  # type: ignore
    LoopStatus = None  # type: ignore
    refine_on_failure = None  # type: ignore
    RefinementOnFailure = None  # type: ignore

if REFINEMENT_LOOP_AVAILABLE:
    __all__.extend([
        "RefinementLoopController",
        "RefinementResult",
        "RefinementConfig",
        "RefinementStrategy",
        "RefinementIteration",
        "LoopStatus",
        "IssueType",
        "VerificationIssue",
        "run_refinement_loop",
        "create_refinement_controller",
        "refine_on_failure",
        "RefinementOnFailure",
    ])
