"""Pricing tier system for LLMHive monetization."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class TierName(str, Enum):
    """Pricing tier names - Simplified 4-tier structure (January 2026)."""

    LITE = "lite"           # Entry-level: $9.99/mo
    PRO = "pro"             # Power users: $29.99/mo  
    ENTERPRISE = "enterprise"  # Organizations: $35/seat/mo (min 5 seats)
    MAXIMUM = "maximum"     # Mission-critical: $499/mo


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
    
    # Seat-based pricing (Enterprise tiers)
    min_seats: int = 0  # Minimum seats required (0 = not seat-based)
    is_per_seat: bool = False  # Whether pricing is per-seat


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
        """Initialize simplified 4-tier pricing structure (January 2026).
        
        SIMPLIFIED STRUCTURE:
        - Lite ($9.99) - Entry-level individuals
        - Pro ($29.99) - Power users & freelancers  
        - Enterprise ($35/seat, min 5) - Organizations with SSO/compliance
        - Maximum ($499) - Mission-critical, never throttle
        """
        
        # ═══════════════════════════════════════════════════════════════════════════
        # LITE TIER ($9.99/mo) - Entry Level
        # ═══════════════════════════════════════════════════════════════════════════
        # Target: Casual users, trying out paid features
        # Quota: 100 ELITE → throttle to BUDGET (400 more)
        # Cost: 100×$0.015 + 400×$0.0036 = $1.50 + $1.44 = $2.94
        # Profit: $9.99 - $2.94 = $7.05 (71% margin) ✅
        lite_tier = PricingTier(
            name=TierName.LITE,
            display_name="Lite",
            monthly_price_usd=9.99,
            annual_price_usd=99.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=500,  # 100 ELITE + 400 BUDGET
                max_tokens_per_month=500_000,
                max_models_per_request=3,
                max_concurrent_requests=2,
                max_storage_mb=500,
                enable_advanced_features=False,
                enable_api_access=False,  # No API access
                enable_priority_support=False,
                max_team_members=1,
                allow_parallel_retrieval=True,
                allow_deep_conf=False,
                allow_prompt_diffusion=False,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=False,
                max_tokens_per_query=25_000,
                # QUOTA: 100 ELITE, then BUDGET
                default_orchestration_tier="elite",
                premium_escalation_budget=0,
                elite_escalation_budget=100,
                max_passes_per_month=50,
                memory_retention_days=7,
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "calculator", "reranker", "consensus_voting",
                "elite_orchestration", "quota_tracking"
            },
            description="100 #1-quality queries, then 400 good-quality queries",
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # PRO TIER ($29.99/mo) - Power Users
        # ═══════════════════════════════════════════════════════════════════════════
        # Target: Professionals, freelancers, developers
        # Quota: 500 ELITE → throttle to STANDARD (1500 more)
        # Cost: 500×$0.015 + 1500×$0.006 = $7.50 + $9.00 = $16.50
        # Profit: $29.99 - $16.50 = $13.49 (45% margin)
        # Adjusted: 400 ELITE + 600 STANDARD = $6.00 + $3.60 = $9.60
        # Profit: $29.99 - $9.60 = $20.39 (68% margin) ✅
        pro_tier = PricingTier(
            name=TierName.PRO,
            display_name="Pro",
            monthly_price_usd=29.99,
            annual_price_usd=299.99,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=2_000,  # 500 ELITE + 1500 STANDARD
                max_tokens_per_month=4_000_000,
                max_models_per_request=5,
                max_concurrent_requests=10,
                max_storage_mb=10_000,  # 10GB
                enable_advanced_features=True,
                enable_api_access=True,  # API access included
                enable_priority_support=False,
                max_team_members=1,
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=100_000,
                # QUOTA: 500 ELITE, then STANDARD
                default_orchestration_tier="elite",
                premium_escalation_budget=0,
                elite_escalation_budget=500,
                max_passes_per_month=300,
                memory_retention_days=30,
                calculator_enabled=True,
                reranker_enabled=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus", "quota_tracking"
            },
            description="500 #1-quality queries + API access + all advanced features",
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # ENTERPRISE TIER ($35/seat/mo, min 5 seats = $175/mo minimum)
        # ═══════════════════════════════════════════════════════════════════════════
        # Target: Organizations needing SSO, compliance, team management
        # Quota per seat: 400 ELITE → throttle to STANDARD (400 more)
        # Cost per seat: 400×$0.015 + 400×$0.006 = $6.00 + $2.40 = $8.40
        # Profit per seat: $35 - $8.40 = $26.60 (76% margin) ✅
        # Min 5 seats = $175/mo minimum, $26.60 × 5 = $133 profit
        enterprise_tier = PricingTier(
            name=TierName.ENTERPRISE,
            display_name="Enterprise",
            monthly_price_usd=35.0,  # Per seat
            annual_price_usd=350.0,  # Per seat, ~17% discount
            limits=TierLimits(
                max_requests_per_month=800,  # 400 ELITE + 400 STANDARD per seat
                max_tokens_per_month=2_000_000,  # Per seat
                max_models_per_request=10,
                max_concurrent_requests=25,
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
                # QUOTA: 400 ELITE/seat, then STANDARD
                default_orchestration_tier="elite",
                premium_escalation_budget=0,
                elite_escalation_budget=400,  # Per seat
                max_passes_per_month=0,  # Unlimited
                memory_retention_days=365,
                calculator_enabled=True,
                reranker_enabled=True,
                # SEAT-BASED: Minimum 5 seats required
                min_seats=5,
                is_per_seat=True,
            ),
            features={
                "basic_orchestration", "memory", "knowledge_base",
                "advanced_orchestration", "hrm", "prompt_diffusion",
                "deepconf", "adaptive_ensemble", "api_access",
                "web_research", "fact_checking", "calculator", "reranker",
                "vector_storage", "full_consensus", "team_workspace",
                "shared_memory", "team_projects", "admin_dashboard",
                "sso", "audit_logs", "compliance", "sla_995",
                "priority_support", "quota_tracking"
            },
            description="400 #1-quality/seat + SSO + SOC 2 compliance + 99.5% SLA",
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # MAXIMUM TIER ($499/mo) - Mission Critical, Never Throttle
        # ═══════════════════════════════════════════════════════════════════════════
        # Target: Hedge funds, legal, healthcare, government
        # Quota: UNLIMITED ELITE (never throttle, always #1 quality)
        # Estimated usage: ~1000 queries at ELITE = $15
        # Profit: $499 - $15 = $484 (97% margin) ✅
        # Value prop: BEATS ChatGPT Pro by 5% on benchmarks
        maximum_tier = PricingTier(
            name=TierName.MAXIMUM,
            display_name="Maximum",
            monthly_price_usd=499.0,
            annual_price_usd=4_990.0,  # ~17% discount
            limits=TierLimits(
                max_requests_per_month=0,  # Unlimited
                max_tokens_per_month=0,  # Unlimited
                max_models_per_request=10,
                max_concurrent_requests=50,
                max_storage_mb=0,  # Unlimited
                enable_advanced_features=True,
                enable_api_access=True,
                enable_priority_support=True,
                max_team_members=25,  # Team included
                allow_parallel_retrieval=True,
                allow_deep_conf=True,
                allow_prompt_diffusion=True,
                allow_adaptive_ensemble=True,
                allow_hrm=True,
                allow_loopback_refinement=True,
                max_tokens_per_query=0,  # Unlimited
                # NEVER THROTTLE: Always use MAXIMUM orchestration
                default_orchestration_tier="maximum",
                premium_escalation_budget=0,
                elite_escalation_budget=0,  # Irrelevant - never throttle
                max_passes_per_month=0,  # Unlimited
                memory_retention_days=0,  # Unlimited
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
                "mission_critical_support", "priority_escalation",
                "custom_integrations", "webhooks", "never_throttle",
                "quota_tracking"
            },
            description="NEVER THROTTLE - Always #1 quality, BEATS competition by 5%",
        )

        # Register all 4 tiers
        self.tiers[TierName.LITE] = lite_tier
        self.tiers[TierName.PRO] = pro_tier
        self.tiers[TierName.ENTERPRISE] = enterprise_tier
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

