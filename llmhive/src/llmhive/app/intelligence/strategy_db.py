"""Strategy DB Integration — Pinecone + Firestore intelligence layer.

Before routing:
  - Embed task signature
  - Retrieve prior failures, best-performing models, category strategy templates
  - Adjust model weighting dynamically

Firestore stores per-model performance history.
Pinecone stores strategy embeddings for similarity retrieval.

No auto-promotion — only recommendation flags.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


FATIGUE_WINDOW = 10
FATIGUE_DROP_THRESHOLD = 0.10


def _interpret_cai(score: float) -> str:
    if score >= 80:
        return "strong_moat"
    if score >= 60:
        return "competitive_advantage"
    if score >= 40:
        return "market_parity"
    return "improvement_needed"


@dataclass
class ModelPerformanceRecord:
    model_id: str
    category: str
    benchmark_history: List[float] = field(default_factory=list)
    win_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost_usd: float = 0.0
    last_updated: str = ""

    def update(self, accuracy: float, latency_ms: float, cost_usd: float) -> None:
        self.benchmark_history.append(accuracy)
        if len(self.benchmark_history) > 30:
            self.benchmark_history = self.benchmark_history[-30:]
        wins = sum(1 for a in self.benchmark_history if a >= 0.80)
        self.win_rate = wins / len(self.benchmark_history) if self.benchmark_history else 0
        n = len(self.benchmark_history)
        self.avg_latency_ms = (self.avg_latency_ms * (n - 1) + latency_ms) / n if n else latency_ms
        self.avg_cost_usd = (self.avg_cost_usd * (n - 1) + cost_usd) / n if n else cost_usd
        self.last_updated = datetime.now(timezone.utc).isoformat()

    @property
    def volatility(self) -> float:
        import math
        h = self.benchmark_history
        if len(h) < 2:
            return 0.0
        mean = sum(h) / len(h)
        var = sum((x - mean) ** 2 for x in h) / len(h)
        return math.sqrt(var)

    @property
    def confidence_weighted_win_rate(self) -> float:
        """Win rate weighted by recency — recent results count more."""
        h = self.benchmark_history
        if not h:
            return 0.0
        total_w = 0.0
        weighted_wins = 0.0
        for i, acc in enumerate(h):
            w = 1.0 + i * 0.1  # more recent = higher weight
            total_w += w
            if acc >= 0.80:
                weighted_wins += w
        return weighted_wins / total_w if total_w else 0.0

    @property
    def rolling_stability_score(self) -> float:
        """0-1 score: 1 = perfectly stable, 0 = highly volatile."""
        v = self.volatility
        return max(0.0, 1.0 - v * 10)  # vol of 0.1 = stability 0

    @property
    def fatigue_detected(self) -> bool:
        """True if performance is decaying over recent window."""
        h = self.benchmark_history
        if len(h) < FATIGUE_WINDOW * 2:
            return False
        early = h[-FATIGUE_WINDOW * 2:-FATIGUE_WINDOW]
        recent = h[-FATIGUE_WINDOW:]
        early_mean = sum(early) / len(early)
        recent_mean = sum(recent) / len(recent)
        return (early_mean - recent_mean) > FATIGUE_DROP_THRESHOLD


WIN_RATE_DELTA_THRESHOLD = 0.03
VOLATILITY_MAX_THRESHOLD = 0.05
MIN_HISTORY_DEPTH = 5


@dataclass
class StrategyRecommendation:
    category: str
    recommended_model: str
    confidence: float
    reasoning: str
    prior_failures: List[str] = field(default_factory=list)
    is_promotion: bool = False
    meets_stability: bool = False
    win_rate_delta: float = 0.0
    volatility: float = 0.0


class StrategyDB:
    """Unified strategy retrieval from Pinecone embeddings and Firestore metadata."""

    def __init__(self) -> None:
        self._performance_cache: Dict[str, ModelPerformanceRecord] = {}
        self._pinecone_available = False
        self._firestore_available = False
        self._init_backends()

    def _init_backends(self) -> None:
        try:
            from ..knowledge.pinecone_registry import get_pinecone_registry
            registry = get_pinecone_registry()
            self._pinecone_available = registry is not None
        except Exception:
            self._pinecone_available = False

        try:
            from ..firestore_db import get_firestore_client
            self._firestore_available = get_firestore_client() is not None
        except Exception:
            self._firestore_available = False

        logger.info(
            "StrategyDB init: pinecone=%s, firestore=%s",
            self._pinecone_available, self._firestore_available,
        )

    def get_recommendation(self, category: str) -> Optional[StrategyRecommendation]:
        """Retrieve strategy recommendation for a category.

        Returns recommendation only if stability thresholds are met:
          - win_rate_delta > 3% over current elite
          - volatility < 5%
          - 30-day history depth >= MIN_HISTORY_DEPTH

        In BENCHMARK_MODE, recommendations are suppressed entirely.
        Never auto-promotes.
        """
        from .elite_policy import is_benchmark_mode
        if is_benchmark_mode():
            return None

        records = [
            r for key, r in self._performance_cache.items()
            if r.category == category
        ]
        if not records:
            return None

        best = max(records, key=lambda r: r.win_rate)
        failures = [
            r.model_id for r in records
            if r.win_rate < 0.5 and len(r.benchmark_history) >= 3
        ]

        import math
        history = best.benchmark_history
        volatility = 0.0
        if len(history) >= 2:
            mean = sum(history) / len(history)
            variance = sum((h - mean) ** 2 for h in history) / len(history)
            volatility = math.sqrt(variance)

        # Find current elite's win rate for delta comparison
        from .elite_policy import ELITE_POLICY
        elite_id = ELITE_POLICY.get(category, "")
        elite_key = f"{elite_id}:{category}"
        elite_record = self._performance_cache.get(elite_key)
        elite_win_rate = elite_record.win_rate if elite_record else 0.0
        win_rate_delta = best.win_rate - elite_win_rate

        meets_stability = (
            win_rate_delta > WIN_RATE_DELTA_THRESHOLD
            and volatility < VOLATILITY_MAX_THRESHOLD
            and len(history) >= MIN_HISTORY_DEPTH
        )

        return StrategyRecommendation(
            category=category,
            recommended_model=best.model_id,
            confidence=best.win_rate,
            reasoning=f"Win rate {best.win_rate:.1%} over {len(history)} runs, "
                      f"delta={win_rate_delta:+.1%}, vol={volatility:.3f}",
            prior_failures=failures,
            is_promotion=False,
            meets_stability=meets_stability,
            win_rate_delta=round(win_rate_delta, 4),
            volatility=round(volatility, 4),
        )

    def record_result(
        self,
        model_id: str,
        category: str,
        accuracy: float,
        latency_ms: float,
        cost_usd: float,
    ) -> None:
        key = f"{model_id}:{category}"
        if key not in self._performance_cache:
            self._performance_cache[key] = ModelPerformanceRecord(
                model_id=model_id, category=category,
            )
        self._performance_cache[key].update(accuracy, latency_ms, cost_usd)

    def persist_to_firestore(self) -> int:
        """Flush cached performance records to Firestore. Returns count persisted."""
        if not self._firestore_available:
            return 0
        count = 0
        try:
            from ..firestore_db import get_firestore_client
            db = get_firestore_client()
            if not db:
                return 0
            for key, record in self._performance_cache.items():
                doc_ref = db.collection("model_performance").document(key)
                doc_ref.set({
                    "model_id": record.model_id,
                    "category": record.category,
                    "benchmark_history": record.benchmark_history[-30:],
                    "win_rate": record.win_rate,
                    "avg_latency_ms": record.avg_latency_ms,
                    "avg_cost_usd": record.avg_cost_usd,
                    "last_updated": record.last_updated,
                }, merge=True)
                count += 1
        except Exception as exc:
            logger.warning("Firestore persist failed: %s", exc)
        return count

    def get_all_recommendations(self) -> Dict[str, Any]:
        """Produce strategy_recommendations.json content."""
        from .elite_policy import ELITE_POLICY
        categories = list(ELITE_POLICY.keys())
        recs: Dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat(), "categories": {}}
        pareto = self.get_pareto_rankings()
        for cat in categories:
            rec = self.get_recommendation(cat)
            records = [r for r in self._performance_cache.values() if r.category == cat]
            cat_data: Dict[str, Any] = {
                "recommendation": None,
                "models_tracked": len(records),
                "fatigue_detected": [r.model_id for r in records if r.fatigue_detected],
                "pareto_ranking": pareto.get(cat, []),
            }
            if rec:
                cat_data["recommendation"] = {
                    "model": rec.recommended_model,
                    "confidence": rec.confidence,
                    "win_rate_delta": rec.win_rate_delta,
                    "volatility": rec.volatility,
                    "meets_stability": rec.meets_stability,
                }
            for r in records:
                cat_data.setdefault("model_stats", {})[r.model_id] = {
                    "win_rate": round(r.win_rate, 4),
                    "confidence_weighted": round(r.confidence_weighted_win_rate, 4),
                    "stability_score": round(r.rolling_stability_score, 4),
                    "volatility": round(r.volatility, 4),
                    "fatigue": r.fatigue_detected,
                    "history_depth": len(r.benchmark_history),
                    "efficiency_score": round(self.get_model_efficiency(r.model_id, cat), 4),
                }
            recs["categories"][cat] = cat_data
        return recs

    def save_recommendations(self) -> str:
        from pathlib import Path as _P
        report_dir = _P("benchmark_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        path = str(report_dir / "strategy_recommendations.json")
        _P(path).write_text(json.dumps(self.get_all_recommendations(), indent=2, default=str))
        return path

    def compute_competitive_advantage_index(
        self,
        ensemble_entropy_avg: float = 0.0,
        reliability_score: float = 1.0,
    ) -> Dict[str, Any]:
        """Compute the composite competitive advantage moat metric.

        CAI = 0.35 * win_rate_delta
            + 0.20 * stability_score
            + 0.15 * entropy_reduction
            + 0.15 * cost_efficiency
            + 0.15 * reliability_score
        """
        from .elite_policy import ELITE_POLICY

        categories = list(ELITE_POLICY.keys())
        cat_scores: Dict[str, Dict[str, float]] = {}
        total_index = 0.0
        scored_cats = 0

        for cat in categories:
            records = [r for r in self._performance_cache.values() if r.category == cat]
            if not records:
                continue

            best = max(records, key=lambda r: r.win_rate)
            elite_id = ELITE_POLICY.get(cat, "")
            elite_rec = self._performance_cache.get(f"{elite_id}:{cat}")
            elite_wr = elite_rec.win_rate if elite_rec else 0.0

            win_delta = best.win_rate - elite_wr
            stability = best.rolling_stability_score
            cost_eff = 1.0 - min(best.avg_cost_usd / 0.05, 1.0) if best.avg_cost_usd > 0 else 1.0
            entropy_reduction = max(0.0, 1.0 - ensemble_entropy_avg)

            cat_index = (
                win_delta * 35
                + stability * 20
                + entropy_reduction * 15
                + cost_eff * 15
                + reliability_score * 15
            )
            cat_index = max(0.0, min(100.0, cat_index))

            cat_scores[cat] = {
                "index": round(cat_index, 2),
                "win_rate_delta": round(win_delta, 4),
                "stability": round(stability, 4),
                "volatility": round(best.volatility, 4),
                "cost_efficiency": round(cost_eff, 4),
                "entropy_reduction": round(entropy_reduction, 4),
                "reliability": round(reliability_score, 4),
            }
            total_index += cat_index
            scored_cats += 1

        composite = round(total_index / scored_cats, 2) if scored_cats else 0.0

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "composite_index": composite,
            "categories": cat_scores,
            "ensemble_entropy_avg": round(ensemble_entropy_avg, 4),
            "reliability_score": round(reliability_score, 4),
            "interpretation": _interpret_cai(composite),
        }
        return result

    def save_competitive_advantage(self, **kwargs) -> str:
        from pathlib import Path as _P
        report_dir = _P("strategy_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        path = str(report_dir / "competitive_advantage_index.json")
        data = self.compute_competitive_advantage_index(**kwargs)
        _P(path).write_text(json.dumps(data, indent=2, default=str))
        return path

    def check_degradation(self, threshold_pct: float = 3.0) -> List[Dict[str, Any]]:
        """Check all categories for >threshold_pct drop from rolling baseline. Advisory only."""
        alerts: List[Dict[str, Any]] = []
        for key, rec in self._performance_cache.items():
            h = rec.benchmark_history
            if len(h) < 3:
                continue
            rolling_mean = sum(h[:-1]) / len(h[:-1])
            latest = h[-1]
            drop_pct = (rolling_mean - latest) * 100
            if drop_pct > threshold_pct:
                alert = {
                    "category": rec.category,
                    "model_id": rec.model_id,
                    "rolling_baseline": round(rolling_mean, 4),
                    "latest": round(latest, 4),
                    "drop_pct": round(drop_pct, 2),
                    "severity": "warning" if drop_pct < 5.0 else "critical",
                }
                alerts.append(alert)
                logger.warning(
                    "PERFORMANCE_DEGRADATION_WARNING: %s/%s dropped %.1f%% "
                    "(baseline=%.2f%% latest=%.2f%%)",
                    rec.category, rec.model_id, drop_pct,
                    rolling_mean * 100, latest * 100,
                )
        return alerts

    def has_real_data_for_all_categories(self) -> bool:
        from .elite_policy import ELITE_POLICY
        for cat in ELITE_POLICY:
            if not any(r.category == cat for r in self._performance_cache.values()):
                return False
        return True

    def generate_activation_summary(self, **cai_kwargs) -> Dict[str, Any]:
        """Produce strategy_activation_summary.json content."""
        from .elite_policy import ELITE_POLICY
        cai = self.compute_competitive_advantage_index(**cai_kwargs)
        degradation = self.check_degradation()
        pareto = self.get_pareto_rankings()

        per_cat: Dict[str, Any] = {}
        for cat in ELITE_POLICY:
            records = [r for r in self._performance_cache.values() if r.category == cat]
            cat_info: Dict[str, Any] = {
                "models_tracked": len(records),
                "history_depth": max((len(r.benchmark_history) for r in records), default=0),
            }
            if records:
                best = max(records, key=lambda r: r.win_rate)
                cat_info["best_model"] = best.model_id
                cat_info["win_rate"] = round(best.win_rate, 4)
                cat_info["stability"] = round(best.rolling_stability_score, 4)
                cat_info["volatility"] = round(best.volatility, 4)
            per_cat[cat] = cat_info

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cai": cai,
            "categories": per_cat,
            "degradation_alerts": degradation,
            "all_categories_populated": self.has_real_data_for_all_categories(),
            "total_records": len(self._performance_cache),
            "pareto_top3": {k: v[:3] for k, v in pareto.items()},
        }

    def save_activation_summary(self, **cai_kwargs) -> str:
        report_dir = Path("benchmark_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        path = str(report_dir / "strategy_activation_summary.json")
        data = self.generate_activation_summary(**cai_kwargs)
        Path(path).write_text(json.dumps(data, indent=2, default=str))
        return path

    def ingest_benchmark_result(
        self,
        category: str,
        model_id: str,
        provider: str,
        accuracy: float,
        latency_p50: float = 0.0,
        latency_p95: float = 0.0,
        cost_per_sample: float = 0.0,
        entropy: float = 0.0,
        verify_timeout_rate: float = 0.0,
    ) -> None:
        """Ingest a single category result into the strategy DB and persist to disk."""
        self.record_result(model_id, category, accuracy, latency_p50, cost_per_sample)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "model": model_id,
            "provider": provider,
            "accuracy": accuracy,
            "latency_p50": latency_p50,
            "latency_p95": latency_p95,
            "cost_per_sample": cost_per_sample,
            "entropy": entropy,
            "verify_timeout_rate": verify_timeout_rate,
        }
        self._append_to_local_history(entry)

    def _append_to_local_history(self, entry: Dict[str, Any]) -> None:
        history_path = Path("benchmark_reports") / "performance_history_detail.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        data: List[Dict[str, Any]] = []
        if history_path.exists():
            try:
                data = json.loads(history_path.read_text())
            except Exception:
                data = []
        data.append(entry)
        if len(data) > 5000:
            data = data[-5000:]
        history_path.write_text(json.dumps(data, indent=2, default=str))

    def load_from_local_history(self) -> int:
        """Bootstrap performance cache from local history file."""
        history_path = Path("benchmark_reports") / "performance_history_detail.json"
        if not history_path.exists():
            return 0
        try:
            data = json.loads(history_path.read_text())
        except Exception:
            return 0
        count = 0
        for entry in data:
            model = entry.get("model", "")
            cat = entry.get("category", "")
            if not model or not cat:
                continue
            self.record_result(
                model_id=model,
                category=cat,
                accuracy=entry.get("accuracy", 0.0),
                latency_ms=entry.get("latency_p50", 0.0),
                cost_usd=entry.get("cost_per_sample", 0.0),
            )
            count += 1
        return count

    def get_model_efficiency(self, model_id: str, category: str) -> float:
        """Compute efficiency_score = accuracy / cost_per_sample for Pareto ranking."""
        key = f"{model_id}:{category}"
        rec = self._performance_cache.get(key)
        if not rec or not rec.benchmark_history:
            return 0.0
        avg_acc = sum(rec.benchmark_history) / len(rec.benchmark_history)
        if rec.avg_cost_usd <= 0:
            return avg_acc * 100
        return avg_acc / rec.avg_cost_usd

    def get_pareto_rankings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Per-category efficiency rankings for cost-performance optimization."""
        from .elite_policy import ELITE_POLICY
        rankings: Dict[str, List[Dict[str, Any]]] = {}
        for cat in ELITE_POLICY:
            records = [r for r in self._performance_cache.values() if r.category == cat]
            scored = []
            for r in records:
                eff = self.get_model_efficiency(r.model_id, cat)
                scored.append({
                    "model_id": r.model_id,
                    "efficiency_score": round(eff, 4),
                    "win_rate": round(r.win_rate, 4),
                    "avg_cost_usd": round(r.avg_cost_usd, 6),
                    "history_depth": len(r.benchmark_history),
                })
            scored.sort(key=lambda x: x["efficiency_score"], reverse=True)
            rankings[cat] = scored
        return rankings

    def backfill_from_benchmark_reports(self) -> Dict[str, Any]:
        """Parse all historical benchmark_reports/*.json files and ingest into strategy DB.

        Returns summary of what was ingested.
        """
        from .elite_policy import ELITE_POLICY

        CATEGORY_MAP = {
            "General Reasoning (MMLU)": "reasoning",
            "Coding (HumanEval)": "coding",
            "Math (GSM8K)": "math",
            "Multilingual (MMMLU)": "multilingual",
            "Long Context (LongBench)": "long_context",
            "Tool Use (ToolBench)": "tool_use",
            "RAG (MS MARCO)": "rag",
            "Dialogue (MT-Bench)": "dialogue",
        }

        report_dir = Path("benchmark_reports")
        files = sorted(report_dir.glob("category_benchmarks_elite_*.json"))
        files += sorted(report_dir.glob("full_suite_*.json"))
        seen: set = set()
        files_deduped = []
        for f in files:
            if f.name not in seen:
                seen.add(f.name)
                files_deduped.append(f)

        total_ingested = 0
        files_processed = 0
        categories_seen: Dict[str, int] = {}

        for fpath in files_deduped:
            try:
                data = json.loads(fpath.read_text())
            except Exception:
                continue
            results = data.get("results", [])
            if not results:
                continue

            files_processed += 1
            ts = data.get("timestamp", "")
            for r in results:
                if not isinstance(r, dict) or "error" in r.get("extra", {}):
                    continue
                cat_name = r.get("category", "")
                cat_key = CATEGORY_MAP.get(cat_name, "")
                if not cat_key:
                    continue
                accuracy = r.get("accuracy", 0)
                sample_size = r.get("sample_size", 0)
                if sample_size == 0:
                    continue

                acc_norm = accuracy / 100.0
                latency = r.get("avg_latency_ms", 0)
                cost = r.get("total_cost", 0) / max(sample_size, 1)

                elite_model = ELITE_POLICY.get(cat_key, "unknown")

                self.record_result(elite_model, cat_key, acc_norm, latency, cost)
                categories_seen[cat_key] = categories_seen.get(cat_key, 0) + 1
                total_ingested += 1

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_scanned": len(files_deduped),
            "files_processed": files_processed,
            "total_records_ingested": total_ingested,
            "categories_populated": categories_seen,
            "performance_cache_size": len(self._performance_cache),
            "all_categories_populated": self.has_real_data_for_all_categories(),
        }
        return summary

    def save_backfill_summary(self) -> str:
        summary = self.backfill_from_benchmark_reports()
        report_dir = Path("benchmark_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = str(report_dir / f"strategy_history_bootstrap_{ts}.json")
        Path(path).write_text(json.dumps(summary, indent=2, default=str))
        return path

    def load_from_firestore(self) -> int:
        """Load cached performance records from Firestore. Returns count loaded."""
        if not self._firestore_available:
            return 0
        count = 0
        try:
            from ..firestore_db import get_firestore_client
            db = get_firestore_client()
            if not db:
                return 0
            docs = db.collection("model_performance").stream()
            for doc in docs:
                data = doc.to_dict()
                key = doc.id
                self._performance_cache[key] = ModelPerformanceRecord(
                    model_id=data.get("model_id", ""),
                    category=data.get("category", ""),
                    benchmark_history=data.get("benchmark_history", []),
                    win_rate=data.get("win_rate", 0),
                    avg_latency_ms=data.get("avg_latency_ms", 0),
                    avg_cost_usd=data.get("avg_cost_usd", 0),
                    last_updated=data.get("last_updated", ""),
                )
                count += 1
        except Exception as exc:
            logger.warning("Firestore load failed: %s", exc)
        return count


_instance: Optional[StrategyDB] = None


def get_strategy_db() -> StrategyDB:
    global _instance
    if _instance is None:
        _instance = StrategyDB()
    return _instance
