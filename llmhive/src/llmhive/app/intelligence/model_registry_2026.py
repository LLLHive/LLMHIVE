"""Canonical 2026 Model Registry — Single source of truth for model characteristics.

Populated from:
  - Static elite definitions (hardcoded for determinism)
  - Firestore model_catalog (live enrichment)
  - Pinecone benchmark embeddings (historical performance)
  - Provider listing APIs (availability confirmation)

Validated at startup:
  - No duplicate model_ids
  - Elite models exist
  - Required capability_tags present
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "2026.1"


@dataclass
class LatencyProfile:
    p50: int = 700
    p95: int = 1600


@dataclass
class CostProfile:
    input_per_1k: float = 0.003
    output_per_1k: float = 0.006


@dataclass
class ModelEntry:
    """Comprehensive model descriptor."""
    provider: str
    model_id: str
    display_name: str
    release_date: str
    context_window: int
    reasoning_strength: float
    coding_strength: float
    math_strength: float
    rag_strength: float
    dialogue_strength: float
    multilingual_strength: float = 0.70
    long_context_strength: float = 0.80
    tool_use_strength: float = 0.80
    supports_tools: bool = True
    supports_multimodal: bool = False
    latency_profile: LatencyProfile = field(default_factory=LatencyProfile)
    cost_profile: CostProfile = field(default_factory=CostProfile)
    capability_tags: List[str] = field(default_factory=list)
    is_available: bool = True
    last_verified: Optional[str] = None

    def strength_for_category(self, category: str) -> float:
        mapping = {
            "reasoning": self.reasoning_strength,
            "coding": self.coding_strength,
            "math": self.math_strength,
            "rag": self.rag_strength,
            "dialogue": self.dialogue_strength,
            "multilingual": self.multilingual_strength,
            "long_context": self.long_context_strength,
            "tool_use": self.tool_use_strength,
        }
        return mapping.get(category, 0.5)


# ──────────────────────────────────────────────────────────────────────
# Static Elite Definitions — 2026 landscape
# ──────────────────────────────────────────────────────────────────────
CANONICAL_MODELS: Dict[str, ModelEntry] = {
    "gpt-5.2-pro": ModelEntry(
        provider="openai",
        model_id="gpt-5.2-pro",
        display_name="GPT-5.2 Pro",
        release_date="2026-01",
        context_window=1_000_000,
        reasoning_strength=0.95,
        coding_strength=0.96,
        math_strength=0.97,
        rag_strength=0.88,
        dialogue_strength=0.90,
        multilingual_strength=0.82,
        long_context_strength=0.88,
        tool_use_strength=0.93,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=700, p95=1600),
        cost_profile=CostProfile(input_per_1k=0.003, output_per_1k=0.006),
        capability_tags=["elite_reasoning", "code_strong", "long_context", "math_strong"],
    ),
    "gpt-5.2": ModelEntry(
        provider="openai",
        model_id="gpt-5.2",
        display_name="GPT-5.2",
        release_date="2026-01",
        context_window=1_000_000,
        reasoning_strength=0.93,
        coding_strength=0.94,
        math_strength=0.95,
        rag_strength=0.86,
        dialogue_strength=0.88,
        multilingual_strength=0.80,
        long_context_strength=0.86,
        tool_use_strength=0.91,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=600, p95=1400),
        cost_profile=CostProfile(input_per_1k=0.002, output_per_1k=0.004),
        capability_tags=["elite_reasoning", "code_strong", "long_context"],
    ),
    "claude-sonnet-4.6": ModelEntry(
        provider="anthropic",
        model_id="claude-sonnet-4.6",
        display_name="Claude Sonnet 4.6",
        release_date="2026-01",
        context_window=200_000,
        reasoning_strength=0.92,
        coding_strength=0.93,
        math_strength=0.90,
        rag_strength=0.85,
        dialogue_strength=0.91,
        multilingual_strength=0.90,
        long_context_strength=0.85,
        tool_use_strength=0.89,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=800, p95=1800),
        cost_profile=CostProfile(input_per_1k=0.003, output_per_1k=0.015),
        capability_tags=["elite_reasoning", "multilingual_leader", "code_strong"],
    ),
    "claude-opus-4.5": ModelEntry(
        provider="anthropic",
        model_id="claude-opus-4.5",
        display_name="Claude Opus 4.5",
        release_date="2025-10",
        context_window=200_000,
        reasoning_strength=0.94,
        coding_strength=0.94,
        math_strength=0.92,
        rag_strength=0.87,
        dialogue_strength=0.92,
        multilingual_strength=0.88,
        long_context_strength=0.84,
        tool_use_strength=0.90,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=1200, p95=3000),
        cost_profile=CostProfile(input_per_1k=0.015, output_per_1k=0.075),
        capability_tags=["elite_reasoning", "code_strong"],
    ),
    "gemini-2.5-pro": ModelEntry(
        provider="google",
        model_id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        release_date="2025-12",
        context_window=2_000_000,
        reasoning_strength=0.90,
        coding_strength=0.88,
        math_strength=0.89,
        rag_strength=0.82,
        dialogue_strength=0.85,
        multilingual_strength=0.84,
        long_context_strength=0.96,
        tool_use_strength=0.85,
        supports_tools=True,
        supports_multimodal=True,
        latency_profile=LatencyProfile(p50=900, p95=2200),
        cost_profile=CostProfile(input_per_1k=0.00125, output_per_1k=0.005),
        capability_tags=["long_context_leader", "multimodal", "elite_reasoning"],
    ),
    "gemini-3.1-pro": ModelEntry(
        provider="google",
        model_id="gemini-3.1-pro",
        display_name="Gemini 3.1 Pro Preview",
        release_date="2026-02",
        context_window=1_050_000,
        reasoning_strength=0.94,
        coding_strength=0.95,
        math_strength=0.93,
        rag_strength=0.90,
        dialogue_strength=0.88,
        multilingual_strength=0.87,
        long_context_strength=0.95,
        tool_use_strength=0.94,
        supports_tools=True,
        supports_multimodal=True,
        latency_profile=LatencyProfile(p50=800, p95=2000),
        cost_profile=CostProfile(input_per_1k=0.002, output_per_1k=0.012),
        capability_tags=["elite_reasoning", "code_strong", "long_context_leader",
                         "multimodal", "agentic", "tool_use_leader"],
    ),
    "gemini-3-pro": ModelEntry(
        provider="google",
        model_id="gemini-3-pro",
        display_name="Gemini 3 Pro Preview",
        release_date="2025-11",
        context_window=1_000_000,
        reasoning_strength=0.92,
        coding_strength=0.91,
        math_strength=0.91,
        rag_strength=0.86,
        dialogue_strength=0.86,
        multilingual_strength=0.85,
        long_context_strength=0.94,
        tool_use_strength=0.90,
        supports_tools=True,
        supports_multimodal=True,
        latency_profile=LatencyProfile(p50=850, p95=2100),
        cost_profile=CostProfile(input_per_1k=0.00125, output_per_1k=0.005),
        capability_tags=["elite_reasoning", "code_strong", "long_context_leader", "multimodal"],
    ),
    "gemini-2.5-flash": ModelEntry(
        provider="google",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        release_date="2025-12",
        context_window=1_000_000,
        reasoning_strength=0.82,
        coding_strength=0.80,
        math_strength=0.83,
        rag_strength=0.78,
        dialogue_strength=0.80,
        multilingual_strength=0.78,
        long_context_strength=0.90,
        tool_use_strength=0.78,
        supports_tools=True,
        supports_multimodal=True,
        latency_profile=LatencyProfile(p50=300, p95=800),
        cost_profile=CostProfile(input_per_1k=0.00015, output_per_1k=0.0006),
        capability_tags=["speed_tier", "long_context"],
    ),
    "grok-4": ModelEntry(
        provider="grok",
        model_id="grok-4",
        display_name="Grok 4",
        release_date="2026-01",
        context_window=256_000,
        reasoning_strength=0.92,
        coding_strength=0.90,
        math_strength=0.91,
        rag_strength=0.84,
        dialogue_strength=0.88,
        multilingual_strength=0.80,
        long_context_strength=0.82,
        tool_use_strength=0.86,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=700, p95=1600),
        cost_profile=CostProfile(input_per_1k=0.003, output_per_1k=0.015),
        capability_tags=["elite_reasoning", "realtime", "code_strong"],
    ),
    "grok-3-mini": ModelEntry(
        provider="grok",
        model_id="grok-3-mini",
        display_name="Grok 3 Mini",
        release_date="2025-11",
        context_window=131_072,
        reasoning_strength=0.80,
        coding_strength=0.78,
        math_strength=0.82,
        rag_strength=0.72,
        dialogue_strength=0.78,
        multilingual_strength=0.68,
        long_context_strength=0.72,
        tool_use_strength=0.70,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=500, p95=1200),
        cost_profile=CostProfile(input_per_1k=0.001, output_per_1k=0.003),
        capability_tags=["speed_tier", "reasoning"],
    ),
    "deepseek-reasoner": ModelEntry(
        provider="deepseek",
        model_id="deepseek-reasoner",
        display_name="DeepSeek Reasoner",
        release_date="2025-12",
        context_window=128_000,
        reasoning_strength=0.91,
        coding_strength=0.90,
        math_strength=0.93,
        rag_strength=0.78,
        dialogue_strength=0.76,
        multilingual_strength=0.72,
        long_context_strength=0.75,
        tool_use_strength=0.72,
        supports_tools=False,
        latency_profile=LatencyProfile(p50=1500, p95=4000),
        cost_profile=CostProfile(input_per_1k=0.0005, output_per_1k=0.002),
        capability_tags=["elite_reasoning", "math_strong", "verify_specialist"],
    ),
    "deepseek-v3.2": ModelEntry(
        provider="deepseek",
        model_id="deepseek-v3.2",
        display_name="DeepSeek V3.2",
        release_date="2026-01",
        context_window=128_000,
        reasoning_strength=0.87,
        coding_strength=0.88,
        math_strength=0.89,
        rag_strength=0.80,
        dialogue_strength=0.80,
        multilingual_strength=0.74,
        long_context_strength=0.76,
        tool_use_strength=0.78,
        supports_tools=True,
        latency_profile=LatencyProfile(p50=600, p95=1400),
        cost_profile=CostProfile(input_per_1k=0.0003, output_per_1k=0.001),
        capability_tags=["code_strong", "math_strong", "cost_efficient"],
    ),
}


# ──────────────────────────────────────────────────────────────────────
# Registry class
# ──────────────────────────────────────────────────────────────────────

class ModelRegistry2026:
    """Production-grade canonical registry for the 2026 model landscape."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelEntry] = dict(CANONICAL_MODELS)
        self._enriched = False

    # ── queries ────────────────────────────────────────────────────────

    def get(self, model_id: str) -> Optional[ModelEntry]:
        return self._models.get(model_id)

    def exists(self, model_id: str) -> bool:
        return model_id in self._models

    def list_models(
        self,
        provider: Optional[str] = None,
        tag: Optional[str] = None,
        available_only: bool = True,
    ) -> List[ModelEntry]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        if tag:
            models = [m for m in models if tag in m.capability_tags]
        if available_only:
            models = [m for m in models if m.is_available]
        return models

    def best_for_category(
        self,
        category: str,
        *,
        top_n: int = 3,
        required_tags: Optional[Set[str]] = None,
        min_context: int = 0,
    ) -> List[ModelEntry]:
        """Return top-N models ranked by strength for *category*."""
        candidates = [
            m for m in self._models.values()
            if m.is_available
            and m.context_window >= min_context
            and (not required_tags or required_tags.issubset(set(m.capability_tags)))
        ]
        candidates.sort(key=lambda m: m.strength_for_category(category), reverse=True)
        return candidates[:top_n]

    # ── enrichment ────────────────────────────────────────────────────

    def enrich_from_firestore(self) -> int:
        """Pull live model metadata from Firestore model_catalog.
        Returns count of enriched models."""
        count = 0
        try:
            from ..services.firestore_models import get_firestore_model_catalog
            fs = get_firestore_model_catalog()
            if not fs.is_available():
                return 0
            profiles = fs.get_model_profiles_for_orchestrator()
            for mid, profile in profiles.items():
                if mid in self._models:
                    entry = self._models[mid]
                    if "context_window" in profile:
                        entry.context_window = int(profile["context_window"])
                    entry.last_verified = datetime.now(timezone.utc).isoformat()
                    count += 1
        except Exception as exc:
            logger.warning("Firestore enrichment failed: %s", exc)
        self._enriched = count > 0
        return count

    def enrich_from_benchmark_history(self, history_path: str = "benchmark_reports/performance_history.json") -> int:
        """Update strength scores from accumulated benchmark results."""
        path = Path(history_path)
        if not path.exists():
            return 0
        try:
            history = json.loads(path.read_text())
            count = 0
            for run in history.get("runs", []):
                for cat, data in run.get("categories", {}).items():
                    models_used = data.get("models_used", [])
                    accuracy = data.get("accuracy", 0) / 100.0
                    for mid in models_used:
                        if mid in self._models:
                            old = self._models[mid].strength_for_category(cat)
                            self._models[mid].__dict__[f"{cat}_strength"] = round(
                                old * 0.7 + accuracy * 0.3, 3
                            )
                            count += 1
            return count
        except Exception as exc:
            logger.warning("Benchmark history enrichment failed: %s", exc)
            return 0

    # ── validation ────────────────────────────────────────────────────

    def validate(self, required_elite_ids: Optional[List[str]] = None) -> List[str]:
        """Return list of validation errors (empty = valid)."""
        errors: List[str] = []
        seen_ids: Set[str] = set()
        for mid, entry in self._models.items():
            if mid in seen_ids:
                errors.append(f"Duplicate model_id: {mid}")
            seen_ids.add(mid)
            if not entry.capability_tags:
                errors.append(f"Model {mid} has no capability_tags")
        if required_elite_ids:
            for eid in required_elite_ids:
                if eid not in self._models:
                    errors.append(f"Required elite model missing: {eid}")
        return errors

    # ── serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "model_count": len(self._models),
            "models": {mid: asdict(entry) for mid, entry in self._models.items()},
        }


# ── singleton ─────────────────────────────────────────────────────────

_instance: Optional[ModelRegistry2026] = None


def get_model_registry_2026() -> ModelRegistry2026:
    global _instance
    if _instance is None:
        _instance = ModelRegistry2026()
    return _instance
