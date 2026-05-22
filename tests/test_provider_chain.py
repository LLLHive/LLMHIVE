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


def test_mistral_free_slug_routes_direct_first(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "ms-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from llmhive.app.providers.provider_chain import (
        build_provider_chain,
        primary_provider_name,
        P_MISTRAL,
        P_OPENROUTER,
    )

    slug = "mistralai/mistral-small-3.1-24b-instruct:free"
    chain = build_provider_chain(slug)
    assert chain[0][0] == P_MISTRAL
    assert primary_provider_name(slug) == "mistral"
    providers = [p for p, _ in chain]
    if P_OPENROUTER in providers:
        assert providers.index(P_OPENROUTER) == len(providers) - 1


def test_provider_router_mistral_direct(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "ms-test")
    from llmhive.app.providers.provider_router import reset_provider_router, get_provider_router, Provider

    reset_provider_router()
    router = get_provider_router()
    provider, native = router.get_provider_for_model(
        "mistralai/mistral-small-3.1-24b-instruct:free"
    )
    assert provider == Provider.MISTRAL
    assert native == "mistral_small"


def test_gemma_free_slug_routes_hf_when_token_set(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from llmhive.app.providers.provider_chain import (
        build_provider_chain,
        primary_provider_name,
        P_HUGGINGFACE,
    )

    # 12b not in FREE_MODELS_DB — explicit PROVIDER_ROUTING → HF first
    slug = "google/gemma-3-12b-it:free"
    chain = build_provider_chain(slug)
    assert chain[0][0] == P_HUGGINGFACE
    assert primary_provider_name(slug) == "huggingface"

    # 27b prefers Google in free_models_database; HF still on chain as spillover
    slug27 = "google/gemma-3-27b-it:free"
    chain27 = build_provider_chain(slug27)
    providers = [p for p, _ in chain27]
    assert providers[0] == "google"
    assert P_HUGGINGFACE in providers


def test_hf_provider_registered_with_token(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf-test-key")
    from llmhive.app.providers.hf_provider import HuggingFaceProvider

    p = HuggingFaceProvider()
    assert p.name == "huggingface"


def test_llama_free_slug_primary_groq_when_registered(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from llmhive.app.providers.provider_chain import primary_provider_name

    providers = {}
    from llmhive.app.providers.spillover_provider_registry import register_spillover_providers

    register_spillover_providers(providers)
    assert "groq" in providers
    assert primary_provider_name("meta-llama/llama-3.3-70b-instruct:free") == "groq"


def test_catalog_sync_adds_mistral_free_slug():
    from llmhive.app.orchestration.direct_provider_catalog_sync import merge_catalog_into_free_models_db
    from llmhive.app.orchestration.free_models_database import FREE_MODELS_DB

    merge_catalog_into_free_models_db()
    assert "mistralai/mistral-small-3.1-24b-instruct:free" in FREE_MODELS_DB or any(
        "mistral" in k for k in FREE_MODELS_DB
    )


def test_benchmark_table_loaded():
    from llmhive.app.knowledge.orchestrator_benchmark_table import (
        BENCHMARK_TABLE_AVAILABLE,
        get_orchestrator_benchmark_snapshot,
    )

    assert BENCHMARK_TABLE_AVAILABLE
    snap = get_orchestrator_benchmark_snapshot(top_k=3)
    assert snap["available"]
    assert len(snap["categories"]) >= 5
