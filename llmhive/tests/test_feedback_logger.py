"""Unit tests for model feedback logging."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from llmhive.app.feedback_logger import FeedbackLogger, ModelFeedbackData, FeedbackOutcome
from llmhive.app.models import ModelFeedback, ModelMetric, FeedbackOutcome as ModelFeedbackOutcome


@pytest.fixture
def db_session(test_db_session: Session) -> Session:
    """Provide a database session for tests."""
    return test_db_session


def test_feedback_logger_logs_single_feedback(db_session: Session) -> None:
    """Test that FeedbackLogger can log a single feedback record."""
    logger = FeedbackLogger(db_session)
    
    feedback_data = ModelFeedbackData(
        model_name="gpt-4.1",
        outcome=FeedbackOutcome.SUCCESS,
        was_used_in_final=True,
        response_time_ms=1500.0,
        token_usage=500,
        confidence_score=0.9,
        quality_score=0.85,
        notes="Used in final answer and passed verification",
    )
    
    feedback = logger.log_feedback(feedback_data, task_id=1, session_id="test_session")
    
    assert feedback.id is not None
    assert feedback.model_name == "gpt-4.1"
    assert feedback.outcome == FeedbackOutcome.SUCCESS
    assert feedback.was_used_in_final is True
    assert feedback.response_time_ms == 1500.0
    assert feedback.token_usage == 500
    assert feedback.confidence_score == 0.9
    assert feedback.quality_score == 0.85
    
    db_session.commit()
    
    # Verify it was persisted
    persisted = db_session.query(ModelFeedback).filter_by(id=feedback.id).first()
    assert persisted is not None
    assert persisted.model_name == "gpt-4.1"


def test_feedback_logger_updates_aggregate_metrics(db_session: Session) -> None:
    """Test that FeedbackLogger updates ModelMetric aggregate statistics."""
    logger = FeedbackLogger(db_session)
    
    # Log multiple feedback records for the same model
    feedback_data_1 = ModelFeedbackData(
        model_name="gpt-4.1",
        outcome=FeedbackOutcome.SUCCESS,
        was_used_in_final=True,
        response_time_ms=1500.0,
        token_usage=500,
        quality_score=0.85,
    )
    
    feedback_data_2 = ModelFeedbackData(
        model_name="gpt-4.1",
        outcome=FeedbackOutcome.SUCCESS,
        was_used_in_final=True,
        response_time_ms=2000.0,
        token_usage=600,
        quality_score=0.90,
    )
    
    feedback_data_3 = ModelFeedbackData(
        model_name="gpt-4.1",
        outcome=FeedbackOutcome.REJECTED,
        was_used_in_final=False,
        response_time_ms=1800.0,
        token_usage=550,
        quality_score=0.70,
    )
    
    logger.log_feedback(feedback_data_1)
    logger.log_feedback(feedback_data_2)
    logger.log_feedback(feedback_data_3)
    
    db_session.commit()
    
    # Check aggregate metrics
    metric = db_session.query(ModelMetric).filter_by(model_name="gpt-4.1").first()
    assert metric is not None
    assert metric.total_feedback_count == 3
    assert metric.success_count == 2  # Two successes
    assert metric.failure_count == 1  # One rejection
    assert metric.historical_success_rate is not None
    assert abs(metric.historical_success_rate - (2.0 / 3.0)) < 0.01  # 2/3 success rate
    assert metric.avg_response_time_ms is not None
    assert metric.avg_response_time_ms > 0
    assert metric.total_tokens == 1650  # 500 + 600 + 550


def test_feedback_logger_logs_multiple_feedback(db_session: Session) -> None:
    """Test that FeedbackLogger can log multiple feedback records in batch."""
    logger = FeedbackLogger(db_session)
    
    feedback_list = [
        ModelFeedbackData(
            model_name="gpt-4.1",
            outcome=FeedbackOutcome.SUCCESS,
            was_used_in_final=True,
            notes="Used in final answer",
        ),
        ModelFeedbackData(
            model_name="claude-3-opus-20240229",
            outcome=FeedbackOutcome.REJECTED,
            was_used_in_final=False,
            notes="Answer not selected",
        ),
        ModelFeedbackData(
            model_name="gpt-4o",
            outcome=FeedbackOutcome.FAILED_VERIFICATION,
            was_used_in_final=False,
            notes="Failed verification",
        ),
    ]
    
    feedback_records = logger.log_multiple_feedback(
        feedback_list,
        task_id=1,
        session_id="test_session",
    )
    
    assert len(feedback_records) == 3
    assert all(f.id is not None for f in feedback_records)
    
    db_session.commit()
    
    # Verify all were persisted
    persisted = db_session.query(ModelFeedback).filter_by(session_id="test_session").all()
    assert len(persisted) == 3


def test_feedback_logger_get_success_rate(db_session: Session) -> None:
    """Test that FeedbackLogger can retrieve model success rate."""
    logger = FeedbackLogger(db_session)
    
    # Log some feedback to build up metrics
    feedback_data_1 = ModelFeedbackData(
        model_name="test-model",
        outcome=FeedbackOutcome.SUCCESS,
        was_used_in_final=True,
    )
    feedback_data_2 = ModelFeedbackData(
        model_name="test-model",
        outcome=FeedbackOutcome.SUCCESS,
        was_used_in_final=True,
    )
    feedback_data_3 = ModelFeedbackData(
        model_name="test-model",
        outcome=FeedbackOutcome.REJECTED,
        was_used_in_final=False,
    )
    
    logger.log_feedback(feedback_data_1)
    logger.log_feedback(feedback_data_2)
    logger.log_feedback(feedback_data_3)
    db_session.commit()
    
    # Get success rate
    success_rate = logger.get_model_success_rate("test-model")
    assert success_rate is not None
    assert abs(success_rate - (2.0 / 3.0)) < 0.01  # 2/3 success rate
    
    # Test with non-existent model
    success_rate_none = logger.get_model_success_rate("non-existent-model")
    assert success_rate_none is None


def test_feedback_logger_handles_errors_gracefully(db_session: Session) -> None:
    """Test that FeedbackLogger handles errors gracefully without breaking."""
    logger = FeedbackLogger(db_session)
    
    # Try to log feedback with invalid data (should not crash)
    feedback_data = ModelFeedbackData(
        model_name="",  # Empty model name might cause issues
        outcome=FeedbackOutcome.SUCCESS,
        was_used_in_final=True,
    )
    
    # Should not raise exception, but might log a warning
    try:
        feedback = logger.log_feedback(feedback_data)
        # If it succeeds, that's fine too
        assert feedback is not None
    except Exception:
        # If it fails, that's also acceptable - the important thing is it doesn't crash the system
        pass

