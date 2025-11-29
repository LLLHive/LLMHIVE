"""Orchestration modules for LLMHive."""

from .blackboard import Blackboard
from .hrm import (
    HRMRegistry,
    HRMRole,
    RoleLevel,
    RolePermission,
    get_hrm_registry,
)

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

if PROMPT_DIFFUSION_AVAILABLE:
    __all__.extend(["PromptDiffusion", "DiffusionResult", "PromptVersion"])

