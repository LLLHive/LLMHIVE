#!/usr/bin/env python3
"""
LLMHive — Multi-Provider Access Verification
==============================================
Tests connectivity, authentication, and inference latency for every
configured provider before allowing certification execution.

Usage:
    python scripts/verify_all_providers.py [--json] [--required openai,google]

Exit codes:
    0  All required providers passed.
    1  One or more required providers failed — abort certification.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LATENCY_LIMIT_MS = 10_000

# ===================================================================
# Provider definitions
# ===================================================================

_PROVIDERS: List[Dict[str, Any]] = [
    {
        "name": "OpenAI",
        "key": "openai",
        "env_var": "OPENAI_API_KEY",
        "test_url": "https://api.openai.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "Google",
        "key": "google",
        "env_var": "GOOGLE_AI_API_KEY",
        "test_fn": "_test_google",
    },
    {
        "name": "Anthropic",
        "key": "anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "test_url": "https://api.anthropic.com/v1/messages",
        "headers_extra": {"anthropic-version": "2023-06-01"},
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "payload": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Return the number 4."}],
        },
        "extract": lambda r: r.get("content", [{}])[0].get("text", ""),
    },
    {
        "name": "Grok",
        "key": "grok",
        "env_var": "XAI_API_KEY",
        "fallback_env": "GROK_API_KEY",
        "test_url": "https://api.x.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "grok-3-mini",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "OpenRouter",
        "key": "openrouter",
        "env_var": "OPENROUTER_API_KEY",
        "test_url": "https://openrouter.ai/api/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "DeepSeek",
        "key": "deepseek",
        "env_var": "DEEPSEEK_API_KEY",
        "test_url": "https://api.deepseek.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "Groq",
        "key": "groq",
        "env_var": "GROQ_API_KEY",
        "test_url": "https://api.groq.com/openai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "Together",
        "key": "together",
        "env_var": "TOGETHER_API_KEY",
        "test_url": "https://api.together.xyz/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "Cerebras",
        "key": "cerebras",
        "env_var": "CEREBRAS_API_KEY",
        "test_url": "https://api.cerebras.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "payload": {
            "model": "llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": "Return the number 4."}],
            "max_tokens": 5,
        },
        "extract": lambda r: r.get("choices", [{}])[0].get("message", {}).get("content", ""),
    },
    {
        "name": "HuggingFace",
        "key": "huggingface",
        "env_var": "HF_TOKEN",
        "fallback_env": "HUGGING_FACE_HUB_TOKEN",
        "test_fn": "_test_huggingface",
    },
]


# ===================================================================
# Custom test functions for non-standard APIs
# ===================================================================

def _test_google(api_key: str) -> Dict[str, Any]:
    """Test Google AI via generateContent."""
    result: Dict[str, Any] = {"status": "FAIL", "latency_ms": 0, "error": None}

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        r = httpx.get(f"{url}?key={api_key}", timeout=15)
        if r.status_code != 200:
            result["error"] = f"Models list HTTP {r.status_code}"
            return result

        models = r.json().get("models", [])
        prod = [
            m for m in models
            if "generateContent" in m.get("supportedGenerationMethods", [])
            and "exp" not in m.get("name", "").lower()
            and "preview" not in m.get("name", "").lower()
        ]
        if not prod:
            result["error"] = "No production models found"
            return result

        model_name = prod[0]["name"]
        gen_url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "Return the number 4."}]}],
            "generationConfig": {"maxOutputTokens": 10},
        }

        t0 = time.time()
        r = httpx.post(gen_url, json=payload, timeout=15)
        result["latency_ms"] = int((time.time() - t0) * 1000)

        if r.status_code != 200:
            result["error"] = f"Generate HTTP {r.status_code}"
            return result

        candidates = r.json().get("candidates", [])
        if candidates:
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if "4" in text:
                result["status"] = "PASS"
            else:
                result["error"] = f"Unexpected: {text[:60]}"
        else:
            result["error"] = "Empty candidates"
    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as exc:
        result["error"] = str(exc)

    return result


def _test_huggingface(api_key: str) -> Dict[str, Any]:
    """Test HuggingFace via whoami endpoint."""
    result: Dict[str, Any] = {"status": "FAIL", "latency_ms": 0, "error": None}

    try:
        t0 = time.time()
        r = httpx.get(
            "https://huggingface.co/api/whoami",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        result["latency_ms"] = int((time.time() - t0) * 1000)

        if r.status_code == 200:
            result["status"] = "PASS"
        elif r.status_code == 401:
            result["error"] = "401 Unauthorized"
        else:
            result["error"] = f"HTTP {r.status_code}"
    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as exc:
        result["error"] = str(exc)

    return result


# ===================================================================
# Generic test runner
# ===================================================================

def _test_generic(provider: dict, api_key: str) -> Dict[str, Any]:
    """Run a standard OpenAI-compatible chat completion test."""
    result: Dict[str, Any] = {"status": "FAIL", "latency_ms": 0, "error": None}

    url = provider["test_url"]
    headers = {
        provider["auth_header"]: f"{provider['auth_prefix']}{api_key}",
        "Content-Type": "application/json",
    }
    if "headers_extra" in provider:
        headers.update(provider["headers_extra"])

    t0 = time.time()
    try:
        r = httpx.post(url, json=provider["payload"], headers=headers, timeout=15)
        result["latency_ms"] = int((time.time() - t0) * 1000)

        if r.status_code == 401:
            result["error"] = "401 Unauthorized"
            return result
        if r.status_code == 404:
            result["error"] = "404 Not Found"
            return result
        if r.status_code not in (200, 201):
            result["error"] = f"HTTP {r.status_code}"
            return result

        data = r.json()
        extract_fn = provider.get("extract")
        if extract_fn:
            text = extract_fn(data)
            if "4" in str(text):
                result["status"] = "PASS"
            else:
                result["error"] = f"Unexpected: {str(text)[:60]}"
        else:
            result["status"] = "PASS"

    except httpx.TimeoutException:
        result["latency_ms"] = int((time.time() - t0) * 1000)
        result["error"] = "Timeout"
    except Exception as exc:
        result["latency_ms"] = int((time.time() - t0) * 1000)
        result["error"] = str(exc)

    return result


# ===================================================================
# Main verification loop
# ===================================================================

def verify_all_providers(
    required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Test all providers and return structured results."""

    if not _HAS_HTTPX:
        print("  httpx not installed — cannot verify providers")
        return {"status": "FAIL", "error": "httpx not installed", "providers": {}}

    results: Dict[str, Dict[str, Any]] = {}

    print()
    print(f"  {'Provider':<15} {'Status':<8} {'Latency(ms)':<14} {'Note'}")
    print(f"  {'-'*15} {'-'*8} {'-'*14} {'-'*30}")

    for prov in _PROVIDERS:
        name = prov["name"]
        key = prov["key"]

        api_key = os.getenv(prov["env_var"], "")
        if not api_key and "fallback_env" in prov:
            api_key = os.getenv(prov["fallback_env"], "")

        if not api_key:
            results[key] = {"status": "SKIP", "latency_ms": 0, "error": "Key not set"}
            print(f"  {name:<15} {'SKIP':<8} {'-':<14} {prov['env_var']} not set")
            continue

        if "test_fn" in prov:
            fn_name = prov["test_fn"]
            fn = {"_test_google": _test_google, "_test_huggingface": _test_huggingface}.get(fn_name)
            if fn:
                res = fn(api_key)
            else:
                res = {"status": "FAIL", "latency_ms": 0, "error": f"Unknown test fn {fn_name}"}
        else:
            res = _test_generic(prov, api_key)

        # Latency guard
        if res["latency_ms"] > _LATENCY_LIMIT_MS and res["status"] == "PASS":
            res["status"] = "FAIL"
            res["error"] = f"Latency {res['latency_ms']}ms > {_LATENCY_LIMIT_MS}ms"

        results[key] = res
        note = res.get("error", "") or ""
        print(f"  {name:<15} {res['status']:<8} {res['latency_ms']:<14} {note}")

    # Check required
    all_pass = True
    if required:
        for req in required:
            r = results.get(req, {})
            if r.get("status") != "PASS":
                all_pass = False

    overall = "PASS" if all_pass else "FAIL"
    return {"status": overall, "providers": results}


# ===================================================================
# Main
# ===================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="LLMHive — Multi-Provider Access Verification"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--required", type=str, default="",
        help="Comma-separated list of required provider keys (e.g., openai,google)",
    )
    args = parser.parse_args()

    required = [r.strip() for r in args.required.split(",") if r.strip()] if args.required else None

    print("=" * 70)
    print("LLMHive — Multi-Provider Access Verification")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    if required:
        print(f"  Required:  {', '.join(required)}")
    print("=" * 70)

    report = verify_all_providers(required=required)

    print()
    if report["status"] == "PASS":
        print("  PROVIDER VERIFICATION: PASS")
    else:
        print("  PROVIDER VERIFICATION: FAIL")
        failed = [
            k for k, v in report["providers"].items()
            if v.get("status") == "FAIL"
        ]
        if failed:
            print(f"  Failed providers: {', '.join(failed)}")
        if required:
            missing = [
                r for r in required
                if report["providers"].get(r, {}).get("status") != "PASS"
            ]
            if missing:
                print(f"  Required but not passing: {', '.join(missing)}")

    # Save report
    report["timestamp"] = datetime.now().isoformat()
    report_path = _PROJECT_ROOT / "benchmark_reports" / "provider_verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved: {report_path}")

    if args.json:
        print()
        print(json.dumps(report, indent=2))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
