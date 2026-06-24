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
# 4-TIER STRUCTURE (January 2026): Free, Lite, Pro, Enterprise
# Stage 3: Added multimodal features (image_analysis, audio_transcription, etc.)
TIER_LIMITS: Dict[str, TierLimits] = {
    # Lite / Standard tier ($10/mo) - spend guard controls elite access
    "lite": TierLimits(
        requests_per_minute=10,
        requests_per_day=None,
        enabled_features={
            "basic_orchestration",
            "standard_models",
            "elite_orchestration",  # All tiers get ELITE quality
            "enhanced_memory",
            "calculator",
            "reranker",
        },
        allowed_domain_presets={"general", "coding", "creative"},
    ),
    # Pro / Premium tier ($20/mo) - spend guard controls elite access
    "pro": TierLimits(
        requests_per_minute=30,
        requests_per_day=None,
        enabled_features={
            "basic_orchestration",
            "standard_models",
            "elite_orchestration",
            "advanced_orchestration",
            "deep_verification",
            "enhanced_memory",
            "deep_conf",
            "prompt_diffusion",
            # Multimodal features for Pro tier
            "image_analysis",
            "audio_transcription",
            "document_ocr",
        },
        allowed_domain_presets={"general", "coding", "creative", "research"},
    ),
    # Enterprise tier ($35/seat/mo, min 5 seats) - Organizations
    "enterprise": TierLimits(
        requests_per_minute=60,
        requests_per_day=None,  # Unlimited (seat-based limits apply)
        enabled_features={
            "basic_orchestration",
            "standard_models",
            "elite_orchestration",
            "advanced_orchestration",
            "deep_verification",
            "enhanced_memory",
            "api_access",
            "deep_conf",
            "prompt_diffusion",
            "custom_models",
            "priority_support",
            "sso",
            "audit_logs",
            "compliance",
            # All multimodal features for Enterprise tier
            "image_analysis",
            "audio_transcription",
            "document_ocr",
            "image_generation",
            "video_analysis",
        },
        allowed_domain_presets={"general", "coding", "creative", "research", "medical", "legal"},
    ),
    # Free tier limits
    "free": TierLimits(
        requests_per_minute=5,
        requests_per_day=20,  # Very limited for free tier
        enabled_features={"basic_orchestration", "standard_models", "calculator", "reranker"},
        allowed_domain_presets={"general", "coding", "creative"},
    ),
}


def get_tier_limits(tier: str) -> TierLimits:
    """Get tier limits for a given tier name.
    
    Args:
        tier: Tier name (free, lite, pro, enterprise, or legacy aliases)
        
    Returns:
        TierLimits for the tier, or Free tier limits if tier not found
    """
    try:
        from .middleware.tier_check import normalize_rate_limit_tier

        tier_lower = normalize_rate_limit_tier(tier)
    except Exception:
        tier_lower = (tier or "free").lower()
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

