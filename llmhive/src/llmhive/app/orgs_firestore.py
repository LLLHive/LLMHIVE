"""
Firestore-backed orgs & memberships with basic RBAC.
Collections:
- organizations (id, name, plan, store_data, retention_days, allow_db_tools, allow_vision, allow_web)
- org_memberships (org_id, user_id, role: admin|member|auditor)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Optional

from google.cloud import firestore  # type: ignore

ORG_COLLECTION = os.getenv("ORG_COLLECTION", "organizations")
MEMBERSHIP_COLLECTION = os.getenv("ORG_MEMBERSHIP_COLLECTION", "org_memberships")


@dataclass
class Organization:
    org_id: str
    name: str
    plan: str = "enterprise"
    store_data: bool = True
    retention_days: Optional[int] = None  # None = no auto purge
    allow_db_tools: bool = False
    allow_vision: bool = True
    allow_web: bool = True


@dataclass
class OrgMembership:
    org_id: str
    user_id: str
    role: str  # admin|member|auditor


def _client() -> firestore.Client:
    return firestore.Client()


def get_org(org_id: str) -> Optional[Organization]:
    doc = _client().collection(ORG_COLLECTION).document(org_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["org_id"] = org_id
    return Organization(**data)


def upsert_org(org: Organization) -> None:
    _client().collection(ORG_COLLECTION).document(org.org_id).set({k: v for k, v in asdict(org).items() if k != "org_id"})


def get_membership(user_id: str, org_id: str) -> Optional[OrgMembership]:
    doc_id = f"{org_id}:{user_id}"
    doc = _client().collection(MEMBERSHIP_COLLECTION).document(doc_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["org_id"] = org_id
    data["user_id"] = user_id
    return OrgMembership(**data)


def upsert_membership(m: OrgMembership) -> None:
    doc_id = f"{m.org_id}:{m.user_id}"
    _client().collection(MEMBERSHIP_COLLECTION).document(doc_id).set({
        "role": m.role
    })


def check_role(user_id: str, org_id: str, min_role: str = "member") -> bool:
    """
    Simple role check: admin > member > auditor
    """
    rank = {"auditor": 0, "member": 1, "admin": 2}
    mb = get_membership(user_id, org_id)
    if not mb:
        return False
    return rank.get(mb.role, -1) >= rank.get(min_role, 1)
