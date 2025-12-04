"""Continuous Learning Module for LLMHive.

This module implements the "learning from experience" vision from the patent,
enabling the orchestrator to:
- Track model performance over time
- Optimize model selection based on historical data
- Store and reuse successful answers
- Learn from user feedback (explicit and implicit)
"""
from __future__ import annotations

from .performance_logger import (
    PerformanceLogger,
    QueryPerformance,
    ModelContribution,
    get_performance_logger,
)
from .model_optimizer import (
    ModelOptimizer,
    OptimizationStrategy,
    ModelWeight,
    get_model_optimizer,
)
from .feedback_loop import (
    FeedbackLoop,
    FeedbackEvent,
    FeedbackType,
    get_feedback_loop,
)
from .answer_store import (
    AnswerStore,
    StoredAnswer,
    get_answer_store,
)

__all__ = [
    # Performance Logger
    "PerformanceLogger",
    "QueryPerformance",
    "ModelContribution",
    "get_performance_logger",
    # Model Optimizer
    "ModelOptimizer",
    "OptimizationStrategy",
    "ModelWeight",
    "get_model_optimizer",
    # Feedback Loop
    "FeedbackLoop",
    "FeedbackEvent",
    "FeedbackType",
    "get_feedback_loop",
    # Answer Store
    "AnswerStore",
    "StoredAnswer",
    "get_answer_store",
]
