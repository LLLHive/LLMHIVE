"""Scheduled HTTP benchmark path: bypass paid gate without consuming subscriber caps."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from llmhive.app.billing.scheduled_benchmark import SCHEDULED_BENCHMARK_HEADER_NAME
from llmhive.app.main import app
from llmhive.app.models.orchestration import (
    AgentMode,
    ChatMetadata,
    ChatResponse,
    DomainPack,
    ReasoningMode,
    TuningOptions,
)

client = TestClient(app)
_PATCH = "llmhive.app.routers.chat.run_orchestration"
_KEY = "llmhive-pytest-sched-bench-key"


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", _KEY)


def _headers(**extra: str) -> dict[str, str]:
    h = {"X-API-Key": _KEY}
    h.update(extra)
    return h


def _minimal_payload() -> dict:
    return {
        "prompt": "ping",
        "reasoning_mode": "standard",
        "domain_pack": "default",
        "agent_mode": "single",
        "tuning": {
            "prompt_optimization": False,
            "output_validation": False,
            "answer_structure": False,
            "learn_from_chat": False,
        },
        "orchestration": {"accuracy_level": 1},
        "metadata": {},
        "history": [],
    }


def test_paid_required_blocks_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "1")
    monkeypatch.delenv("LLMHIVE_SCHEDULED_BENCHMARK_SECRET", raising=False)
    response = client.post("/v1/chat", json=_minimal_payload(), headers=_headers())
    assert response.status_code == 402


def test_benchmark_secret_bypasses_paid_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "1")
    secret = "unit-test-scheduled-benchmark-secret-value-32bytes!"
    monkeypatch.setenv("LLMHIVE_SCHEDULED_BENCHMARK_SECRET", secret)
    mock_resp = ChatResponse(
        message="ok",
        models_used=["gpt-4o-mini"],
        reasoning_mode=ReasoningMode.standard,
        reasoning_method=None,
        domain_pack=DomainPack.default,
        agent_mode=AgentMode.single,
        used_tuning=TuningOptions(
            prompt_optimization=False,
            output_validation=False,
            answer_structure=False,
            learn_from_chat=False,
        ),
        metadata=ChatMetadata(chat_id="t"),
        tokens_used=1,
        latency_ms=1,
        agent_traces=[],
        extra={},
    )
    with patch(_PATCH, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_resp
        response = client.post(
            "/v1/chat",
            json=_minimal_payload(),
            headers=_headers(**{SCHEDULED_BENCHMARK_HEADER_NAME: secret}),
        )
    assert response.status_code == 200, response.text
    mock_run.assert_awaited_once()


def test_wrong_benchmark_secret_still_requires_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "1")
    monkeypatch.setenv("LLMHIVE_SCHEDULED_BENCHMARK_SECRET", "server-side-secret-aaaaaaaaaaaa")
    response = client.post(
        "/v1/chat",
        json=_minimal_payload(),
        headers=_headers(**{SCHEDULED_BENCHMARK_HEADER_NAME: "wrong-secret-aaaaaaaaaaaaaaaa"}),
    )
    assert response.status_code == 402
