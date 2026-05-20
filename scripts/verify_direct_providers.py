#!/usr/bin/env python3
"""
Read-only provider connectivity audit (Phase 1 + 2 of ORCHESTRATION_RESILIENCE_PLAN).

Pings each direct API and aggregator with a minimal completion (or /models list
when chat is unavailable). Does not change production routing.

Usage:
  export OPENAI_API_KEY=...  # etc.
  python3 scripts/verify_direct_providers.py
  python3 scripts/verify_direct_providers.py --json
  python3 scripts/verify_direct_providers.py --skip-chat   # list-models only (faster)

See docs/PROVIDER_BILLING_STATUS.md for auto-recharge checklist (manual, per dashboard).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "llmhive", "src"))


@dataclass
class ProbeResult:
    name: str
    tier: str  # direct | aggregator | infra
    env_var: str
    key_present: bool
    status: str  # ok | throttled | auth_fail | model_error | skip | fail
    http_code: Optional[int]
    latency_ms: Optional[float]
    detail: str
    model_tested: Optional[str] = None


def _classify_http(code: int, body: str, *, list_ok: bool = False) -> str:
    """Map HTTP result to connectivity semantics (not just pass/fail)."""
    if code == 200:
        return "ok"
    if code == 429:
        return "throttled"  # key works; provider rate-limited
    if code in (401, 403):
        return "auth_fail"
    if code in (404, 422) and list_ok:
        return "ok"  # e.g. chat model slug wrong but API reachable
    if code == 400 and "incorrect api key" in body.lower():
        return "auth_fail"
    if code == 400 and "model not found" in body.lower():
        return "model_error"
    return "fail"


def _key(env: str) -> Optional[str]:
    return os.environ.get(env) or None


def _mask(key: Optional[str]) -> str:
    if not key:
        return "(missing)"
    return f"…{key[-4:]}" if len(key) >= 4 else "****"


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: float = 45.0,
) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    r = await client.post(url, headers=headers, json=payload, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000
    body = r.text[:500]
    return r.status_code, body, ms


async def _get(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    timeout: float = 30.0,
) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    r = await client.get(url, headers=headers, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000
    return r.status_code, r.text[:500], ms


# ── Direct providers ────────────────────────────────────────────────────


async def probe_openai(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "OPENAI_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("OpenAI", "direct", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "gpt-4o-mini"
    if not chat:
        code, body, ms = await _get(client, "https://api.openai.com/v1/models", headers)
        ok = code == 200
        return ProbeResult(
            "OpenAI", "direct", env, True,
            "ok" if ok else "fail", code, ms,
            "models list" if ok else body[:200], model,
        )
    code, body, ms = await _post_json(
        client,
        "https://api.openai.com/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    ok = code == 200
    return ProbeResult(
        "OpenAI", "direct", env, True,
        "ok" if ok else "fail", code, ms,
        "chat ok" if ok else body[:200], model,
    )


async def probe_anthropic(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "ANTHROPIC_API_KEY"
    key = _key(env) or _key("CLAUDE_API_KEY")
    if not key:
        return ProbeResult("Anthropic", "direct", env, False, "skip", None, None, "no key")
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    candidates = (
        "claude-3-5-haiku-latest",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-latest",
    )
    if not chat:
        return ProbeResult("Anthropic", "direct", env, True, "skip", None, None, "chat-only probe", candidates[0])
    last_code, last_body, last_ms, last_model = 404, "", 0.0, candidates[0]
    for model in candidates:
        code, body, ms = await _post_json(
            client,
            "https://api.anthropic.com/v1/messages",
            headers,
            {
                "model": model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
        if code == 200:
            return ProbeResult(
                "Anthropic", "direct", env, True, "ok", code, ms,
                f"messages ok ({model})", model,
            )
        last_code, last_body, last_ms, last_model = code, body, ms, model
    st = _classify_http(last_code, last_body)
    if last_code == 404:
        st = "model_error"
    return ProbeResult(
        "Anthropic", "direct", env, True, st, last_code, last_ms,
        last_body[:200], last_model,
    )


async def probe_google(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "GOOGLE_AI_API_KEY"
    key = _key(env) or _key("GEMINI_API_KEY")
    if not key:
        return ProbeResult("Google AI Studio", "direct", env, False, "skip", None, None, "no key")
    model = "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={key}"
    )
    if not chat:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        code, body, ms = await _get(client, list_url, {})
        ok = code == 200
        return ProbeResult(
            "Google AI Studio", "direct", env, True,
            "ok" if ok else "fail", code, ms,
            "models list" if ok else body[:200], model,
        )
    code, body, ms = await _post_json(
        client,
        url,
        {"Content-Type": "application/json"},
        {"contents": [{"parts": [{"text": "ping"}]}], "generationConfig": {"maxOutputTokens": 1}},
    )
    ok = code == 200
    return ProbeResult(
        "Google AI Studio", "direct", env, True,
        "ok" if ok else "fail", code, ms,
        "generateContent ok" if ok else body[:200], model,
    )


async def probe_grok(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "GROK_API_KEY"
    key = _key(env) or _key("XAI_API_KEY")
    if not key:
        return ProbeResult("xAI Grok", "direct", env, False, "skip", None, None, "no key")
    # Groq keys are often mis-set as GROK_API_KEY (gsk_ prefix)
    if key.startswith("gsk_"):
        return ProbeResult(
            "xAI Grok", "direct", env, True, "auth_fail", None, None,
            "GROK_API_KEY looks like a Groq key (gsk_…); use XAI key from console.x.ai",
            None,
        )
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "grok-3-mini"
    if not chat:
        code, body, ms = await _get(client, "https://api.x.ai/v1/models", headers)
        st = _classify_http(code, body)
        return ProbeResult(
            "xAI Grok", "direct", env, True, st, code, ms,
            "models list" if st == "ok" else body[:200], model,
        )
    code, body, ms = await _post_json(
        client,
        "https://api.x.ai/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    st = _classify_http(code, body)
    return ProbeResult(
        "xAI Grok", "direct", env, True, st, code, ms,
        f"chat ({model})" if st == "ok" else body[:200], model,
    )


async def probe_deepseek(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "DEEPSEEK_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("DeepSeek", "direct", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "deepseek-chat"
    if not chat:
        return ProbeResult("DeepSeek", "direct", env, True, "skip", None, None, "chat-only probe", model)
    code, body, ms = await _post_json(
        client,
        "https://api.deepseek.com/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    ok = code == 200
    return ProbeResult(
        "DeepSeek", "direct", env, True,
        "ok" if ok else "fail", code, ms,
        "chat ok" if ok else body[:200], model,
    )


async def probe_mistral(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "MISTRAL_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("Mistral", "direct", env, False, "skip", None, None, "not wired in repo yet")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "mistral-small-latest"
    code, body, ms = await _post_json(
        client,
        "https://api.mistral.ai/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    ) if chat else (0, "", 0.0)
    if not chat:
        code, body, ms = await _get(client, "https://api.mistral.ai/v1/models", headers)
    ok = code == 200
    return ProbeResult(
        "Mistral", "direct", env, True,
        "ok" if ok else "fail", code, ms,
        "ok" if ok else body[:200], model,
    )


# ── Aggregators ─────────────────────────────────────────────────────────


async def probe_openrouter(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "OPENROUTER_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("OpenRouter", "aggregator", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}"}
    code, body, ms = await _get(client, "https://openrouter.ai/api/v1/models", headers)
    if code != 200:
        return ProbeResult(
            "OpenRouter", "aggregator", env, True, "fail", code, ms, body[:200], None,
        )
    if not chat:
        return ProbeResult(
            "OpenRouter", "aggregator", env, True, "ok", code, ms, "models list (auth OK)", None,
        )
    paid_model = "openai/gpt-4o-mini"
    code2, body2, ms2 = await _post_json(
        client,
        "https://openrouter.ai/api/v1/chat/completions",
        {**headers, "Content-Type": "application/json", "HTTP-Referer": "https://llmhive.ai"},
        {"model": paid_model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    st = _classify_http(code2, body2, list_ok=True)
    detail = f"paid chat ({paid_model})" if st == "ok" else body2[:120]
    if st == "ok":
        free_model = "meta-llama/llama-3.3-70b-instruct:free"
        code3, body3, _ = await _post_json(
            client,
            "https://openrouter.ai/api/v1/chat/completions",
            {**headers, "Content-Type": "application/json", "HTTP-Referer": "https://llmhive.ai"},
            {"model": free_model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
        )
        if code3 == 429:
            detail += "; :free upstream throttled (expected)"
        elif code3 == 200:
            detail += "; :free ok"
    return ProbeResult(
        "OpenRouter", "aggregator", env, True, st, code2, ms2, detail, paid_model,
    )


async def probe_together(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "TOGETHERAI_API_KEY"
    key = _key(env) or _key("TOGETHER_API_KEY")
    if not key:
        return ProbeResult("Together AI", "aggregator", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}"}
    serverless_candidates = (
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "Qwen/Qwen3-Next-80B-A3B-Instruct",
    )
    if not chat:
        code, body, ms = await _get(client, "https://api.together.ai/v1/models", headers)
        ok = code == 200
        return ProbeResult(
            "Together AI", "aggregator", env, True,
            "ok" if ok else "fail", code, ms,
            "models list" if ok else body[:200], serverless_candidates[0],
        )
    last_code, last_body, last_ms, last_model = 400, "", 0.0, serverless_candidates[0]
    for model in serverless_candidates:
        code, body, ms = await _post_json(
            client,
            "https://api.together.ai/v1/chat/completions",
            {**headers, "Content-Type": "application/json"},
            {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
        )
        if code == 200:
            return ProbeResult(
                "Together AI", "aggregator", env, True, "ok", code, ms,
                f"serverless chat ({model})", model,
            )
        last_code, last_body, last_ms, last_model = code, body, ms, model
    st = _classify_http(last_code, last_body)
    if "non-serverless" in last_body.lower() or "unable to access" in last_body.lower():
        st = "model_error"
    return ProbeResult(
        "Together AI", "aggregator", env, True, st, last_code, last_ms,
        last_body[:200], last_model,
    )


async def probe_hyperbolic(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "HYPERBOLIC_API_KEY"
    key = _key(env) or _key("HYPERBOLIC_KEY")
    if not key:
        return ProbeResult("Hyperbolic", "aggregator", env, False, "skip", None, None, "no key")
    model = "meta-llama/Llama-3.3-70B-Instruct"
    raw = os.environ.get("HYPERBOLIC_MODELS", "").strip()
    if raw:
        try:
            cat = json.loads(raw)
            dk = cat.get("default_chat") or "llama_33_70b"
            model = (cat.get("chat") or {}).get(dk, model)
        except json.JSONDecodeError:
            pass
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    code, body, ms = await _post_json(
        client,
        "https://api.hyperbolic.xyz/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        timeout=120.0,
    )
    if code == 402:
        return ProbeResult(
            "Hyperbolic", "aggregator", env if _key(env) else "HYPERBOLIC_KEY", True,
            "model_error", code, ms, "key valid; add credits", model,
        )
    ok = code == 200
    return ProbeResult(
        "Hyperbolic", "aggregator", env if _key(env) else "HYPERBOLIC_KEY", True,
        "ok" if ok else _classify_http(code, body), code, ms,
        "chat ok" if ok else body[:200], model,
    )


async def probe_fireworks(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "FIREWORKS_API_KEY"
    key = _key(env) or _key("FIREWORKS_KEY")
    if not key:
        return ProbeResult("Fireworks", "aggregator", env, False, "skip", None, None, "no key")
    model = "accounts/fireworks/models/deepseek-v4-flash"
    raw = os.environ.get("FIREWORKS_MODELS", "").strip()
    if raw:
        try:
            cat = json.loads(raw)
            dk = cat.get("default_chat") or "deepseek_v4_flash"
            model = (cat.get("chat") or {}).get(dk, model)
        except json.JSONDecodeError:
            pass
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    code, body, ms = await _post_json(
        client,
        "https://api.fireworks.ai/inference/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        timeout=90.0,
    )
    ok = code == 200
    return ProbeResult(
        "Fireworks", "aggregator", env if _key(env) else "FIREWORKS_KEY", True,
        "ok" if ok else _classify_http(code, body), code, ms,
        "chat ok" if ok else body[:200], model,
    )


async def probe_groq(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "GROQ_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("Groq", "aggregator", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "llama-3.1-8b-instant"
    code, body, ms = await _post_json(
        client,
        "https://api.groq.com/openai/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    ok = code == 200
    return ProbeResult(
        "Groq", "aggregator", env, True,
        "ok" if ok else "fail", code, ms,
        "chat ok" if ok else body[:200], model,
    )


async def probe_cerebras(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "CEREBRAS_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("Cerebras", "aggregator", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "llama3.1-8b"
    code, body, ms = await _post_json(
        client,
        "https://api.cerebras.ai/v1/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    ok = code == 200
    return ProbeResult(
        "Cerebras", "aggregator", env, True,
        "ok" if ok else "fail", code, ms,
        "chat ok" if ok else body[:200], model,
    )


async def probe_deepinfra(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "DeepInfra_Api_Key"
    key = _key(env) or _key("DEEPINFRA_API_KEY")
    if not key:
        return ProbeResult("DeepInfra", "direct", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    if not chat:
        t0 = time.perf_counter()
        r = await client.get(
            "https://api.deepinfra.com/v1/models",
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )
        ms = (time.perf_counter() - t0) * 1000
        code, body = r.status_code, r.text[:500]
        st = "ok" if code == 200 else _classify_http(code, body)
        return ProbeResult(
            "DeepInfra", "direct", env, True, st, code, ms,
            "models list" if st == "ok" else body[:200], model,
        )
    code, body, ms = await _post_json(
        client,
        "https://api.deepinfra.com/v1/openai/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    if code == 402:
        return ProbeResult(
            "DeepInfra", "direct", env, True, "model_error", code, ms,
            f"billing/limit response: {body[:160]}", model,
        )
    if code == 404 and "model" in body.lower():
        return ProbeResult(
            "DeepInfra", "direct", env, True, "model_error", code, ms,
            f"model slug not on DeepInfra: {body[:160]}", model,
        )
    st = _classify_http(code, body)
    return ProbeResult(
        "DeepInfra", "direct", env, True, st, code, ms,
        "chat ok" if st == "ok" else body[:200], model,
    )


async def probe_dashscope(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "DASHSCOPE_API_KEY"
    key = _key(env)
    if not key:
        return ProbeResult("DashScope (Qwen)", "direct", env, False, "skip", None, None, "no key")
    base = (_key("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
    if base.startswith("{"):
        try:
            base = json.loads(base).get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        except json.JSONDecodeError:
            base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    base = base.rstrip("/")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "qwen-plus"
    if not chat:
        code, body, ms = await _post_json(
            client,
            f"{base}/chat/completions",
            headers,
            {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
        )
        st = _classify_http(code, body)
        return ProbeResult(
            "DashScope (Qwen)", "direct", env, True, st, code, ms,
            "chat probe" if st == "ok" else body[:200], model,
        )
    code, body, ms = await _post_json(
        client,
        f"{base}/chat/completions",
        headers,
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    st = _classify_http(code, body)
    return ProbeResult(
        "DashScope (Qwen)", "direct", env, True,
        "ok" if st == "ok" else st, code, ms,
        "chat ok" if st == "ok" else body[:200], model,
    )


async def probe_azure_foundry(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "AZURE_FOUNDRY_API_KEY"
    key = _key(env)
    endpoint = (_key("AZURE_FOUNDRY_ENDPOINT") or "https://llnhive.services.ai.azure.com").rstrip("/")
    if not key:
        return ProbeResult("Azure Foundry", "direct", env, False, "skip", None, None, "no key")
    deployment = "DeepSeek-V4-Flash"
    dep_raw = _key("AZURE_FOUNDRY_DEPLOYMENTS")
    if dep_raw:
        try:
            dep_map = json.loads(dep_raw)
            if isinstance(dep_map, dict):
                deployment = dep_map.get("deepseek_flash", deployment)
        except json.JSONDecodeError:
            pass
    if not chat:
        return ProbeResult(
            "Azure Foundry", "direct", env, True, "skip", None, None,
            f"endpoint set; deployment={deployment}", deployment,
        )
    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        "?api-version=2024-06-01"
    )
    code, body, ms = await _post_json(
        client,
        url,
        {"api-key": key, "Content-Type": "application/json"},
        {"messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
    )
    st = _classify_http(code, body)
    return ProbeResult(
        "Azure Foundry", "direct", env, True,
        "ok" if st == "ok" else st, code, ms,
        f"chat ({deployment})" if st == "ok" else body[:200], deployment,
    )


async def probe_kimi(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "Kimi_K26_Api_Key"
    key = _key(env) or _key("MOONSHOT_API_KEY") or _key("KIMI_API_KEY")
    if not key:
        return ProbeResult("Kimi (Moonshot)", "direct", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    model = "kimi-k2.6"
    code, body, ms = await _get(client, "https://api.moonshot.ai/v1/models", headers)
    if code != 200:
        st = _classify_http(code, body)
        return ProbeResult(
            "Kimi (Moonshot)", "direct", env, True, st, code, ms, body[:200], model,
        )
    if not chat:
        return ProbeResult(
            "Kimi (Moonshot)", "direct", env, True, "ok", code, ms, "models list (auth OK)", model,
        )
    for try_model in (model, "moonshot-v1-8k", "kimi-k2-turbo-preview"):
        code2, body2, ms2 = await _post_json(
            client,
            "https://api.moonshot.ai/v1/chat/completions",
            headers,
            {
                "model": try_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            },
        )
        if code2 == 200:
            return ProbeResult(
                "Kimi (Moonshot)", "direct", env, True, "ok", code2, ms2,
                f"chat ok ({try_model})", try_model,
            )
        if "suspended" in body2.lower():
            return ProbeResult(
                "Kimi (Moonshot)", "direct", env, True, "auth_fail", code2, ms2,
                "Moonshot account suspended — reactivate in console", try_model,
            )
    st = _classify_http(code2, body2)
    return ProbeResult(
        "Kimi (Moonshot)", "direct", env, True, st, code2, ms2, body2[:200], model,
    )


async def probe_gemini_secondary(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "GEMINI_API_KEY_2"
    key = _key(env)
    if not key:
        return ProbeResult("Google (key 2)", "direct", env, False, "skip", None, None, "no key")
    model = "gemini-2.5-flash"
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    code, body, ms = await _get(client, list_url, {})
    if code != 200:
        return ProbeResult(
            "Google (key 2)", "direct", env, True, "fail", code, ms, body[:200], model,
        )
    if not chat:
        return ProbeResult(
            "Google (key 2)", "direct", env, True, "ok", code, ms, "models list (auth OK)", model,
        )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={key}"
    )
    code2, body2, ms2 = await _post_json(
        client,
        url,
        {"Content-Type": "application/json"},
        {"contents": [{"parts": [{"text": "ping"}]}], "generationConfig": {"maxOutputTokens": 1}},
    )
    st = _classify_http(code2, body2)
    if code2 == 429:
        st = "throttled"
    return ProbeResult(
        "Google (key 2)", "direct", env, True, st, code2, ms2,
        f"generateContent ({model})" if st == "ok" else body2[:200], model,
    )


async def probe_cloudflare(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "Cloudflare_Api_Key"
    key = _key(env) or _key("CLOUDFLARE_API_KEY")
    if not key:
        return ProbeResult("Cloudflare Workers AI", "direct", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    code, body, ms = await _get(
        client, "https://api.cloudflare.com/client/v4/user/tokens/verify", headers
    )
    if code != 200:
        st = _classify_http(code, body)
        return ProbeResult(
            "Cloudflare Workers AI", "direct", env, True, st, code, ms, body[:200], None,
        )
    account_id = (
        _key("Cloudflare_Account_ID")
        or _key("CLOUDFLARE_ACCOUNT_ID")
        or _key("Cloudflare_Account_Id")
    )
    if not chat or not account_id:
        detail = "token verify ok"
        if not account_id:
            detail += "; set CLOUDFLARE_ACCOUNT_ID to test chat"
        return ProbeResult(
            "Cloudflare Workers AI", "direct", env, True, "ok", code, ms, detail, None,
        )
    chat_url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
    )
    model = "@cf/meta/llama-3.1-8b-instruct"
    code2, body2, ms2 = await _post_json(
        client,
        chat_url,
        headers,
        {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        },
    )
    st = _classify_http(code2, body2)
    return ProbeResult(
        "Cloudflare Workers AI", "direct", env, True,
        "ok" if st == "ok" else st, code2, ms2,
        f"token + chat ({model})" if st == "ok" else f"token ok; chat: {body2[:120]}",
        model,
    )


async def probe_huggingface(client: httpx.AsyncClient, chat: bool) -> ProbeResult:
    env = "HF_TOKEN"
    key = _key(env) or _key("HUGGINGFACE_TOKEN")
    if not key:
        return ProbeResult("HuggingFace", "aggregator", env, False, "skip", None, None, "no key")
    headers = {"Authorization": f"Bearer {key}"}
    code, body, ms = await _get(
        client,
        "https://huggingface.co/api/whoami-v2",
        headers,
    )
    ok = code == 200
    return ProbeResult(
        "HuggingFace", "aggregator", env, True,
        "ok" if ok else "fail", code, ms,
        "whoami ok" if ok else body[:200], None,
    )


async def probe_llmhive_orchestrator(client: httpx.AsyncClient) -> ProbeResult:
    """Production orchestrator health (not a model provider)."""
    base = os.environ.get(
        "LLMHIVE_ORCHESTRATOR_URL",
        "https://llmhive-orchestrator-792354158895.us-east1.run.app",
    ).rstrip("/")
    code, body, ms = await _get(client, f"{base}/health", {})
    ok = code == 200
    return ProbeResult(
        "LLMHive Orchestrator", "infra", "LLMHIVE_ORCHESTRATOR_URL", True,
        "ok" if ok else "fail", code, ms,
        body[:120] if ok else body[:200], None,
    )


PROBES: List[Callable] = [
    probe_openai,
    probe_anthropic,
    probe_google,
    probe_gemini_secondary,
    probe_grok,
    probe_deepseek,
    probe_deepinfra,
    probe_dashscope,
    probe_azure_foundry,
    probe_kimi,
    probe_cloudflare,
    probe_mistral,
    probe_openrouter,
    probe_together,
    probe_fireworks,
    probe_hyperbolic,
    probe_groq,
    probe_cerebras,
    probe_huggingface,
]


def _print_table(results: List[ProbeResult]) -> None:
    print("\n" + "=" * 88)
    print(f"{'Provider':<22} {'Tier':<11} {'Key':<8} {'Status':<6} {'HTTP':<5} {'ms':>7}  Detail")
    print("-" * 88)
    for r in results:
        http = str(r.http_code) if r.http_code is not None else "-"
        ms = f"{r.latency_ms:.0f}" if r.latency_ms is not None else "-"
        key = "yes" if r.key_present else "NO"
        print(f"{r.name:<22} {r.tier:<11} {key:<8} {r.status:<6} {http:<5} {ms:>7}  {r.detail[:40]}")
    print("=" * 88)

    ok = sum(1 for r in results if r.status == "ok")
    throttled = sum(1 for r in results if r.status == "throttled")
    auth_fail = sum(1 for r in results if r.status == "auth_fail")
    model_err = sum(1 for r in results if r.status == "model_error")
    fail = sum(1 for r in results if r.status == "fail")
    skip = sum(1 for r in results if r.status == "skip")
    print(
        f"\nSummary: {ok} ok, {throttled} throttled (connection OK), "
        f"{auth_fail} auth_fail, {model_err} model/tier, {fail} fail, {skip} skip"
    )
    if throttled:
        print("Throttled = API key works; provider is rate-limiting (expected under load).")
    if auth_fail:
        print("Auth failures = wrong/expired key or wrong key in wrong env var (e.g. Groq key in GROK_API_KEY).")
    if model_err:
        print("Model/tier errors = API reachable; fix model slug or billing tier for that model.")
    if fail:
        print("Action: fix hard failures, then re-run.")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Verify LLM provider connections (read-only).")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of table")
    parser.add_argument("--skip-chat", action="store_true", help="Use list-models / whoami only")
    args = parser.parse_args()

    results: List[ProbeResult] = []
    async with httpx.AsyncClient() as client:
        for probe in PROBES:
            try:
                results.append(await probe(client, chat=not args.skip_chat))
            except Exception as e:
                name = probe.__name__.replace("probe_", "").replace("_", " ").title()
                results.append(
                    ProbeResult(name, "?", "?", False, "fail", None, None, str(e)[:200]),
                )
        try:
            results.append(await probe_llmhive_orchestrator(client))
        except Exception as e:
            results.append(
                ProbeResult("LLMHive Orchestrator", "infra", "?", True, "fail", None, None, str(e)[:200]),
            )

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        _print_table(results)

    failed = [r for r in results if r.status in ("fail", "auth_fail")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
