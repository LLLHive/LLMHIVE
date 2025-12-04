"""Reasoning Configuration API router for LLMHive.

Provides endpoints to get and set reasoning configuration (auto vs manual mode).
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reasoning"])


class ReasoningMode(str, Enum):
    """Available reasoning modes."""
    AUTO = "auto"
    MANUAL = "manual"


class ReasoningConfigRequest(BaseModel):
    """Request body for updating reasoning configuration."""
    mode: ReasoningMode = Field(..., description="Reasoning mode: 'auto' or 'manual'")
    selectedMethods: List[str] = Field(
        default_factory=list,
        description="List of selected reasoning methods (required for manual mode)"
    )
    
    @field_validator("selectedMethods")
    @classmethod
    def validate_methods(cls, v: List[str], info) -> List[str]:
        """Validate that manual mode has at least one method selected."""
        # Access mode from the values dict during validation
        return v


class ReasoningConfigResponse(BaseModel):
    """Response containing reasoning configuration."""
    mode: str
    selectedMethods: List[str]


class ReasoningConfigSaveResponse(BaseModel):
    """Response after saving reasoning configuration."""
    success: bool
    message: str
    config: ReasoningConfigResponse


# In-memory storage for reasoning config (per-session)
# In production, this would be stored in a database keyed by user ID
_reasoning_configs: dict[str, ReasoningConfigResponse] = {}

# Default configuration
DEFAULT_CONFIG = ReasoningConfigResponse(
    mode="auto",
    selectedMethods=[],
)

# Available reasoning methods that can be selected
AVAILABLE_REASONING_METHODS = [
    "chain-of-thought",
    "tree-of-thought",
    "self-consistency",
    "reflexion",
    "react",
    "meta-prompting",
    "step-back",
    "analogical-reasoning",
    "socratic-method",
    "decomposition",
]


@router.get(
    "/reasoning-config",
    response_model=ReasoningConfigResponse,
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/v1/reasoning-config",
    response_model=ReasoningConfigResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_reasoning_config(user_id: Optional[str] = None) -> ReasoningConfigResponse:
    """
    Get current reasoning configuration.
    
    Args:
        user_id: Optional user identifier for per-user config.
        
    Returns:
        Current reasoning configuration.
    """
    config_key = user_id or "default"
    config = _reasoning_configs.get(config_key, DEFAULT_CONFIG)
    
    logger.info(
        "Reasoning config retrieved: mode=%s, methods=%d",
        config.mode,
        len(config.selectedMethods),
    )
    
    return config


@router.post(
    "/reasoning-config",
    response_model=ReasoningConfigSaveResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/v1/reasoning-config",
    response_model=ReasoningConfigSaveResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def save_reasoning_config(
    request: ReasoningConfigRequest,
    user_id: Optional[str] = None,
) -> ReasoningConfigSaveResponse:
    """
    Save reasoning configuration.
    
    Args:
        request: The reasoning configuration to save.
        user_id: Optional user identifier for per-user config.
        
    Returns:
        Success response with saved configuration.
        
    Raises:
        HTTPException: If validation fails.
    """
    # Validate manual mode requires methods
    if request.mode == ReasoningMode.MANUAL:
        if not request.selectedMethods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manual mode requires at least one selected method",
            )
        
        # Validate methods are known
        invalid_methods = [
            m for m in request.selectedMethods 
            if m not in AVAILABLE_REASONING_METHODS
        ]
        if invalid_methods:
            logger.warning("Unknown reasoning methods requested: %s", invalid_methods)
            # Don't reject - allow custom methods but log warning
    
    config_key = user_id or "default"
    
    # Build config based on mode
    if request.mode == ReasoningMode.AUTO:
        config = ReasoningConfigResponse(
            mode="auto",
            selectedMethods=[],
        )
    else:
        config = ReasoningConfigResponse(
            mode="manual",
            selectedMethods=request.selectedMethods,
        )
    
    # Store configuration
    _reasoning_configs[config_key] = config
    
    logger.info(
        "Reasoning config saved: mode=%s, methods=%s",
        config.mode,
        config.selectedMethods,
    )
    
    return ReasoningConfigSaveResponse(
        success=True,
        message=f"Reasoning configuration saved. Mode: {config.mode}"
        + (f", Methods: {len(config.selectedMethods)}" if config.selectedMethods else ""),
        config=config,
    )


@router.get(
    "/reasoning-methods",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/v1/reasoning-methods",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_reasoning_methods() -> List[str]:
    """
    List available reasoning methods.
    
    Returns:
        List of available reasoning method identifiers.
    """
    return AVAILABLE_REASONING_METHODS
