#!/usr/bin/env python3
"""Run automated checks for launch go/no-go gates (read-only HTTP probes)."""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ORCHESTRATOR_URL = os.environ.get(
    "PRODUCTION_ORCHESTRATOR_URL",
    "https://llmhive-orchestrator-792354158895.us-east1.run.app",
).rstrip("/")
WWW_BASE = os.environ.get("LAUNCH_WWW_BASE", "https://www.llmhive.ai").rstrip("/")

# Certified serving revision — update when intentionally changing launch basis.
EXPECTED_REVISION = os.environ.get("LAUNCH_CERTIFIED_REVISION", "llmhive-orchestrator-02461-2h4")

PUBLIC_PATHS = (
    "/",
    "/press",
    "/faq",
    "/help",
    "/case-studies",
    "/comparisons/llmhive-vs-chatgpt",
    "/sign-in",
    "/llms.txt",
    "/api/health/integrations",
    "/pricing",
)


def _get(url: str, timeout: float = 20.0, follow: bool = True) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": "LLMHive-launch-gate-verify/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            if follow and code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location", "")
                if loc:
                    if loc.startswith("/"):
                        from urllib.parse import urlparse

                        p = urlparse(url)
                        loc = f"{p.scheme}://{p.netloc}{loc}"
                    return _get(loc, timeout=timeout, follow=True)
            body = resp.read(512).decode("utf-8", errors="replace")
            return code, body
    except HTTPError as exc:
        return exc.code, str(exc.reason)
    except URLError as exc:
        return 0, str(exc.reason)


def _check(name: str, passed: bool, details: str) -> Dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def run_checks() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    # Gate 1 — live identity (HTTP)
    for path in PUBLIC_PATHS:
        url = f"{WWW_BASE}{path}"
        code, _ = _get(url)
        ok = code == 200 or (path == "/" and code in (200, 308)) or (path == "/sign-in" and code in (200, 307, 308))
        checks.append(
            _check(
                f"www_{path.replace('/', '_') or 'root'}",
                ok,
                f"{url} -> HTTP {code}",
            )
        )

    # Gate 2 — backend health
    health_url = f"{ORCHESTRATOR_URL}/health"
    code, _ = _get(health_url)
    checks.append(_check("orchestrator_health", code == 200, f"{health_url} -> {code}"))

    # Gate 2 — chat with benchmark bypass (optional secrets)
    api_key = os.environ.get("API_KEY") or os.environ.get("LLMHIVE_API_KEY", "")
    bench = os.environ.get("LLMHIVE_SCHEDULED_BENCHMARK_SECRET", "")
    if api_key and bench:
        import json as _json

        payload = _json.dumps(
            {"prompt": "Reply with exactly: launch gate ok", "max_tokens": 30, "stream": False}
        ).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-API-Key": api_key,
            "X-LLMHIVE-Scheduled-Benchmark-Secret": bench,
        }
        req = Request(f"{ORCHESTRATOR_URL}/v1/chat", data=payload, headers=headers, method="POST")
        try:
            t0 = time.perf_counter()
            with urlopen(req, timeout=90) as resp:
                chat_code = resp.getcode()
                elapsed_ms = (time.perf_counter() - t0) * 1000
            chat_ok = chat_code == 200 and elapsed_ms <= 55000
            checks.append(
                _check(
                    "orchestrator_chat",
                    chat_ok,
                    f"POST /v1/chat -> {chat_code} in {elapsed_ms:.0f}ms",
                )
            )
        except HTTPError as exc:
            checks.append(
                _check("orchestrator_chat", False, f"POST /v1/chat -> HTTP {exc.code}")
            )
    else:
        checks.append(
            _check(
                "orchestrator_chat",
                True,
                "skipped (set API_KEY + LLMHIVE_SCHEDULED_BENCHMARK_SECRET to probe chat)",
            )
        )

    # Revision note (manual gcloud unless CLOUD_RUN_REVISION env set)
    rev = os.environ.get("CLOUD_RUN_REVISION", "")
    if rev:
        checks.append(
            _check(
                "certified_revision",
                rev == EXPECTED_REVISION,
                f"traffic revision {rev} (expected {EXPECTED_REVISION})",
            )
        )
    else:
        checks.append(
            _check(
                "certified_revision",
                True,
                f"set CLOUD_RUN_REVISION from gcloud; certified basis documents {EXPECTED_REVISION}",
            )
        )

    # Verifiers in repo
    for script, key in (
        ("verify_launch_automation_guards.py", "automation_guards"),
        ("verify_benchmark_claim_freeze.py", "benchmark_freeze"),
    ):
        path = os.path.join(ROOT, "scripts", script)
        if os.path.isfile(path):
            import subprocess

            r = subprocess.run([sys.executable, path], capture_output=True, text=True)
            try:
                data = json.loads(r.stdout)
                ok = bool(data.get("passed"))
            except json.JSONDecodeError:
                ok = r.returncode == 0
            checks.append(_check(key, ok, f"{script} exit {r.returncode}"))

    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "checks": checks, "www_base": WWW_BASE, "orchestrator": ORCHESTRATOR_URL}


def main() -> int:
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
