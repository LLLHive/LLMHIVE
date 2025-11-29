"""Model performance feedback logging for LLMHive.

This module provides functionality to log model performance feedback after each query,
enabling the system to learn from past performance and improve model routing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from .models import FeedbackOutcome, ModelFeedback, ModelMetric, Task

logger = logging.getLogger(__name__)


@dataclass
class ModelFeedbackData:
    """Data structure for a single model feedback record."""

    model_name: str
    outcome: FeedbackOutcome
    was_used_in_final: bool
    response_time_ms: Optional[float] = None
    token_usage: Optional[int] = None
    confidence_score: Optional[float] = None
    quality_score: Optional[float] = None
    notes: Optional[str] = None


class FeedbackLogger:
    """Service for logging model performance feedback and updating aggregate metrics."""

    def __init__(self, db_session: Session):
        """Initialize feedback logger with database session."""
        self.db = db_session

    def log_feedback(
        self,
        feedback_data: ModelFeedbackData,
        task_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ModelFeedback:
        """Log a single model feedback record.

        Args:
            feedback_data: Feedback data for the model
            task_id: Optional task ID this feedback is associated with
            session_id: Optional session ID for grouping feedback

        Returns:
            Created ModelFeedback record
        """
        try:
            feedback = ModelFeedback(
                task_id=task_id,
                session_id=session_id,
                model_name=feedback_data.model_name,
                outcome=feedback_data.outcome,
                was_used_in_final=feedback_data.was_used_in_final,
                response_time_ms=feedback_data.response_time_ms,
                token_usage=feedback_data.token_usage,
                confidence_score=feedback_data.confidence_score,
                quality_score=feedback_data.quality_score,
                notes=feedback_data.notes,
            )
            self.db.add(feedback)
            self.db.flush()  # Flush to get the ID without committing

            # Update aggregate metrics
            self._update_model_metrics(feedback_data)

            logger.debug(
                "Model Feedback: Logged feedback for %s: outcome=%s, used_in_final=%s",
                feedback_data.model_name,
                feedback_data.outcome.value,
                feedback_data.was_used_in_final,
            )
            return feedback
        except Exception as exc:
            logger.error("Model Feedback: Failed to log feedback for %s: %s", feedback_data.model_name, exc)
            raise

    def log_multiple_feedback(
        self,
        feedback_list: list[ModelFeedbackData],
        task_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> list[ModelFeedback]:
        """Log multiple model feedback records in a batch.

        Args:
            feedback_list: List of feedback data records
            task_id: Optional task ID this feedback is associated with
            session_id: Optional session ID for grouping feedback

        Returns:
            List of created ModelFeedback records
        """
        feedback_records = []
        for feedback_data in feedback_list:
            try:
                feedback = self.log_feedback(feedback_data, task_id=task_id, session_id=session_id)
                feedback_records.append(feedback)
            except Exception as exc:
                logger.error(
                    "Model Feedback: Failed to log feedback for %s in batch: %s",
                    feedback_data.model_name,
                    exc,
                )
                # Continue with other feedback records
        return feedback_records

    def _update_model_metrics(self, feedback_data: ModelFeedbackData) -> None:
        """Update aggregate ModelMetric record for a model based on feedback.

        Args:
            feedback_data: Feedback data to incorporate into metrics
        """
        try:
            # Get or create ModelMetric record
            metric = self.db.query(ModelMetric).filter_by(model_name=feedback_data.model_name).first()
            if not metric:
                metric = ModelMetric(
                    model_name=feedback_data.model_name,
                    total_tokens=0,
                    total_cost=0.0,
                    calls=0,
                    success_count=0,
                    failure_count=0,
                    avg_quality=0.0,
                    historical_success_rate=None,
                    avg_response_time_ms=None,
                    total_feedback_count=0,
                )
                self.db.add(metric)

            # Update feedback count
            metric.total_feedback_count += 1

            # Update success/failure counts based on outcome
            if feedback_data.outcome == FeedbackOutcome.SUCCESS:
                metric.success_count += 1
            elif feedback_data.outcome in (
                FeedbackOutcome.REJECTED,
                FeedbackOutcome.FAILED_VERIFICATION,
                FeedbackOutcome.CORRECTED,
            ):
                metric.failure_count += 1

            # Calculate historical success rate
            total_outcomes = metric.success_count + metric.failure_count
            if total_outcomes > 0:
                metric.historical_success_rate = metric.success_count / total_outcomes

            # Update average response time (moving average)
            if feedback_data.response_time_ms is not None:
                if metric.avg_response_time_ms is None:
                    metric.avg_response_time_ms = feedback_data.response_time_ms
                else:
                    # Simple moving average: weight new value by 1/feedback_count
                    weight = 1.0 / metric.total_feedback_count
                    metric.avg_response_time_ms = (
                        (1 - weight) * metric.avg_response_time_ms + weight * feedback_data.response_time_ms
                    )

            # Update average quality (moving average)
            if feedback_data.quality_score is not None:
                if metric.avg_quality == 0.0:
                    metric.avg_quality = feedback_data.quality_score
                else:
                    # Simple moving average
                    weight = 1.0 / metric.total_feedback_count
                    metric.avg_quality = (1 - weight) * metric.avg_quality + weight * feedback_data.quality_score

            # Update token usage if provided
            if feedback_data.token_usage is not None:
                metric.total_tokens += feedback_data.token_usage

            self.db.flush()
            logger.debug(
                "Model Feedback: Updated metrics for %s: success_rate=%.2f, feedback_count=%d",
                feedback_data.model_name,
                metric.historical_success_rate or 0.0,
                metric.total_feedback_count,
            )
        except Exception as exc:
            logger.error(
                "Model Feedback: Failed to update metrics for %s: %s",
                feedback_data.model_name,
                exc,
            )
            # Don't raise - metrics update failure shouldn't break feedback logging

    def get_model_success_rate(self, model_name: str) -> Optional[float]:
        """Get historical success rate for a model.

        Args:
            model_name: Name of the model

        Returns:
            Success rate (0.0-1.0) or None if no data available
        """
        try:
            metric = self.db.query(ModelMetric).filter_by(model_name=model_name).first()
            if metric and metric.historical_success_rate is not None:
                return metric.historical_success_rate
            return None
        except Exception as exc:
            logger.error("Model Feedback: Failed to get success rate for %s: %s", model_name, exc)
            return None

    def get_recent_feedback(
        self,
        model_name: Optional[str] = None,
        task_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[ModelFeedback]:
        """Get recent feedback records.

        Args:
            model_name: Optional filter by model name
            task_id: Optional filter by task ID
            limit: Maximum number of records to return

        Returns:
            List of ModelFeedback records, ordered by created_at descending
        """
        try:
            query = self.db.query(ModelFeedback)
            if model_name:
                query = query.filter_by(model_name=model_name)
            if task_id:
                query = query.filter_by(task_id=task_id)
            return query.order_by(ModelFeedback.created_at.desc()).limit(limit).all()
        except Exception as exc:
            logger.error("Model Feedback: Failed to get recent feedback: %s", exc)
            return []

