"""Domain presets configuration for LLMHive orchestrator.

This module defines domain-specific presets (e.g., "General", "Medical", "Legal", "Research")
and associates models with each domain based on their expertise and capabilities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class DomainPreset:
    """Configuration for a domain preset."""
    
    name: str
    display_name: str
    description: str
    preferred_models: List[str]  # Model names prioritized for this domain
    required_capabilities: Set[str]  # Required capabilities for models in this domain
    security_level: str = "standard"  # "standard", "strict", "relaxed"
    enable_fact_checking: bool = True
    enable_deep_verification: bool = False


# Domain Presets: Define presets with model associations
DOMAIN_PRESETS: Dict[str, DomainPreset] = {
    "general": DomainPreset(
        name="general",
        display_name="General",
        description="General-purpose queries with balanced model selection",
        preferred_models=[
            "gpt-4.1",
            "gpt-4o",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "gemini-2.5-flash",
        ],
        required_capabilities={"reasoning", "analysis", "synthesis"},
        security_level="standard",
        enable_fact_checking=True,
        enable_deep_verification=False,
    ),
    "medical": DomainPreset(
        name="medical",
        display_name="Medical",
        description="Medical and healthcare queries requiring accuracy and safety",
        preferred_models=[
            "gpt-4.1",  # Strong reasoning for medical questions
            "claude-3-opus-20240229",  # Excellent for complex medical reasoning
            "gpt-4o",  # Fast and accurate
        ],
        required_capabilities={"reasoning", "analysis", "fact_checking"},
        security_level="strict",  # Strict guardrails for medical content
        enable_fact_checking=True,
        enable_deep_verification=True,  # Extra verification for medical claims
    ),
    "legal": DomainPreset(
        name="legal",
        display_name="Legal",
        description="Legal queries requiring precise reasoning and fact-checking",
        preferred_models=[
            "claude-3-opus-20240229",  # Excellent legal reasoning
            "gpt-4.1",  # Strong analytical capabilities
            "claude-3-sonnet-20240229",  # Good balance
        ],
        required_capabilities={"reasoning", "analysis", "fact_checking", "synthesis"},
        security_level="strict",
        enable_fact_checking=True,
        enable_deep_verification=True,
    ),
    "research": DomainPreset(
        name="research",
        display_name="Research",
        description="Research and academic queries requiring comprehensive analysis",
        preferred_models=[
            "gpt-4.1",
            "claude-3-opus-20240229",
            "gemini-2.5-flash",
            "gpt-4o",
        ],
        required_capabilities={"reasoning", "analysis", "synthesis", "coding"},
        security_level="standard",
        enable_fact_checking=True,
        enable_deep_verification=False,
    ),
    "coding": DomainPreset(
        name="coding",
        display_name="Coding",
        description="Programming and code-related queries",
        preferred_models=[
            "gpt-4.1",
            "gpt-4o",
            "claude-3-opus-20240229",
            "deepseek-chat",
        ],
        required_capabilities={"coding", "reasoning", "analysis"},
        security_level="relaxed",  # Less strict for code
        enable_fact_checking=False,  # Code doesn't need fact-checking
        enable_deep_verification=False,
    ),
    "creative": DomainPreset(
        name="creative",
        display_name="Creative",
        description="Creative writing and content generation",
        preferred_models=[
            "gpt-4.1",
            "claude-3-opus-20240229",
            "gpt-4o",
            "gemini-2.5-flash",
        ],
        required_capabilities={"synthesis", "reasoning"},
        security_level="relaxed",
        enable_fact_checking=False,
        enable_deep_verification=False,
    ),
}


def get_domain_preset(domain: Optional[str]) -> Optional[DomainPreset]:
    """Get domain preset by name (case-insensitive).
    
    Args:
        domain: Domain name (e.g., "medical", "legal", "general")
        
    Returns:
        DomainPreset if found, None otherwise
    """
    if not domain:
        return None
    
    domain_lower = domain.lower().strip()
    return DOMAIN_PRESETS.get(domain_lower)


def list_available_domains() -> List[str]:
    """List all available domain preset names.
    
    Returns:
        List of domain preset names
    """
    return list(DOMAIN_PRESETS.keys())


def get_domain_display_names() -> Dict[str, str]:
    """Get mapping of domain names to display names.
    
    Returns:
        Dictionary mapping domain names to display names
    """
    return {name: preset.display_name for name, preset in DOMAIN_PRESETS.items()}


def filter_models_by_domain(
    available_models: List[str],
    domain: Optional[str],
    model_registry: Optional[object] = None,
) -> List[str]:
    """Filter and prioritize models based on domain preset.
    
    Args:
        available_models: List of available model names
        domain: Domain preset name (e.g., "medical", "legal")
        model_registry: Optional ModelRegistry instance for capability checking
        
    Returns:
        Filtered and prioritized list of models
    """
    if not domain:
        # No domain specified: return all available models
        return available_models
    
    preset = get_domain_preset(domain)
    if not preset:
        logger.warning("Unknown domain preset: %s, using all available models", domain)
        return available_models
    
    # Start with preferred models that are available
    filtered: List[str] = []
    seen: Set[str] = set()
    
    # First, add preferred models that are available
    for model in preset.preferred_models:
        if model in available_models and model not in seen:
            filtered.append(model)
            seen.add(model)
    
    # Then, add other available models that match required capabilities
    if model_registry and hasattr(model_registry, "available_profiles"):
        for profile in model_registry.available_profiles():
            if profile.name in available_models and profile.name not in seen:
                # Check if model has required capabilities
                model_capabilities = set(profile.capabilities)
                if preset.required_capabilities.issubset(model_capabilities):
                    filtered.append(profile.name)
                    seen.add(profile.name)
    
    # Finally, add any remaining available models
    for model in available_models:
        if model not in seen:
            filtered.append(model)
            seen.add(model)
    
    logger.info(
        "Domain preset '%s': Filtered %d models from %d available (prioritized: %d)",
        domain,
        len(filtered),
        len(available_models),
        len([m for m in filtered if m in preset.preferred_models]),
    )
    
    return filtered

