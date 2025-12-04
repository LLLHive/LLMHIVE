"""Tests for Local Model Provider and Fine-Tuning.

These tests verify:
1. LocalModelProvider configuration and loading
2. Model generation interface
3. Fine-tuning pipeline
4. Model registry operations
5. Orchestrator integration
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Any, Dict

# Skip tests if dependencies not available
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Import modules under test
from llmhive.app.providers.local_model import (
    LocalModelProvider,
    ChatLocalModelProvider,
    LocalModelConfig,
    DeviceType,
    QuantizationType,
    GenerationResult,
    RECOMMENDED_MODELS,
)
from llmhive.app.providers.fine_tuning import (
    FineTuner,
    FineTuneConfig,
    FineTuneMethod,
    LoRAConfig,
    TrainingConfig,
    TrainingStatus,
    DatasetPreparer,
    DatasetItem,
)
from llmhive.app.providers.model_registry import (
    ModelRegistry,
    ModelInfo,
    ModelType,
    ModelCapability,
    DEFAULT_API_MODELS,
    DEFAULT_LOCAL_MODELS,
    get_model_registry,
)


# ==============================================================================
# LocalModelProvider Tests
# ==============================================================================

class TestLocalModelConfig:
    """Tests for LocalModelConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LocalModelConfig(model_name="test/model")
        
        assert config.model_name == "test/model"
        assert config.device == DeviceType.AUTO
        assert config.quantization == QuantizationType.NONE
        assert config.max_new_tokens == 512
        assert config.temperature == 0.7
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = LocalModelConfig(
            model_name="mistral-7b",
            device=DeviceType.CUDA,
            quantization=QuantizationType.INT4,
            max_new_tokens=1024,
            temperature=0.5,
        )
        
        assert config.device == DeviceType.CUDA
        assert config.quantization == QuantizationType.INT4
        assert config.max_new_tokens == 1024


class TestLocalModelProvider:
    """Tests for LocalModelProvider."""
    
    def test_initialization(self):
        """Test provider initialization."""
        provider = LocalModelProvider(
            model_name="test/model",
            device=DeviceType.CPU,
        )
        
        assert provider.name == "local"
        assert provider.model_name == "test/model"
        assert provider.device == DeviceType.CPU
        assert not provider.is_loaded
    
    def test_initialization_with_quantization(self):
        """Test initialization with quantization options."""
        provider = LocalModelProvider(
            model_name="test/model",
            use_4bit=True,
        )
        
        assert provider.use_4bit is True
        assert provider.use_8bit is False
    
    def test_get_model_info_not_loaded(self):
        """Test model info when not loaded."""
        provider = LocalModelProvider(model_name="test/model")
        
        info = provider.get_model_info()
        
        assert info["name"] == "test/model"
        assert info["loaded"] is False
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_device_detection_cpu(self):
        """Test CPU device detection."""
        provider = LocalModelProvider(
            model_name="test/model",
            device=DeviceType.CPU,
        )
        
        device = provider._detect_device()
        assert device == "cpu"
    
    @pytest.mark.asyncio
    async def test_generate_interface(self):
        """Test generate method interface."""
        provider = LocalModelProvider(model_name="test/model")
        
        # Mock the sync generation
        mock_result = GenerationResult(
            content="Test response",
            text="Test response",
            model="test/model",
            tokens_used=50,
            generation_time_ms=100.0,
        )
        
        provider._generate_sync = MagicMock(return_value=mock_result)
        provider._loaded = True
        
        result = await provider.generate("Test prompt")
        
        assert result.content == "Test response"
        assert result.tokens_used == 50


class TestChatLocalModelProvider:
    """Tests for ChatLocalModelProvider with chat templates."""
    
    def test_initialization_with_system_prompt(self):
        """Test initialization with custom system prompt."""
        provider = ChatLocalModelProvider(
            model_name="test/model",
            system_prompt="You are a helpful assistant.",
        )
        
        assert provider.system_prompt == "You are a helpful assistant."
    
    def test_format_chat_fallback(self):
        """Test chat formatting fallback."""
        provider = ChatLocalModelProvider(model_name="test/model")
        provider._loaded = True
        
        # Mock tokenizer without chat template
        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template = MagicMock(side_effect=Exception("No template"))
        provider._tokenizer = mock_tokenizer
        
        result = provider._format_chat("Hello, how are you?")
        
        assert "Hello, how are you?" in result


# ==============================================================================
# Fine-Tuning Tests
# ==============================================================================

class TestDatasetItem:
    """Tests for DatasetItem."""
    
    def test_to_prompt_alpaca(self):
        """Test Alpaca template formatting."""
        item = DatasetItem(
            instruction="What is the capital of France?",
            output="The capital of France is Paris.",
        )
        
        prompt = item.to_prompt("alpaca")
        
        assert "### Instruction:" in prompt
        assert "What is the capital of France?" in prompt
        assert "### Response:" in prompt
        assert "Paris" in prompt
    
    def test_to_prompt_with_input(self):
        """Test Alpaca template with input context."""
        item = DatasetItem(
            instruction="Summarize the following text:",
            input="Long text here...",
            output="Summary here.",
        )
        
        prompt = item.to_prompt("alpaca")
        
        assert "### Input:" in prompt
        assert "Long text here" in prompt
    
    def test_to_prompt_chat(self):
        """Test chat template formatting."""
        item = DatasetItem(
            instruction="Hello",
            output="Hi there!",
        )
        
        prompt = item.to_prompt("chat")
        
        assert "<|user|>" in prompt
        assert "<|assistant|>" in prompt


class TestDatasetPreparer:
    """Tests for DatasetPreparer."""
    
    def test_from_qa_pairs(self):
        """Test creating dataset from Q&A pairs."""
        pairs = [
            {"question": "What is 2+2?", "answer": "4"},
            {"question": "What color is the sky?", "answer": "Blue"},
        ]
        
        prompts = DatasetPreparer.from_qa_pairs(pairs)
        
        assert len(prompts) == 2
        assert "2+2" in prompts[0]
        assert "4" in prompts[0]
    
    def test_from_qa_pairs_with_context(self):
        """Test Q&A pairs with context."""
        pairs = [
            {
                "question": "What is mentioned?",
                "context": "Some context here",
                "answer": "Something",
            },
        ]
        
        prompts = DatasetPreparer.from_qa_pairs(pairs)
        
        assert len(prompts) == 1
        assert "context" in prompts[0].lower()


class TestFineTuner:
    """Tests for FineTuner."""
    
    def test_initialization(self):
        """Test fine-tuner initialization."""
        tuner = FineTuner(
            base_model="test/model",
            output_dir="./output",
            method=FineTuneMethod.LORA,
        )
        
        assert tuner.base_model == "test/model"
        assert tuner.output_dir == "./output"
        assert tuner.method == FineTuneMethod.LORA
        assert tuner.status == TrainingStatus.PENDING
    
    def test_lora_config(self):
        """Test LoRA configuration."""
        config = LoRAConfig(
            r=32,
            lora_alpha=64,
            lora_dropout=0.1,
        )
        
        assert config.r == 32
        assert config.lora_alpha == 64
        assert config.lora_dropout == 0.1
    
    def test_training_config(self):
        """Test training configuration."""
        config = TrainingConfig(
            num_epochs=5,
            batch_size=8,
            learning_rate=1e-4,
        )
        
        assert config.num_epochs == 5
        assert config.batch_size == 8
        assert config.learning_rate == 1e-4


# ==============================================================================
# Model Registry Tests
# ==============================================================================

class TestModelInfo:
    """Tests for ModelInfo."""
    
    def test_model_info_creation(self):
        """Test creating ModelInfo."""
        info = ModelInfo(
            model_id="test-model",
            model_name="test/model",
            model_type=ModelType.LOCAL,
            provider="local",
            domains=["general", "coding"],
        )
        
        assert info.model_id == "test-model"
        assert info.model_type == ModelType.LOCAL
        assert "coding" in info.domains
    
    def test_default_values(self):
        """Test default values."""
        info = ModelInfo(
            model_id="test",
            model_name="test",
            model_type=ModelType.API,
            provider="openai",
        )
        
        assert info.context_length == 4096
        assert info.success_rate == 1.0
        assert info.is_available is True


class TestModelRegistry:
    """Tests for ModelRegistry."""
    
    def test_initialization_with_defaults(self):
        """Test registry initialization with defaults."""
        registry = ModelRegistry(include_defaults=True)
        
        # Should have API and local defaults
        assert len(registry._models) > 0
        assert "gpt-4o" in registry._models
        assert "mistral-7b-instruct" in registry._models
    
    def test_initialization_without_defaults(self):
        """Test registry initialization without defaults."""
        registry = ModelRegistry(include_defaults=False)
        
        assert len(registry._models) == 0
    
    def test_register_model(self):
        """Test registering a model."""
        registry = ModelRegistry(include_defaults=False)
        
        info = registry.register(
            model_id="custom-model",
            model_name="path/to/model",
            model_type=ModelType.FINE_TUNED,
            domains=["medical"],
        )
        
        assert info.model_id == "custom-model"
        assert registry.get("custom-model") is not None
    
    def test_unregister_model(self):
        """Test unregistering a model."""
        registry = ModelRegistry(include_defaults=False)
        registry.register("test", "test/model")
        
        result = registry.unregister("test")
        
        assert result is True
        assert registry.get("test") is None
    
    def test_list_models_by_type(self):
        """Test listing models by type."""
        registry = ModelRegistry(include_defaults=True)
        
        api_models = registry.list_models(model_type=ModelType.API)
        local_models = registry.list_models(model_type=ModelType.LOCAL)
        
        assert len(api_models) > 0
        assert len(local_models) > 0
        assert all(m.model_type == ModelType.API for m in api_models)
    
    def test_list_models_by_domain(self):
        """Test listing models by domain."""
        registry = ModelRegistry(include_defaults=True)
        
        coding_models = registry.list_models(domain="coding")
        
        assert len(coding_models) > 0
        assert all("coding" in m.domains for m in coding_models)
    
    def test_get_models_for_domain(self):
        """Test getting best models for a domain."""
        registry = ModelRegistry(include_defaults=True)
        
        models = registry.get_models_for_domain("general", limit=3)
        
        assert len(models) <= 3
        # Should be sorted by priority
        if len(models) >= 2:
            assert models[0].priority >= models[1].priority
    
    def test_get_best_model(self):
        """Test getting single best model."""
        registry = ModelRegistry(include_defaults=True)
        
        model = registry.get_best_model(domain="coding")
        
        assert model is not None
        assert "coding" in model.domains
    
    def test_get_best_model_prefer_local(self):
        """Test preferring local models."""
        registry = ModelRegistry(include_defaults=True)
        
        model = registry.get_best_model(domain="general", prefer_local=True)
        
        assert model is not None
        assert model.model_type in (ModelType.LOCAL, ModelType.FINE_TUNED)
    
    def test_update_performance(self):
        """Test updating performance metrics."""
        registry = ModelRegistry(include_defaults=True)
        
        initial_requests = registry._models["gpt-4o"].total_requests
        
        registry.update_performance("gpt-4o", latency_ms=100.0, success=True)
        
        assert registry._models["gpt-4o"].total_requests == initial_requests + 1
        assert registry._models["gpt-4o"].avg_latency_ms > 0


class TestDefaultModels:
    """Tests for default model configurations."""
    
    def test_api_models_defined(self):
        """Test that API models are properly defined."""
        assert "gpt-4o" in DEFAULT_API_MODELS
        assert "claude-3-5-sonnet" in DEFAULT_API_MODELS
        
        gpt4o = DEFAULT_API_MODELS["gpt-4o"]
        assert gpt4o.provider == "openai"
        assert ModelCapability.CHAT in gpt4o.capabilities
    
    def test_local_models_defined(self):
        """Test that local models are properly defined."""
        assert "mistral-7b-instruct" in DEFAULT_LOCAL_MODELS
        assert "phi-3-mini" in DEFAULT_LOCAL_MODELS
        
        mistral = DEFAULT_LOCAL_MODELS["mistral-7b-instruct"]
        assert mistral.provider == "local"
        assert mistral.use_4bit is True


class TestRecommendedModels:
    """Tests for recommended models mapping."""
    
    def test_general_models(self):
        """Test general purpose models."""
        assert "general" in RECOMMENDED_MODELS
        assert "small" in RECOMMENDED_MODELS["general"]
        assert "medium" in RECOMMENDED_MODELS["general"]
    
    def test_coding_models(self):
        """Test coding-specific models."""
        assert "coding" in RECOMMENDED_MODELS
        assert "codellama" in RECOMMENDED_MODELS["coding"]["medium"].lower()
    
    def test_fast_models(self):
        """Test fast/lightweight models."""
        assert "fast" in RECOMMENDED_MODELS
        assert "tinyllama" in RECOMMENDED_MODELS["fast"]["small"].lower()


# ==============================================================================
# GenerationResult Tests
# ==============================================================================

class TestGenerationResult:
    """Tests for GenerationResult."""
    
    def test_creation(self):
        """Test result creation."""
        result = GenerationResult(
            content="Generated text",
            text="Generated text",
            model="test/model",
            tokens_used=100,
            input_tokens=30,
            output_tokens=70,
        )
        
        assert result.content == "Generated text"
        assert result.text == result.content  # Alias
        assert result.tokens_used == 100
    
    def test_metadata(self):
        """Test result metadata."""
        result = GenerationResult(
            content="Test",
            text="Test",
            model="test",
            metadata={"temperature": 0.7},
        )
        
        assert result.metadata["temperature"] == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

