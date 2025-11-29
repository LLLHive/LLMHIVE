"""Services for persisting and retrieving model performance metrics."""
from __future__ import annotations

from typing import Dict, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import ModelMetric
from .orchestrator import UsageSummary, ResponseAssessment


class ModelMetricsService:
    """Records aggregated per-model metrics for long-term routing decisions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record_run(
        self,
        usage: UsageSummary,
        quality_assessments: Mapping[str, ResponseAssessment],
    ) -> None:
        per_model = usage.per_model
        for model_name, usage_metrics in per_model.items():
            stmt = select(ModelMetric).where(ModelMetric.model_name == model_name)
            metric = self.session.scalars(stmt).first()
            if metric is None:
                metric = ModelMetric(model_name=model_name)
                self.session.add(metric)

            # Ensure numeric fields are initialised before incremental updates.
            metric.total_tokens = int(metric.total_tokens or 0)
            metric.total_cost = float(metric.total_cost or 0.0)
            metric.calls = int(metric.calls or 0)

            metric.total_tokens += int(usage_metrics.tokens)
            metric.total_cost += float(usage_metrics.cost)
            increment_calls = int(usage_metrics.responses or 1)
            prior_calls = metric.calls
            metric.calls += increment_calls

            assessment = quality_assessments.get(model_name)
            if assessment is not None:
                # Incremental average update
                total_obs = prior_calls if prior_calls > 0 else 0
                metric.avg_quality = (
                    (metric.avg_quality * total_obs + assessment.score * increment_calls)
                    / max(metric.calls, 1)
                )

                # Heuristic success/failure classification based on quality threshold.
                threshold = getattr(settings, "minimum_quality_score", 0.3)
                if assessment.score >= threshold:
                    metric.success_count += 1
                else:
                    metric.failure_count += 1

    def all_metrics(self) -> Dict[str, Dict[str, float]]:
        stmt = select(ModelMetric)
        rows = self.session.scalars(stmt).all()
        payload: Dict[str, Dict[str, float]] = {}
        for row in rows:
            payload[row.model_name] = {
                "total_tokens": float(row.total_tokens),
                "total_cost": float(row.total_cost),
                "calls": float(row.calls),
                "success_rate": float(
                    row.success_count / row.calls if row.calls else 0.0
                ),
                "avg_quality": float(row.avg_quality),
            }
        return payload


