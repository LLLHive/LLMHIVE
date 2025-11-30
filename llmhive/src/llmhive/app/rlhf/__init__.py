"""Reinforcement Learning from Human Feedback (RLHF) for LLMHive.

This module provides RLHF capabilities:
- Feedback collection and storage
- Reward model training
- Preference-based fine-tuning
- Answer ranking and selection

The RLHF pipeline:
1. Collect user feedback on answers (thumbs up/down, ratings)
2. Train a reward model to predict answer quality
3. Use reward model to select/rank candidate answers
4. Fine-tune models on preferred responses
"""
from __future__ import annotations

# Feedback collection
try:
    from .feedback import (
        FeedbackCollector,
        FeedbackEntry,
        FeedbackType,
        get_feedback_collector,
    )
    FEEDBACK_AVAILABLE = True
except ImportError:
    FEEDBACK_AVAILABLE = False
    FeedbackCollector = None  # type: ignore

# Reward model
try:
    from .reward_model import (
        RewardModel,
        RewardModelConfig,
        train_reward_model,
        get_reward_model,
    )
    REWARD_MODEL_AVAILABLE = True
except ImportError:
    REWARD_MODEL_AVAILABLE = False
    RewardModel = None  # type: ignore

# RLHF training
try:
    from .trainer import (
        RLHFTrainer,
        RLHFConfig,
        PreferenceDataset,
    )
    RLHF_TRAINER_AVAILABLE = True
except ImportError:
    RLHF_TRAINER_AVAILABLE = False
    RLHFTrainer = None  # type: ignore

# Answer ranker
try:
    from .ranker import (
        AnswerRanker,
        RankedAnswer,
        rank_answers,
    )
    RANKER_AVAILABLE = True
except ImportError:
    RANKER_AVAILABLE = False
    AnswerRanker = None  # type: ignore


__all__ = [
    "FEEDBACK_AVAILABLE",
    "REWARD_MODEL_AVAILABLE",
    "RLHF_TRAINER_AVAILABLE",
    "RANKER_AVAILABLE",
]

if FEEDBACK_AVAILABLE:
    __all__.extend([
        "FeedbackCollector",
        "FeedbackEntry",
        "FeedbackType",
        "get_feedback_collector",
    ])

if REWARD_MODEL_AVAILABLE:
    __all__.extend([
        "RewardModel",
        "RewardModelConfig",
        "train_reward_model",
        "get_reward_model",
    ])

if RLHF_TRAINER_AVAILABLE:
    __all__.extend([
        "RLHFTrainer",
        "RLHFConfig",
        "PreferenceDataset",
    ])

if RANKER_AVAILABLE:
    __all__.extend([
        "AnswerRanker",
        "RankedAnswer",
        "rank_answers",
    ])

