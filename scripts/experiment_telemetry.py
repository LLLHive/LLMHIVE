"""
LLMHive — Experiment Telemetry & Continuous Improvement Engine
===============================================================
Provides versioned experiment directories, structured per-question trace
logging, token/cost accounting, failure clustering, and historical
cost-performance tracking.

All write operations are wrapped in try/except guards so that a
logging failure never interrupts a benchmark run.

Usage (from run_category_benchmarks.py):

    from experiment_telemetry import ExperimentTracer

    tracer = ExperimentTracer.init()          # creates versioned dir
    tracer.log_trace(category, trace_dict)    # per-question
    tracer.finalize(results)                  # summary + cost + history
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REPORTS_ROOT = _PROJECT_ROOT / "benchmark_reports"
_HISTORY_PATH = _REPORTS_ROOT / "history.json"

_write_lock = threading.Lock()


def _git_info() -> Dict[str, str]:
    info: Dict[str, str] = {}
    for key, cmd in [
        ("commit", ["git", "rev-parse", "HEAD"]),
        ("commit_short", ["git", "rev-parse", "--short", "HEAD"]),
        ("branch", ["git", "branch", "--show-current"]),
    ]:
        try:
            info[key] = subprocess.check_output(
                cmd, cwd=str(_PROJECT_ROOT), text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            info[key] = "unknown"
    return info


class ExperimentTracer:
    """Versioned, thread-safe experiment trace logger."""

    def __init__(self, run_dir: Path, git: Dict[str, str], ts: str):
        self._run_dir = run_dir
        self._git = git
        self._ts = ts
        self._category_writers: Dict[str, Path] = {}
        self._cost_accum: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"total_cost": 0.0, "input_tokens": 0, "output_tokens": 0, "calls": 0}
        )
        self._env = {
            "cloud_revision": os.getenv("K_REVISION", "local"),
            "runtime_minutes_cap": os.getenv("MAX_RUNTIME_MINUTES", ""),
            "cost_cap_usd": os.getenv("MAX_TOTAL_COST_USD", ""),
            "tier": os.getenv("CATEGORY_BENCH_TIER", "elite"),
            "seed": os.getenv("CATEGORY_BENCH_SEED", "42"),
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def init(cls) -> "ExperimentTracer":
        git = _git_info()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        commit = git.get("commit_short", "unknown")
        run_dir = _REPORTS_ROOT / f"{commit}_{ts}"

        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "commit": git.get("commit", ""),
                "commit_short": commit,
                "branch": git.get("branch", ""),
                "timestamp": ts,
                "iso_timestamp": datetime.now().isoformat(),
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        except Exception:
            pass

        return cls(run_dir, git, ts)

    # ------------------------------------------------------------------
    # Per-question trace
    # ------------------------------------------------------------------

    def _category_dir(self, category: str) -> Path:
        safe = category.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        d = self._run_dir / safe
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return d

    def _answers_path(self, category: str) -> Path:
        return self._category_dir(category) / "answers.jsonl"

    def log_trace(self, category: str, trace: Dict[str, Any]) -> None:
        """Append a single trace record. Never raises."""
        try:
            enriched = {
                "commit": self._git.get("commit_short", ""),
                "branch": self._git.get("branch", ""),
                "timestamp": datetime.now().isoformat(),
                "environment": self._env,
                "category": category,
            }
            enriched.update(trace)

            cost = float(trace.get("cost_usd", 0) or 0)
            inp = int(trace.get("input_tokens", 0) or 0)
            out = int(trace.get("output_tokens", 0) or 0)
            acc = self._cost_accum[category]
            acc["total_cost"] += cost
            acc["input_tokens"] += inp
            acc["output_tokens"] += out
            acc["calls"] += 1

            line = json.dumps(enriched, default=str) + "\n"
            with _write_lock:
                with open(self._answers_path(category), "a") as f:
                    f.write(line)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Dialogue transcript storage (Phase 6)
    # ------------------------------------------------------------------

    def log_dialogue_transcript(
        self,
        question_id: str,
        category: str,
        turn1_response: str,
        turn2_response: str,
        judge_score1: float,
        judge_score2: float,
        judge_rationale1: str = "",
        judge_rationale2: str = "",
        consistency_drop: bool = False,
        extra: Optional[Dict] = None,
    ) -> None:
        """Store a full dialogue transcript with judge details."""
        try:
            record = {
                "question_id": question_id,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "turn1_response": turn1_response,
                "turn2_response": turn2_response,
                "judge_score1": judge_score1,
                "judge_score2": judge_score2,
                "judge_rationale1": judge_rationale1,
                "judge_rationale2": judge_rationale2,
                "consistency_drop": consistency_drop,
            }
            if extra:
                record.update(extra)

            cat_dir = self._category_dir("Dialogue")
            path = cat_dir / "transcripts.jsonl"
            with _write_lock:
                with open(path, "a") as f:
                    f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # GSM8K verify persistence (Phase 7)
    # ------------------------------------------------------------------

    def log_gsm8k_verify(
        self,
        question_id: str,
        candidates: List[Dict],
        verify_scores: List[float],
        selected_answer: Optional[str],
        majority_vote: Optional[str],
        circuit_breaker_active: bool,
        verify_latencies_ms: List[int],
        extra: Optional[Dict] = None,
    ) -> None:
        """Persist full GSM8K verify pipeline state."""
        try:
            record = {
                "question_id": question_id,
                "timestamp": datetime.now().isoformat(),
                "candidates": candidates,
                "verify_scores": verify_scores,
                "selected_answer": selected_answer,
                "majority_vote": majority_vote,
                "circuit_breaker_active": circuit_breaker_active,
                "verify_latencies_ms": verify_latencies_ms,
            }
            if extra:
                record.update(extra)

            cat_dir = self._category_dir("Math_GSM8K")
            path = cat_dir / "verify_traces.jsonl"
            with _write_lock:
                with open(path, "a") as f:
                    f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Token accounting helper
    # ------------------------------------------------------------------

    def record_api_call(
        self, category: str, cost: float = 0, input_tokens: int = 0, output_tokens: int = 0
    ) -> None:
        """Accumulate cost/token stats without writing a full trace."""
        try:
            acc = self._cost_accum[category]
            acc["total_cost"] += cost
            acc["input_tokens"] += input_tokens
            acc["output_tokens"] += output_tokens
            acc["calls"] += 1
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Finalization — summaries, cost, clustering, history
    # ------------------------------------------------------------------

    def finalize(self, results: List[Dict[str, Any]]) -> None:
        """Generate summary.json, cost.json, and update history.json."""
        try:
            self._write_cost_json(results)
        except Exception:
            pass
        try:
            self._write_summary_json(results)
        except Exception:
            pass
        try:
            self._update_history(results)
        except Exception:
            pass

    # ---- cost.json ----

    def _write_cost_json(self, results: List[Dict]) -> None:
        total_tokens = sum(
            a["input_tokens"] + a["output_tokens"] for a in self._cost_accum.values()
        )
        total_cost = sum(a["total_cost"] for a in self._cost_accum.values())
        total_correct = sum(r.get("correct", 0) for r in results if isinstance(r, dict) and "error" not in r)
        total_samples = sum(r.get("sample_size", 0) for r in results if isinstance(r, dict) and "error" not in r)

        cost_per_category = {}
        for cat, acc in self._cost_accum.items():
            cost_per_category[cat] = {
                "total_cost_usd": round(acc["total_cost"], 6),
                "input_tokens": acc["input_tokens"],
                "output_tokens": acc["output_tokens"],
                "calls": acc["calls"],
            }

        prev_cost = self._load_previous_cost()

        cost_data = {
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "cost_per_category": cost_per_category,
            "cost_per_correct_answer": round(total_cost / total_correct, 6) if total_correct else 0,
            "cost_per_benchmark": round(total_cost / len(results), 6) if results else 0,
            "cost_vs_previous_commit_delta": round(total_cost - prev_cost, 6) if prev_cost is not None else None,
        }

        (self._run_dir / "cost.json").write_text(json.dumps(cost_data, indent=2))

    def _load_previous_cost(self) -> Optional[float]:
        try:
            history = json.loads(_HISTORY_PATH.read_text()) if _HISTORY_PATH.exists() else []
            if history:
                return history[-1].get("total_cost_usd", 0)
        except Exception:
            pass
        return None

    # ---- summary.json (failure clustering) ----

    def _write_summary_json(self, results: List[Dict]) -> None:
        cluster: Dict[str, Any] = {
            "failure_by_category": {},
            "failure_by_type": defaultdict(int),
            "failure_by_subject": defaultdict(int),
            "extraction_failures": 0,
            "verify_failures": 0,
            "low_confidence_cases": 0,
            "pred_none_cases": 0,
            "top_hardest_subjects": [],
        }

        for cat_dir in self._run_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            answers_path = cat_dir / "answers.jsonl"
            if not answers_path.exists():
                continue

            cat_name = cat_dir.name
            cat_failures = 0
            subject_errors: Dict[str, int] = defaultdict(int)
            subject_totals: Dict[str, int] = defaultdict(int)

            for line in answers_path.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                subj = rec.get("subject", "unknown")
                subject_totals[subj] += 1

                is_correct = rec.get("is_correct", rec.get("passed", False))
                if not is_correct:
                    cat_failures += 1
                    subject_errors[subj] += 1

                    ft = rec.get("failure_type", "unknown")
                    cluster["failure_by_type"][ft] += 1

                    if ft in ("extraction", "PARSING_FAILURE"):
                        cluster["extraction_failures"] += 1
                    if ft in ("verify_failure", "VERIFY_FAILURE"):
                        cluster["verify_failures"] += 1

                conf = rec.get("confidence")
                if conf is not None and conf < 0.5:
                    cluster["low_confidence_cases"] += 1

                if rec.get("extracted_answer") is None and rec.get("predicted") is None:
                    cluster["pred_none_cases"] += 1

            cluster["failure_by_category"][cat_name] = cat_failures

            for subj, errs in subject_errors.items():
                cluster["failure_by_subject"][subj] += errs

        hardest = sorted(
            cluster["failure_by_subject"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        cluster["top_hardest_subjects"] = [{"subject": s, "failures": f} for s, f in hardest]

        cluster["failure_by_type"] = dict(cluster["failure_by_type"])
        cluster["failure_by_subject"] = dict(cluster["failure_by_subject"])

        (self._run_dir / "summary.json").write_text(json.dumps(cluster, indent=2))

    # ---- history.json ----

    def _update_history(self, results: List[Dict]) -> None:
        try:
            history = json.loads(_HISTORY_PATH.read_text()) if _HISTORY_PATH.exists() else []
        except Exception:
            history = []

        total_correct = sum(r.get("correct", 0) for r in results if isinstance(r, dict) and "error" not in r)
        total_attempted = sum(
            r.get("sample_size", 0) - r.get("errors", 0) for r in results if isinstance(r, dict) and "error" not in r
        )
        total_cost = sum(a["total_cost"] for a in self._cost_accum.values())
        total_tokens = sum(a["input_tokens"] + a["output_tokens"] for a in self._cost_accum.values())

        accuracy_by_category = {}
        cost_by_category = {}
        for r in results:
            if isinstance(r, dict) and "error" not in r:
                cat = r.get("category", "unknown")
                accuracy_by_category[cat] = r.get("accuracy", 0)
                cost_by_category[cat] = round(r.get("total_cost", 0), 6)

        entry = {
            "commit": self._git.get("commit", ""),
            "commit_short": self._git.get("commit_short", ""),
            "branch": self._git.get("branch", ""),
            "timestamp": self._ts,
            "iso_timestamp": datetime.now().isoformat(),
            "overall_accuracy": round(total_correct / total_attempted * 100, 1) if total_attempted else 0,
            "total_correct": total_correct,
            "total_attempted": total_attempted,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "cost_per_correct": round(total_cost / total_correct, 6) if total_correct else 0,
            "cost_per_1pct_accuracy": (
                round(total_cost / (total_correct / total_attempted * 100), 6)
                if total_attempted and total_correct else 0
            ),
            "token_efficiency": round(total_correct / total_tokens * 1000, 4) if total_tokens else 0,
            "accuracy_by_category": accuracy_by_category,
            "cost_by_category": cost_by_category,
        }

        if history:
            prev = history[-1]
            entry["cost_delta_vs_previous"] = round(
                total_cost - prev.get("total_cost_usd", 0), 6
            )
            prev_acc = prev.get("overall_accuracy", 0)
            entry["accuracy_delta_vs_previous"] = round(
                entry["overall_accuracy"] - prev_acc, 1
            )

        history.append(entry)

        _REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
        _HISTORY_PATH.write_text(json.dumps(history, indent=2))

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    @property
    def git_info(self) -> Dict[str, str]:
        return dict(self._git)
