"""Tier limits and capabilities configuration for LLMHive.

This module defines rate limits and feature access for each account tier.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass
class TierLimits:
    """Rate limits and capabilities for an account tier."""

    # Rate limiting: Requests per minute
    requests_per_minute: int
    # Rate limiting: Requests per day (optional, None = unlimited)
    requests_per_day: int | None = None
    # Feature flags: Which features are enabled for this tier
    enabled_features: Set[str] | None = None
    # Domain presets: Which domain presets are available
    allowed_domain_presets: Set[str] | None = None


# Tier Limits: Define limits for each tier
# Stage 3: Added multimodal features (image_analysis, audio_transcription, etc.)
TIER_LIMITS: Dict[str, TierLimits] = {
    "free": TierLimits(
        requests_per_minute=5,
        requests_per_day=100,  # 100 requests per day for Free tier
        enabled_features={"basic_orchestration", "standard_models"},
        allowed_domain_presets={"general", "coding", "creative"},
    ),
    "basic": TierLimits(
        requests_per_minute=10,
        requests_per_day=300,  # 300 requests per day for Basic tier
        enabled_features={
            "basic_orchestration",
            "standard_models",
            "enhanced_memory",
        },
        allowed_domain_presets={"general", "coding", "creative"},
    ),
    "pro": TierLimits(
        requests_per_minute=20,
        requests_per_day=1000,  # 1000 requests per day for Pro tier
        enabled_features={
            "basic_orchestration",
            "standard_models",
            "advanced_orchestration",
            "deep_verification",
            "enhanced_memory",
            # Stage 3: Multimodal features for Pro tier
            "image_analysis",
            "audio_transcription",
            "document_ocr",
        },
        allowed_domain_presets={"general", "coding", "creative", "research"},
    ),
    "enterprise": TierLimits(
        requests_per_minute=60,
        requests_per_day=None,  # Unlimited daily requests for Enterprise
        enabled_features={
            "basic_orchestration",
            "standard_models",
            "advanced_orchestration",
            "deep_verification",
            "enhanced_memory",
            "custom_models",
            "priority_support",
            # Stage 3: All multimodal features for Enterprise tier
            "image_analysis",
            "audio_transcription",
            "document_ocr",
            "image_generation",
            "video_analysis",
        },
        allowed_domain_presets={"general", "coding", "creative", "research", "medical", "legal"},
    ),
}


def get_tier_limits(tier: str) -> TierLimits:
    """Get tier limits for a given tier name.
    
    Args:
        tier: Tier name (free, pro, enterprise)
        
    Returns:
        TierLimits for the tier, or Free tier limits if tier not found
    """
    tier_lower = tier.lower()
    return TIER_LIMITS.get(tier_lower, TIER_LIMITS["free"])


def is_feature_enabled(tier: str, feature: str) -> bool:
    """Check if a feature is enabled for a tier.
    
    Args:
        tier: Tier name (free, pro, enterprise)
        feature: Feature name to check
        
    Returns:
        True if feature is enabled, False otherwise
    """
    limits = get_tier_limits(tier)
    if limits.enabled_features is None:
        return False
    return feature in limits.enabled_features


def is_domain_preset_allowed(tier: str, preset: str) -> bool:
    """Check if a domain preset is allowed for a tier.
    
    Args:
        tier: Tier name (free, pro, enterprise)
        preset: Domain preset name to check
        
    Returns:
        True if preset is allowed, False otherwise
    """
    limits = get_tier_limits(tier)
    if limits.allowed_domain_presets is None:
        return False
    return preset.lower() in limits.allowed_domain_presets

