"""LLMHive Intelligence Layer — 2026 Orchestration Finalization.

Public API:
  - ModelRegistry2026 / get_model_registry_2026()
  - ELITE_POLICY / get_elite_model() / assert_elite_locked()
  - RoutingEngine / get_routing_engine()
  - VerifyPolicy / get_verify_policy()
  - IntelligenceTelemetry / get_intelligence_telemetry()
  - AdaptiveEnsemble / get_adaptive_ensemble()
  - StrategyDB / get_strategy_db()
  - record_benchmark_run() / print_performance_summary()
  - assert_startup_invariants() / assert_call_invariants()
"""
from .model_registry_2026 import (
    ModelRegistry2026,
    ModelEntry,
    get_model_registry_2026,
    CANONICAL_MODELS,
)
from .elite_policy import (
    ELITE_POLICY,
    get_elite_model,
    get_verify_model,
    assert_elite_locked,
    validate_elite_registry,
    print_elite_config,
    is_benchmark_mode,
    get_intelligence_mode,
)
from .routing_engine import (
    RoutingEngine,
    ScoredModel,
    get_routing_engine,
)
from .verify_policy import (
    VerifyPolicy,
    VerifyTrace,
    VerifyTimeoutError,
    get_verify_policy,
)
from .telemetry import (
    IntelligenceTelemetry,
    IntelligenceTraceEntry,
    get_intelligence_telemetry,
)
from .ensemble import (
    AdaptiveEnsemble,
    Vote,
    EnsembleResult,
    get_adaptive_ensemble,
)
from .strategy_db import (
    StrategyDB,
    get_strategy_db,
)
from .performance_feedback import (
    record_benchmark_run,
    print_performance_summary,
)
from .drift_guard import (
    assert_startup_invariants,
    assert_call_invariants,
    print_drift_status,
    DriftViolation,
)
from .transition_summary import (
    generate_transition_summary,
    save_transition_summary,
)
from .model_validation import (
    validate_all_models,
    save_validation_report,
    print_validation_summary,
)
from .reliability_guard import (
    ReliabilityGuard,
    get_reliability_guard,
)
from .explainability import (
    ExplainabilityRecord,
    ExplainabilityExporter,
    get_explainability_exporter,
)
from .enterprise_readiness import (
    generate_enterprise_readiness,
    generate_board_report,
    save_enterprise_readiness,
    save_board_report,
)
from .team_composer import (
    TeamComposer,
    TeamConfig,
    TeamMember,
    get_team_composer,
)
from .reliability_guard import SLA_TIERS
