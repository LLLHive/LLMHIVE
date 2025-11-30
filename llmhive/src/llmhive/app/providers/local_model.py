"""Local Model Provider for LLMHive.

This module provides a provider for running local/open-source LLMs:
- HuggingFace Transformers integration
- 4-bit/8-bit quantization support via bitsandbytes
- GPU acceleration via CUDA/MPS
- Model loading from local paths or HuggingFace Hub
- Async generation with thread pool execution

Supported Models:
- Llama 2 / Llama 3 family
- Mistral / Mixtral
- Phi-2 / Phi-3
- GPT-J / GPT-NeoX
- Any HuggingFace compatible model

Usage:
    provider = LocalModelProvider(
        model_name="mistralai/Mistral-7B-Instruct-v0.2",
        use_4bit=True,
        device="cuda",
    )
    result = await provider.generate("What is machine learning?")
"""
from __future__ import annotations

import asyncio
import gc
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class DeviceType(str, Enum):
    """Supported device types."""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Silicon
    AUTO = "auto"


class QuantizationType(str, Enum):
    """Quantization options."""
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    GPTQ = "gptq"
    AWQ = "awq"


class ModelLoadError(Exception):
    """Error loading a model."""
    pass


@dataclass(slots=True)
class LocalModelConfig:
    """Configuration for local model loading."""
    model_name: str  # HuggingFace model ID or local path
    device: DeviceType = DeviceType.AUTO
    quantization: QuantizationType = QuantizationType.NONE
    max_memory: Optional[Dict[str, str]] = None  # e.g., {"cuda:0": "6GB"}
    trust_remote_code: bool = False
    use_flash_attention: bool = True
    torch_dtype: str = "auto"  # "float16", "bfloat16", "float32", "auto"
    cache_dir: Optional[str] = None
    load_in_8bit: bool = False
    load_in_4bit: bool = False
    # Generation defaults
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True


@dataclass(slots=True)
class GenerationResult:
    """Result of text generation."""
    content: str
    text: str  # Alias for content
    model: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    generation_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Default model recommendations by use case
RECOMMENDED_MODELS = {
    "general": {
        "small": "microsoft/phi-2",
        "medium": "mistralai/Mistral-7B-Instruct-v0.2",
        "large": "meta-llama/Llama-2-13b-chat-hf",
    },
    "coding": {
        "small": "Salesforce/codegen25-7b-mono",
        "medium": "codellama/CodeLlama-7b-Instruct-hf",
        "large": "codellama/CodeLlama-13b-Instruct-hf",
    },
    "reasoning": {
        "small": "microsoft/phi-2",
        "medium": "mistralai/Mistral-7B-Instruct-v0.2",
        "large": "meta-llama/Llama-2-13b-chat-hf",
    },
    "fast": {
        "small": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "medium": "microsoft/phi-2",
    },
}


# ==============================================================================
# Local Model Provider
# ==============================================================================

class LocalModelProvider:
    """Provider for running local HuggingFace models.
    
    Features:
    - Automatic device detection (CUDA, MPS, CPU)
    - Quantization support (4-bit, 8-bit)
    - Flash Attention 2 support
    - Async generation via thread pool
    - Memory management and cleanup
    
    Usage:
        provider = LocalModelProvider(
            model_name="mistralai/Mistral-7B-Instruct-v0.2",
            use_4bit=True,
        )
        
        result = await provider.generate(
            "Explain quantum computing",
            max_new_tokens=256,
            temperature=0.7,
        )
    """
    
    def __init__(
        self,
        model_name: str,
        *,
        device: Union[str, DeviceType] = DeviceType.AUTO,
        use_4bit: bool = False,
        use_8bit: bool = False,
        max_memory: Optional[Dict[str, str]] = None,
        trust_remote_code: bool = False,
        cache_dir: Optional[str] = None,
        max_workers: int = 2,
    ):
        """
        Initialize the LocalModelProvider.
        
        Args:
            model_name: HuggingFace model ID or local path
            device: Device to load model on
            use_4bit: Enable 4-bit quantization (requires bitsandbytes)
            use_8bit: Enable 8-bit quantization
            max_memory: Memory limits per device
            trust_remote_code: Trust remote code for custom models
            cache_dir: Custom cache directory
            max_workers: Thread pool workers for async
        """
        self.name = "local"
        self.model_name = model_name
        self.device = DeviceType(device) if isinstance(device, str) else device
        self.use_4bit = use_4bit
        self.use_8bit = use_8bit
        self.max_memory = max_memory
        self.trust_remote_code = trust_remote_code
        self.cache_dir = cache_dir
        
        self._model = None
        self._tokenizer = None
        self._device = None
        self._loaded = False
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Model info
        self._model_info: Dict[str, Any] = {}
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded
    
    def _detect_device(self) -> str:
        """Detect best available device."""
        import torch
        
        if self.device == DeviceType.CUDA and torch.cuda.is_available():
            return "cuda"
        elif self.device == DeviceType.MPS and torch.backends.mps.is_available():
            return "mps"
        elif self.device == DeviceType.AUTO:
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        
        return "cpu"
    
    def load_model(self) -> None:
        """Load the model and tokenizer.
        
        This is called automatically on first generation if not done manually.
        """
        if self._loaded:
            return
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            logger.info("Loading model: %s", self.model_name)
            start_time = time.time()
            
            # Detect device
            self._device = self._detect_device()
            logger.info("Using device: %s", self._device)
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=self.trust_remote_code,
                cache_dir=self.cache_dir,
            )
            
            # Ensure pad token is set
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Prepare model loading kwargs
            model_kwargs: Dict[str, Any] = {
                "trust_remote_code": self.trust_remote_code,
                "cache_dir": self.cache_dir,
            }
            
            # Handle quantization
            if self.use_4bit or self.use_8bit:
                try:
                    from transformers import BitsAndBytesConfig
                    
                    if self.use_4bit:
                        model_kwargs["quantization_config"] = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4",
                        )
                        logger.info("Using 4-bit quantization")
                    else:
                        model_kwargs["quantization_config"] = BitsAndBytesConfig(
                            load_in_8bit=True,
                        )
                        logger.info("Using 8-bit quantization")
                    
                    model_kwargs["device_map"] = "auto"
                    
                except ImportError:
                    logger.warning("bitsandbytes not available, loading without quantization")
            
            # Set torch dtype
            if self._device == "cuda":
                model_kwargs["torch_dtype"] = torch.float16
            elif self._device == "mps":
                model_kwargs["torch_dtype"] = torch.float16
            
            # Memory limits
            if self.max_memory:
                model_kwargs["max_memory"] = self.max_memory
                model_kwargs["device_map"] = "auto"
            
            # Load model
            if not self.use_4bit and not self.use_8bit and "device_map" not in model_kwargs:
                model_kwargs["device_map"] = self._device
            
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs,
            )
            
            # Set to eval mode
            self._model.eval()
            
            self._loaded = True
            load_time = time.time() - start_time
            
            # Store model info
            self._model_info = {
                "name": self.model_name,
                "device": self._device,
                "quantization": "4bit" if self.use_4bit else ("8bit" if self.use_8bit else "none"),
                "load_time_s": load_time,
                "parameters": sum(p.numel() for p in self._model.parameters()),
            }
            
            logger.info(
                "Model loaded in %.1fs: %d parameters",
                load_time,
                self._model_info["parameters"],
            )
            
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            raise ModelLoadError(f"Failed to load model {self.model_name}: {e}")
    
    def unload_model(self) -> None:
        """Unload the model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
        
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        
        self._loaded = False
        
        # Force garbage collection
        gc.collect()
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        
        logger.info("Model unloaded")
    
    def _generate_sync(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        do_sample: bool = True,
        **kwargs,
    ) -> GenerationResult:
        """Synchronous generation (runs in thread pool)."""
        import torch
        
        if not self._loaded:
            self.load_model()
        
        start_time = time.time()
        
        # Tokenize input
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096,
        )
        
        # Move to device
        if hasattr(self._model, 'device'):
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        input_length = inputs["input_ids"].shape[1]
        
        # Generate
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if do_sample else 1.0,
                top_p=top_p if do_sample else 1.0,
                top_k=top_k if do_sample else 0,
                repetition_penalty=repetition_penalty,
                do_sample=do_sample,
                pad_token_id=self._tokenizer.pad_token_id,
                eos_token_id=self._tokenizer.eos_token_id,
                **kwargs,
            )
        
        # Decode output (only new tokens)
        generated_ids = outputs[0, input_length:]
        generated_text = self._tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        
        generation_time = (time.time() - start_time) * 1000
        output_tokens = len(generated_ids)
        
        return GenerationResult(
            content=generated_text.strip(),
            text=generated_text.strip(),
            model=self.model_name,
            tokens_used=input_length + output_tokens,
            input_tokens=input_length,
            output_tokens=output_tokens,
            generation_time_ms=generation_time,
            metadata={
                "temperature": temperature,
                "top_p": top_p,
                "device": self._device,
            },
        )
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,  # Ignored for local, kept for interface
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        do_sample: bool = True,
        **kwargs,
    ) -> GenerationResult:
        """
        Generate text asynchronously.
        
        Args:
            prompt: Input prompt
            model: Ignored (uses loaded model)
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p (nucleus) sampling
            top_k: Top-k sampling
            repetition_penalty: Repetition penalty
            do_sample: Whether to sample
            **kwargs: Additional generation kwargs
            
        Returns:
            GenerationResult with generated text
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self._executor,
            lambda: self._generate_sync(
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                do_sample=do_sample,
                **kwargs,
            ),
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self._loaded:
            return {"name": self.model_name, "loaded": False}
        
        return {
            **self._model_info,
            "loaded": True,
        }
    
    def __del__(self):
        """Cleanup on deletion."""
        self.unload_model()
        self._executor.shutdown(wait=False)


# ==============================================================================
# Chat Template Support
# ==============================================================================

class ChatLocalModelProvider(LocalModelProvider):
    """Local model provider with chat template support.
    
    Automatically formats prompts using the model's chat template
    for instruction-following models like Llama-2-Chat, Mistral-Instruct, etc.
    """
    
    def __init__(
        self,
        model_name: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize with chat support.
        
        Args:
            model_name: HuggingFace model ID
            system_prompt: Default system prompt
            **kwargs: Parent class arguments
        """
        super().__init__(model_name, **kwargs)
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
    
    def _format_chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Format prompt using chat template."""
        if not self._loaded:
            self.load_model()
        
        messages = []
        
        if system_prompt or self.system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt or self.system_prompt,
            })
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Use tokenizer's chat template if available
            formatted = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            return formatted
        except Exception:
            # Fallback to simple formatting
            if messages[0]["role"] == "system":
                return f"System: {messages[0]['content']}\n\nUser: {prompt}\n\nAssistant:"
            return f"User: {prompt}\n\nAssistant:"
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate with chat formatting."""
        formatted_prompt = self._format_chat(prompt, system_prompt)
        return await super().generate(formatted_prompt, model=model, **kwargs)


# ==============================================================================
# Convenience Functions
# ==============================================================================

_local_provider: Optional[LocalModelProvider] = None


def get_local_provider(
    model_name: Optional[str] = None,
    **kwargs,
) -> LocalModelProvider:
    """Get or create global local model provider."""
    global _local_provider
    
    if _local_provider is None:
        if model_name is None:
            # Default to a small, fast model
            model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        
        _local_provider = ChatLocalModelProvider(
            model_name,
            use_4bit=kwargs.get("use_4bit", True),
            **kwargs,
        )
    
    return _local_provider


def reset_local_provider() -> None:
    """Reset global local provider."""
    global _local_provider
    if _local_provider is not None:
        _local_provider.unload_model()
        _local_provider = None


async def generate_local(
    prompt: str,
    model_name: Optional[str] = None,
    **kwargs,
) -> GenerationResult:
    """Quick helper to generate with local model."""
    provider = get_local_provider(model_name)
    return await provider.generate(prompt, **kwargs)

