"""Pricing tier system for LLMHive monetization."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class TierName(str, Enum):
    """Pricing tier names."""

    FREE = "free"
    LITE = "lite"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"
    MAXIMUM = "maximum"  # NEW: Full power tier - crush competition


class OrchestrationTier(str, Enum):
    """Orchestration quality tiers - maps to elite_orchestration.py."""
    
    BUDGET = "budget"      # $0.0036/query - Claude Sonnet primary, #1 in 6 categories
    STANDARD = "standard"  # $0.0060/query - Mixed routing, #1 in 8 categories
    PREMIUM = "premium"    # $0.0108/query - GPT-5.2 access, #1 in ALL categories
    ELITE = "elite"        # $0.0150/query - Multi-consensus + verification
    MAXIMUM = "maximum"    # $0.0250/query - 5-model consensus, mission-critical


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
    
    # NEW: Orchestration tier configuration (January 2026)
    default_orchestration_tier: str = "budget"  # Default quality level
    premium_escalation_budget: int = 0  # How many queries can use PREMIUM tier
    elite_escalation_budget: int = 0  # How many queries can use ELITE tier
    max_passes_per_month: int = 0  # Full pipeline runs (consensus + verification)
    memory_retention_days: int = 0  # How long to retain conversation memory
    calculator_enabled: bool = True  # Calculator is ALWAYS on (our key differentiator)
    reranker_enabled: bool = True  # Pinecone reranker is ALWAYS on


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
        """Initialize default pricing tiers aligned with Elite Orchestration (Jan 2026)."""
        
        # Free Trial (7 days) - WOW introduction with PREMIUM default
        free_tier = PricingTier(
            name=TierName.FREE,
            display_name="Free Trial",
            monthly_price_usd=0.0,
            annual_price_usd=0.0,
            limits=TierLimits(
                max_requests_per_month=50,  # 50 total during trial
                max_tokens_per_month=150_000,
                max_models_per_request=3,
                max_concurrent_requests=1,
                max_storage_mb=100,
                enable_advanced_features=False,
                enable_api_access=False,
                enable_priority_support=False,
                max_team_members=1,
                allow_parallel_retrieval=False,
                allow_deep_conf=False,
                allow_prompt_diffusion=False,
                allow_adaptive_ensemble=False,
                allow_hrm=False,
                allow_loopback_refinement=False,
                max_tokens_per_query=10_000,
                # Orchestration: PREMIUM default so they see the magic
                default_orchestration_tier="premium",
                premium_escalation_budget=50,  # All queries use premium
                elite_escalation_budget=10,
                max_passes_per_month=5,
                memory_retention_days=0,  # Session only
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={"basic_orchestration", "memory", "calculator", "reranker"},
            description="7-day free trial - experience #1 AI quality",
        )
        
        # Lite Tier ($9.99/mo) - #1 ELITE orchestration for everyone
        lite_tier = PricingTier(
            name=TierName.LITE,
            display_name="Lite",
            monthly_price_usd=9.99,
            annual_price_usd=99.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=800,  # Total effective queries
                max_tokens_per_month=1_000_000,
                max_models_per_request=5,
                max_concurrent_requests=2,
                max_storage_mb=500,
                enable_advanced_features=False,
                enable_api_access=False,
                enable_priority_support=False,
                max_team_members=1,
                allow_parallel_retrieval=True,
                allow_deep_conf=False,
                allow_prompt_diffusion=False,
                allow_adaptive_ensemble=True,
                allow_hrm=True,  # Light HRM
                allow_loopback_refinement=False,
                max_tokens_per_query=25_000,
                # NEW: ELITE orchestration available to Lite!
                default_orchestration_tier="elite",  # #1 quality as DEFAULT
                premium_escalation_budget=200,  # Additional PREMIUM queries
                elite_escalation_budget=100,  # 100 full ELITE queries/month
                max_passes_per_month=50,  # Deep reasoning passes
                memory_retention_days=7,
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "calculator", "reranker", "consensus_voting",
                "elite_orchestration", "multi_model_routing"
            },
            description="#1 AI quality for $9.99 - ELITE orchestration included",
        )

        # Pro Tier ($29.99/mo) - Full power, #1 in ALL categories
        pro_tier = PricingTier(
            name=TierName.PRO,
            display_name="Pro",
            monthly_price_usd=29.99,
            annual_price_usd=299.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=2_000,
                max_tokens_per_month=5_000_000,
                max_models_per_request=5,
                max_concurrent_requests=5,
                max_storage_mb=5_000,
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=False,
                max_team_members=1,
                # Pro tier - all advanced features enabled
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=100_000,
                # Orchestration: STANDARD default with PREMIUM/ELITE escalation
                default_orchestration_tier="standard",
                premium_escalation_budget=500,
                elite_escalation_budget=100,
                max_passes_per_month=200,
                memory_retention_days=30,
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus"
            },
            description="AI command center - #1 in ALL 10 categories",
        )
        
        # Team Tier ($49.99/mo, 3 seats) - Collaborative workspace
        team_tier = PricingTier(
            name=TierName.TEAM,
            display_name="Team",
            monthly_price_usd=49.99,
            annual_price_usd=499.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=5_000,  # Pooled
                max_tokens_per_month=10_000_000,  # Pooled
                max_models_per_request=5,
                max_concurrent_requests=10,
                max_storage_mb=20_000,
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=False,
                max_team_members=3,
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=100_000,
                # Orchestration: STANDARD default, pooled budgets
                default_orchestration_tier="standard",
                premium_escalation_budget=1_000,
                elite_escalation_budget=200,
                max_passes_per_month=500,
                memory_retention_days=90,
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus", "team_workspace",
                "shared_memory", "team_projects", "admin_dashboard"
            },
            description="Team workspace with pooled intelligence",
        )

        # Enterprise Standard ($25/seat/mo, min 5 seats)
        enterprise_tier = PricingTier(
            name=TierName.ENTERPRISE,
            display_name="Enterprise",
            monthly_price_usd=25.0,  # Per seat
            annual_price_usd=250.0,  # Per seat, ~17% discount
            limits=TierLimits(
                max_requests_per_month=1_000,  # Per seat
                max_tokens_per_month=2_000_000,  # Per seat
                max_models_per_request=10,
                max_concurrent_requests=20,
                max_storage_mb=0,  # Unlimited org-wide
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=True,
                max_team_members=0,  # Unlimited (seat-based)
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=0,  # Unlimited
                # Orchestration: PREMIUM default for enterprise
                default_orchestration_tier="premium",
                premium_escalation_budget=0,  # Unlimited premium
                elite_escalation_budget=200,  # Per seat
                max_passes_per_month=0,  # Unlimited
                memory_retention_days=365,  # 1 year
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus", "team_workspace",
                "shared_memory", "team_projects", "admin_dashboard",
                "sso", "audit_logs", "compliance", "sla_995"
            },
            description="Enterprise with SSO, compliance, and SLA",
        )
        
        # Enterprise Plus ($45/seat/mo, min 5 seats)
        enterprise_plus_tier = PricingTier(
            name=TierName.ENTERPRISE_PLUS,
            display_name="Enterprise Plus",
            monthly_price_usd=45.0,  # Per seat
            annual_price_usd=450.0,  # Per seat, ~17% discount
            limits=TierLimits(
                max_requests_per_month=2_500,  # Per seat
                max_tokens_per_month=5_000_000,  # Per seat
                max_models_per_request=10,
                max_concurrent_requests=50,
                max_storage_mb=0,  # Unlimited
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=True,
                max_team_members=0,  # Unlimited
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=0,  # Unlimited
                # Orchestration: ELITE default for enterprise plus
                default_orchestration_tier="elite",
                premium_escalation_budget=0,  # Unlimited
                elite_escalation_budget=0,  # Unlimited elite
                max_passes_per_month=0,  # Unlimited
                memory_retention_days=0,  # Unlimited (compliance-defined)
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus", "team_workspace",
                "shared_memory", "team_projects", "admin_dashboard",
                "sso", "audit_logs", "compliance", "sla_999",
                "custom_routing_policies", "dedicated_support",
                "custom_integrations", "webhooks", "priority_routing"
            },
            description="Enterprise Plus with ELITE orchestration and custom policies",
        )

        # MAXIMUM Tier ($499/mo) - Full power, crush competition by maximum margin
        # Target: Hedge funds, legal, healthcare, government, mission-critical
        maximum_tier = PricingTier(
            name=TierName.MAXIMUM,
            display_name="Maximum",
            monthly_price_usd=499.0,
            annual_price_usd=4_990.0,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=1_000,  # 1000 full-power queries
                max_tokens_per_month=50_000_000,
                max_models_per_request=10,
                max_concurrent_requests=20,
                max_storage_mb=100_000,  # 100GB
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=True,
                max_team_members=10,
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=0,  # Unlimited
                # MAXIMUM Orchestration: Full power, no limits
                default_orchestration_tier="maximum",
                premium_escalation_budget=0,  # Unlimited
                elite_escalation_budget=0,  # Unlimited
                max_passes_per_month=0,  # Unlimited
                memory_retention_days=365,
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus", "team_workspace",
                "shared_memory", "team_projects", "admin_dashboard",
                "sso", "audit_logs", "compliance", "sla_999",
                "custom_routing_policies", "dedicated_support",
                "maximum_orchestration", "multi_model_consensus",
                "verification_loops", "reflection_chains",
                "mission_critical_support", "priority_escalation"
            },
            description="MAXIMUM power - crush competition by +5% margin average",
        )

        self.tiers[TierName.FREE] = free_tier
        self.tiers[TierName.LITE] = lite_tier
        self.tiers[TierName.PRO] = pro_tier
        self.tiers[TierName.TEAM] = team_tier
        self.tiers[TierName.ENTERPRISE] = enterprise_tier
        self.tiers[TierName.ENTERPRISE_PLUS] = enterprise_plus_tier
        self.tiers[TierName.MAXIMUM] = maximum_tier

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

