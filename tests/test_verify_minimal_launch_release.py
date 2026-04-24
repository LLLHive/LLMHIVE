from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_minimal_launch_release import (
    _check_backend_health,
    _check_build_info,
    _check_launch_kpis,
    _check_root_redirect,
    _check_sign_in_page,
    _check_vercel_redirect,
)


class _FakeResponse:
    def __init__(self, status_code: int, *, text: str = "", url: str = "", headers=None, payload=None):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = headers or {"content-type": "application/json"}
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_vercel_redirect_passes_when_redirects_to_canonical(monkeypatch):
    def fake_probe(url, timeout=20):
        return _FakeResponse(308, headers={"Location": "https://www.llmhive.ai/sign-in"})

    monkeypatch.setattr("scripts.verify_minimal_launch_release._probe_redirect", fake_probe)
    result = _check_vercel_redirect("https://llmhive.vercel.app", "https://www.llmhive.ai", 20)
    assert result.passed is True


def test_sign_in_page_requires_expected_markers(monkeypatch):
    def fake_get(url, timeout=20, allow_redirects=True, headers=None):
        return _FakeResponse(
            200,
            text=(
                "Next-Generation AI Orchestration "
                "Protected by enterprise-grade security "
                "https://clerk.llmhive.ai/npm/@clerk/clerk-js "
                'data-clerk-publishable-key="pk_live_test"'
            ),
        )

    monkeypatch.setattr("scripts.verify_minimal_launch_release._get", fake_get)
    result = _check_sign_in_page("https://www.llmhive.ai", 20)
    assert result.passed is True


def test_root_redirect_checks_final_url_and_sign_in_text(monkeypatch):
    def fake_probe(url, timeout=20):
        return _FakeResponse(
            308,
            headers={"Location": "https://www.llmhive.ai/sign-in?redirect_url=https%3A%2F%2Fwww.llmhive.ai%2F"},
        )

    monkeypatch.setattr("scripts.verify_minimal_launch_release._probe_redirect", fake_probe)
    result = _check_root_redirect("https://www.llmhive.ai", 20)
    assert result.passed is True
    assert result.severity == "P1"


def test_backend_health_requires_200(monkeypatch):
    def fake_get(url, timeout=20, allow_redirects=True, headers=None):
        return _FakeResponse(200)

    monkeypatch.setattr("scripts.verify_minimal_launch_release._get", fake_get)
    result = _check_backend_health("https://backend.example", 20)
    assert result.passed is True


def test_build_info_requires_non_unknown_commit(monkeypatch):
    def fake_get(url, timeout=20, allow_redirects=True, headers=None):
        return _FakeResponse(200, payload={"commit": "abc123"}, headers={"content-type": "application/json"})

    monkeypatch.setattr("scripts.verify_minimal_launch_release._get", fake_get)
    result = _check_build_info("https://backend.example", 20)
    assert result.passed is True


def test_launch_kpis_skips_without_internal_key(monkeypatch):
    monkeypatch.delenv("INTERNAL_ADMIN_OVERRIDE_KEY", raising=False)
    result = _check_launch_kpis("https://backend.example", 20)
    assert result.passed is True
    assert result.severity == "P1"
    assert "skipped" in result.detail


def test_launch_kpis_uses_internal_key_when_present(monkeypatch):
    monkeypatch.setenv("INTERNAL_ADMIN_OVERRIDE_KEY", "secret")

    def fake_get(url, timeout=20, allow_redirects=True, headers=None):
        assert headers == {"X-LLMHive-Internal-Key": "secret"}
        return _FakeResponse(200)

    monkeypatch.setattr("scripts.verify_minimal_launch_release._get", fake_get)
    result = _check_launch_kpis("https://backend.example", 20)
    assert result.passed is True
