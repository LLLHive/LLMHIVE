"""
Test that the application handles missing API keys gracefully with stub fallback.
"""
import pytest
from app.config import settings
from app.models.llm_provider import get_provider_by_name, StubProvider
from app.services.model_gateway import model_gateway


def test_config_allows_optional_keys():
    """Test that configuration allows API keys to be None."""
    # All API keys should be allowed to be None
    assert settings.OPENAI_API_KEY is None or isinstance(settings.OPENAI_API_KEY, str)
    assert settings.ANTHROPIC_API_KEY is None or isinstance(settings.ANTHROPIC_API_KEY, str)
    assert settings.TAVILY_API_KEY is None or isinstance(settings.TAVILY_API_KEY, str)


def test_provider_factory_falls_back_to_stub_for_missing_key():
    """Test that provider factory falls back to stub when API key is missing."""
    # When API keys are not set, should return stub provider
    if settings.OPENAI_API_KEY is None:
        provider = get_provider_by_name('openai')
        assert isinstance(provider, StubProvider), "Should fallback to StubProvider when API key missing"
    
    if settings.ANTHROPIC_API_KEY is None:
        provider = get_provider_by_name('anthropic')
        assert isinstance(provider, StubProvider), "Should fallback to StubProvider when API key missing"


def test_provider_factory_returns_stub_for_unknown_provider():
    """Test that provider factory returns stub for unknown provider."""
    provider = get_provider_by_name('unknown')
    assert isinstance(provider, StubProvider), "Should return StubProvider for unknown provider"


@pytest.mark.asyncio
async def test_gateway_handles_missing_api_key_with_stub():
    """Test that model gateway returns stub response when API key is missing."""
    # When OpenAI API key is not set, should use stub provider
    if settings.OPENAI_API_KEY is None:
        result = await model_gateway.call(
            model_id='gpt-4-turbo',
            messages=[{'role': 'user', 'content': 'Hello'}]
        )
        
        # Should return a non-empty string response from stub provider
        assert isinstance(result.content, str)
        assert len(result.content) > 0, "Should return non-empty response"
        # Verify it's a stub response by checking it doesn't require real API
        assert not result.content.startswith("Error:"), "Stub should not return error messages"


def test_app_version_updated():
    """Test that app version was bumped to 1.3.0 for this feature."""
    assert settings.APP_VERSION == "1.3.0"
