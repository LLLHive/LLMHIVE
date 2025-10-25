"""
Test that the application handles missing API keys gracefully.
"""
import pytest
from app.config import settings
from app.models.llm_provider import get_provider_by_name
from app.services.model_gateway import model_gateway


def test_config_allows_optional_keys():
    """Test that configuration allows API keys to be None."""
    # All API keys should be allowed to be None
    assert settings.OPENAI_API_KEY is None or isinstance(settings.OPENAI_API_KEY, str)
    assert settings.ANTHROPIC_API_KEY is None or isinstance(settings.ANTHROPIC_API_KEY, str)
    assert settings.TAVILY_API_KEY is None or isinstance(settings.TAVILY_API_KEY, str)


def test_provider_factory_raises_error_for_missing_key():
    """Test that provider factory raises ValueError when API key is missing."""
    # Assuming API keys are not set in test environment
    if settings.OPENAI_API_KEY is None:
        with pytest.raises(ValueError, match="API key for provider 'openai' is not set"):
            get_provider_by_name('openai')
    
    if settings.ANTHROPIC_API_KEY is None:
        with pytest.raises(ValueError, match="API key for provider 'anthropic' is not set"):
            get_provider_by_name('anthropic')


def test_provider_factory_raises_error_for_unknown_provider():
    """Test that provider factory raises ValueError for unknown provider."""
    with pytest.raises(ValueError, match="Provider 'unknown' is not configured"):
        get_provider_by_name('unknown')


@pytest.mark.asyncio
async def test_gateway_handles_missing_api_key_gracefully():
    """Test that model gateway returns error message when API key is missing."""
    # Assuming OpenAI API key is not set
    if settings.OPENAI_API_KEY is None:
        result = await model_gateway.call(
            model_id='gpt-4-turbo',
            messages=[{'role': 'user', 'content': 'Hello'}]
        )
        
        # Should return specific error message about missing API key
        assert "API key for provider 'openai' is not set" in result.content
        assert isinstance(result.content, str)


def test_app_version_updated():
    """Test that app version was bumped to 1.3.0 for this feature."""
    assert settings.APP_VERSION == "1.3.0"
