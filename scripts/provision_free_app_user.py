#!/usr/bin/env python3
"""Create a Clerk user and provision free-tier app access in Firestore.

Usage (credentials via args — do not commit passwords):

  python3 scripts/provision_free_app_user.py user@example.com 'TheirPassword' First Last

Requires in environment (.env.local): CLERK_SECRET_KEY, LLMHIVE_API_KEY,
ORCHESTRATOR_API_BASE_URL (or uses production orchestrator default).

Note: Clerk's API is behind Cloudflare and blocks Python urllib; we use curl.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def curl_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    """HTTP JSON via curl (avoids Cloudflare blocks on api.clerk.com)."""
    cmd = ["curl", "-sS", "-w", "\n__HTTP_STATUS__:%{http_code}", "-X", method, url]
    for key, value in (headers or {}).items():
        cmd.extend(["-H", f"{key}: {value}"])
    if body is not None:
        cmd.extend(["-d", json.dumps(body)])
        if not any(k.lower() == "content-type" for k in (headers or {})):
            cmd.extend(["-H", "Content-Type: application/json"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except FileNotFoundError as exc:
        raise SystemExit("curl is required but was not found on PATH") from exc

    if result.returncode != 0:
        raise SystemExit(f"curl failed ({result.returncode}): {result.stderr.strip()}")

    raw = result.stdout
    if "\n__HTTP_STATUS__:" not in raw:
        raise SystemExit(f"Unexpected curl output: {raw[:300]}")

    payload, _, status_part = raw.rpartition("\n__HTTP_STATUS__:")
    status = int(status_part.strip())
    payload = payload.strip()
    if not payload:
        return status, None
    try:
        return status, json.loads(payload)
    except json.JSONDecodeError:
        return status, payload


def clerk_headers() -> dict[str, str]:
    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret:
        raise SystemExit("CLERK_SECRET_KEY is not set (check .env.local)")
    return {"Authorization": f"Bearer {secret}"}


def find_clerk_user_by_email(email: str) -> dict | None:
    query = urllib.parse.urlencode({"email_address": email})
    status, data = curl_json(
        "GET",
        f"https://api.clerk.com/v1/users?{query}",
        headers=clerk_headers(),
    )
    if status == 403:
        raise SystemExit(
            "Clerk API returned 403. Verify CLERK_SECRET_KEY in .env.local is the "
            "production secret (sk_live_...) for the LLMHive Clerk instance."
        )
    if status >= 400:
        raise SystemExit(f"Clerk lookup failed ({status}): {data}")

    if isinstance(data, list) and data:
        return data[0]
    return None


def create_clerk_user(email: str, password: str, first_name: str, last_name: str) -> dict:
    status, data = curl_json(
        "POST",
        "https://api.clerk.com/v1/users",
        headers=clerk_headers(),
        body={
            "email_address": [email],
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "skip_password_checks": True,
        },
    )
    if status == 422 and isinstance(data, dict):
        errors = data.get("errors") or []
        for err in errors:
            if err.get("code") == "form_identifier_exists":
                existing = find_clerk_user_by_email(email)
                if existing:
                    return existing
    if status >= 400:
        raise SystemExit(f"Clerk create user failed ({status}): {data}")
    if not isinstance(data, dict) or "id" not in data:
        raise SystemExit(f"Unexpected Clerk create response: {data}")
    return data


def ensure_clerk_user(email: str, password: str, first_name: str, last_name: str) -> str:
    existing = find_clerk_user_by_email(email)
    if existing:
        user_id = existing["id"]
        print(f"Clerk user already exists: {user_id}")
        return user_id

    created = create_clerk_user(email, password, first_name, last_name)
    user_id = created["id"]
    print(f"Created Clerk user: {user_id}")
    return user_id


def backend_url() -> str:
    return (
        os.environ.get("ORCHESTRATOR_API_BASE_URL")
        or os.environ.get("LLMHIVE_BACKEND_URL")
        or "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
    ).rstrip("/")


def backend_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.environ.get("LLMHIVE_API_KEY", "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def sync_free_subscription(user_id: str) -> dict:
    status, data = curl_json(
        "POST",
        f"{backend_url()}/api/v1/billing/subscription/sync",
        headers=backend_headers(),
        body={
            "userId": user_id,
            "tier": "free",
            "status": "active",
            "billingCycle": "monthly",
        },
    )
    if status >= 400:
        raise SystemExit(f"Subscription sync failed ({status}): {data}")
    if not isinstance(data, dict):
        raise SystemExit(f"Unexpected sync response: {data}")
    return data


def verify_entitlement(user_id: str) -> dict:
    status, data = curl_json(
        "GET",
        f"{backend_url()}/api/v1/billing/subscription/{urllib.parse.quote(user_id)}",
        headers=backend_headers(),
    )
    if status >= 400:
        raise SystemExit(f"Entitlement check failed ({status}): {data}")
    if not isinstance(data, dict):
        raise SystemExit(f"Unexpected entitlement response: {data}")
    return data


def main() -> None:
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT / ".env")

    if len(sys.argv) not in (3, 5):
        raise SystemExit(
            "Usage: provision_free_app_user.py <email> <password> [first_name last_name]"
        )

    email = sys.argv[1].strip().lower()
    password = sys.argv[2]
    first_name = sys.argv[3] if len(sys.argv) >= 4 else "Marketing"
    last_name = sys.argv[4] if len(sys.argv) >= 5 else "Agency"

    if not email or "@" not in email:
        raise SystemExit("Invalid email")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    user_id = ensure_clerk_user(email, password, first_name, last_name)
    sync_result = sync_free_subscription(user_id)
    print("Firestore sync:", json.dumps(sync_result, indent=2))

    sub = verify_entitlement(user_id)
    print("Entitlement check:", json.dumps(sub, indent=2))

    tier = str(sub.get("tier_name") or sub.get("tier", "")).lower()
    status = str(sub.get("status", "")).lower()
    if tier == "free" and status == "active":
        print(f"\nOK — {email} can sign in at https://llmhive.ai/sign-in and use free orchestration.")
    else:
        raise SystemExit(f"Unexpected subscription state: tier={tier} status={status}")


if __name__ == "__main__":
    main()
