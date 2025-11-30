"""Fine-Tuning Pipeline for LLMHive.

This module provides tools for fine-tuning language models:
- LoRA (Low-Rank Adaptation) for efficient fine-tuning
- Full fine-tuning support
- Dataset preparation utilities
- Training job management
- Model versioning and registration

Usage:
    tuner = FineTuner(
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        output_dir="./fine_tuned_models/medical_v1",
    )
    
    result = await tuner.train(
        train_dataset=my_qa_pairs,
        num_epochs=3,
        use_lora=True,
    )
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class TrainingStatus(str, Enum):
    """Status of a training job."""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FineTuneMethod(str, Enum):
    """Fine-tuning methods."""
    FULL = "full"
    LORA = "lora"
    QLORA = "qlora"  # QLoRA with 4-bit quantization
    PREFIX = "prefix"


@dataclass(slots=True)
class LoRAConfig:
    """Configuration for LoRA fine-tuning."""
    r: int = 16  # Rank
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: Optional[List[str]] = None  # Auto-detect if None
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass(slots=True)
class TrainingConfig:
    """Configuration for training."""
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    max_seq_length: int = 512
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    fp16: bool = True
    bf16: bool = False
    gradient_checkpointing: bool = True
    optim: str = "adamw_torch"
    lr_scheduler_type: str = "cosine"
    seed: int = 42


@dataclass(slots=True)
class FineTuneConfig:
    """Full configuration for fine-tuning job."""
    base_model: str
    output_dir: str
    method: FineTuneMethod = FineTuneMethod.LORA
    lora_config: LoRAConfig = field(default_factory=LoRAConfig)
    training_config: TrainingConfig = field(default_factory=TrainingConfig)
    use_4bit: bool = True  # For QLoRA
    use_8bit: bool = False
    domain: Optional[str] = None  # e.g., "medical", "legal", "coding"
    description: Optional[str] = None


@dataclass(slots=True)
class FineTuneResult:
    """Result of fine-tuning job."""
    success: bool
    output_dir: str
    model_name: str
    status: TrainingStatus
    training_loss: Optional[float] = None
    eval_loss: Optional[float] = None
    total_steps: int = 0
    training_time_s: float = 0.0
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetItem:
    """A single training example."""
    instruction: str
    input: str = ""
    output: str = ""
    
    def to_prompt(self, template: str = "alpaca") -> str:
        """Convert to training prompt."""
        if template == "alpaca":
            if self.input:
                return f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{self.instruction}

### Input:
{self.input}

### Response:
{self.output}"""
            else:
                return f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{self.instruction}

### Response:
{self.output}"""
        
        elif template == "chat":
            if self.input:
                return f"<|user|>\n{self.instruction}\n\n{self.input}<|end|>\n<|assistant|>\n{self.output}<|end|>"
            else:
                return f"<|user|>\n{self.instruction}<|end|>\n<|assistant|>\n{self.output}<|end|>"
        
        else:
            return f"Q: {self.instruction}\nA: {self.output}"


# ==============================================================================
# Dataset Utilities
# ==============================================================================

class DatasetPreparer:
    """Prepare datasets for fine-tuning."""
    
    @staticmethod
    def from_qa_pairs(
        pairs: List[Dict[str, str]],
        template: str = "alpaca",
    ) -> List[str]:
        """Convert Q&A pairs to training prompts.
        
        Args:
            pairs: List of dicts with 'question' and 'answer' keys
            template: Prompt template to use
            
        Returns:
            List of formatted training strings
        """
        items = []
        for pair in pairs:
            item = DatasetItem(
                instruction=pair.get("question", pair.get("instruction", "")),
                input=pair.get("context", pair.get("input", "")),
                output=pair.get("answer", pair.get("output", "")),
            )
            items.append(item.to_prompt(template))
        
        return items
    
    @staticmethod
    def from_jsonl(
        file_path: str,
        template: str = "alpaca",
    ) -> List[str]:
        """Load dataset from JSONL file."""
        items = []
        with open(file_path, "r") as f:
            for line in f:
                data = json.loads(line)
                item = DatasetItem(
                    instruction=data.get("instruction", data.get("question", "")),
                    input=data.get("input", data.get("context", "")),
                    output=data.get("output", data.get("answer", "")),
                )
                items.append(item.to_prompt(template))
        
        return items
    
    @staticmethod
    def from_csv(
        file_path: str,
        question_col: str = "question",
        answer_col: str = "answer",
        context_col: Optional[str] = None,
        template: str = "alpaca",
    ) -> List[str]:
        """Load dataset from CSV file."""
        import csv
        
        items = []
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = DatasetItem(
                    instruction=row.get(question_col, ""),
                    input=row.get(context_col, "") if context_col else "",
                    output=row.get(answer_col, ""),
                )
                items.append(item.to_prompt(template))
        
        return items
    
    @staticmethod
    def save_prepared_dataset(
        prompts: List[str],
        output_path: str,
    ) -> str:
        """Save prepared dataset to file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            for prompt in prompts:
                json.dump({"text": prompt}, f)
                f.write("\n")
        
        logger.info("Saved %d training examples to %s", len(prompts), output_path)
        return output_path


# ==============================================================================
# Fine-Tuner
# ==============================================================================

class FineTuner:
    """Fine-tune language models with LoRA or full training.
    
    Features:
    - LoRA/QLoRA for efficient training
    - Full fine-tuning support
    - Automatic dataset preparation
    - Training progress callbacks
    - Model versioning
    
    Usage:
        tuner = FineTuner(
            base_model="mistralai/Mistral-7B-Instruct-v0.2",
            output_dir="./models/medical_v1",
        )
        
        # Prepare dataset
        train_data = [
            {"question": "What is diabetes?", "answer": "Diabetes is..."},
            ...
        ]
        
        # Train
        result = await tuner.train(
            train_dataset=train_data,
            num_epochs=3,
        )
        
        # Load fine-tuned model
        provider = tuner.get_provider()
    """
    
    def __init__(
        self,
        base_model: str,
        output_dir: str,
        *,
        method: FineTuneMethod = FineTuneMethod.LORA,
        use_4bit: bool = True,
        domain: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize fine-tuner.
        
        Args:
            base_model: HuggingFace model ID
            output_dir: Directory to save fine-tuned model
            method: Fine-tuning method (lora, qlora, full)
            use_4bit: Use 4-bit quantization (for QLoRA)
            domain: Domain tag for the model
            description: Description of the fine-tuned model
        """
        self.base_model = base_model
        self.output_dir = output_dir
        self.method = method
        self.use_4bit = use_4bit and method in (FineTuneMethod.LORA, FineTuneMethod.QLORA)
        self.domain = domain
        self.description = description
        
        self._status = TrainingStatus.PENDING
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._cancel_requested = False
    
    @property
    def status(self) -> TrainingStatus:
        return self._status
    
    def _train_sync(
        self,
        train_texts: List[str],
        eval_texts: Optional[List[str]] = None,
        lora_config: Optional[LoRAConfig] = None,
        training_config: Optional[TrainingConfig] = None,
        on_step: Optional[Callable[[int, float], None]] = None,
    ) -> FineTuneResult:
        """Synchronous training (runs in thread pool)."""
        import torch
        
        try:
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                TrainingArguments,
                Trainer,
                DataCollatorForLanguageModeling,
            )
            from datasets import Dataset
        except ImportError as e:
            return FineTuneResult(
                success=False,
                output_dir=self.output_dir,
                model_name=self.base_model,
                status=TrainingStatus.FAILED,
                error=f"Missing required libraries: {e}. Install with: pip install transformers datasets",
            )
        
        lora_config = lora_config or LoRAConfig()
        training_config = training_config or TrainingConfig()
        
        self._status = TrainingStatus.PREPARING
        start_time = time.time()
        
        try:
            # Create output directory
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            
            logger.info("Loading base model: %s", self.base_model)
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                self.base_model,
                trust_remote_code=True,
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Prepare model loading kwargs
            model_kwargs: Dict[str, Any] = {
                "trust_remote_code": True,
            }
            
            # Handle quantization for QLoRA
            if self.use_4bit and self.method in (FineTuneMethod.LORA, FineTuneMethod.QLORA):
                try:
                    from transformers import BitsAndBytesConfig
                    
                    model_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                    model_kwargs["device_map"] = "auto"
                    logger.info("Using 4-bit QLoRA")
                except ImportError:
                    logger.warning("bitsandbytes not available, using standard LoRA")
            else:
                model_kwargs["torch_dtype"] = torch.float16
                if torch.cuda.is_available():
                    model_kwargs["device_map"] = "auto"
            
            # Load model
            model = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                **model_kwargs,
            )
            
            # Apply LoRA if using that method
            if self.method in (FineTuneMethod.LORA, FineTuneMethod.QLORA):
                try:
                    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
                    
                    # Prepare for k-bit training if quantized
                    if self.use_4bit:
                        model = prepare_model_for_kbit_training(model)
                    
                    # Determine target modules
                    target_modules = lora_config.target_modules
                    if target_modules is None:
                        # Auto-detect common target modules
                        target_modules = self._detect_target_modules(model)
                    
                    peft_config = LoraConfig(
                        r=lora_config.r,
                        lora_alpha=lora_config.lora_alpha,
                        lora_dropout=lora_config.lora_dropout,
                        target_modules=target_modules,
                        bias=lora_config.bias,
                        task_type=lora_config.task_type,
                    )
                    
                    model = get_peft_model(model, peft_config)
                    model.print_trainable_parameters()
                    logger.info("LoRA adapters applied")
                    
                except ImportError:
                    logger.error("PEFT library not available for LoRA training")
                    return FineTuneResult(
                        success=False,
                        output_dir=self.output_dir,
                        model_name=self.base_model,
                        status=TrainingStatus.FAILED,
                        error="PEFT library required for LoRA. Install with: pip install peft",
                    )
            
            # Prepare dataset
            def tokenize_function(examples):
                return tokenizer(
                    examples["text"],
                    truncation=True,
                    max_length=training_config.max_seq_length,
                    padding="max_length",
                )
            
            train_dataset = Dataset.from_dict({"text": train_texts})
            train_dataset = train_dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=["text"],
            )
            
            eval_dataset = None
            if eval_texts:
                eval_dataset = Dataset.from_dict({"text": eval_texts})
                eval_dataset = eval_dataset.map(
                    tokenize_function,
                    batched=True,
                    remove_columns=["text"],
                )
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=self.output_dir,
                num_train_epochs=training_config.num_epochs,
                per_device_train_batch_size=training_config.batch_size,
                gradient_accumulation_steps=training_config.gradient_accumulation_steps,
                learning_rate=training_config.learning_rate,
                warmup_ratio=training_config.warmup_ratio,
                weight_decay=training_config.weight_decay,
                logging_steps=training_config.logging_steps,
                save_steps=training_config.save_steps,
                eval_steps=training_config.eval_steps if eval_dataset else None,
                evaluation_strategy="steps" if eval_dataset else "no",
                fp16=training_config.fp16 and torch.cuda.is_available(),
                bf16=training_config.bf16,
                gradient_checkpointing=training_config.gradient_checkpointing,
                optim=training_config.optim,
                lr_scheduler_type=training_config.lr_scheduler_type,
                seed=training_config.seed,
                save_total_limit=3,
                load_best_model_at_end=bool(eval_dataset),
                report_to=[],  # Disable wandb etc
            )
            
            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False,
            )
            
            # Custom callback for progress
            class ProgressCallback:
                def __init__(self, on_step_fn):
                    self.on_step = on_step_fn
                
                def on_log(self, args, state, control, logs=None, **kwargs):
                    if logs and self.on_step and "loss" in logs:
                        self.on_step(state.global_step, logs.get("loss", 0))
            
            callbacks = []
            if on_step:
                callbacks.append(ProgressCallback(on_step))
            
            # Create trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
                callbacks=callbacks,
            )
            
            # Train
            self._status = TrainingStatus.TRAINING
            logger.info("Starting training...")
            
            train_result = trainer.train()
            
            # Save model
            trainer.save_model(self.output_dir)
            tokenizer.save_pretrained(self.output_dir)
            
            # Save training info
            info = {
                "base_model": self.base_model,
                "method": self.method.value,
                "domain": self.domain,
                "description": self.description,
                "training_loss": train_result.training_loss,
                "total_steps": train_result.global_step,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            with open(os.path.join(self.output_dir, "fine_tune_info.json"), "w") as f:
                json.dump(info, f, indent=2)
            
            self._status = TrainingStatus.COMPLETED
            training_time = time.time() - start_time
            
            logger.info("Training completed in %.1fs", training_time)
            
            return FineTuneResult(
                success=True,
                output_dir=self.output_dir,
                model_name=f"{self.base_model}-finetuned",
                status=TrainingStatus.COMPLETED,
                training_loss=train_result.training_loss,
                total_steps=train_result.global_step,
                training_time_s=training_time,
                metrics=train_result.metrics,
            )
            
        except Exception as e:
            self._status = TrainingStatus.FAILED
            logger.error("Training failed: %s", e)
            
            return FineTuneResult(
                success=False,
                output_dir=self.output_dir,
                model_name=self.base_model,
                status=TrainingStatus.FAILED,
                error=str(e),
            )
    
    def _detect_target_modules(self, model) -> List[str]:
        """Auto-detect LoRA target modules based on model architecture."""
        model_type = getattr(model.config, "model_type", "").lower()
        
        # Common target modules by model type
        target_modules_map = {
            "llama": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            "mistral": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            "phi": ["q_proj", "k_proj", "v_proj", "dense"],
            "gpt2": ["c_attn", "c_proj"],
            "gpt_neo": ["k_proj", "v_proj", "q_proj", "out_proj"],
            "bloom": ["query_key_value", "dense"],
            "falcon": ["query_key_value", "dense"],
            "default": ["q_proj", "v_proj"],
        }
        
        return target_modules_map.get(model_type, target_modules_map["default"])
    
    async def train(
        self,
        train_dataset: Union[List[str], List[Dict[str, str]]],
        eval_dataset: Optional[Union[List[str], List[Dict[str, str]]]] = None,
        lora_config: Optional[LoRAConfig] = None,
        training_config: Optional[TrainingConfig] = None,
        prompt_template: str = "alpaca",
        on_step: Optional[Callable[[int, float], None]] = None,
    ) -> FineTuneResult:
        """
        Fine-tune the model asynchronously.
        
        Args:
            train_dataset: Training data (list of strings or Q&A dicts)
            eval_dataset: Optional evaluation data
            lora_config: LoRA configuration
            training_config: Training configuration
            prompt_template: Template for formatting (alpaca, chat)
            on_step: Optional callback for progress (step, loss)
            
        Returns:
            FineTuneResult with training metrics
        """
        # Prepare training texts
        if train_dataset and isinstance(train_dataset[0], dict):
            train_texts = DatasetPreparer.from_qa_pairs(train_dataset, prompt_template)
        else:
            train_texts = train_dataset
        
        eval_texts = None
        if eval_dataset:
            if isinstance(eval_dataset[0], dict):
                eval_texts = DatasetPreparer.from_qa_pairs(eval_dataset, prompt_template)
            else:
                eval_texts = eval_dataset
        
        logger.info("Starting fine-tuning with %d training examples", len(train_texts))
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self._train_sync(
                train_texts,
                eval_texts,
                lora_config,
                training_config,
                on_step,
            ),
        )
    
    def get_provider(self, use_4bit: bool = True) -> "LocalModelProvider":
        """Get a provider for the fine-tuned model.
        
        Args:
            use_4bit: Use 4-bit quantization
            
        Returns:
            LocalModelProvider for the fine-tuned model
        """
        from .local_model import ChatLocalModelProvider
        
        return ChatLocalModelProvider(
            self.output_dir,
            use_4bit=use_4bit,
        )
    
    def cancel(self) -> None:
        """Request training cancellation."""
        self._cancel_requested = True
        logger.info("Training cancellation requested")


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def fine_tune_model(
    base_model: str,
    train_data: List[Dict[str, str]],
    output_dir: str,
    *,
    eval_data: Optional[List[Dict[str, str]]] = None,
    num_epochs: int = 3,
    use_lora: bool = True,
    use_4bit: bool = True,
    domain: Optional[str] = None,
) -> FineTuneResult:
    """
    Quick helper to fine-tune a model.
    
    Args:
        base_model: HuggingFace model ID
        train_data: List of Q&A dicts
        output_dir: Output directory
        eval_data: Optional evaluation data
        num_epochs: Number of training epochs
        use_lora: Use LoRA (default True)
        use_4bit: Use 4-bit quantization (default True)
        domain: Domain tag
        
    Returns:
        FineTuneResult
    
    Example:
        result = await fine_tune_model(
            "mistralai/Mistral-7B-Instruct-v0.2",
            train_data=[
                {"question": "What is X?", "answer": "X is..."},
                ...
            ],
            output_dir="./models/my_model",
            domain="medical",
        )
    """
    method = FineTuneMethod.QLORA if use_lora and use_4bit else (
        FineTuneMethod.LORA if use_lora else FineTuneMethod.FULL
    )
    
    tuner = FineTuner(
        base_model=base_model,
        output_dir=output_dir,
        method=method,
        use_4bit=use_4bit,
        domain=domain,
    )
    
    training_config = TrainingConfig(num_epochs=num_epochs)
    
    return await tuner.train(
        train_dataset=train_data,
        eval_dataset=eval_data,
        training_config=training_config,
    )

