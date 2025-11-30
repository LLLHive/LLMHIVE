"""Reward Model for RLHF.

This module provides:
- Reward model training on preference data
- Answer quality scoring
- Model checkpointing and versioning

The reward model learns to predict which answers users prefer,
enabling better answer selection and fine-tuning guidance.

Usage:
    # Train reward model
    reward_model = await train_reward_model(
        preference_pairs=pairs,
        output_dir="./models/reward",
    )
    
    # Score answers
    score = await reward_model.score(query, answer)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass(slots=True)
class RewardModelConfig:
    """Configuration for reward model training."""
    base_model: str = "microsoft/deberta-v3-base"  # Small but effective
    max_length: int = 512
    batch_size: int = 8
    learning_rate: float = 2e-5
    num_epochs: int = 3
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    output_dir: str = "./models/reward"
    use_class_weights: bool = True


@dataclass(slots=True)
class RewardScore:
    """Score from reward model."""
    score: float  # 0-1, higher is better
    confidence: float  # Model confidence
    reasoning: Optional[str] = None


@dataclass(slots=True)
class TrainingResult:
    """Result of reward model training."""
    success: bool
    model_path: str
    accuracy: float
    loss: float
    training_time_s: float
    num_examples: int
    error: Optional[str] = None


# ==============================================================================
# Heuristic Reward Model
# ==============================================================================

class HeuristicRewardModel:
    """Rule-based reward model for bootstrap/fallback.
    
    Uses heuristics to score answers when not enough data
    for neural reward model training.
    """
    
    def __init__(self):
        self.weights = {
            "length": 0.15,
            "structure": 0.2,
            "relevance": 0.35,
            "clarity": 0.3,
        }
    
    async def score(
        self,
        query: str,
        answer: str,
        context: Optional[str] = None,
    ) -> RewardScore:
        """Score an answer using heuristics."""
        scores = {}
        
        # Length score (prefer substantive but not too long)
        word_count = len(answer.split())
        if word_count < 10:
            scores["length"] = 0.3
        elif word_count < 50:
            scores["length"] = 0.7
        elif word_count < 200:
            scores["length"] = 1.0
        elif word_count < 500:
            scores["length"] = 0.8
        else:
            scores["length"] = 0.5
        
        # Structure score (paragraphs, lists, etc.)
        has_paragraphs = "\n\n" in answer or len(answer) < 200
        has_lists = any(c in answer for c in ["•", "-", "*", "1.", "2."])
        has_code = "```" in answer or "`" in answer
        
        scores["structure"] = 0.5
        if has_paragraphs:
            scores["structure"] += 0.2
        if has_lists and word_count > 50:
            scores["structure"] += 0.2
        if has_code and any(kw in query.lower() for kw in ["code", "program", "function", "python"]):
            scores["structure"] += 0.1
        
        # Relevance (keyword overlap)
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(query_words & answer_words) / max(len(query_words), 1)
        scores["relevance"] = min(0.5 + overlap, 1.0)
        
        # Clarity (no filler, direct)
        filler_phrases = [
            "i think", "maybe", "probably", "kind of", "sort of",
            "um", "uh", "you know", "like", "basically",
        ]
        filler_count = sum(1 for p in filler_phrases if p in answer.lower())
        scores["clarity"] = max(0.3, 1.0 - filler_count * 0.1)
        
        # Calculate weighted score
        total_score = sum(
            scores[k] * self.weights[k]
            for k in self.weights
        )
        
        return RewardScore(
            score=round(total_score, 3),
            confidence=0.5,  # Low confidence for heuristic
            reasoning=f"Length: {scores['length']:.2f}, Structure: {scores['structure']:.2f}, "
                      f"Relevance: {scores['relevance']:.2f}, Clarity: {scores['clarity']:.2f}",
        )


# ==============================================================================
# Neural Reward Model
# ==============================================================================

class RewardModel:
    """Neural reward model for answer quality prediction.
    
    Uses a transformer-based classifier to predict which answers
    users would prefer. Trained on preference pair data.
    
    Usage:
        model = RewardModel(config=RewardModelConfig())
        await model.load("./models/reward")
        
        score = await model.score("What is AI?", "AI is...")
    """
    
    def __init__(
        self,
        config: Optional[RewardModelConfig] = None,
    ):
        self.config = config or RewardModelConfig()
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._heuristic = HeuristicRewardModel()
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    async def load(self, model_path: str) -> bool:
        """Load trained reward model."""
        def _load():
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                
                self._tokenizer = AutoTokenizer.from_pretrained(model_path)
                self._model = AutoModelForSequenceClassification.from_pretrained(model_path)
                self._model.eval()
                
                return True
            except Exception as e:
                logger.warning("Could not load reward model: %s", e)
                return False
        
        try:
            success = await asyncio.to_thread(_load)
            self._loaded = success
            
            if success:
                logger.info("Reward model loaded from %s", model_path)
            
            return success
        except Exception as e:
            logger.warning("Failed to load reward model: %s", e)
            return False
    
    async def score(
        self,
        query: str,
        answer: str,
        context: Optional[str] = None,
    ) -> RewardScore:
        """
        Score an answer.
        
        Args:
            query: The question
            answer: The answer to score
            context: Optional context
            
        Returns:
            RewardScore with quality prediction
        """
        if not self._loaded:
            # Fall back to heuristic model
            return await self._heuristic.score(query, answer, context)
        
        def _score():
            import torch
            
            # Format input
            if context:
                text = f"Query: {query}\nContext: {context}\nAnswer: {answer}"
            else:
                text = f"Query: {query}\nAnswer: {answer}"
            
            # Tokenize
            inputs = self._tokenizer(
                text,
                truncation=True,
                max_length=self.config.max_length,
                padding="max_length",
                return_tensors="pt",
            )
            
            # Predict
            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                
                # Softmax for probabilities
                probs = torch.softmax(logits, dim=-1)
                
                # Assuming binary classification (bad=0, good=1)
                score = probs[0, 1].item()
                confidence = max(probs[0]).item()
            
            return score, confidence
        
        try:
            score, confidence = await asyncio.to_thread(_score)
            
            return RewardScore(
                score=round(score, 4),
                confidence=round(confidence, 4),
            )
        except Exception as e:
            logger.warning("Reward model scoring failed, using heuristic: %s", e)
            return await self._heuristic.score(query, answer, context)
    
    async def score_batch(
        self,
        items: List[Tuple[str, str, Optional[str]]],
    ) -> List[RewardScore]:
        """Score multiple query-answer pairs."""
        tasks = [
            self.score(query, answer, context)
            for query, answer, context in items
        ]
        return await asyncio.gather(*tasks)
    
    async def compare(
        self,
        query: str,
        answer_a: str,
        answer_b: str,
        context: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Compare two answers and return the better one.
        
        Returns:
            (better_answer, confidence)
        """
        score_a = await self.score(query, answer_a, context)
        score_b = await self.score(query, answer_b, context)
        
        if score_a.score > score_b.score:
            return answer_a, abs(score_a.score - score_b.score)
        else:
            return answer_b, abs(score_b.score - score_a.score)


# ==============================================================================
# Reward Model Training
# ==============================================================================

async def train_reward_model(
    preference_pairs: List[Any],  # List of PreferencePair
    config: Optional[RewardModelConfig] = None,
    on_step: Optional[Callable[[int, float], None]] = None,
) -> TrainingResult:
    """
    Train a reward model on preference data.
    
    Args:
        preference_pairs: List of (chosen, rejected) pairs
        config: Training configuration
        on_step: Optional callback for progress
        
    Returns:
        TrainingResult with trained model path
    """
    config = config or RewardModelConfig()
    
    if len(preference_pairs) < 10:
        return TrainingResult(
            success=False,
            model_path="",
            accuracy=0.0,
            loss=0.0,
            training_time_s=0.0,
            num_examples=len(preference_pairs),
            error="Insufficient training data (need at least 10 pairs)",
        )
    
    def _train():
        try:
            import torch
            from torch.utils.data import Dataset, DataLoader
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                TrainingArguments,
                Trainer,
            )
        except ImportError as e:
            return TrainingResult(
                success=False,
                model_path="",
                accuracy=0.0,
                loss=0.0,
                training_time_s=0.0,
                num_examples=len(preference_pairs),
                error=f"Missing dependencies: {e}",
            )
        
        start_time = time.time()
        
        try:
            # Prepare data
            texts = []
            labels = []
            
            for pair in preference_pairs:
                # Chosen answer (label=1)
                if hasattr(pair, 'context') and pair.context:
                    texts.append(f"Query: {pair.query}\nContext: {pair.context}\nAnswer: {pair.chosen}")
                else:
                    texts.append(f"Query: {pair.query}\nAnswer: {pair.chosen}")
                labels.append(1)
                
                # Rejected answer (label=0)
                if hasattr(pair, 'context') and pair.context:
                    texts.append(f"Query: {pair.query}\nContext: {pair.context}\nAnswer: {pair.rejected}")
                else:
                    texts.append(f"Query: {pair.query}\nAnswer: {pair.rejected}")
                labels.append(0)
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(config.base_model)
            model = AutoModelForSequenceClassification.from_pretrained(
                config.base_model,
                num_labels=2,
            )
            
            # Tokenize
            encodings = tokenizer(
                texts,
                truncation=True,
                max_length=config.max_length,
                padding="max_length",
                return_tensors="pt",
            )
            
            # Create dataset
            class RewardDataset(Dataset):
                def __init__(self, encodings, labels):
                    self.encodings = encodings
                    self.labels = labels
                
                def __len__(self):
                    return len(self.labels)
                
                def __getitem__(self, idx):
                    item = {k: v[idx] for k, v in self.encodings.items()}
                    item["labels"] = torch.tensor(self.labels[idx])
                    return item
            
            dataset = RewardDataset(encodings, labels)
            
            # Split train/eval
            train_size = int(0.9 * len(dataset))
            eval_size = len(dataset) - train_size
            train_dataset, eval_dataset = torch.utils.data.random_split(
                dataset, [train_size, eval_size]
            )
            
            # Training arguments
            Path(config.output_dir).mkdir(parents=True, exist_ok=True)
            
            training_args = TrainingArguments(
                output_dir=config.output_dir,
                num_train_epochs=config.num_epochs,
                per_device_train_batch_size=config.batch_size,
                per_device_eval_batch_size=config.batch_size,
                learning_rate=config.learning_rate,
                warmup_ratio=config.warmup_ratio,
                weight_decay=config.weight_decay,
                evaluation_strategy="epoch",
                save_strategy="epoch",
                load_best_model_at_end=True,
                logging_steps=10,
                report_to=[],
            )
            
            # Compute metrics
            def compute_metrics(pred):
                labels = pred.label_ids
                preds = pred.predictions.argmax(-1)
                acc = (preds == labels).mean()
                return {"accuracy": acc}
            
            # Train
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                compute_metrics=compute_metrics,
            )
            
            train_result = trainer.train()
            
            # Save final model
            trainer.save_model(config.output_dir)
            tokenizer.save_pretrained(config.output_dir)
            
            # Evaluate
            eval_result = trainer.evaluate()
            
            training_time = time.time() - start_time
            
            return TrainingResult(
                success=True,
                model_path=config.output_dir,
                accuracy=eval_result.get("eval_accuracy", 0.0),
                loss=eval_result.get("eval_loss", 0.0),
                training_time_s=training_time,
                num_examples=len(preference_pairs),
            )
            
        except Exception as e:
            logger.error("Reward model training failed: %s", e)
            return TrainingResult(
                success=False,
                model_path="",
                accuracy=0.0,
                loss=0.0,
                training_time_s=time.time() - start_time,
                num_examples=len(preference_pairs),
                error=str(e),
            )
    
    logger.info("Starting reward model training with %d pairs", len(preference_pairs))
    result = await asyncio.to_thread(_train)
    
    if result.success:
        logger.info(
            "Reward model trained: accuracy=%.2f%% time=%.1fs",
            result.accuracy * 100, result.training_time_s,
        )
    
    return result


# ==============================================================================
# Global Instance
# ==============================================================================

_reward_model: Optional[RewardModel] = None


def get_reward_model() -> RewardModel:
    """Get or create global reward model."""
    global _reward_model
    if _reward_model is None:
        _reward_model = RewardModel()
        
        # Try to load pre-trained model
        model_path = os.getenv("LLMHIVE_REWARD_MODEL", "./models/reward")
        if Path(model_path).exists():
            asyncio.create_task(_reward_model.load(model_path))
    
    return _reward_model

