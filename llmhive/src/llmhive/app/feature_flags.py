"""Feature flags for LLMHive.

This module provides feature flags to control which features are enabled.
Features can be toggled via environment variables or configuration.

USAGE:
    from .feature_flags import FeatureFlags, is_feature_enabled
    
    if is_feature_enabled(FeatureFlags.SMS_OTP):
        # SMS OTP code path
        pass
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureFlags(str, Enum):
    """Available feature flags."""
    
    # Authentication features
    SMS_OTP = "sms_otp"  # SMS-based OTP login (requires Clerk/Twilio config)
    
    # Collaboration features
    GROUP_CHAT = "group_chat"  # Multi-user real-time collaboration
    GROUP_PROJECTS = "group_projects"  # Multi-user project cooperation
    
    # Memory features
    VECTOR_MEMORY = "vector_memory"  # Long-term vector DB storage
    CROSS_SESSION_REUSE = "cross_session_reuse"  # Reuse answers across sessions
    
    # Learning features
    ADAPTIVE_ROUTING = "adaptive_routing"  # Performance-based model routing
    WEEKLY_OPTIMIZATION = "weekly_optimization"  # Weekly improvement jobs
    
    # Advanced orchestration
    DEEP_CONSENSUS = "deep_consensus"  # Multi-model consensus building
    PROMPT_DIFFUSION = "prompt_diffusion"  # Advanced prompt optimization


# Default feature states (can be overridden by env vars)
DEFAULT_FEATURE_STATES: Dict[FeatureFlags, bool] = {
    # Disabled by default (not fully implemented or tested)
    FeatureFlags.SMS_OTP: False,
    FeatureFlags.GROUP_CHAT: False,
    FeatureFlags.GROUP_PROJECTS: False,
    FeatureFlags.VECTOR_MEMORY: False,
    FeatureFlags.CROSS_SESSION_REUSE: False,
    FeatureFlags.WEEKLY_OPTIMIZATION: False,
    
    # Enabled by default (stable features)
    FeatureFlags.ADAPTIVE_ROUTING: True,
    FeatureFlags.DEEP_CONSENSUS: True,
    FeatureFlags.PROMPT_DIFFUSION: False,
}


def is_feature_enabled(flag: FeatureFlags) -> bool:
    """Check if a feature flag is enabled.
    
    Features can be enabled/disabled via environment variables:
    - FEATURE_SMS_OTP=true/false
    - FEATURE_GROUP_CHAT=true/false
    etc.
    
    Args:
        flag: The feature flag to check
        
    Returns:
        True if the feature is enabled, False otherwise
    """
    # Check environment variable first (allows runtime override)
    env_var = f"FEATURE_{flag.value.upper()}"
    env_value = os.getenv(env_var)
    
    if env_value is not None:
        enabled = env_value.lower() in ("true", "1", "yes", "on")
        logger.debug("Feature %s: %s (from env %s)", flag.value, enabled, env_var)
        return enabled
    
    # Fall back to default state
    default = DEFAULT_FEATURE_STATES.get(flag, False)
    logger.debug("Feature %s: %s (default)", flag.value, default)
    return default


def get_all_feature_states() -> Dict[str, bool]:
    """Get the current state of all feature flags.
    
    Returns:
        Dictionary mapping feature names to their enabled state
    """
    return {
        flag.value: is_feature_enabled(flag)
        for flag in FeatureFlags
    }


def log_feature_states() -> None:
    """Log all feature flag states for debugging."""
    states = get_all_feature_states()
    enabled = [k for k, v in states.items() if v]
    disabled = [k for k, v in states.items() if not v]
    
    logger.info("Feature flags - Enabled: %s", enabled)
    logger.info("Feature flags - Disabled: %s", disabled)

