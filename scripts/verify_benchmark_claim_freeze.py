#!/usr/bin/env python3
"""Verify launch surfaces reference only the frozen benchmark claim basis.

Read-only: does not contact production or rerun benchmarks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "artifacts/launch_freeze/benchmark_claim_basis.json"

# Benchmark report filenames that must not appear as claim sources on launch surfaces.
FORBIDDEN_REPORT_PATTERNS = [
    re.compile(r"category_benchmarks_free_202602\d{2}"),
    re.compile(r"category_benchmarks_elite_202602\d{2}"),
    re.compile(r"category_benchmarks_free_202604\d{2}(?!01)"),  # allow 20260401 elite only via separate check
    re.compile(r"elite_tier_launch_report_202602"),
    re.compile(r"PRODUCTION_PERFORMANCE_CORRECTED_202602"),
    re.compile(r"CATEGORY_PERFORMANCE_COST_202602"),
]

ALLOWED_FREE = "category_benchmarks_free_20260331"
ALLOWED_ELITE = "category_benchmarks_elite_20260401"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _scan_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text()
    except OSError as exc:
        return [f"{path}: unreadable ({exc})"]

    for pat in FORBIDDEN_REPORT_PATTERNS:
        for match in pat.finditer(text):
            issues.append(f"{path}: forbidden benchmark reference `{match.group(0)}`")

    # Mixed-date free/elite pairs (common launch mistake)
    if ALLOWED_FREE in text and "category_benchmarks_elite_202603" in text:
        issues.append(f"{path}: mixes free 20260331 with non-frozen elite date")
    if ALLOWED_ELITE in text and "category_benchmarks_free_202604" in text:
        issues.append(f"{path}: mixes elite 20260401 with non-frozen free date")

    return issues


def _required_artifacts_exist(manifest: dict) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    for key in ("free", "elite"):
        for field in ("json", "summary_md"):
            rel = manifest[key][field]
            if not (ROOT / rel).is_file():
                issues.append(f"Missing required artifact: {rel}")
    for key in ("leaders", "leaders_optional"):
        leaders = manifest.get(key)
        if leaders and not (ROOT / leaders).is_file():
            warnings.append(f"Optional leader artifact not present: {leaders}")
    return issues, warnings


def run_checks(extra_paths: list[Path] | None = None) -> dict:
    manifest = _load_manifest()
    issues, warnings = _required_artifacts_exist(manifest)

    paths: list[Path] = []
    for rel in manifest.get("surfaces", []):
        p = ROOT / rel
        if p.is_file():
            paths.append(p)

    # Launch freeze docs should cite approved basis
    for p in sorted((ROOT / "artifacts/launch_freeze").glob("*.md")):
        paths.append(p)

    if extra_paths:
        paths.extend(extra_paths)

    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        issues.extend(_scan_file(path))

    # Marketing quick reference known stale cite
    mqr = ROOT / "docs/MARKETING_QUICK_REFERENCE.md"
    if mqr.is_file():
        text = mqr.read_text()
        if "elite_tier_launch_report_202602" in text:
            issues.append(
                f"{mqr}: references elite_tier_launch_report_20260201 "
                f"(update to {ALLOWED_ELITE} before launch)"
            )

    passed = not issues
    return {
        "passed": passed,
        "manifest": str(MANIFEST),
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
