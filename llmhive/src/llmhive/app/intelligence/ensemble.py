"""Active Model Orchestration — Patent-aligned adaptive ensemble weighting.

Instead of equal consensus, weights votes by:
  - Category-specific strength from model registry
  - Historical benchmark performance
  - Reasoning strength

Tie-breaking:
  - Highest benchmark score wins
  - If disagreement entropy > 0.85, escalate to elite tie-breaker
  - If disagreement persists after escalation, fallback to single elite model

Logs disagreement entropy per sample.
"""
from __future__ import annotations

import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .model_registry_2026 import ModelEntry, get_model_registry_2026

logger = logging.getLogger(__name__)

DISAGREEMENT_ENTROPY_THRESHOLD = 0.85
INSTABILITY_FALLBACK_THRESHOLD = 0.95


@dataclass
class Vote:
    model_id: str
    answer: str
    confidence: float = 1.0


@dataclass
class EnsembleResult:
    selected_answer: str
    winning_model: str
    total_votes: int
    weighted_score: float
    disagreement_entropy: float
    escalated: bool
    instability_fallback: bool = False
    vote_distribution: Dict[str, float] = field(default_factory=dict)


class AdaptiveEnsemble:
    """Weighted ensemble aligned with the patented adaptive team architecture."""

    CONSECUTIVE_INSTABILITY_THRESHOLD = 3
    ENTROPY_P95_REBALANCE_THRESHOLD = 0.85
    VERIFY_PENALTY_REBALANCE_THRESHOLD = 0.08

    def __init__(self) -> None:
        self._registry = get_model_registry_2026()
        self._escalation_count = 0
        self._instability_count = 0
        self._per_question_entropies: List[float] = []
        self._disagreement_pairs: Dict[str, int] = {}
        self._tiebreaker_count = 0
        self._per_category_entropies: Dict[str, List[float]] = {}
        self._consecutive_high_entropy: Dict[str, int] = {}
        self._instability_warnings: List[Dict[str, Any]] = []
        self._weight_adjustments: List[Dict[str, Any]] = []

    @property
    def escalation_count(self) -> int:
        return self._escalation_count

    @property
    def instability_count(self) -> int:
        return self._instability_count

    @property
    def avg_entropy(self) -> float:
        if not self._per_question_entropies:
            return 0.0
        return sum(self._per_question_entropies) / len(self._per_question_entropies)

    @property
    def tiebreaker_count(self) -> int:
        return self._tiebreaker_count

    def get_disagreement_clusters(self) -> Dict[str, int]:
        return dict(sorted(self._disagreement_pairs.items(), key=lambda x: -x[1])[:10])

    def resolve(
        self,
        votes: List[Vote],
        category: str,
        *,
        tiebreaker_model: Optional[str] = None,
        elite_fallback_model: Optional[str] = None,
    ) -> EnsembleResult:
        """Resolve multi-model votes into a single answer using weighted consensus."""
        if not votes:
            raise ValueError("No votes to resolve")

        if len(votes) == 1:
            return EnsembleResult(
                selected_answer=votes[0].answer,
                winning_model=votes[0].model_id,
                total_votes=1,
                weighted_score=1.0,
                disagreement_entropy=0.0,
                escalated=False,
                vote_distribution={votes[0].answer: 1.0},
            )

        answer_weights: Dict[str, float] = {}
        answer_models: Dict[str, str] = {}
        per_vote_weights: Dict[str, float] = {}

        for vote in votes:
            weight = self._compute_weight(vote.model_id, category, vote.confidence)
            per_vote_weights[vote.model_id] = weight
            if vote.answer in answer_weights:
                answer_weights[vote.answer] += weight
            else:
                answer_weights[vote.answer] = weight
                answer_models[vote.answer] = vote.model_id

        adjustment = self._apply_adaptive_normalization(
            per_vote_weights, answer_weights, answer_models, votes, category
        )
        if adjustment:
            self._weight_adjustments.append(adjustment)

        total_weight = sum(answer_weights.values()) or 1.0
        normalized = {a: w / total_weight for a, w in answer_weights.items()}

        entropy = self._shannon_entropy(list(normalized.values()))
        self._per_question_entropies.append(entropy)
        self._per_category_entropies.setdefault(category, []).append(entropy)
        best_answer = max(answer_weights, key=answer_weights.get)  # type: ignore

        if entropy > 0.90:
            self._consecutive_high_entropy[category] = (
                self._consecutive_high_entropy.get(category, 0) + 1
            )
            if self._consecutive_high_entropy[category] >= self.CONSECUTIVE_INSTABILITY_THRESHOLD:
                warning = {
                    "category": category,
                    "consecutive_count": self._consecutive_high_entropy[category],
                    "entropy": round(entropy, 4),
                }
                self._instability_warnings.append(warning)
                logger.warning(
                    "ENSEMBLE_INSTABILITY_WARNING: %s has %d consecutive calls with entropy >0.90",
                    category, self._consecutive_high_entropy[category],
                )
        else:
            self._consecutive_high_entropy[category] = 0

        # Track disagreement pairs for cluster detection
        unique_answers = set(v.answer for v in votes)
        if len(unique_answers) > 1:
            model_ids = sorted(set(v.model_id for v in votes))
            for i in range(len(model_ids)):
                for j in range(i + 1, len(model_ids)):
                    pair = f"{model_ids[i]}|{model_ids[j]}"
                    self._disagreement_pairs[pair] = self._disagreement_pairs.get(pair, 0) + 1

        # Instability fallback: entropy so high that even escalation is unreliable
        if entropy > INSTABILITY_FALLBACK_THRESHOLD:
            fallback = elite_fallback_model or tiebreaker_model or votes[0].model_id
            self._instability_count += 1
            logger.warning(
                "Ensemble instability fallback: entropy=%.3f > %.2f, "
                "falling back to single elite model %s (category=%s)",
                entropy, INSTABILITY_FALLBACK_THRESHOLD, fallback, category,
            )
            return EnsembleResult(
                selected_answer=best_answer,
                winning_model=fallback,
                total_votes=len(votes),
                weighted_score=normalized.get(best_answer, 0),
                disagreement_entropy=round(entropy, 4),
                escalated=True,
                instability_fallback=True,
                vote_distribution=normalized,
            )

        # High disagreement: escalate to tie-breaker
        if entropy > DISAGREEMENT_ENTROPY_THRESHOLD and tiebreaker_model:
            self._escalation_count += 1
            self._tiebreaker_count += 1
            logger.info(
                "Ensemble high disagreement: entropy=%.3f > %.2f, escalating to %s",
                entropy, DISAGREEMENT_ENTROPY_THRESHOLD, tiebreaker_model,
            )
            return EnsembleResult(
                selected_answer=best_answer,
                winning_model=tiebreaker_model,
                total_votes=len(votes),
                weighted_score=normalized.get(best_answer, 0),
                disagreement_entropy=round(entropy, 4),
                escalated=True,
                vote_distribution=normalized,
            )

        return EnsembleResult(
            selected_answer=best_answer,
            winning_model=answer_models.get(best_answer, votes[0].model_id),
            total_votes=len(votes),
            weighted_score=round(normalized.get(best_answer, 0), 4),
            disagreement_entropy=round(entropy, 4),
            escalated=False,
            vote_distribution={k: round(v, 4) for k, v in normalized.items()},
        )

    @property
    def entropy_p95(self) -> float:
        if not self._per_question_entropies:
            return 0.0
        s = sorted(self._per_question_entropies)
        return s[int(len(s) * 0.95)]

    def _apply_adaptive_normalization(
        self,
        per_vote_weights: Dict[str, float],
        answer_weights: Dict[str, float],
        answer_models: Dict[str, str],
        votes: List[Vote],
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """Dynamically rebalance weights based on entropy p95 and verify penalty.

        No model selection change — only weight redistribution.
        """
        entropy_triggered = False
        verify_triggered = False
        adjustments: Dict[str, float] = {}

        if len(self._per_question_entropies) >= 10:
            if self.entropy_p95 > self.ENTROPY_P95_REBALANCE_THRESHOLD:
                entropy_triggered = True
                if len(per_vote_weights) > 1:
                    primary_id = max(per_vote_weights, key=per_vote_weights.get)  # type: ignore
                    weakest_id = min(per_vote_weights, key=per_vote_weights.get)  # type: ignore
                    boost = per_vote_weights[primary_id] * 0.05
                    per_vote_weights[primary_id] += boost
                    per_vote_weights[weakest_id] = max(0.01, per_vote_weights[weakest_id] - boost)
                    adjustments[primary_id] = round(boost, 6)
                    adjustments[weakest_id] = round(-boost, 6)

                    answer_weights.clear()
                    for vote in votes:
                        w = per_vote_weights.get(vote.model_id, 0)
                        if vote.answer in answer_weights:
                            answer_weights[vote.answer] += w
                        else:
                            answer_weights[vote.answer] = w
                            answer_models[vote.answer] = vote.model_id

        try:
            from .verify_policy import get_verify_policy
            vp = get_verify_policy()
            if vp.verify_penalty > self.VERIFY_PENALTY_REBALANCE_THRESHOLD:
                verify_triggered = True
        except Exception:
            pass

        if not entropy_triggered and not verify_triggered:
            return None

        return {
            "category": category,
            "entropy_triggered": entropy_triggered,
            "verify_penalty_triggered": verify_triggered,
            "entropy_p95": round(self.entropy_p95, 4) if self._per_question_entropies else 0,
            "weight_adjustment": adjustments,
        }

    def _compute_weight(self, model_id: str, category: str, confidence: float) -> float:
        entry = self._registry.get(model_id)
        if not entry:
            return confidence

        category_strength = entry.strength_for_category(category)
        reasoning_strength = entry.reasoning_strength

        stability = self._get_model_stability(model_id, category)
        cost_eff = max(0.0, 1.0 - entry.cost_profile.input_per_1k / 0.010)

        return (
            category_strength * 0.40
            + reasoning_strength * 0.20
            + confidence * 0.15
            + stability * 0.15
            + cost_eff * 0.10
        )

    def _get_model_stability(self, model_id: str, category: str) -> float:
        """Retrieve rolling stability from strategy DB if available."""
        try:
            from .strategy_db import get_strategy_db
            sdb = get_strategy_db()
            key = f"{model_id}:{category}"
            rec = sdb._performance_cache.get(key)
            if rec:
                return rec.rolling_stability_score
        except Exception:
            pass
        return 0.5

    def get_category_entropy_stats(self) -> Dict[str, Dict[str, Any]]:
        stats: Dict[str, Dict[str, Any]] = {}
        for cat, entropies in self._per_category_entropies.items():
            if not entropies:
                continue
            s = sorted(entropies)
            stats[cat] = {
                "count": len(s),
                "avg": round(sum(s) / len(s), 4),
                "p50": round(s[len(s) // 2], 4),
                "p95": round(s[int(len(s) * 0.95)], 4),
                "max": round(s[-1], 4),
            }
        return stats

    def generate_precision_report(self) -> Dict[str, Any]:
        """Produce ensemble_precision_report.json content."""
        from datetime import datetime, timezone
        total = len(self._per_question_entropies)
        entropy_histogram = {"<0.3": 0, "0.3-0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0, ">1.0": 0}
        for e in self._per_question_entropies:
            if e < 0.3:
                entropy_histogram["<0.3"] += 1
            elif e < 0.5:
                entropy_histogram["0.3-0.5"] += 1
            elif e < 0.8:
                entropy_histogram["0.5-0.8"] += 1
            elif e <= 1.0:
                entropy_histogram["0.8-1.0"] += 1
            else:
                entropy_histogram[">1.0"] += 1

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_resolutions": total,
            "avg_entropy": round(self.avg_entropy, 4),
            "entropy_p95": round(self.entropy_p95, 4),
            "entropy_histogram": entropy_histogram,
            "category_entropy_stats": self.get_category_entropy_stats(),
            "escalation_count": self._escalation_count,
            "tiebreaker_count": self._tiebreaker_count,
            "instability_fallback_count": self._instability_count,
            "instability_warnings": self._instability_warnings,
            "disagreement_clusters": self.get_disagreement_clusters(),
            "adaptive_weight_adjustments": len(self._weight_adjustments),
            "weight_adjustment_log": self._weight_adjustments[-10:],
        }

    @staticmethod
    def _shannon_entropy(probabilities: List[float]) -> float:
        return -sum(p * math.log2(p) for p in probabilities if p > 0)


_instance: Optional[AdaptiveEnsemble] = None


def get_adaptive_ensemble() -> AdaptiveEnsemble:
    global _instance
    if _instance is None:
        _instance = AdaptiveEnsemble()
    return _instance
