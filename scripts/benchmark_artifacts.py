from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


_ROOT = Path(__file__).resolve().parent.parent
_REPORTS = _ROOT / "benchmark_reports"
_DEFAULT_CERTIFIED_MANIFEST = _REPORTS / "certified_manifest.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_path(path_str: str, root: Path | None = None) -> Path:
    base = root or _ROOT
    candidate = Path(path_str)
    return candidate if candidate.is_absolute() else (base / candidate)


def find_latest_artifact(
    pattern: str,
    roots: Optional[Iterable[Path]] = None,
) -> Optional[Path]:
    search_roots = list(roots or (_REPORTS, _ROOT / "scripts" / "benchmark_reports"))
    candidates = []
    for directory in search_roots:
        if directory.exists():
            candidates.extend(directory.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_certified_manifest(
    manifest_path: Path | None = None,
    root: Path | None = None,
) -> Dict[str, Any]:
    base = root or _ROOT
    path = manifest_path or (base / _DEFAULT_CERTIFIED_MANIFEST.relative_to(_ROOT))
    return load_json(path)


def get_certified_artifacts(
    manifest_path: Path | None = None,
    root: Path | None = None,
) -> Dict[str, Path]:
    base = root or _ROOT
    manifest = load_certified_manifest(manifest_path=manifest_path, root=base)
    artifacts = manifest.get("artifacts", {})
    resolved: Dict[str, Path] = {}
    for key, rel_path in artifacts.items():
        if isinstance(rel_path, str) and rel_path.strip():
            resolved[key] = resolve_path(rel_path, root=base)
    return resolved


def validate_certified_artifacts(
    manifest_path: Path | None = None,
    root: Path | None = None,
) -> Dict[str, Any]:
    base = root or _ROOT
    manifest = load_certified_manifest(manifest_path=manifest_path, root=base)
    artifacts = get_certified_artifacts(manifest_path=manifest_path, root=base)
    checksums = manifest.get("checksums", {})
    validation: Dict[str, Any] = {}
    for key, path in artifacts.items():
        entry: Dict[str, Any] = {"path": str(path), "exists": path.exists()}
        expected = checksums.get(key)
        if path.exists():
            entry["sha256"] = compute_sha256(path)
            if expected:
                entry["checksum_match"] = entry["sha256"] == expected
        validation[key] = entry
    return validation


def is_dialogue_result(result: Dict[str, Any]) -> bool:
    category = result.get("category", "")
    return "Dialogue" in category or "MT-Bench" in category


def is_rag_result(result: Dict[str, Any]) -> bool:
    category = result.get("category", "")
    return "RAG" in category or "MS MARCO" in category


def metric_type_for_result(result: Dict[str, Any]) -> str:
    if is_dialogue_result(result):
        return "dialogue_score_out_of_10"
    if is_rag_result(result):
        return "rag_mrr_normalized_pct"
    return "accuracy_pct"


def build_result_summary(results: list[Dict[str, Any]]) -> Dict[str, Any]:
    valid_results = [r for r in results if isinstance(r, dict) and "error" not in r]
    requested_samples = sum(max(int(r.get("sample_size", 0) or 0), 0) for r in valid_results)
    graded_samples = sum(
        max(int(r.get("sample_size", 0) or 0) - int(r.get("errors", 0) or 0), 0)
        for r in valid_results
    )
    total_errors = sum(max(int(r.get("errors", 0) or 0), 0) for r in valid_results)
    normalized_scores = [
        float(r.get("accuracy", 0) or 0)
        for r in valid_results
        if isinstance(r.get("accuracy", 0), (int, float))
    ]
    average_normalized_score = (
        round(sum(normalized_scores) / len(normalized_scores), 1) if normalized_scores else 0.0
    )

    per_category: Dict[str, Dict[str, Any]] = {}
    for result in valid_results:
        category = result.get("category", "unknown")
        sample_size = max(int(result.get("sample_size", 0) or 0), 0)
        errors = max(int(result.get("errors", 0) or 0), 0)
        per_category[category] = {
            "metric_type": metric_type_for_result(result),
            "requested_samples": sample_size,
            "graded_samples": max(sample_size - errors, 0),
            "errors": errors,
            "normalized_score_pct": float(result.get("accuracy", 0) or 0),
        }

    notes = [
        "overall_score_pct is the mean normalized category score across completed categories"
    ]
    if any(is_rag_result(r) for r in valid_results):
        notes.append("RAG contributes via normalized MRR@10-derived percent score, not raw correct/incorrect counts")
    if any(is_dialogue_result(r) for r in valid_results):
        notes.append("Dialogue contributes via normalized MT-Bench score, not raw correct/incorrect counts")

    return {
        "overall_score_pct": average_normalized_score,
        "summary_method": "mean_normalized_category_score",
        "requested_samples": requested_samples,
        "graded_samples": graded_samples,
        "total_errors": total_errors,
        "categories_count": len(valid_results),
        "mixed_metric_categories_present": any(
            is_rag_result(r) or is_dialogue_result(r) for r in valid_results
        ),
        "notes": notes,
        "per_category": per_category,
    }
