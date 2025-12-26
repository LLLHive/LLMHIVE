"""
LLMHive ModelDB Enrichers Package

Modular enrichers that add data to the model catalog from various sources.
Each enricher takes a DataFrame and returns an enriched DataFrame with new columns.

RULES FOR ALL ENRICHERS:
1. NEVER drop rows
2. NEVER drop columns
3. NEVER overwrite non-null values with null
4. Always add provenance columns for new data
5. Use consistent naming: <source>_<metric>_<detail>
"""

from .base import BaseEnricher, EnricherResult
from .openrouter_rankings import OpenRouterRankingsEnricher
from .lmsys_arena import LMSYSArenaEnricher
from .hf_open_llm_leaderboard import HFLeaderboardEnricher
from .provider_docs_extract import ProviderDocsEnricher
from .derived_rankings import DerivedRankingsEnricher

# Optional enrichers (require API calls with cost)
try:
    from .eval_harness import EvalHarnessEnricher
    EVAL_HARNESS_AVAILABLE = True
except ImportError:
    EVAL_HARNESS_AVAILABLE = False

try:
    from .telemetry_probe import TelemetryProbeEnricher
    TELEMETRY_PROBE_AVAILABLE = True
except ImportError:
    TELEMETRY_PROBE_AVAILABLE = False

__all__ = [
    "BaseEnricher",
    "EnricherResult",
    "OpenRouterRankingsEnricher",
    "LMSYSArenaEnricher",
    "HFLeaderboardEnricher",
    "ProviderDocsEnricher",
    "DerivedRankingsEnricher",
    "EVAL_HARNESS_AVAILABLE",
    "TELEMETRY_PROBE_AVAILABLE",
]

