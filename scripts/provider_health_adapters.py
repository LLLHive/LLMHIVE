"""
LLMHive — Provider Health Adapters
====================================
Non-inference health validation for all LLM providers.

Each adapter validates system viability through:
    1. connectivity_check()  — Can we reach the endpoint?
    2. auth_check()          — Is the API key accepted?
    3. list_models()         — What models are available?
    4. model_exists()        — Is our target model present?

No inference calls.  No "Return 4." prompts.  No MAX_TOKENS noise.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_TIMEOUT = 15


@dataclass
class HealthResult:
    provider: str = ""
    connectivity: bool = False
    auth: bool = False
    models_listed: bool = False
    target_model_exists: bool = False
    latency_ms: int = 0
    models_found: int = 0
    selected_model: str = ""
    error: Optional[str] = None

    @property
    def status(self) -> str:
        if self.connectivity and self.auth and self.models_listed and self.target_model_exists:
            return "PASS"
        return "FAIL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "connectivity": self.connectivity,
            "auth": self.auth,
            "models_listed": self.models_listed,
            "target_model_exists": self.target_model_exists,
            "latency_ms": self.latency_ms,
            "models_found": self.models_found,
            "selected_model": self.selected_model,
            "error": self.error,
        }


# ===================================================================
# Base adapter
# ===================================================================

class ProviderHealthAdapter:
    name: str = "base"
    env_var: str = ""
    fallback_env: str = ""

    def _get_key(self) -> str:
        key = os.getenv(self.env_var, "")
        if not key and self.fallback_env:
            key = os.getenv(self.fallback_env, "")
        return key

    def check(self) -> HealthResult:
        r = HealthResult(provider=self.name)
        key = self._get_key()
        if not key:
            r.error = f"{self.env_var} not set"
            return r
        if not _HAS_HTTPX:
            r.error = "httpx not installed"
            return r

        t0 = time.time()
        try:
            self._run_checks(r, key)
        except Exception as exc:
            r.error = str(exc)
        r.latency_ms = int((time.time() - t0) * 1000)
        return r

    def _run_checks(self, r: HealthResult, key: str) -> None:
        raise NotImplementedError


# ===================================================================
# OpenAI-compatible adapter (shared by OpenAI, Groq, Together,
# Cerebras, DeepSeek)
# ===================================================================

class OpenAICompatibleAdapter(ProviderHealthAdapter):
    base_url: str = ""
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    extra_headers: Dict[str, str] = {}
    target_model_prefix: str = ""

    def _run_checks(self, r: HealthResult, key: str) -> None:
        headers = {
            self.auth_header: f"{self.auth_prefix}{key}",
        }
        headers.update(self.extra_headers)

        # 1. Connectivity + auth via /models
        resp = httpx.get(
            f"{self.base_url}/models",
            headers=headers, timeout=_TIMEOUT,
        )

        r.connectivity = True

        if resp.status_code == 401:
            r.error = "401 Unauthorized"
            return
        if resp.status_code not in (200, 201):
            r.error = f"Models endpoint HTTP {resp.status_code}"
            return

        r.auth = True

        # 3. List models
        data = resp.json()
        models_raw = data.get("data", data.get("models", []))
        if isinstance(models_raw, list):
            model_ids = [
                m.get("id", "") for m in models_raw if isinstance(m, dict)
            ]
        else:
            model_ids = []

        r.models_found = len(model_ids)
        r.models_listed = len(model_ids) > 0

        # 4. Target model exists
        if self.target_model_prefix:
            matches = [
                m for m in model_ids
                if m.startswith(self.target_model_prefix)
                or self.target_model_prefix in m
            ]
            if matches:
                r.target_model_exists = True
                r.selected_model = matches[0]
            else:
                r.error = f"No model matching '{self.target_model_prefix}'"
        elif model_ids:
            r.target_model_exists = True
            r.selected_model = model_ids[0]


# ===================================================================
# Concrete adapters
# ===================================================================

class OpenAIAdapter(OpenAICompatibleAdapter):
    name = "openai"
    env_var = "OPENAI_API_KEY"
    base_url = "https://api.openai.com/v1"
    target_model_prefix = "gpt-"


class GroqAdapter(OpenAICompatibleAdapter):
    name = "groq"
    env_var = "GROQ_API_KEY"
    base_url = "https://api.groq.com/openai/v1"
    target_model_prefix = "llama"


class TogetherAdapter(OpenAICompatibleAdapter):
    name = "together"
    env_var = "TOGETHERAI_API_KEY"
    fallback_env = "TOGETHER_API_KEY"
    base_url = "https://api.together.xyz/v1"
    target_model_prefix = "meta-llama"


class CerebrasAdapter(OpenAICompatibleAdapter):
    name = "cerebras"
    env_var = "CEREBRAS_API_KEY"
    base_url = "https://api.cerebras.ai/v1"
    target_model_prefix = "llama"


class DeepSeekAdapter(OpenAICompatibleAdapter):
    name = "deepseek"
    env_var = "DEEPSEEK_API_KEY"
    base_url = "https://api.deepseek.com/v1"
    target_model_prefix = "deepseek"


class GrokAdapter(ProviderHealthAdapter):
    """xAI Grok — no /v1/models endpoint; dynamic model fallback via completions."""
    name = "grok"
    env_var = "XAI_API_KEY"
    fallback_env = "GROK_API_KEY"

    _FALLBACK_MODELS = ["grok-3-mini", "grok-3", "grok-2", "grok-beta"]

    def _run_checks(self, r: HealthResult, key: str) -> None:
        env_model = os.getenv("GROK_MODEL", "")
        candidates = ([env_model] if env_model else []) + [
            m for m in self._FALLBACK_MODELS if m != env_model
        ]

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        last_status = 0
        for model in candidates:
            resp = httpx.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "temperature": 0,
                },
                timeout=_TIMEOUT,
            )

            r.connectivity = True
            last_status = resp.status_code

            if resp.status_code == 401:
                r.error = "401 Unauthorized"
                return

            if resp.status_code not in (200, 201):
                continue  # try next candidate

            r.auth = True

            data = resp.json()
            if "choices" not in data:
                continue  # structural mismatch, try next

            r.models_listed = True
            r.models_found = 1
            r.target_model_exists = True
            r.selected_model = model
            return

        r.error = f"All candidates failed (last HTTP {last_status})"


# ===================================================================
# Google Gemini — model listing only, no inference
# ===================================================================

class GoogleAdapter(ProviderHealthAdapter):
    name = "google"
    env_var = "GOOGLE_AI_API_KEY"

    def _run_checks(self, r: HealthResult, key: str) -> None:
        resp = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            timeout=_TIMEOUT,
        )

        r.connectivity = True

        if resp.status_code == 401:
            r.error = "401 Unauthorized"
            return
        if resp.status_code == 400:
            r.error = f"400 Bad Request (key format?)"
            return
        if resp.status_code != 200:
            r.error = f"Models endpoint HTTP {resp.status_code}"
            return

        r.auth = True

        models_raw = resp.json().get("models", [])
        prod = [
            m for m in models_raw
            if "generateContent" in m.get("supportedGenerationMethods", [])
            and "exp" not in m.get("name", "").lower()
            and "preview" not in m.get("name", "").lower()
        ]

        r.models_found = len(prod)
        r.models_listed = len(prod) > 0

        if prod:
            r.target_model_exists = True
            r.selected_model = prod[0].get("name", "").replace("models/", "")
        else:
            r.error = "No production Gemini models found"


# ===================================================================
# Anthropic — /v1/models listing
# ===================================================================

class AnthropicAdapter(ProviderHealthAdapter):
    name = "anthropic"
    env_var = "ANTHROPIC_API_KEY"

    def _run_checks(self, r: HealthResult, key: str) -> None:
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }

        resp = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers=headers, timeout=_TIMEOUT,
        )

        r.connectivity = True

        if resp.status_code == 401:
            r.error = "401 Unauthorized"
            return
        if resp.status_code not in (200, 201):
            r.error = f"Models endpoint HTTP {resp.status_code}"
            return

        r.auth = True

        data = resp.json()
        models_raw = data.get("data", [])
        model_ids = [m.get("id", "") for m in models_raw if isinstance(m, dict)]

        r.models_found = len(model_ids)
        r.models_listed = len(model_ids) > 0

        claude = [m for m in model_ids if "claude" in m.lower()]
        if claude:
            r.target_model_exists = True
            r.selected_model = claude[0]
        elif model_ids:
            r.target_model_exists = True
            r.selected_model = model_ids[0]
        else:
            r.error = "No Claude models found"


# ===================================================================
# OpenRouter — model listing with 429 backoff, no inference
# ===================================================================

class OpenRouterAdapter(ProviderHealthAdapter):
    name = "openrouter"
    env_var = "OPENROUTER_API_KEY"

    def _run_checks(self, r: HealthResult, key: str) -> None:
        last_err = ""
        for attempt in range(3):
            try:
                resp = httpx.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=_TIMEOUT,
                )

                r.connectivity = True

                if resp.status_code == 429:
                    last_err = "429 Rate Limited"
                    time.sleep(2 ** attempt)
                    continue
                if resp.status_code == 401:
                    r.error = "401 Unauthorized"
                    return
                if resp.status_code != 200:
                    r.error = f"Models endpoint HTTP {resp.status_code}"
                    return

                r.auth = True

                data = resp.json()
                models_raw = data.get("data", [])
                model_ids = [
                    m.get("id", "") for m in models_raw
                    if isinstance(m, dict) and m.get("id", "")
                ]

                r.models_found = len(model_ids)
                r.models_listed = len(model_ids) > 0

                if model_ids:
                    r.target_model_exists = True
                    r.selected_model = model_ids[0]
                else:
                    r.error = "No models listed"
                return

            except httpx.TimeoutException:
                last_err = "Timeout"
                time.sleep(2 ** attempt)
            except Exception as exc:
                r.error = str(exc)
                return

        r.error = last_err


# ===================================================================
# HuggingFace — whoami auth check, no inference
# ===================================================================

class HuggingFaceAdapter(ProviderHealthAdapter):
    name = "huggingface"
    env_var = "HF_TOKEN"
    fallback_env = "HUGGING_FACE_HUB_TOKEN"

    def _run_checks(self, r: HealthResult, key: str) -> None:
        resp = httpx.get(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {key}"},
            timeout=_TIMEOUT,
        )

        r.connectivity = True

        if resp.status_code == 401:
            r.error = "401 Unauthorized — run: huggingface-cli login"
            return
        if resp.status_code != 200:
            r.error = f"whoami HTTP {resp.status_code}"
            return

        r.auth = True
        r.models_listed = True
        r.target_model_exists = True

        data = resp.json()
        r.selected_model = data.get("name", data.get("fullname", "authenticated"))


# ===================================================================
# Registry
# ===================================================================

ALL_ADAPTERS: List[ProviderHealthAdapter] = [
    OpenAIAdapter(),
    GoogleAdapter(),
    AnthropicAdapter(),
    GrokAdapter(),
    OpenRouterAdapter(),
    DeepSeekAdapter(),
    GroqAdapter(),
    TogetherAdapter(),
    CerebrasAdapter(),
    HuggingFaceAdapter(),
]

ADAPTER_MAP: Dict[str, ProviderHealthAdapter] = {a.name: a for a in ALL_ADAPTERS}


def check_all(
    required: Optional[List[str]] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Run health checks for all providers.

    Args:
        required: Provider names that must PASS.
        strict:   If True, unconfigured (SKIP) counts as FAIL.

    Returns:
        {status, providers: {name: HealthResult.to_dict()}}
    """
    results: Dict[str, Dict[str, Any]] = {}

    for adapter in ALL_ADAPTERS:
        key = adapter._get_key()
        if not key:
            status = "FAIL" if strict else "SKIP"
            results[adapter.name] = {
                "provider": adapter.name,
                "status": status,
                "latency_ms": 0,
                "error": f"{adapter.env_var} not set",
            }
            continue

        hr = adapter.check()
        d = hr.to_dict()
        if hr.latency_ms > 10_000 and hr.status == "PASS":
            d["status"] = "FAIL"
            d["error"] = f"Latency {hr.latency_ms}ms > 10s"
        results[adapter.name] = d

    all_pass = True
    if required:
        for req in required:
            if results.get(req, {}).get("status") != "PASS":
                all_pass = False
    if strict:
        for v in results.values():
            if v.get("status") != "PASS":
                all_pass = False

    return {"status": "PASS" if all_pass else "FAIL", "providers": results}
