"""ROUTING_V2 provider chain tests (no live API calls)."""

import os

import pytest


@pytest.fixture(autouse=True)
def routing_v2_on(monkeypatch):
    monkeypatch.setenv("ROUTING_V2_ENABLED", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    for key in (
        "GROQ_API_KEY",
        "TOGETHERAI_API_KEY",
        "HF_TOKEN",
        "CEREBRAS_API_KEY",
        "FIREWORKS_KEY",
        "HYPERBOLIC_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_free_slug_chain_puts_openrouter_last():
    from llmhive.app.providers.provider_chain import build_provider_chain, P_OPENROUTER

    chain = build_provider_chain("meta-llama/llama-3.3-70b-instruct:free")
    providers = [p for p, _ in chain]
    assert providers[-1] == P_OPENROUTER
    assert P_OPENROUTER not in providers[:-1] or providers.index(P_OPENROUTER) == len(providers) - 1


def test_explicit_routing_from_free_db():
    from llmhive.app.providers.provider_chain import get_explicit_routing, P_GROQ

    routing = get_explicit_routing()
    assert routing["meta-llama/llama-3.3-70b-instruct:free"] == (P_GROQ, "llama-3.3-70b-versatile")


def test_primary_provider_name_maps_groq():
    from llmhive.app.providers.provider_chain import primary_provider_name

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert primary_provider_name("meta-llama/llama-3.3-70b-instruct:free") == "groq"
    monkeypatch.undo()


def test_routing_v2_disabled_puts_openrouter_first(monkeypatch):
    from llmhive.app.providers.provider_chain import build_provider_chain, P_OPENROUTER

    monkeypatch.setenv("ROUTING_V2_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    chain = build_provider_chain("meta-llama/llama-3.3-70b-instruct:free")
    assert chain[0][0] == P_OPENROUTER


def test_non_free_slug_not_forced_to_v2_chain():
    from llmhive.app.providers.provider_chain import is_free_tier_slug

    assert not is_free_tier_slug("openai/gpt-4o-mini")


def test_provider_router_chain_for_free(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gk-test")
    from llmhive.app.providers.provider_router import reset_provider_router, get_provider_router, Provider

    reset_provider_router()
    router = get_provider_router()
    provider, native = router.get_provider_for_model("meta-llama/llama-3.3-70b-instruct:free")
    assert provider == Provider.GROQ
    assert native == "llama-3.3-70b-versatile"
