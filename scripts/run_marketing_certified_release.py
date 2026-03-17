#!/usr/bin/env python3
"""Marketing-Certified Release Pack — fresh eval + gate + provenance.

Single entrypoint to produce a marketing-certified benchmark bundle with:
  1. Fresh Elite+ eval artifact (run_category_benchmarks.py)
  2. Launch-candidate gate evaluation
  3. Marketing benchmark generation (injected gate result)
  4. Launch KPIs compilation
  5. Provenance file (ref, sha, timestamp, sample sizes)

Exits nonzero if any P0 gate fails or gate status is unknown.

Usage:
    python scripts/run_marketing_certified_release.py --ref certified-eliteplus-firestore-2026-03-07
    python scripts/run_marketing_certified_release.py --ref certified-eliteplus-firestore-2026-03-07 --outdir artifacts/marketing_certified
    python scripts/run_marketing_certified_release.py  # run in current workspace (must be clean)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUTDIR = _ROOT / "artifacts" / "marketing_certified"

# Sample sizes for certification (aligned with run_final_certification)
CERT_SAMPLE_SIZES = {
    "math": 100,
    "coding": 50,
    "reasoning": 100,
    "multilingual": 100,
    "long_context": 50,
    "tool_use": 50,
    "rag": 200,
    "dialogue": 30,
}


def _parse_args() -> Dict[str, Any]:
    args: Dict[str, Any] = {"ref": "", "outdir": str(_DEFAULT_OUTDIR)}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--ref" and i + 1 < len(sys.argv):
            args["ref"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--outdir" and i + 1 < len(sys.argv):
            args["outdir"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def _run(cmd: List[str], cwd: Path, env_extra: Dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(cmd, cwd=str(cwd), env=env, check=check)


def _git_sha(cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(cwd),
        )
        return r.stdout.strip()[:12] if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_ref(cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            capture_output=True, text=True, cwd=str(cwd),
        )
        if r.returncode == 0:
            return r.stdout.strip()
        r2 = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=str(cwd),
        )
        return r2.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _is_workspace_clean(cwd: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(cwd),
        )
        return r.returncode == 0 and not r.stdout.strip()
    except Exception:
        return False


def main() -> int:
    args = _parse_args()
    work_dir = _ROOT
    temp_clone: Path | None = None

    print("=" * 70)
    print("MARKETING-CERTIFIED RELEASE PACK")
    print("=" * 70)
    print(f"  Ref:    {args['ref'] or '(current HEAD)'}")
    print(f"  Outdir: {args['outdir']}")
    print()

    # Step 1: Resolve workspace
    if args["ref"]:
        if not _is_workspace_clean(_ROOT):
            print("[1/6] Workspace dirty — cloning to temp directory...")
            temp_clone = Path(tempfile.mkdtemp(prefix="llmhive_marketing_"))
            _run(["git", "clone", "--depth", "50", "https://github.com/LLLHive/LLMHIVE.git", str(temp_clone)], cwd=_ROOT)
            work_dir = temp_clone
            _run(["git", "fetch", "origin", f"tag", args["ref"]], cwd=work_dir, check=False)
            _run(["git", "checkout", args["ref"]], cwd=work_dir)
        else:
            _run(["git", "checkout", args["ref"]], cwd=work_dir)
    else:
        if not _is_workspace_clean(_ROOT):
            print("WARNING: Workspace has uncommitted changes. For reproducible marketing pack, use --ref <tag>")
    print(f"  Working dir: {work_dir}")
    print()

    outdir = Path(args["outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    reports = work_dir / "benchmark_reports"
    reports.mkdir(parents=True, exist_ok=True)
    gate_output = reports / "latest" / "gate_result.json"
    gate_output.parent.mkdir(parents=True, exist_ok=True)

    # Step 2: Run Elite+ eval benchmark
    print("[2/6] Running Elite+ eval benchmark...")
    bench_env = {
        "ELITE_PLUS_EVAL": "1",
        "ALLOW_INTERNAL_BENCH_OUTPUT": "1",
        "CATEGORY_BENCH_TIER": "elite",
        "CATEGORY_BENCH_FORCE_RESUME": "1",  # Fresh cert run; ignore checkpoint mismatch
        "ELITE_PLUS_LAUNCH_MODE": "1",
        "ELITE_PLUS_MODE": "active",
        "CATEGORY_BENCH_MMLU_SAMPLES": str(CERT_SAMPLE_SIZES["reasoning"]),
        "CATEGORY_BENCH_HUMANEVAL_SAMPLES": str(CERT_SAMPLE_SIZES["coding"]),
        "CATEGORY_BENCH_GSM8K_SAMPLES": str(CERT_SAMPLE_SIZES["math"]),
        "CATEGORY_BENCH_MMMLU_SAMPLES": str(CERT_SAMPLE_SIZES["multilingual"]),
        "CATEGORY_BENCH_LONGBENCH_SAMPLES": str(CERT_SAMPLE_SIZES["long_context"]),
        "CATEGORY_BENCH_TOOLBENCH_SAMPLES": str(CERT_SAMPLE_SIZES["tool_use"]),
        "CATEGORY_BENCH_MSMARCO_SAMPLES": str(CERT_SAMPLE_SIZES["rag"]),
        "CATEGORY_BENCH_MTBENCH_SAMPLES": str(CERT_SAMPLE_SIZES["dialogue"]),
    }
    try:
        _run(
            [sys.executable, "scripts/run_category_benchmarks.py"],
            cwd=work_dir,
            env_extra=bench_env,
        )
    except subprocess.CalledProcessError as e:
        print(f"  FAIL: Benchmark exited {e.returncode}")
        if temp_clone:
            shutil.rmtree(temp_clone, ignore_errors=True)
        return 1

    # Step 3: Run launch-candidate gate
    print("[3/6] Running launch-candidate gate...")
    try:
        _run(
            [sys.executable, "scripts/run_launch_candidate_gate.py", "--output", str(gate_output)],
            cwd=work_dir,
        )
    except subprocess.CalledProcessError as e:
        print(f"  FAIL: Gate exited {e.returncode} (P0 failures)")
        if temp_clone:
            shutil.rmtree(temp_clone, ignore_errors=True)
        return 1

    gate_data = json.loads(gate_output.read_text())
    gate_pass = gate_data.get("gate_pass", False)
    gate_status = "pass" if gate_pass else "fail"
    if gate_status not in ("pass", "fail"):
        print(f"  FAIL: Gate status unknown: {gate_status}")
        if temp_clone:
            shutil.rmtree(temp_clone, ignore_errors=True)
        return 1

    # Step 4: Run marketing benchmark with injected gate
    print("[4/6] Generating marketing benchmark pack...")
    try:
        _run(
            [sys.executable, "scripts/run_marketing_benchmark.py", "--gate-json", str(gate_output), "--require-eval"],
            cwd=work_dir,
        )
    except subprocess.CalledProcessError as e:
        print(f"  FAIL: Marketing benchmark exited {e.returncode}")
        if temp_clone:
            shutil.rmtree(temp_clone, ignore_errors=True)
        return 1

    # Step 5: Compile launch KPIs
    print("[5/6] Compiling launch KPIs...")
    try:
        _run([sys.executable, "scripts/compile_launch_kpis.py"], cwd=work_dir)
    except subprocess.CalledProcessError:
        pass  # Non-fatal; may lack some inputs

    # Step 6: Copy artifacts and write provenance
    print("[6/6] Copying artifacts and writing provenance...")
    eval_files = list((work_dir / "benchmark_reports").glob("elite_plus_eval_*.json"))
    eval_sources = [str(f.relative_to(work_dir)) for f in sorted(eval_files, key=lambda f: f.stat().st_mtime, reverse=True)[:3]]

    provenance = {
        "ref": args["ref"] or _git_ref(work_dir),
        "commit_sha": _git_sha(work_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate_status": gate_status,
        "gate_source": str(gate_output.relative_to(work_dir)),
        "eval_sources": eval_sources,
        "sample_sizes": CERT_SAMPLE_SIZES,
        "total_samples": gate_data.get("total_samples", 0),
    }
    (outdir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    to_copy = [
        (work_dir / "benchmark_reports" / "marketing_benchmark.json", "marketing_benchmark.json"),
        (work_dir / "benchmark_reports" / "marketing_benchmark.md", "marketing_benchmark.md"),
        (gate_output, "gate_result.json"),
        (work_dir / "launch_kpis.json", "launch_kpis.json"),
    ]
    for src, name in to_copy:
        if src.exists():
            shutil.copy2(src, outdir / name)

    # Step 2 (guardrail): Validate no Gate: UNKNOWN
    print("[Guardrail] Validating outputs...")
    failures: List[str] = []
    mb_json_path = outdir / "marketing_benchmark.json"
    mb_md_path = outdir / "marketing_benchmark.md"
    gate_copied = outdir / "gate_result.json"
    if gate_status.upper() != "PASS":
        failures.append(f"gate_status must be PASS, got: {gate_status}")
    if not gate_copied.exists():
        failures.append("gate_source: gate_result.json missing")
    if not provenance.get("eval_sources"):
        failures.append("eval_source: no eval artifacts in provenance")
    if mb_json_path.exists():
        mb_data = json.loads(mb_json_path.read_text())
        if mb_data.get("gate_status", "").upper() not in ("PASS", ""):
            failures.append(f"marketing_benchmark.json gate_status: {mb_data.get('gate_status')}")
        if mb_data.get("gate_status", "").lower() == "unknown":
            failures.append("Marketing benchmark must not contain Gate: UNKNOWN")
        mb_rev = mb_data.get("version_manifest", {}).get("orchestrator_revision") or ""
        prov_sha = provenance.get("commit_sha") or ""
        if mb_rev and prov_sha and prov_sha not in mb_rev and mb_rev not in prov_sha:
            failures.append("marketing_benchmark.json SHA mismatch with provenance")
    if mb_md_path.exists():
        md_text = mb_md_path.read_text()
        if "Gate: UNKNOWN" in md_text or "Gate status: UNKNOWN" in md_text:
            failures.append("marketing_benchmark.md must not show Gate: UNKNOWN")
    if failures:
        print("  FAIL: Validation errors:")
        for f in failures:
            print(f"    - {f}")
        if temp_clone:
            shutil.rmtree(temp_clone, ignore_errors=True)
        return 1

    # Step 3: Publish-ready bundle (atomic write)
    print("[Publish] Creating publish/ bundle...")
    publish_staging = Path(tempfile.mkdtemp(prefix="llmhive_publish_"))
    publish_files = [
        ("marketing_benchmark.md", outdir / "marketing_benchmark.md"),
        ("marketing_benchmark.json", outdir / "marketing_benchmark.json"),
        ("launch_kpis.json", outdir / "launch_kpis.json"),
        ("gate.json", outdir / "gate_result.json"),
        ("provenance.json", outdir / "provenance.json"),
    ]
    release_manifest = work_dir / "public" / "release_manifest.json"
    if release_manifest.exists():
        publish_files.append(("release_manifest.json", release_manifest))
    else:
        minimal_manifest = {
            "ref": provenance.get("ref"),
            "commit_sha": provenance.get("commit_sha"),
            "timestamp": provenance.get("timestamp"),
            "model_registry_version": "unknown",
        }
        (publish_staging / "release_manifest.json").write_text(
            json.dumps(minimal_manifest, indent=2) + "\n"
        )
    for name, src in publish_files:
        if src.exists():
            shutil.copy2(src, publish_staging / name)
    # Checksums
    checksum_lines: List[str] = []
    for f in sorted(publish_staging.iterdir()):
        if f.is_file():
            h = hashlib.sha256()
            h.update(f.read_bytes())
            checksum_lines.append(f"{h.hexdigest()}  {f.name}")
    (publish_staging / "checksums.txt").write_text("\n".join(checksum_lines) + "\n")
    # README
    readme = f"""# Marketing-Certified Elite+ Benchmark Pack

## What "Marketing-Certified" Means

This bundle is produced from a **fresh Elite+ evaluation** run against the certified release. It includes:

- **Gate status: PASS** — All P0 category floors met
- **Provenance** — Git ref, commit SHA, timestamp, sample sizes
- **No Gate: UNKNOWN** — All inputs are evaluation-backed

## Reproduce from Tag

```bash
git clone https://github.com/LLLHive/LLMHIVE.git
cd LLMHIVE
git checkout {provenance.get('ref', 'certified-eliteplus-firestore-2026-03-07')}

python3 scripts/run_marketing_certified_release.py \\
  --ref {provenance.get('ref', 'certified-eliteplus-firestore-2026-03-07')} \\
  --outdir artifacts/marketing_certified
```

## Sample Sizes (per category)

| Category   | Samples |
|------------|---------|
"""
    for cat, n in CERT_SAMPLE_SIZES.items():
        readme += f"| {cat} | {n} |\n"
    readme += f"""
## Floors

Defined in `benchmark_configs/launch_candidate_floors.json`. P0 categories (tool_use, rag, dialogue, math) must pass floor thresholds.

## Files in This Bundle

- `marketing_benchmark.md` — Publish-ready markdown report
- `marketing_benchmark.json` — Structured JSON artifact
- `gate.json` — Launch-candidate gate result
- `provenance.json` — Ref, SHA, timestamp, sample sizes
- `launch_kpis.json` — Launch KPIs snapshot
- `release_manifest.json` — Release manifest (or minimal snapshot)
- `checksums.txt` — SHA-256 of all files

---
Generated at {provenance.get('timestamp', '')}
"""
    (publish_staging / "README.md").write_text(readme)
    # Atomic rename
    publish_dest = outdir / "publish"
    if publish_dest.exists():
        shutil.rmtree(publish_dest)
    shutil.move(str(publish_staging), str(publish_dest))

    if temp_clone:
        shutil.rmtree(temp_clone, ignore_errors=True)

    # Summary
    print()
    print("=" * 70)
    print("MARKETING-CERTIFIED RELEASE PACK: COMPLETE")
    print("=" * 70)
    print(f"  Gate status:   {gate_status.upper()}")
    print(f"  Commit:        {provenance['commit_sha']}")
    print(f"  Ref:           {provenance['ref']}")
    print(f"  Total samples: {provenance['total_samples']}")
    print(f"  Output dir:    {outdir}")
    print(f"  Publish dir:   {outdir / 'publish'}")
    for f, _ in to_copy:
        if f.exists():
            print(f"    - {(outdir / f.name) if f.name != 'gate_result.json' else 'gate_result.json'}")
    print(f"    - provenance.json")
    print(f"    - publish/ (checksums, README)")
    print()

    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
