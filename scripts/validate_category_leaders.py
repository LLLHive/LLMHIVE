#!/usr/bin/env python3
"""Validate category_leaders_llmhive.json — fail fast on missing or inconsistent definitions.

Usage:
    python scripts/validate_category_leaders.py
    python scripts/validate_category_leaders.py --path benchmark_configs/category_leaders_llmhive.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PATH = _ROOT / "benchmark_configs" / "category_leaders_llmhive.json"

_REQUIRED_KEYS = {"category_key", "display_name", "leader_score", "leader_model"}
_SCORE_PERCENT = re.compile(r"^\d+(\.\d+)?%$")
_SCORE_OUT_OF_10 = re.compile(r"^\d+(\.\d+)?/10$")


def _parse_args() -> Path:
    path = _DEFAULT_PATH
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--path" and i + 1 < len(sys.argv):
            path = Path(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    return path


def main() -> int:
    path = _parse_args()

    if not path.exists():
        print(f"FAIL: {path} does not exist.")
        return 1

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"FAIL: Invalid JSON in {path}: {e}")
        return 1

    if "version" not in data:
        print("FAIL: Missing 'version' field.")
        return 1

    if "categories" not in data:
        print("FAIL: Missing 'categories' array.")
        return 1

    categories = data["categories"]
    if not isinstance(categories, list):
        print("FAIL: 'categories' must be an array.")
        return 1

    seen_keys: set[str] = set()
    for i, cat in enumerate(categories):
        if not isinstance(cat, dict):
            print(f"FAIL: categories[{i}] must be an object.")
            return 1

        missing = _REQUIRED_KEYS - set(cat.keys())
        if missing:
            print(f"FAIL: categories[{i}] missing keys: {missing}")
            return 1

        ck = cat.get("category_key", "")
        if ck in seen_keys:
            print(f"FAIL: Duplicate category_key: {ck}")
            return 1
        seen_keys.add(ck)

        score = str(cat.get("leader_score", ""))
        if not (_SCORE_PERCENT.match(score) or _SCORE_OUT_OF_10.match(score)):
            print(f"FAIL: categories[{i}] leader_score must be '<float>%' or '<float>/10', got: {score!r}")
            return 1

        if not cat.get("leader_model"):
            print(f"FAIL: categories[{i}] leader_model must be non-empty.")
            return 1

    print(f"OK: {path} valid (version={data['version']}, categories={len(categories)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
