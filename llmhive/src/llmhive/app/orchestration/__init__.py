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

# Adaptive Router
try:
    from .adaptive_router import (
        AdaptiveModelRouter,
        AdaptiveRoutingResult,
        ModelScore,
        get_adaptive_router,
        select_models_adaptive,
        infer_domain,
    )
    ADAPTIVE_ROUTING_AVAILABLE = True
except ImportError:
    ADAPTIVE_ROUTING_AVAILABLE = False
    AdaptiveModelRouter = None  # type: ignore
    AdaptiveRoutingResult = None  # type: ignore
    ModelScore = None  # type: ignore

# Prompt Diffusion
try:
    from .prompt_diffusion import PromptDiffusion, DiffusionResult, PromptVersion
    PROMPT_DIFFUSION_AVAILABLE = True
except ImportError:
    PROMPT_DIFFUSION_AVAILABLE = False
    PromptDiffusion = None  # type: ignore
    DiffusionResult = None  # type: ignore
    PromptVersion = None  # type: ignore

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

if ADAPTIVE_ROUTING_AVAILABLE:
    __all__.extend([
        "AdaptiveModelRouter",
        "AdaptiveRoutingResult",
        "ModelScore",
        "get_adaptive_router",
        "select_models_adaptive",
        "infer_domain",
    ])

if PROMPT_DIFFUSION_AVAILABLE:
    __all__.extend(["PromptDiffusion", "DiffusionResult", "PromptVersion"])

