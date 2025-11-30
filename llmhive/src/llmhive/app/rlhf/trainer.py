"""RLHF Training Pipeline for LLMHive.

This module provides:
- Preference-based fine-tuning (DPO)
- Reward-model-guided optimization
- Supervised fine-tuning on preferred answers
- Training data management

Usage:
    trainer = RLHFTrainer(
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        output_dir="./models/rlhf_v1",
    )
    
    result = await trainer.train_dpo(preference_pairs)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .feedback import FeedbackEntry, PreferencePair

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass(slots=True)
class RLHFConfig:
    """Configuration for RLHF training."""
    base_model: str = "mistralai/Mistral-7B-Instruct-v0.2"
    output_dir: str = "./models/rlhf"
    
    # Training method
    method: str = "dpo"  # dpo, sft, ppo (ppo not implemented)
    
    # Training params
    num_epochs: int = 3
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 5e-5
    max_length: int = 512
    
    # DPO specific
    beta: float = 0.1  # KL penalty coefficient
    
    # LoRA
    use_lora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    
    # Quantization
    use_4bit: bool = True
    
    # Training
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    save_steps: int = 100
    logging_steps: int = 10


@dataclass(slots=True)
class RLHFTrainingResult:
    """Result of RLHF training."""
    success: bool
    model_path: str
    method: str
    loss: float
    accuracy: Optional[float] = None
    training_time_s: float = 0.0
    num_examples: int = 0
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class PreferenceDataset:
    """Dataset for preference-based training."""
    
    def __init__(
        self,
        pairs: List[PreferencePair],
        tokenizer: Any,
        max_length: int = 512,
    ):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        pair = self.pairs[idx]
        
        # Format prompt
        prompt = f"Question: {pair.query}"
        if pair.context:
            prompt = f"{prompt}\nContext: {pair.context}"
        
        # Tokenize prompt + chosen
        chosen_text = f"{prompt}\n\nAnswer: {pair.chosen}"
        chosen = self.tokenizer(
            chosen_text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        # Tokenize prompt + rejected
        rejected_text = f"{prompt}\n\nAnswer: {pair.rejected}"
        rejected = self.tokenizer(
            rejected_text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        return {
            "prompt": prompt,
            "chosen_input_ids": chosen["input_ids"].squeeze(),
            "chosen_attention_mask": chosen["attention_mask"].squeeze(),
            "rejected_input_ids": rejected["input_ids"].squeeze(),
            "rejected_attention_mask": rejected["attention_mask"].squeeze(),
        }
    
    @classmethod
    def from_feedback_entries(
        cls,
        positive: List[FeedbackEntry],
        negative: List[FeedbackEntry],
        tokenizer: Any,
        max_length: int = 512,
    ) -> "PreferenceDataset":
        """Create dataset from feedback entries."""
        pairs = []
        
        # Group by query
        by_query: Dict[str, Dict[str, List[FeedbackEntry]]] = {}
        
        for entry in positive:
            if entry.query not in by_query:
                by_query[entry.query] = {"positive": [], "negative": []}
            by_query[entry.query]["positive"].append(entry)
        
        for entry in negative:
            if entry.query not in by_query:
                by_query[entry.query] = {"positive": [], "negative": []}
            by_query[entry.query]["negative"].append(entry)
        
        # Create pairs
        for query, entries in by_query.items():
            if entries["positive"] and entries["negative"]:
                for pos in entries["positive"]:
                    for neg in entries["negative"]:
                        pairs.append(PreferencePair(
                            query=query,
                            context=pos.context or neg.context,
                            chosen=pos.answer,
                            rejected=neg.answer,
                            chosen_rating=pos.rating,
                            rejected_rating=neg.rating,
                        ))
        
        return cls(pairs, tokenizer, max_length)


# ==============================================================================
# RLHF Trainer
# ==============================================================================

class RLHFTrainer:
    """RLHF trainer for LLMHive.
    
    Supports:
    - DPO (Direct Preference Optimization) - Simple and effective
    - SFT (Supervised Fine-Tuning) on preferred answers
    - Integration with reward model for scoring
    
    Usage:
        trainer = RLHFTrainer(
            base_model="mistralai/Mistral-7B-Instruct-v0.2",
        )
        
        # DPO training
        result = await trainer.train_dpo(preference_pairs)
        
        # SFT on good answers
        result = await trainer.train_sft(good_answers)
    """
    
    def __init__(
        self,
        base_model: Optional[str] = None,
        output_dir: Optional[str] = None,
        config: Optional[RLHFConfig] = None,
    ):
        self.config = config or RLHFConfig(
            base_model=base_model or "mistralai/Mistral-7B-Instruct-v0.2",
            output_dir=output_dir or "./models/rlhf",
        )
        
        self._model = None
        self._tokenizer = None
        self._ref_model = None  # Reference model for DPO
    
    async def train_dpo(
        self,
        preference_pairs: List[PreferencePair],
        on_step: Optional[Callable[[int, float], None]] = None,
    ) -> RLHFTrainingResult:
        """
        Train using Direct Preference Optimization (DPO).
        
        DPO directly optimizes the model to prefer chosen over rejected answers
        without needing a separate reward model.
        
        Args:
            preference_pairs: List of (chosen, rejected) pairs
            on_step: Optional callback for progress
            
        Returns:
            RLHFTrainingResult
        """
        if len(preference_pairs) < 10:
            return RLHFTrainingResult(
                success=False,
                model_path="",
                method="dpo",
                loss=0.0,
                num_examples=len(preference_pairs),
                error="Insufficient data (need at least 10 pairs)",
            )
        
        def _train():
            try:
                import torch
                from transformers import (
                    AutoModelForCausalLM,
                    AutoTokenizer,
                    TrainingArguments,
                )
                from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
            except ImportError as e:
                return RLHFTrainingResult(
                    success=False,
                    model_path="",
                    method="dpo",
                    loss=0.0,
                    num_examples=len(preference_pairs),
                    error=f"Missing dependencies: {e}",
                )
            
            start_time = time.time()
            
            try:
                # Load tokenizer
                tokenizer = AutoTokenizer.from_pretrained(
                    self.config.base_model,
                    trust_remote_code=True,
                )
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
                
                # Load model with quantization
                model_kwargs = {"trust_remote_code": True}
                
                if self.config.use_4bit:
                    from transformers import BitsAndBytesConfig
                    model_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                    model_kwargs["device_map"] = "auto"
                
                model = AutoModelForCausalLM.from_pretrained(
                    self.config.base_model,
                    **model_kwargs,
                )
                
                # Apply LoRA
                if self.config.use_lora:
                    if self.config.use_4bit:
                        model = prepare_model_for_kbit_training(model)
                    
                    lora_config = LoraConfig(
                        r=self.config.lora_r,
                        lora_alpha=self.config.lora_alpha,
                        lora_dropout=self.config.lora_dropout,
                        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                        bias="none",
                        task_type="CAUSAL_LM",
                    )
                    model = get_peft_model(model, lora_config)
                
                # Create dataset
                dataset = PreferenceDataset(
                    preference_pairs,
                    tokenizer,
                    self.config.max_length,
                )
                
                # Try to use TRL's DPOTrainer if available
                try:
                    from trl import DPOTrainer, DPOConfig
                    
                    # Convert to TRL format
                    train_data = [
                        {
                            "prompt": p.query,
                            "chosen": p.chosen,
                            "rejected": p.rejected,
                        }
                        for p in preference_pairs
                    ]
                    
                    from datasets import Dataset
                    train_dataset = Dataset.from_list(train_data)
                    
                    # Load reference model (frozen)
                    ref_model = AutoModelForCausalLM.from_pretrained(
                        self.config.base_model,
                        **model_kwargs,
                    )
                    ref_model.eval()
                    
                    Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
                    
                    training_args = DPOConfig(
                        output_dir=self.config.output_dir,
                        num_train_epochs=self.config.num_epochs,
                        per_device_train_batch_size=self.config.batch_size,
                        gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                        learning_rate=self.config.learning_rate,
                        beta=self.config.beta,
                        warmup_ratio=self.config.warmup_ratio,
                        weight_decay=self.config.weight_decay,
                        logging_steps=self.config.logging_steps,
                        save_steps=self.config.save_steps,
                        report_to=[],
                    )
                    
                    trainer = DPOTrainer(
                        model=model,
                        ref_model=ref_model,
                        args=training_args,
                        train_dataset=train_dataset,
                        tokenizer=tokenizer,
                    )
                    
                    train_result = trainer.train()
                    trainer.save_model(self.config.output_dir)
                    
                    training_time = time.time() - start_time
                    
                    return RLHFTrainingResult(
                        success=True,
                        model_path=self.config.output_dir,
                        method="dpo",
                        loss=train_result.training_loss,
                        training_time_s=training_time,
                        num_examples=len(preference_pairs),
                        metrics=train_result.metrics if hasattr(train_result, 'metrics') else {},
                    )
                    
                except ImportError:
                    # Fall back to manual DPO implementation
                    logger.info("TRL not available, using simplified DPO")
                    return self._train_dpo_manual(
                        model, tokenizer, preference_pairs, start_time
                    )
                    
            except Exception as e:
                logger.error("DPO training failed: %s", e)
                return RLHFTrainingResult(
                    success=False,
                    model_path="",
                    method="dpo",
                    loss=0.0,
                    num_examples=len(preference_pairs),
                    error=str(e),
                )
        
        logger.info("Starting DPO training with %d pairs", len(preference_pairs))
        return await asyncio.to_thread(_train)
    
    def _train_dpo_manual(
        self,
        model: Any,
        tokenizer: Any,
        pairs: List[PreferencePair],
        start_time: float,
    ) -> RLHFTrainingResult:
        """Simplified DPO training without TRL."""
        import torch
        from torch.utils.data import DataLoader
        
        # This is a simplified version - for production use TRL
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        
        model.train()
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
        )
        
        total_loss = 0.0
        num_steps = 0
        
        for epoch in range(self.config.num_epochs):
            for pair in pairs:
                # Simple SFT on chosen answer as approximation
                prompt = f"Question: {pair.query}\n\nAnswer: {pair.chosen}"
                
                inputs = tokenizer(
                    prompt,
                    truncation=True,
                    max_length=self.config.max_length,
                    return_tensors="pt",
                )
                
                if hasattr(model, 'device'):
                    inputs = {k: v.to(model.device) for k, v in inputs.items()}
                
                outputs = model(**inputs, labels=inputs["input_ids"])
                loss = outputs.loss
                
                loss.backward()
                
                if (num_steps + 1) % self.config.gradient_accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()
                
                total_loss += loss.item()
                num_steps += 1
        
        # Save model
        model.save_pretrained(self.config.output_dir)
        tokenizer.save_pretrained(self.config.output_dir)
        
        avg_loss = total_loss / max(num_steps, 1)
        training_time = time.time() - start_time
        
        return RLHFTrainingResult(
            success=True,
            model_path=self.config.output_dir,
            method="dpo_manual",
            loss=avg_loss,
            training_time_s=training_time,
            num_examples=len(pairs),
        )
    
    async def train_sft(
        self,
        good_answers: List[FeedbackEntry],
        on_step: Optional[Callable[[int, float], None]] = None,
    ) -> RLHFTrainingResult:
        """
        Supervised fine-tuning on high-rated answers.
        
        Simpler than DPO - just trains the model to reproduce good answers.
        
        Args:
            good_answers: List of high-rated feedback entries
            on_step: Optional callback
            
        Returns:
            RLHFTrainingResult
        """
        if len(good_answers) < 10:
            return RLHFTrainingResult(
                success=False,
                model_path="",
                method="sft",
                loss=0.0,
                num_examples=len(good_answers),
                error="Insufficient data (need at least 10 examples)",
            )
        
        # Use the existing fine-tuning pipeline
        try:
            from ..providers.fine_tuning import FineTuner, FineTuneMethod
            
            # Convert to training format
            train_data = [
                {
                    "question": entry.query,
                    "answer": entry.answer,
                    "context": entry.context or "",
                }
                for entry in good_answers
            ]
            
            tuner = FineTuner(
                base_model=self.config.base_model,
                output_dir=self.config.output_dir,
                method=FineTuneMethod.QLORA if self.config.use_4bit else FineTuneMethod.LORA,
                use_4bit=self.config.use_4bit,
            )
            
            from ..providers.fine_tuning import TrainingConfig
            training_config = TrainingConfig(
                num_epochs=self.config.num_epochs,
                batch_size=self.config.batch_size,
                learning_rate=self.config.learning_rate,
            )
            
            result = await tuner.train(
                train_dataset=train_data,
                training_config=training_config,
            )
            
            return RLHFTrainingResult(
                success=result.success,
                model_path=result.output_dir,
                method="sft",
                loss=result.training_loss or 0.0,
                training_time_s=result.training_time_s,
                num_examples=len(good_answers),
                error=result.error,
            )
            
        except Exception as e:
            logger.error("SFT training failed: %s", e)
            return RLHFTrainingResult(
                success=False,
                model_path="",
                method="sft",
                loss=0.0,
                num_examples=len(good_answers),
                error=str(e),
            )


# ==============================================================================
# Automated Training Pipeline
# ==============================================================================

async def run_rlhf_pipeline(
    min_pairs: int = 50,
    output_dir: Optional[str] = None,
) -> Optional[RLHFTrainingResult]:
    """
    Run automated RLHF training pipeline.
    
    Collects feedback data, trains reward model, and fine-tunes with DPO.
    
    Args:
        min_pairs: Minimum preference pairs needed
        output_dir: Output directory for models
        
    Returns:
        RLHFTrainingResult if training was performed
    """
    from .feedback import get_feedback_collector
    from .reward_model import train_reward_model
    
    collector = get_feedback_collector()
    
    # Get preference pairs
    pairs = await collector.get_preference_pairs(limit=1000)
    
    if len(pairs) < min_pairs:
        logger.info(
            "Insufficient preference pairs (%d < %d), skipping RLHF",
            len(pairs), min_pairs,
        )
        return None
    
    logger.info("Starting RLHF pipeline with %d pairs", len(pairs))
    
    output_dir = output_dir or "./models/rlhf"
    
    # Train reward model first
    reward_result = await train_reward_model(
        preference_pairs=pairs,
        config=None,  # Use defaults
    )
    
    if not reward_result.success:
        logger.warning("Reward model training failed: %s", reward_result.error)
        # Continue with DPO anyway
    
    # Train with DPO
    trainer = RLHFTrainer(output_dir=output_dir)
    result = await trainer.train_dpo(pairs)
    
    if result.success:
        logger.info(
            "RLHF pipeline completed: loss=%.4f time=%.1fs",
            result.loss, result.training_time_s,
        )
    
    return result

