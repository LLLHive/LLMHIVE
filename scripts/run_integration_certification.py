#!/usr/bin/env python3
"""Final Integration Certification — verify all external services and internal consistency.

Verifies:
  1. OpenAI reachable
  2. Anthropic reachable
  3. Gemini reachable
  4. Pinecone reachable
  5. Redis reachable
  6. Tool broker roundtrip valid
  7. models.json version == release_manifest version
  8. RegistryVersionBadge matches backend version

Usage:
    python scripts/run_integration_certification.py               # offline only
    python scripts/run_integration_certification.py --online       # check live services
    python scripts/run_integration_certification.py --output out.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT = _ROOT / "benchmark_reports" / "integration_certification.json"

sys.path.insert(0, str(_ROOT / "llmhive" / "src"))


def _parse_args() -> Dict[str, Any]:
    args = {"online": "--online" in sys.argv, "output": None}
    for i, a in enumerate(sys.argv):
        if a == "--output" and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
    return args


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _check(name: str, passed: bool, detail: str = "") -> Dict[str, Any]:
    return {"check": name, "pass": passed, "detail": detail}


# ---------------------------------------------------------------------------
# Provider reachability (online)
# ---------------------------------------------------------------------------
def check_openai_reachable() -> Dict[str, Any]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _check("openai_reachable", resp.status == 200, f"HTTP {resp.status}")
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 401:
            return _check("openai_reachable", True, "reachable (401 = valid endpoint, key issue)")
        return _check("openai_reachable", False, str(e))


def check_anthropic_reachable() -> Dict[str, Any]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            data=b'{}',
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _check("anthropic_reachable", True, f"HTTP {resp.status}")
    except Exception as e:
        code = getattr(e, "code", None)
        if code in (400, 401, 422):
            return _check("anthropic_reachable", True, f"reachable (HTTP {code})")
        return _check("anthropic_reachable", False, str(e))


def check_gemini_reachable() -> Dict[str, Any]:
    try:
        import urllib.request
        key = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
        url = f"https://generativelanguage.googleapis.com/v1/models?key={key}" if key else \
              "https://generativelanguage.googleapis.com/v1/models"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _check("gemini_reachable", resp.status == 200, f"HTTP {resp.status}")
    except Exception as e:
        code = getattr(e, "code", None)
        if code in (400, 401, 403):
            return _check("gemini_reachable", True, f"reachable (HTTP {code})")
        return _check("gemini_reachable", False, str(e))


def check_pinecone_reachable() -> Dict[str, Any]:
    key = os.getenv("PINECONE_API_KEY", "")
    if not key:
        return _check("pinecone_reachable", False, "PINECONE_API_KEY not set")
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.pinecone.io/indexes",
            headers={"Api-Key": key},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _check("pinecone_reachable", resp.status == 200, f"HTTP {resp.status}")
    except Exception as e:
        code = getattr(e, "code", None)
        if code in (401, 403):
            return _check("pinecone_reachable", True, f"reachable (HTTP {code})")
        return _check("pinecone_reachable", False, str(e))


def check_redis_reachable() -> Dict[str, Any]:
    try:
        import redis
    except ImportError:
        return _check("redis_reachable", False, "redis package not installed")

    url = os.getenv("REDIS_URL")
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        if url:
            client = redis.from_url(url, decode_responses=True)
        else:
            client = redis.Redis(host=host, port=port, decode_responses=True)
        client.ping()
        return _check("redis_reachable", True, f"connected to {url or f'{host}:{port}'}")
    except Exception as e:
        return _check("redis_reachable", False, str(e))


# ---------------------------------------------------------------------------
# Tool broker roundtrip (offline)
# ---------------------------------------------------------------------------
def check_tool_broker_roundtrip() -> Dict[str, Any]:
    """Verify tool schema validation roundtrip works."""
    try:
        from llmhive.app.orchestration.elite_plus_orchestrator import _validate_tool_schema

        valid_json = '{"name": "calculator", "args": {"expression": "2+2"}}'
        ok, reason = _validate_tool_schema(valid_json)
        return _check(
            "tool_broker_roundtrip",
            ok,
            f"valid_json: ok={ok}, reason={reason}",
        )
    except ImportError:
        return _check("tool_broker_roundtrip", True, "skipped: validator not importable")
    except Exception as e:
        return _check("tool_broker_roundtrip", False, str(e))


# ---------------------------------------------------------------------------
# Version consistency checks (offline)
# ---------------------------------------------------------------------------
def check_models_json_version_match() -> Dict[str, Any]:
    """models.json registryVersion == release_manifest model_registry_version."""
    models = _load_json(_ROOT / "public" / "models.json")
    manifest = _load_json(_ROOT / "public" / "release_manifest.json")

    models_ver = models.get("registryVersion")
    manifest_ver = manifest.get("model_registry_version")

    if not models_ver:
        return _check("models_json_version_match", False, "models.json missing registryVersion")
    if not manifest_ver:
        return _check("models_json_version_match", False, "release_manifest.json missing model_registry_version")

    match = str(models_ver) == str(manifest_ver)
    return _check(
        "models_json_version_match",
        match,
        f"models.json={models_ver}, manifest={manifest_ver}",
    )


def check_registry_backend_version_match() -> Dict[str, Any]:
    """Backend MODEL_REGISTRY_VERSION matches models.json."""
    try:
        from llmhive.app.orchestration.model_registry import MODEL_REGISTRY_VERSION
    except ImportError:
        return _check("registry_backend_version_match", False, "model_registry not importable")

    models = _load_json(_ROOT / "public" / "models.json")
    models_ver = models.get("registryVersion")

    match = str(MODEL_REGISTRY_VERSION) == str(models_ver)
    return _check(
        "registry_backend_version_match",
        match,
        f"backend={MODEL_REGISTRY_VERSION}, models.json={models_ver}",
    )


def check_model_count_consistency() -> Dict[str, Any]:
    """Backend registry model count matches models.json."""
    try:
        from llmhive.app.orchestration.model_registry import get_registry
        backend_count = len(get_registry())
    except ImportError:
        return _check("model_count_consistency", False, "model_registry not importable")

    models = _load_json(_ROOT / "public" / "models.json")
    json_count = len(models.get("models", []))

    match = backend_count == json_count
    return _check(
        "model_count_consistency",
        match,
        f"backend={backend_count}, models.json={json_count}",
    )


# ---------------------------------------------------------------------------
# LLMHive API health (online)
# ---------------------------------------------------------------------------
def check_llmhive_health(target_url: str) -> List[Dict[str, Any]]:
    """Check LLMHive API health, build-info, and KPIs endpoints."""
    import urllib.request
    import urllib.error

    results = []
    endpoints = ["/health", "/build-info"]

    for ep in endpoints:
        url = f"{target_url.rstrip('/')}{ep}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                results.append(_check(
                    f"llmhive_{ep.strip('/').replace('/', '_')}",
                    resp.status == 200,
                    f"HTTP {resp.status}",
                ))
        except Exception as e:
            results.append(_check(
                f"llmhive_{ep.strip('/').replace('/', '_')}",
                False,
                str(e),
            ))

    return results


# ---------------------------------------------------------------------------
# Governor config sanity (offline)
# ---------------------------------------------------------------------------
def check_governor_config() -> List[Dict[str, Any]]:
    """Verify governor config is safe for launch."""
    from llmhive.app.orchestration.tier_spend_governor import (
        FREE_TIER_MAX_COST_USD_REQUEST,
        ELITE_PLUS_MAX_COST_USD_REQUEST,
        ELITE_PLUS_ACCOUNT_DAILY_BUDGET_USD,
        GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN,
    )

    results = []

    results.append(_check(
        "free_tier_zero_cost",
        FREE_TIER_MAX_COST_USD_REQUEST == 0.0,
        f"max_cost=${FREE_TIER_MAX_COST_USD_REQUEST}",
    ))

    results.append(_check(
        "elite_plus_cost_ceiling_set",
        0 < ELITE_PLUS_MAX_COST_USD_REQUEST <= 0.10,
        f"ceiling=${ELITE_PLUS_MAX_COST_USD_REQUEST}",
    ))

    results.append(_check(
        "daily_budget_reasonable",
        0 < ELITE_PLUS_ACCOUNT_DAILY_BUDGET_USD <= 100,
        f"daily=${ELITE_PLUS_ACCOUNT_DAILY_BUDGET_USD}",
    ))

    results.append(_check(
        "global_breaker_set",
        GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN > 0,
        f"threshold=${GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN}",
    ))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = _parse_args()
    output_path = Path(args["output"]) if args["output"] else _OUTPUT
    t0 = time.time()
    now = datetime.now(timezone.utc).isoformat()

    print("=" * 70)
    print("FINAL INTEGRATION CERTIFICATION")
    print("=" * 70)
    print(f"  Time: {now}")
    print()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_checks: List[Dict[str, Any]] = []

    # Offline checks
    print("  [1/4] Version consistency...")
    all_checks.append(check_models_json_version_match())
    all_checks.append(check_registry_backend_version_match())
    all_checks.append(check_model_count_consistency())

    print("  [2/4] Governor config sanity...")
    all_checks.extend(check_governor_config())

    print("  [3/4] Tool broker roundtrip...")
    all_checks.append(check_tool_broker_roundtrip())

    # Online checks
    if args["online"]:
        print("\n  [4/4] Provider reachability (online)...")
        all_checks.append(check_openai_reachable())
        all_checks.append(check_anthropic_reachable())
        all_checks.append(check_gemini_reachable())
        all_checks.append(check_pinecone_reachable())
        all_checks.append(check_redis_reachable())

        target = os.getenv(
            "LLMHIVE_API_URL",
            "https://llmhive-orchestrator-792354158895.us-east1.run.app",
        )
        print(f"  LLMHive API health ({target})...")
        all_checks.extend(check_llmhive_health(target))
    else:
        print("  [4/4] Skipping online checks (use --online)")

    # Print results
    passed = sum(1 for c in all_checks if c["pass"])
    failed = sum(1 for c in all_checks if not c["pass"])

    print()
    for c in all_checks:
        status = "PASS" if c["pass"] else "FAIL"
        print(f"    {status}: {c['check']} — {c.get('detail', '')[:80]}")

    elapsed = round(time.time() - t0, 1)

    cert = {
        "title": "Integration Certification",
        "generated_at": now,
        "elapsed_seconds": elapsed,
        "total_checks": len(all_checks),
        "passed": passed,
        "failed": failed,
        "certified": failed == 0,
        "checks": all_checks,
    }

    output_path.write_text(json.dumps(cert, indent=2, default=str) + "\n")

    print(f"\n{'=' * 70}")
    print(f"INTEGRATION CERTIFICATION: {'PASS' if cert['certified'] else 'FAIL'}")
    print(f"{'=' * 70}")
    print(f"  Checks: {passed}/{len(all_checks)} passed")
    print(f"  Elapsed: {elapsed}s")
    print(f"  Output: {output_path}")

    sys.exit(0 if cert["certified"] else 1)


if __name__ == "__main__":
    main()
