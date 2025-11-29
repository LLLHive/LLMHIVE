"""Pricing tier system for LLMHive monetization."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class TierName(str, Enum):
    """Pricing tier names."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(slots=True)
class TierLimits:
    """Usage limits for a pricing tier.
    
    Subscription tiers: Extended with feature flags for advanced orchestration features.
    """

    max_requests_per_month: int = 0  # 0 = unlimited
    max_tokens_per_month: int = 0  # 0 = unlimited
    max_models_per_request: int = 1
    max_concurrent_requests: int = 1
    max_storage_mb: int = 0  # 0 = unlimited
    enable_advanced_features: bool = False
    enable_api_access: bool = False
    enable_priority_support: bool = False
    max_team_members: int = 1
    # Subscription tiers: Feature flags for advanced orchestration
    allow_parallel_retrieval: bool = False  # Parallel evidence retrieval
    allow_deep_conf: bool = False  # Deep Consensus Framework
    allow_prompt_diffusion: bool = False  # Prompt Diffusion refinement
    allow_adaptive_ensemble: bool = False  # Adaptive Ensemble Logic
    allow_hrm: bool = False  # Hierarchical Role Management
    allow_loopback_refinement: bool = False  # Loop-back refinement on verification failure
    max_tokens_per_query: int = 0  # 0 = unlimited tokens per query


@dataclass(slots=True)
class PricingTier:
    """Represents a pricing tier with features and limits."""

    name: TierName
    display_name: str
    monthly_price_usd: float
    annual_price_usd: float  # Annual price (usually discounted)
    limits: TierLimits
    features: Set[str] = field(default_factory=set)
    description: str = ""

    def has_feature(self, feature: str) -> bool:
        """Check if this tier includes a specific feature."""
        return feature in self.features

    def can_use_feature(self, feature: str) -> bool:
        """Check if this tier can use a feature (either included or advanced features enabled)."""
        if feature in self.features:
            return True
        if self.limits.enable_advanced_features:
            # Advanced features include: HRM, Prompt Diffusion, DeepConf, Adaptive Ensemble
            advanced_features = {"hrm", "prompt-diffusion", "deep-conf", "adaptive-ensemble"}
            return feature in advanced_features
        return False


class PricingTierManager:
    """Manages pricing tiers and feature access."""

    def __init__(self) -> None:
        self.tiers: Dict[TierName, PricingTier] = {}
        self._initialize_default_tiers()

    def _initialize_default_tiers(self) -> None:
        """Initialize default pricing tiers."""
        # Free Tier
        free_tier = PricingTier(
            name=TierName.FREE,
            display_name="Free",
            monthly_price_usd=0.0,
            annual_price_usd=0.0,
            limits=TierLimits(
                max_requests_per_month=100,
                max_tokens_per_month=100_000,
                max_models_per_request=2,
                max_concurrent_requests=1,
                max_storage_mb=100,
                enable_advanced_features=False,
                enable_api_access=False,
                enable_priority_support=False,
                max_team_members=1,
                # Subscription tiers: Free tier - no advanced features
                allow_parallel_retrieval=False,
                allow_deep_conf=False,
                allow_prompt_diffusion=False,
                allow_adaptive_ensemble=False,
                allow_hrm=False,
                allow_loopback_refinement=False,
                max_tokens_per_query=10_000,  # 10K tokens per query limit
            ),
            features={"basic_orchestration", "memory", "knowledge_base"},
            description="Perfect for trying out LLMHive",
        )

        # Pro Tier
        pro_tier = PricingTier(
            name=TierName.PRO,
            display_name="Pro",
            monthly_price_usd=29.99,
            annual_price_usd=299.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=10_000,
                max_tokens_per_month=10_000_000,
                max_models_per_request=5,
                max_concurrent_requests=5,
                max_storage_mb=10_000,
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=False,
                max_team_members=5,
                # Subscription tiers: Pro tier - all advanced features enabled
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=100_000,  # 100K tokens per query
            ),
            features={
                "basic_orchestration",
                "memory",
                "knowledge_base",
                "advanced_orchestration",
                "hrm",
                "prompt_diffusion",
                "deepconf",
                "adaptive_ensemble",
                "api_access",
                "web_research",
                "fact_checking",
            },
            description="For professionals and small teams",
        )

        # Enterprise Tier
        enterprise_tier = PricingTier(
            name=TierName.ENTERPRISE,
            display_name="Enterprise",
            monthly_price_usd=199.99,
            annual_price_usd=1999.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=0,  # Unlimited
                max_tokens_per_month=0,  # Unlimited
                max_models_per_request=10,
                max_concurrent_requests=20,
                max_storage_mb=0,  # Unlimited
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=True,
                max_team_members=0,  # Unlimited
                # Subscription tiers: Enterprise tier - all features, unlimited
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=0,  # Unlimited tokens per query
            ),
            features={
                "basic_orchestration",
                "memory",
                "knowledge_base",
                "advanced_orchestration",
                "hrm",
                "prompt_diffusion",
                "deepconf",
                "adaptive_ensemble",
                "api_access",
                "web_research",
                "fact_checking",
                "custom_integrations",
                "sso",
                "audit_logs",
                "dedicated_support",
                "sla",
            },
            description="For large organizations with custom needs",
        )

        self.tiers[TierName.FREE] = free_tier
        self.tiers[TierName.PRO] = pro_tier
        self.tiers[TierName.ENTERPRISE] = enterprise_tier

    def get_tier(self, tier_name: TierName | str) -> Optional[PricingTier]:
        """Get a pricing tier by name."""
        if isinstance(tier_name, str):
            try:
                tier_name = TierName(tier_name.lower())
            except ValueError:
                return None
        return self.tiers.get(tier_name)

    def list_tiers(self) -> List[PricingTier]:
        """List all available pricing tiers."""
        return list(self.tiers.values())

    def can_access_feature(self, tier_name: TierName | str, feature: str) -> bool:
        """Check if a tier can access a specific feature."""
        tier = self.get_tier(tier_name)
        if tier is None:
            return False
        return tier.can_use_feature(feature)

    def check_limits(
        self,
        tier_name: TierName | str,
        *,
        requests_this_month: int = 0,
        tokens_this_month: int = 0,
        models_in_request: int = 1,
        concurrent_requests: int = 1,
        storage_mb: int = 0,
    ) -> Dict[str, bool]:
        """Check if usage is within tier limits.

        Returns a dict with limit checks:
        {
            "within_limits": bool,
            "requests_ok": bool,
            "tokens_ok": bool,
            "models_ok": bool,
            "concurrent_ok": bool,
            "storage_ok": bool,
        }
        """
        tier = self.get_tier(tier_name)
        if tier is None:
            return {
                "within_limits": False,
                "requests_ok": False,
                "tokens_ok": False,
                "models_ok": False,
                "concurrent_ok": False,
                "storage_ok": False,
            }

        limits = tier.limits

        requests_ok = (
            limits.max_requests_per_month == 0
            or requests_this_month < limits.max_requests_per_month
        )
        tokens_ok = (
            limits.max_tokens_per_month == 0
            or tokens_this_month < limits.max_tokens_per_month
        )
        models_ok = models_in_request <= limits.max_models_per_request
        concurrent_ok = concurrent_requests <= limits.max_concurrent_requests
        storage_ok = (
            limits.max_storage_mb == 0 or storage_mb < limits.max_storage_mb
        )

        within_limits = (
            requests_ok and tokens_ok and models_ok and concurrent_ok and storage_ok
        )

        return {
            "within_limits": within_limits,
            "requests_ok": requests_ok,
            "tokens_ok": tokens_ok,
            "models_ok": models_ok,
            "concurrent_ok": concurrent_ok,
            "storage_ok": storage_ok,
        }


# Global pricing manager instance
_pricing_manager: Optional[PricingTierManager] = None


def get_pricing_manager() -> PricingTierManager:
    """Get the global pricing tier manager instance."""
    global _pricing_manager
    if _pricing_manager is None:
        _pricing_manager = PricingTierManager()
    return _pricing_manager

