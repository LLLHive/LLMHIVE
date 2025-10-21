"""Configuration parsing tests."""

from llmhive.app import config


def reload_settings(monkeypatch, **env):
    for key in [
        "OPENAI_API_KEY",
        "OPENAI_KEY",
        "GROK_API_KEY",
        "GROCK_API_KEY",
        "XAI_API_KEY",
        "DEFAULT_MODELS",
        "MODEL_ALIASES",
    ]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    config.reset_settings_cache()
    config.settings = config.get_settings()


def test_alias_parsing_for_provider_keys(monkeypatch):
    reload_settings(
        monkeypatch,
        OPENAI_KEY="sk-test-123",
        GROCK_API_KEY="xai-key-456",
    )

    settings = config.get_settings()
    assert settings.openai_api_key == "sk-test-123"
    assert settings.grok_api_key == "xai-key-456"


def test_default_models_and_alias_string_parsing(monkeypatch):
    reload_settings(
        monkeypatch,
        DEFAULT_MODELS="Grock, GPT-4 , stub-debug",
        MODEL_ALIASES="grock=grok-beta,gpt-4=gpt-4o-mini",
    )

    settings = config.get_settings()
    assert settings.default_models == ["Grock", "GPT-4", "stub-debug"]
    assert settings.model_aliases["grock"] == "grok-beta"
    assert settings.model_aliases["gpt-4"] == "gpt-4o-mini"
