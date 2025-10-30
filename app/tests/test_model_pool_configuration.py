"""
Test model pool configuration with all 6 required models.
"""
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.models.model_pool import ModelPool


def test_model_pool_loads_all_models():
    """Test that ModelPool loads all 6 models from models.yaml."""
    pool = ModelPool()
    models = pool.list_models()
    
    # Should have exactly 6 models
    assert len(models) == 6, f"Expected 6 models but got {len(models)}"
    print(f"✓ ModelPool loaded {len(models)} models")


def test_all_required_models_present():
    """Test that all required models are present in ModelPool."""
    pool = ModelPool()
    
    expected_models = {
        'gpt-4-turbo': 'openai',
        'gpt-4': 'openai',
        'claude-3-opus': 'anthropic',
        'claude-3-sonnet': 'anthropic',
        'gemini-pro': 'google',
        'grok-1': 'xai',
    }
    
    for model_id, expected_provider in expected_models.items():
        profile = pool.get_model_profile(model_id)
        assert profile is not None, f"Model {model_id} not found in ModelPool"
        assert profile.provider == expected_provider, f"Model {model_id} has wrong provider: {profile.provider}"
        print(f"✓ {model_id} ({expected_provider}) found")


def test_model_attributes():
    """Test that models have correct attributes."""
    pool = ModelPool()
    
    # Test gemini-pro
    gemini = pool.get_model_profile('gemini-pro')
    assert gemini is not None
    assert gemini.provider == 'google'
    assert 'multimodal' in gemini.strengths
    assert 'reasoning' in gemini.strengths
    assert gemini.context_window == 128000
    assert gemini.cost_per_token == 0.0025
    print("✓ gemini-pro attributes correct")
    
    # Test grok-1
    grok = pool.get_model_profile('grok-1')
    assert grok is not None
    assert grok.provider == 'xai'
    assert 'real-time-information' in grok.strengths
    assert 'humor' in grok.strengths
    assert grok.context_window == 8192
    assert grok.cost_per_token == 0.01
    print("✓ grok-1 attributes correct")


def test_default_models_fallback():
    """Test that default models include all 6 models when config file is missing."""
    import tempfile
    import os
    
    # Temporarily set MODEL_CONFIG_PATH to non-existent file
    original_path = os.environ.get('MODEL_CONFIG_PATH', '')
    os.environ['MODEL_CONFIG_PATH'] = '/tmp/non_existent_models_file.yaml'
    
    try:
        # Create a new ModelPool instance (should use defaults)
        pool = ModelPool()
        models = pool.list_models()
        
        # Should still have 6 models from defaults
        assert len(models) == 6, f"Expected 6 default models but got {len(models)}"
        print(f"✓ Default models fallback works: {len(models)} models")
        
    finally:
        # Restore original environment
        if original_path:
            os.environ['MODEL_CONFIG_PATH'] = original_path
        else:
            os.environ.pop('MODEL_CONFIG_PATH', None)


if __name__ == "__main__":
    print("Running Model Pool Configuration Tests...\n")
    
    test_model_pool_loads_all_models()
    test_all_required_models_present()
    test_model_attributes()
    test_default_models_fallback()
    
    print("\n✅ All model pool configuration tests passed!")
