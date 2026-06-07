#!/usr/bin/env python3
"""Create a Clerk user and provision free-tier app access in Firestore.

Usage (credentials via args — do not commit passwords):

  python3 scripts/provision_free_app_user.py user@example.com 'TheirPassword'

Requires in environment (.env.local): CLERK_SECRET_KEY, LLMHIVE_API_KEY,
ORCHESTRATOR_API_BASE_URL (or uses production orchestrator default).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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


def clerk_request(method: str, path: str, body: dict | None = None) -> dict:
    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret:
        raise SystemExit("CLERK_SECRET_KEY is not set")

    url = f"https://api.clerk.com/v1{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def find_clerk_user_by_email(email: str) -> dict | None:
    query = urllib.parse.urlencode({"email_address": [email]})
    users = clerk_request("GET", f"/users?{query}")
    if isinstance(users, list) and users:
        return users[0]
    return None


def create_clerk_user(email: str, password: str, first_name: str, last_name: str) -> dict:
    return clerk_request(
        "POST",
        "/users",
        {
            "email_address": [email],
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "skip_password_checks": True,
        },
    )


def ensure_clerk_user(email: str, password: str, first_name: str, last_name: str) -> str:
    existing = find_clerk_user_by_email(email)
    if existing:
        user_id = existing["id"]
        print(f"Clerk user already exists: {user_id}")
        return user_id

    try:
        created = create_clerk_user(email, password, first_name, last_name)
        user_id = created["id"]
        print(f"Created Clerk user: {user_id}")
        return user_id
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        raise SystemExit(f"Clerk API error {exc.code}: {payload}") from exc


def sync_free_subscription(user_id: str) -> dict:
    backend = (
        os.environ.get("ORCHESTRATOR_API_BASE_URL")
        or os.environ.get("LLMHIVE_BACKEND_URL")
        or "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
    ).rstrip("/")
    api_key = os.environ.get("LLMHIVE_API_KEY", "").strip()

    body = {
        "userId": user_id,
        "tier": "free",
        "status": "active",
        "billingCycle": "monthly",
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(
        f"{backend}/api/v1/billing/subscription/sync",
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise SystemExit(f"Subscription sync failed {exc.code}: {detail}") from exc


def verify_entitlement(user_id: str) -> dict:
    backend = (
        os.environ.get("ORCHESTRATOR_API_BASE_URL")
        or os.environ.get("LLMHIVE_BACKEND_URL")
        or "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
    ).rstrip("/")
    api_key = os.environ.get("LLMHIVE_API_KEY", "").strip()
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(
        f"{backend}/api/v1/billing/subscription/{urllib.parse.quote(user_id)}",
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT / ".env")

    if len(sys.argv) != 3:
        raise SystemExit("Usage: provision_free_app_user.py <email> <password>")

    email = sys.argv[1].strip().lower()
    password = sys.argv[2]

    if not email or "@" not in email:
        raise SystemExit("Invalid email")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    user_id = ensure_clerk_user(email, password)
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
