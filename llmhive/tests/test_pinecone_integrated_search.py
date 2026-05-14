"""Tests for Pinecone integrated search compatibility helper."""

from __future__ import annotations

from unittest.mock import MagicMock

from llmhive.app.knowledge.pinecone_integrated_search import integrated_search_to_dict


def test_integrated_search_skips_when_no_query_param() -> None:
    idx = MagicMock()

    def search(namespace: str, body: dict) -> dict:  # noqa: ARG001
        return {"result": {"hits": []}}

    idx.search = search
    assert integrated_search_to_dict(idx, namespace="ns", search_query={"top_k": 1}) is None


def test_integrated_search_calls_when_query_param_present() -> None:
    idx = MagicMock()

    def search(*, namespace: str, query: dict, rerank=None) -> dict:  # noqa: ARG001
        return {"result": {"hits": []}}

    idx.search = search
    out = integrated_search_to_dict(
        idx,
        namespace="ns",
        search_query={"top_k": 2, "inputs": {"text": "hello"}},
        rerank=None,
    )
    assert out == {"result": {"hits": []}}


def test_integrated_search_typeerror_falls_back() -> None:
    idx = MagicMock()

    def search(*, namespace: str, query: dict) -> dict:  # noqa: ARG001
        raise TypeError("got an unexpected keyword argument 'query'")

    idx.search = search
    assert integrated_search_to_dict(idx, namespace="ns", search_query={}) is None
