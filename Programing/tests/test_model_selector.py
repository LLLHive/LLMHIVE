import pytest
from app.model_selector import ModelProfile, ModelSelector


def test_model_profile_creation():
    """Test creating a model profile."""
    profile = ModelProfile("GPT-4", ["reasoning", "coding"], cost=0.06, latency=1.0)
    assert profile.name == "GPT-4"
    assert profile.strengths == ["reasoning", "coding"]
    assert profile.cost == 0.06
    assert profile.latency == 1.0


def test_model_selector_add_model():
    """Test adding models to the selector."""
    selector = ModelSelector()
    profile = ModelProfile("GPT-4", ["reasoning"], cost=0.06, latency=1.0)
    selector.add_model(profile)
    assert len(selector.models) == 1


def test_model_selector_select_models():
    """Test selecting models based on task requirements."""
    selector = ModelSelector()
    selector.add_model(ModelProfile("GPT-4", ["reasoning", "coding"], cost=0.06, latency=1.0))
    selector.add_model(ModelProfile("Claude", ["long-form writing"], cost=0.04, latency=1.2))
    selector.add_model(ModelProfile("Llama", ["coding", "fast"], cost=0.01, latency=0.5))
    
    # Test selecting models for reasoning
    selected = selector.select_models(["reasoning"])
    assert len(selected) == 1
    assert selected[0].name == "GPT-4"
    
    # Test selecting models for coding
    selected = selector.select_models(["coding"])
    assert len(selected) == 2
    assert any(m.name == "GPT-4" for m in selected)
    assert any(m.name == "Llama" for m in selected)
    
    # Test selecting models for long-form writing
    selected = selector.select_models(["long-form writing"])
    assert len(selected) == 1
    assert selected[0].name == "Claude"


def test_model_selector_no_match():
    """Test selecting models when no match is found."""
    selector = ModelSelector()
    selector.add_model(ModelProfile("GPT-4", ["reasoning"], cost=0.06, latency=1.0))
    
    selected = selector.select_models(["translation"])
    assert len(selected) == 0
