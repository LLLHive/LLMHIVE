"""Test provider connectivity and initialization with API keys."""
import builtins
import os
import pytest
from unittest.mock import MagicMock, patch

from llmhive.app.services.base import ProviderNotConfiguredError
from llmhive.app.services.openai_provider import OpenAIProvider
from llmhive.app.services.grok_provider import GrokProvider
from llmhive.app.services.anthropic_provider import AnthropicProvider
from llmhive.providers.gemini import GeminiProvider
from llmhive.app.services.deepseek_provider import DeepSeekProvider
from llmhive.app.services.manus_provider import ManusProvider


class TestOpenAIProvider:
    """Test OpenAI provider initialization and configuration."""

    def test_openai_provider_requires_api_key(self):
        """Test that OpenAI provider raises error without API key."""
        with pytest.raises(ProviderNotConfiguredError, match="API key is missing"):
            OpenAIProvider(api_key=None)

    def test_openai_provider_initializes_with_api_key(self):
        """Test that OpenAI provider initializes successfully with API key."""
        provider = OpenAIProvider(api_key="sk-test-key-123")
        assert provider.client is not None
        assert provider.client.api_key == "sk-test-key-123"

    def test_openai_provider_reports_missing_dependency(self, monkeypatch):
        """Test that OpenAI provider raises a helpful error when `openai` is missing."""

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ProviderNotConfiguredError, match="OpenAI library import failed"):
            OpenAIProvider(api_key="sk-test-key-123")


class TestGrokProvider:
    """Test Grok provider initialization and configuration."""

    def test_grok_provider_requires_api_key(self):
        """Test that Grok provider raises error without API key."""
        with pytest.raises(ProviderNotConfiguredError, match="API key is missing"):
            GrokProvider(api_key=None)

    def test_grok_provider_initializes_with_api_key(self):
        """Test that Grok provider initializes successfully with API key."""
        provider = GrokProvider(api_key="xai-test-key-123")
        assert provider.client is not None
        assert provider.client.api_key == "xai-test-key-123"
        # Verify it's using the xAI base URL
        assert "x.ai" in str(provider.client.base_url)

    def test_grok_provider_uses_correct_base_url(self):
        """Test that Grok provider uses xAI's API endpoint."""
        provider = GrokProvider(api_key="xai-test-key")
        # The base URL should point to xAI's API (OpenAI client adds trailing slash)
        assert str(provider.client.base_url).rstrip('/') == "https://api.x.ai/v1"

    def test_grok_provider_reports_missing_dependency(self, monkeypatch):
        """Test that Grok provider raises a helpful error when OpenAI client is unavailable."""

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ProviderNotConfiguredError, match="OpenAI library import failed"):
            GrokProvider(api_key="xai-test-key")


class TestAnthropicProvider:
    """Test Anthropic provider initialization and configuration."""

    def test_anthropic_provider_requires_api_key(self):
        """Test that Anthropic provider raises error without API key."""
        # Anthropic library might not be installed, so we expect either:
        # 1. ProviderNotConfiguredError for missing key
        # 2. ProviderNotConfiguredError for missing library
        with pytest.raises(ProviderNotConfiguredError):
            AnthropicProvider(api_key=None)

    def test_anthropic_provider_initializes_with_api_key(self):
        """Test that Anthropic provider initializes successfully with API key."""
        # This test requires the anthropic library to be installed
        # If it's not installed, the provider should raise ProviderNotConfiguredError
        try:
            import anthropic  # type: ignore
            # Library is installed, test initialization
            with patch('anthropic.AsyncAnthropic') as mock_client:
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                
                provider = AnthropicProvider(api_key="sk-ant-test-key-123")
                assert provider.client is not None
        except ImportError:
            # Library not installed, verify provider raises error gracefully
            with pytest.raises(ProviderNotConfiguredError, match="Anthropic library import failed"):
                AnthropicProvider(api_key="sk-ant-test-key-123")


class TestGeminiProvider:
    """Test Gemini provider initialization and configuration."""

    def test_gemini_provider_requires_api_key(self):
        """Test that Gemini provider raises error without API key."""
        with pytest.raises(ProviderNotConfiguredError):
            GeminiProvider(api_key=None)

    def test_gemini_provider_initializes_with_api_key(self):
        """Test that Gemini provider initializes successfully with API key."""
        # This test requires the google-generativeai library to be installed
        # If it's not installed, the provider should raise ProviderNotConfiguredError
        try:
            import google.generativeai  # type: ignore
            # Library is installed, test initialization
            with patch('google.generativeai.configure') as mock_configure:
                provider = GeminiProvider(api_key="gemini-test-key-123")
                assert provider.genai is not None
                mock_configure.assert_called_once_with(api_key="gemini-test-key-123")
        except ImportError:
            # Library not installed, verify provider raises error gracefully
            with pytest.raises(ProviderNotConfiguredError, match="Google Generative AI library import failed"):
                GeminiProvider(api_key="gemini-test-key-123")

    @pytest.mark.parametrize(
        "label,expected",
        [
            ("Gemini 1.5 Pro (Google)", "gemini-1.5-pro"),
            ("Gemini 1.5 Flash", "gemini-1.5-flash"),
            ("gemini pro", "gemini-1.5-pro"),
            ("gemini_pro_vision", "gemini-1.0-pro-vision"),
        ],
    )
    def test_gemini_provider_resolves_human_friendly_labels(self, label, expected):
        """Ensure UI-facing labels map to the correct Gemini model slug."""

        try:
            import google.generativeai  # type: ignore
            with patch('google.generativeai.configure'):
                provider = GeminiProvider(api_key="gemini-test-key-456")
        except ImportError:
            pytest.skip("google-generativeai is not installed")

        assert provider._resolve_model_name(label) == expected


class TestDeepSeekProvider:
    """Test DeepSeek provider initialization and configuration."""

    def test_deepseek_provider_requires_api_key(self):
        """Test that DeepSeek provider raises error without API key."""
        with pytest.raises(ProviderNotConfiguredError, match="API key is missing"):
            DeepSeekProvider(api_key=None)

    def test_deepseek_provider_initializes_with_api_key(self):
        """Test that DeepSeek provider initializes successfully with API key."""
        provider = DeepSeekProvider(api_key="deepseek-test-key-123")
        assert provider.client is not None
        assert provider.client.api_key == "deepseek-test-key-123"

    def test_deepseek_provider_uses_correct_base_url(self):
        """Test that DeepSeek provider uses DeepSeek's API endpoint."""
        provider = DeepSeekProvider(api_key="deepseek-test-key")
        # OpenAI client adds trailing slash
        assert str(provider.client.base_url).rstrip('/') == "https://api.deepseek.com/v1"


class TestManusProvider:
    """Test Manus provider initialization and configuration."""

    def test_manus_provider_requires_api_key(self):
        """Test that Manus provider raises error without API key."""
        with pytest.raises(ProviderNotConfiguredError, match="API key is missing"):
            ManusProvider(api_key=None)

    def test_manus_provider_initializes_with_api_key(self):
        """Test that Manus provider initializes successfully with API key."""
        provider = ManusProvider(api_key="manus-test-key-123")
        assert provider.client is not None
        assert provider.client.api_key == "manus-test-key-123"

    def test_manus_provider_uses_default_base_url(self):
        """Test that Manus provider uses default base URL."""
        provider = ManusProvider(api_key="manus-test-key")
        # OpenAI client adds trailing slash
        assert str(provider.client.base_url).rstrip('/') == "https://api.manus.ai/v1"

    def test_manus_provider_accepts_custom_base_url(self):
        """Test that Manus provider accepts custom base URL."""
        custom_url = "https://custom.manus.ai/v1"
        provider = ManusProvider(api_key="manus-test-key", base_url=custom_url)
        # OpenAI client adds trailing slash
        assert str(provider.client.base_url).rstrip('/') == custom_url


class TestProviderEnvironmentVariables:
    """Test that providers can read API keys from environment variables."""

    def test_openai_reads_from_env(self):
        """Test that OpenAI provider reads API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-test-key"}):
            with patch('llmhive.app.services.openai_provider.settings') as mock_settings:
                mock_settings.openai_api_key = "sk-env-test-key"
                mock_settings.openai_timeout_seconds = 45.0
                provider = OpenAIProvider()
                assert provider.client.api_key == "sk-env-test-key"

    def test_grok_reads_from_env(self):
        """Test that Grok provider reads API key from environment."""
        with patch('llmhive.app.services.grok_provider.settings') as mock_settings:
            mock_settings.grok_api_key = "xai-env-test-key"
            mock_settings.grok_timeout_seconds = 45.0
            provider = GrokProvider()
            assert provider.client.api_key == "xai-env-test-key"
