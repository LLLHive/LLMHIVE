#!/usr/bin/env python3
"""
LLMHive ModelDB Refresh Runner - One-command pipeline execution.

This script orchestrates the complete ModelDB refresh workflow:
1. Archive the current Excel (timestamped backup)
2. Run update from OpenRouter API
3. Run enrichment layer (rankings, benchmarks, evals, telemetry)
4. Validate no data loss (row + column name superset)
5. Run pipeline to Firestore + Pinecone
6. Rollback if errors detected

Usage:
    python run_modeldb_refresh.py
    python run_modeldb_refresh.py --doctor          # Check environment
    python run_modeldb_refresh.py --dry-run         # Validate without changes
    python run_modeldb_refresh.py --skip-update     # Only run enrichment + pipeline
    python run_modeldb_refresh.py --skip-enrichment # Skip rankings/benchmarks/evals
    python run_modeldb_refresh.py --skip-pipeline   # Only update Excel
    python run_modeldb_refresh.py --evals-enabled false    # Skip eval harness
    python run_modeldb_refresh.py --telemetry-enabled false  # Skip telemetry

Guardrails:
- If row count decreases: FAIL and restore archive
- If column names not superset: FAIL and restore archive
- If duplicate slugs detected: FAIL
- If .env missing for real runs: FAIL with helpful message
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# =============================================================================
# Constants
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_EXCEL = SCRIPT_DIR / "LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx"
DEFAULT_ARCHIVE_DIR = SCRIPT_DIR / "archives"
DEFAULT_CACHE_DIR = Path(".cache/llmhive_modeldb")
ENV_FILE = SCRIPT_DIR / ".env"
ENV_EXAMPLE_FILE = SCRIPT_DIR / ".env.example"
SCHEMA_BASELINE_FILE = SCRIPT_DIR / "schema_baseline_columns.json"

# Required columns for validation
REQUIRED_COLUMNS = ["openrouter_slug"]


def load_schema_baseline() -> Dict[str, Any]:
    """Load schema baseline for column name superset validation."""
    if not SCHEMA_BASELINE_FILE.exists():
        return {}
    
    try:
        with open(SCHEMA_BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# Environment variables and their requirements
ENV_REQUIREMENTS = {
    "GOOGLE_APPLICATION_CREDENTIALS": {
        "required_for": ["pipeline"],
        "description": "Path to GCP service account JSON",
        "is_file": True,
    },
    "PINECONE_API_KEY": {
        "required_for": ["pipeline"],
        "description": "Pinecone API key",
        "is_file": False,
    },
    "OPENROUTER_API_KEY": {
        "required_for": ["update"],
        "description": "OpenRouter API key (optional but recommended)",
        "is_file": False,
    },
    "GOOGLE_CLOUD_PROJECT": {
        "required_for": [],
        "description": "GCP project ID (default: llmhive-orchestrator)",
        "is_file": False,
    },
    "PINECONE_INDEX_NAME": {
        "required_for": [],
        "description": "Pinecone index name (default: modeldb-embeddings)",
        "is_file": False,
    },
    "MODELDB_EMBEDDINGS_ENABLED": {
        "required_for": [],
        "description": "Enable Pinecone embeddings (default: true)",
        "is_file": False,
    },
}


# =============================================================================
# Environment Loading
# =============================================================================


def load_dotenv_safely() -> Tuple[bool, str]:
    """
    Load .env file if present.
    
    Returns:
        (success, message) tuple
    """
    try:
        from dotenv import load_dotenv
        
        if ENV_FILE.exists():
            load_dotenv(ENV_FILE)
            return True, f"Loaded environment from {ENV_FILE}"
        else:
            return False, f".env file not found at {ENV_FILE}"
    except ImportError:
        return False, "python-dotenv not installed. Run: pip install python-dotenv"


def check_required_env_vars(skip_update: bool, skip_pipeline: bool, dry_run: bool) -> Tuple[bool, List[str]]:
    """
    Check if required environment variables are set.
    
    Returns:
        (all_ok, list_of_issues) tuple
    """
    issues = []
    
    if dry_run:
        # Dry run doesn't need secrets
        return True, []
    
    for var_name, config in ENV_REQUIREMENTS.items():
        required_for = config["required_for"]
        
        # Check if this var is needed based on what we're running
        needed = False
        if "update" in required_for and not skip_update:
            needed = True
        if "pipeline" in required_for and not skip_pipeline:
            needed = True
        
        # Skip optional vars
        if not required_for:
            continue
        
        if needed:
            value = os.getenv(var_name)
            if not value:
                issues.append(f"  {var_name}: MISSING ({config['description']})")
            elif config.get("is_file") and not Path(value).exists():
                issues.append(f"  {var_name}: FILE NOT FOUND at {value}")
    
    return len(issues) == 0, issues


# =============================================================================
# Doctor Mode
# =============================================================================


def run_doctor() -> int:
    """
    Run diagnostics and print environment status.
    
    Returns exit code: 0 if healthy, 2 if issues found.
    """
    print("=" * 70)
    print("LLMHive ModelDB Pipeline - Doctor Mode")
    print("=" * 70)
    print()
    
    issues = []
    
    # Python info
    print("🐍 Python Environment")
    print(f"   Executable: {sys.executable}")
    
    # Check if in venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_status = "✅ Active" if in_venv else "⚠️  Not in virtual environment"
    print(f"   Virtual Env: {venv_status}")
    print()
    
    # Check dependencies
    print("📦 Dependencies")
    deps_to_check = [
        ("pandas", "Data manipulation", "pandas"),
        ("openpyxl", "Excel read/write", "openpyxl"),
        ("requests", "HTTP client", "requests"),
        ("tenacity", "Retry logic", "tenacity"),
        ("dotenv", "Environment loading", "dotenv"),
        ("google.cloud.firestore", "Firestore client", "google.cloud.firestore"),
        ("pinecone", "Pinecone vector DB", "pinecone"),
        ("datasets", "HuggingFace datasets (for leaderboards)", "datasets"),
    ]
    
    import importlib
    for display_name, desc, import_path in deps_to_check:
        try:
            importlib.import_module(import_path)
            print(f"   ✅ {display_name}: installed")
        except ImportError:
            print(f"   ❌ {display_name}: NOT INSTALLED ({desc})")
            issues.append(f"Missing dependency: {display_name}")
    print()
    
    # Check files
    print("📁 Files")
    
    # Canonical Excel
    if DEFAULT_EXCEL.exists():
        import pandas as pd
        try:
            df = pd.read_excel(DEFAULT_EXCEL)
            print(f"   ✅ Canonical Excel: {DEFAULT_EXCEL.name}")
            print(f"      Rows: {len(df)}, Columns: {len(df.columns)}")
        except Exception as e:
            print(f"   ⚠️  Canonical Excel exists but unreadable: {e}")
            issues.append(f"Excel file unreadable: {e}")
    else:
        print(f"   ⚠️  Canonical Excel: NOT FOUND")
        print(f"      Expected: {DEFAULT_EXCEL}")
        issues.append("Canonical Excel file missing")
    
    # Archive dir
    if DEFAULT_ARCHIVE_DIR.exists():
        archive_count = len(list(DEFAULT_ARCHIVE_DIR.glob("*.xlsx")))
        log_count = len(list(DEFAULT_ARCHIVE_DIR.glob("*.json")))
        print(f"   ✅ Archive Dir: exists ({archive_count} Excel, {log_count} logs)")
        
        # Check writable
        test_file = DEFAULT_ARCHIVE_DIR / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
            print(f"      Writable: ✅")
        except Exception:
            print(f"      Writable: ❌")
            issues.append("Archive directory not writable")
    else:
        print(f"   ⚠️  Archive Dir: will be created at {DEFAULT_ARCHIVE_DIR}")
    print()
    
    # Environment
    print("🔐 Environment Configuration")
    
    # .env file
    if ENV_FILE.exists():
        print(f"   ✅ .env file: exists at {ENV_FILE}")
    else:
        print(f"   ❌ .env file: NOT FOUND")
        if ENV_EXAMPLE_FILE.exists():
            print(f"      To fix, run:")
            print(f"      cp {ENV_EXAMPLE_FILE} {ENV_FILE}")
        else:
            print(f"      Create from template and fill in secrets")
        issues.append(".env file missing")
    
    # Load .env and check vars
    load_dotenv_safely()
    print()
    print("   Environment Variables:")
    
    for var_name, config in ENV_REQUIREMENTS.items():
        value = os.getenv(var_name)
        required_for = config["required_for"]
        
        if value:
            # Don't print secrets
            if "KEY" in var_name or "CREDENTIALS" in var_name:
                display = f"SET ({len(value)} chars)"
            else:
                display = f"SET = {value}"
            
            # Check if file exists for file-type vars
            if config.get("is_file"):
                if Path(value).exists():
                    display += " ✓ file exists"
                else:
                    display += " ✗ FILE NOT FOUND"
                    issues.append(f"{var_name} points to missing file")
            
            status = "✅"
        else:
            if required_for:
                status = "⚠️ "
                display = f"MISSING (needed for: {', '.join(required_for)})"
            else:
                status = "ℹ️ "
                display = "not set (optional)"
        
        print(f"   {status} {var_name}: {display}")
    print()
    
    # Summary
    print("=" * 70)
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   • {issue}")
        print()
        print("Fix the issues above and run --doctor again.")
        return 2
    else:
        print("✅ ALL CHECKS PASSED - Ready to run!")
        print()
        print("Next steps:")
        print("  python run_modeldb_refresh.py --dry-run   # Test without changes")
        print("  python run_modeldb_refresh.py             # Full run")
        return 0


# =============================================================================
# Logging Setup
# =============================================================================


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("modeldb_refresh")


logger = logging.getLogger("modeldb_refresh")


# =============================================================================
# Helpers
# =============================================================================


def archive_file(source: Path, archive_dir: Path) -> Optional[Path]:
    """Create a timestamped archive copy of a file."""
    if not source.exists():
        logger.warning("Source file not found, skipping archive: %s", source)
        return None
    
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"{source.stem}_{timestamp}{source.suffix}"
    archive_path = archive_dir / archive_name
    
    shutil.copy2(source, archive_path)
    logger.info("Archived: %s -> %s", source.name, archive_path.name)
    
    return archive_path


def restore_from_archive(archive_path: Path, target: Path) -> bool:
    """Restore a file from archive."""
    if not archive_path.exists():
        logger.error("Archive not found: %s", archive_path)
        return False
    
    shutil.copy2(archive_path, target)
    logger.info("Restored: %s <- %s", target.name, archive_path.name)
    return True


def validate_excel(
    path: Path, 
    min_rows: int = 0, 
    required_column_names: Optional[set] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate an Excel file meets requirements.
    
    Uses column NAME superset validation (not just count).
    """
    import pandas as pd
    
    errors = []
    
    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors
    
    try:
        df = pd.read_excel(path)
    except Exception as e:
        errors.append(f"Failed to read Excel: {e}")
        return False, errors
    
    # Check required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    # Check row count
    if len(df) < min_rows:
        errors.append(f"Row count decreased: {len(df)} < {min_rows}")
    
    # Check column NAME superset (not just count)
    if required_column_names:
        current_columns = set(df.columns)
        missing_columns = required_column_names - current_columns
        if missing_columns:
            errors.append(
                f"Missing {len(missing_columns)} columns: {sorted(list(missing_columns))[:5]}..."
            )
    
    # Check for duplicate slugs
    if "openrouter_slug" in df.columns:
        duplicates = df["openrouter_slug"].dropna().duplicated()
        if duplicates.any():
            dup_count = duplicates.sum()
            dup_examples = df.loc[duplicates, "openrouter_slug"].head(3).tolist()
            errors.append(f"Found {dup_count} duplicate slugs: {dup_examples}")
    
    return len(errors) == 0, errors


def run_script(script_path: Path, args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run a Python script as subprocess."""
    cmd = [sys.executable, str(script_path)] + args
    logger.info("Running: %s", " ".join(cmd))
    
    result = subprocess.run(
        cmd,
        cwd=cwd or SCRIPT_DIR,
        capture_output=True,
        text=True,
    )
    
    return result.returncode, result.stdout, result.stderr


# =============================================================================
# Main Runner
# =============================================================================


class ModelDBRefreshRunner:
    """Orchestrates the complete refresh workflow."""
    
    def __init__(
        self,
        excel_path: Optional[Path] = None,
        archive_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        dry_run: bool = False,
        skip_update: bool = False,
        skip_enrichment: bool = False,
        skip_pipeline: bool = False,
        allow_row_decrease: bool = False,
        evals_enabled: bool = True,
        telemetry_enabled: bool = True,
        evals_max_models: int = 0,
        evals_ttl_days: int = 30,
        evals_seed: Optional[str] = None,
        evals_always_include_top: int = 10,
        telemetry_max_models: int = 0,
        telemetry_trials: int = 3,
        telemetry_ttl_days: int = 14,
        telemetry_seed: Optional[str] = None,
        telemetry_always_include_top: int = 10,
        skip_expensive: bool = False,
    ):
        self.excel_path = excel_path or DEFAULT_EXCEL
        self.archive_dir = archive_dir or DEFAULT_ARCHIVE_DIR
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.dry_run = dry_run
        self.skip_update = skip_update
        self.skip_enrichment = skip_enrichment
        self.skip_pipeline = skip_pipeline
        self.allow_row_decrease = allow_row_decrease
        self.evals_enabled = evals_enabled
        self.telemetry_enabled = telemetry_enabled
        self.evals_max_models = evals_max_models
        self.evals_ttl_days = evals_ttl_days
        self.evals_seed = evals_seed
        self.evals_always_include_top = evals_always_include_top
        self.telemetry_max_models = telemetry_max_models
        self.telemetry_trials = telemetry_trials
        self.telemetry_ttl_days = telemetry_ttl_days
        self.telemetry_seed = telemetry_seed
        self.telemetry_always_include_top = telemetry_always_include_top
        self.skip_expensive = skip_expensive
        
        self.archive_path: Optional[Path] = None
        self.original_row_count = 0
        self.original_column_names: set = set()
        
        self.run_log: Dict[str, Any] = {
            "started_at": None,
            "completed_at": None,
            "excel_path": str(self.excel_path),
            "dry_run": dry_run,
            "steps": [],
            "success": False,
            "errors": [],
        }
    
    def run(self) -> Dict[str, Any]:
        """Execute the full refresh workflow."""
        import pandas as pd
        
        self.run_log["started_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info("=" * 70)
        logger.info("ModelDB Refresh Runner")
        logger.info("=" * 70)
        logger.info("Excel: %s", self.excel_path)
        logger.info("Archive Dir: %s", self.archive_dir)
        logger.info("Dry Run: %s", self.dry_run)
        logger.info("Skip Update: %s", self.skip_update)
        logger.info("Skip Enrichment: %s", self.skip_enrichment)
        logger.info("Skip Pipeline: %s", self.skip_pipeline)
        logger.info("Evals Enabled: %s", self.evals_enabled)
        logger.info("Telemetry Enabled: %s", self.telemetry_enabled)
        logger.info("=" * 70)
        
        try:
            # Step 1: Validate existing file (if exists)
            self._step_validate_existing()
            
            # Step 2: Archive
            self._step_archive()
            
            # Step 3: Run update script (fetch OpenRouter)
            if not self.skip_update:
                self._step_update()
            else:
                logger.info("[SKIP] Update step skipped")
                self.run_log["steps"].append({"step": "update", "status": "skipped"})
            
            # Step 4: Run enrichment layer (rankings, benchmarks, evals, telemetry)
            if not self.skip_enrichment:
                self._step_enrichment()
            else:
                logger.info("[SKIP] Enrichment step skipped")
                self.run_log["steps"].append({"step": "enrichment", "status": "skipped"})
            
            # Step 5: Validate updated file
            self._step_validate_updated()
            
            # Step 6: Run pipeline (Firestore + Pinecone)
            if not self.skip_pipeline:
                self._step_pipeline()
            else:
                logger.info("[SKIP] Pipeline step skipped")
                self.run_log["steps"].append({"step": "pipeline", "status": "skipped"})
            
            # Step 7: Generate coverage report
            self._step_coverage_report()
            
            self.run_log["success"] = True
            logger.info("=" * 70)
            logger.info("✅ Refresh completed successfully!")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error("❌ Refresh failed: %s", e)
            self.run_log["errors"].append(str(e))
            self.run_log["success"] = False
            
            # Attempt rollback
            if self.archive_path and not self.dry_run:
                logger.info("Attempting rollback from archive...")
                if restore_from_archive(self.archive_path, self.excel_path):
                    logger.info("Rollback successful")
                else:
                    logger.error("Rollback failed!")
        
        finally:
            self.run_log["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._write_run_log()
        
        return self.run_log
    
    def _step_validate_existing(self) -> None:
        """Validate existing Excel file and capture column names."""
        import pandas as pd
        
        step: Dict[str, Any] = {"step": "validate_existing", "status": "pending"}
        
        if not self.excel_path.exists():
            logger.info("No existing Excel file, will create new")
            step["status"] = "skipped"
            step["reason"] = "file not found"
            self.run_log["steps"].append(step)
            return
        
        try:
            df = pd.read_excel(self.excel_path)
            self.original_row_count = len(df)
            self.original_column_names = set(df.columns)
            
            # Also load baseline columns
            baseline = load_schema_baseline()
            baseline_cols = set(baseline.get("columns", []))
            if baseline_cols:
                self.original_column_names = self.original_column_names | baseline_cols
            
            logger.info("Existing file has %d rows, %d columns", 
                       self.original_row_count, len(self.original_column_names))
            
            step["status"] = "success"
            step["row_count"] = self.original_row_count
            step["column_count"] = len(self.original_column_names)
            step["column_names"] = sorted(list(self.original_column_names))
            
        except Exception as e:
            step["status"] = "error"
            step["error"] = str(e)
            logger.warning("Could not read existing file: %s", e)
        
        self.run_log["steps"].append(step)
    
    def _step_archive(self) -> None:
        """Archive existing file."""
        step: Dict[str, Any] = {"step": "archive", "status": "pending"}
        
        if self.dry_run:
            logger.info("[DRY RUN] Would archive %s", self.excel_path)
            step["status"] = "skipped"
            step["reason"] = "dry run"
            self.run_log["steps"].append(step)
            return
        
        try:
            self.archive_path = archive_file(self.excel_path, self.archive_dir)
            if self.archive_path:
                step["status"] = "success"
                step["archive_path"] = str(self.archive_path)
            else:
                step["status"] = "skipped"
                step["reason"] = "no file to archive"
        except Exception as e:
            step["status"] = "error"
            step["error"] = str(e)
            raise
        
        self.run_log["steps"].append(step)
    
    def _step_update(self) -> None:
        """Run the update script."""
        step: Dict[str, Any] = {"step": "update", "status": "pending"}
        
        update_script = SCRIPT_DIR / "llmhive_modeldb_update.py"
        
        if not update_script.exists():
            step["status"] = "error"
            step["error"] = f"Update script not found: {update_script}"
            self.run_log["steps"].append(step)
            raise FileNotFoundError(f"Update script not found: {update_script}")
        
        args = [
            "--output", str(self.excel_path),
            "--cache-dir", str(self.cache_dir),
        ]
        
        if self.excel_path.exists():
            args.extend(["--previous", str(self.excel_path)])
        else:
            args.append("--from-openrouter")
        
        if self.dry_run:
            args.append("--dry-run")
        
        returncode, stdout, stderr = run_script(update_script, args)
        
        step["returncode"] = returncode
        if stdout:
            step["stdout_tail"] = stdout[-1000:]
        if stderr:
            step["stderr_tail"] = stderr[-1000:]
        
        if returncode != 0:
            step["status"] = "error"
            logger.error("Update script failed:\n%s", stderr or stdout)
            self.run_log["steps"].append(step)
            raise RuntimeError(f"Update script failed with code {returncode}")
        
        step["status"] = "success"
        self.run_log["steps"].append(step)
        logger.info("Update step completed")
    
    def _step_enrichment(self) -> None:
        """Run the enrichment layer."""
        step: Dict[str, Any] = {"step": "enrichment", "status": "pending"}
        
        enrich_script = SCRIPT_DIR / "llmhive_modeldb_enrich.py"
        
        if not enrich_script.exists():
            step["status"] = "error"
            step["error"] = f"Enrichment script not found: {enrich_script}"
            self.run_log["steps"].append(step)
            raise FileNotFoundError(f"Enrichment script not found: {enrich_script}")
        
        args = [
            "--excel", str(self.excel_path),
            "--output", str(self.excel_path),
            "--evals-enabled", "true" if self.evals_enabled else "false",
            "--telemetry-enabled", "true" if self.telemetry_enabled else "false",
        ]
        
        if self.evals_max_models > 0:
            args.extend(["--evals-max-models", str(self.evals_max_models)])
        
        args.extend(["--evals-ttl-days", str(self.evals_ttl_days)])
        
        if self.evals_seed:
            args.extend(["--evals-seed", self.evals_seed])
        
        args.extend(["--evals-always-include-top", str(self.evals_always_include_top)])
        
        if self.telemetry_max_models > 0:
            args.extend(["--telemetry-max-models", str(self.telemetry_max_models)])
        
        if self.telemetry_trials:
            args.extend(["--telemetry-trials", str(self.telemetry_trials)])
        
        args.extend(["--telemetry-ttl-days", str(self.telemetry_ttl_days)])
        
        if self.telemetry_seed:
            args.extend(["--telemetry-seed", self.telemetry_seed])
        
        args.extend(["--telemetry-always-include-top", str(self.telemetry_always_include_top)])
        
        if self.skip_expensive:
            args.append("--skip-expensive")
        
        if self.dry_run:
            args.append("--dry-run")
        
        returncode, stdout, stderr = run_script(enrich_script, args)
        
        step["returncode"] = returncode
        if stdout:
            step["stdout_tail"] = stdout[-1000:]
        if stderr:
            step["stderr_tail"] = stderr[-1000:]
        
        if returncode != 0:
            step["status"] = "error"
            logger.error("Enrichment script failed:\n%s", stderr or stdout)
            self.run_log["steps"].append(step)
            raise RuntimeError(f"Enrichment script failed with code {returncode}")
        
        step["status"] = "success"
        self.run_log["steps"].append(step)
        logger.info("Enrichment step completed")
    
    def _step_validate_updated(self) -> None:
        """Validate the updated file using column NAME superset."""
        import pandas as pd
        
        step: Dict[str, Any] = {"step": "validate_updated", "status": "pending"}
        
        if self.dry_run:
            logger.info("[DRY RUN] Would validate updated file")
            step["status"] = "skipped"
            step["reason"] = "dry run"
            self.run_log["steps"].append(step)
            return
        
        min_rows = 0 if self.allow_row_decrease else self.original_row_count
        required_cols = self.original_column_names if self.original_column_names else None
        
        is_valid, errors = validate_excel(
            self.excel_path, 
            min_rows=min_rows, 
            required_column_names=required_cols,
        )
        
        step["is_valid"] = is_valid
        step["validation_errors"] = errors
        
        if is_valid:
            step["status"] = "success"
            df = pd.read_excel(self.excel_path)
            step["row_count"] = len(df)
            step["column_count"] = len(df.columns)
            step["new_columns"] = sorted(list(set(df.columns) - self.original_column_names))
            logger.info("✅ Validation passed: %d rows, %d columns", len(df), len(df.columns))
            if step["new_columns"]:
                logger.info("   Added %d new columns", len(step["new_columns"]))
        else:
            step["status"] = "error"
            for err in errors:
                logger.error("Validation error: %s", err)
            self.run_log["steps"].append(step)
            raise ValueError(f"Validation failed: {errors}")
        
        self.run_log["steps"].append(step)
    
    def _step_pipeline(self) -> None:
        """Run the pipeline script."""
        step: Dict[str, Any] = {"step": "pipeline", "status": "pending"}
        
        pipeline_script = SCRIPT_DIR / "llmhive_modeldb_pipeline.py"
        
        if not pipeline_script.exists():
            step["status"] = "error"
            step["error"] = f"Pipeline script not found: {pipeline_script}"
            self.run_log["steps"].append(step)
            raise FileNotFoundError(f"Pipeline script not found: {pipeline_script}")
        
        args = [
            "--excel", str(self.excel_path),
            "--archive-dir", str(self.archive_dir),
        ]
        
        if self.dry_run:
            args.append("--dry-run")
        
        returncode, stdout, stderr = run_script(pipeline_script, args)
        
        step["returncode"] = returncode
        if stdout:
            step["stdout_tail"] = stdout[-1000:]
        if stderr:
            step["stderr_tail"] = stderr[-1000:]
        
        if returncode != 0:
            step["status"] = "error"
            logger.error("Pipeline script failed:\n%s", stderr or stdout)
            self.run_log["steps"].append(step)
            raise RuntimeError(f"Pipeline script failed with code {returncode}")
        
        step["status"] = "success"
        self.run_log["steps"].append(step)
        logger.info("Pipeline step completed")
    
    def _step_coverage_report(self) -> None:
        """Generate coverage report after successful pipeline run."""
        step: Dict[str, Any] = {"step": "coverage_report", "status": "pending"}
        
        coverage_script = SCRIPT_DIR / "modeldb_coverage_report.py"
        
        if not coverage_script.exists():
            step["status"] = "skipped"
            step["reason"] = "Coverage report script not found"
            self.run_log["steps"].append(step)
            logger.info("[SKIP] Coverage report script not found")
            return
        
        if self.dry_run:
            # In dry-run mode, run with --dry-run flag to show what would be reported
            logger.info("[DRY RUN] Would generate coverage report")
            step["status"] = "skipped"
            step["reason"] = "dry run"
            self.run_log["steps"].append(step)
            return
        
        try:
            args = [
                "--excel", str(self.excel_path),
                "--output-dir", str(self.archive_dir),
                "--print-summary",
            ]
            
            returncode, stdout, stderr = run_script(coverage_script, args)
            
            step["returncode"] = returncode
            if stdout:
                step["stdout_tail"] = stdout[-2000:]
                # Print summary to console
                print("\n" + stdout)
            
            if returncode != 0:
                step["status"] = "warning"
                step["warning"] = "Coverage report generation had issues"
                logger.warning("Coverage report had issues but continuing")
            else:
                step["status"] = "success"
                logger.info("Coverage report generated successfully")
            
        except Exception as e:
            step["status"] = "warning"
            step["error"] = str(e)
            logger.warning("Coverage report failed: %s", e)
            # Don't fail the entire run for coverage report issues
        
        self.run_log["steps"].append(step)
    
    def _write_run_log(self) -> None:
        """Write the run log to archive directory."""
        if self.dry_run:
            logger.info("[DRY RUN] Would write run log")
            return
        
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
            log_path = self.archive_dir / f"refresh_runlog_{timestamp}.json"
            
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(self.run_log, f, indent=2, default=str)
            
            logger.info("Run log written: %s", log_path)
        except Exception as e:
            logger.warning("Failed to write run log: %s", e)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="LLMHive ModelDB Refresh - One-command pipeline runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_modeldb_refresh.py --doctor    # Check environment first
    python run_modeldb_refresh.py --dry-run   # Validate without changes
    python run_modeldb_refresh.py             # Full run
    python run_modeldb_refresh.py --skip-update
    python run_modeldb_refresh.py --skip-enrichment
    python run_modeldb_refresh.py --evals-enabled false
    python run_modeldb_refresh.py --telemetry-enabled false
    python run_modeldb_refresh.py --excel custom/path/models.xlsx
        """,
    )
    
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run diagnostics and check environment (then exit)",
    )
    parser.add_argument(
        "--excel",
        type=Path,
        help=f"Path to Excel file (default: {DEFAULT_EXCEL.name})",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help=f"Archive directory (default: {DEFAULT_ARCHIVE_DIR})",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help=f"Cache directory (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making changes",
    )
    parser.add_argument(
        "--skip-update",
        action="store_true",
        help="Skip OpenRouter update step",
    )
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip enrichment layer (rankings, benchmarks, evals, telemetry)",
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip Firestore/Pinecone pipeline step",
    )
    parser.add_argument(
        "--evals-enabled",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Enable eval harness (costs API credits, default: true)",
    )
    parser.add_argument(
        "--telemetry-enabled",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Enable telemetry probes (costs API credits, default: true)",
    )
    parser.add_argument(
        "--evals-max-models",
        type=int,
        default=0,
        help="Limit number of models for evals (0 = no limit)",
    )
    parser.add_argument(
        "--evals-ttl-days",
        type=int,
        default=30,
        help="Time-to-live in days for eval metrics (default: 30)",
    )
    parser.add_argument(
        "--evals-seed",
        type=str,
        default=None,
        help="Seed for eval cohort selection (default: ISO week)",
    )
    parser.add_argument(
        "--evals-always-include-top",
        type=int,
        default=10,
        help="Always include top N ranked models in eval cohort (default: 10)",
    )
    parser.add_argument(
        "--telemetry-max-models",
        type=int,
        default=0,
        help="Limit number of models for telemetry (0 = no limit)",
    )
    parser.add_argument(
        "--telemetry-trials",
        type=int,
        default=3,
        help="Number of telemetry trials per model (default: 3)",
    )
    parser.add_argument(
        "--telemetry-ttl-days",
        type=int,
        default=14,
        help="Time-to-live in days for telemetry metrics (default: 14)",
    )
    parser.add_argument(
        "--telemetry-seed",
        type=str,
        default=None,
        help="Seed for telemetry cohort selection (default: ISO week)",
    )
    parser.add_argument(
        "--telemetry-always-include-top",
        type=int,
        default=10,
        help="Always include top N ranked models in telemetry cohort (default: 10)",
    )
    parser.add_argument(
        "--skip-expensive",
        action="store_true",
        help="Skip expensive models in evals",
    )
    parser.add_argument(
        "--allow-row-decrease",
        action="store_true",
        help="Allow row count to decrease (normally fails as safety)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Doctor mode - run diagnostics and exit
    if args.doctor:
        sys.exit(run_doctor())
    
    # Load .env automatically
    env_loaded, env_message = load_dotenv_safely()
    if env_loaded:
        logger.info(env_message)
    else:
        if not args.dry_run:
            # For real runs, .env is required
            logger.warning(env_message)
    
    # Check required environment variables for non-dry runs
    if not args.dry_run:
        env_ok, env_issues = check_required_env_vars(
            skip_update=args.skip_update,
            skip_pipeline=args.skip_pipeline,
            dry_run=args.dry_run,
        )
        
        if not env_ok and not ENV_FILE.exists():
            logger.error("")
            logger.error("=" * 70)
            logger.error("❌ MISSING CONFIGURATION")
            logger.error("=" * 70)
            logger.error("")
            logger.error("The .env file is required for real runs.")
            logger.error("")
            logger.error("To fix, run:")
            if ENV_EXAMPLE_FILE.exists():
                logger.error(f"  cp {ENV_EXAMPLE_FILE} {ENV_FILE}")
            else:
                logger.error(f"  Create {ENV_FILE} with required secrets")
            logger.error("")
            logger.error("Then edit the file and fill in your API keys.")
            logger.error("")
            logger.error("Alternatively, run with --dry-run to validate without secrets:")
            logger.error("  python run_modeldb_refresh.py --dry-run")
            logger.error("")
            sys.exit(1)
        
        if not env_ok:
            logger.warning("")
            logger.warning("Missing environment variables:")
            for issue in env_issues:
                logger.warning(issue)
            logger.warning("")
            logger.warning("Some features may not work. Run --doctor for full diagnostics.")
    
    # Run
    runner = ModelDBRefreshRunner(
        excel_path=args.excel,
        archive_dir=args.archive_dir,
        cache_dir=args.cache_dir,
        dry_run=args.dry_run,
        skip_update=args.skip_update,
        skip_enrichment=args.skip_enrichment,
        skip_pipeline=args.skip_pipeline,
        allow_row_decrease=args.allow_row_decrease,
        evals_enabled=args.evals_enabled.lower() == "true",
        telemetry_enabled=args.telemetry_enabled.lower() == "true",
        evals_max_models=args.evals_max_models,
        evals_ttl_days=args.evals_ttl_days,
        evals_seed=args.evals_seed,
        evals_always_include_top=args.evals_always_include_top,
        telemetry_max_models=args.telemetry_max_models,
        telemetry_trials=args.telemetry_trials,
        telemetry_ttl_days=args.telemetry_ttl_days,
        telemetry_seed=args.telemetry_seed,
        telemetry_always_include_top=args.telemetry_always_include_top,
        skip_expensive=args.skip_expensive,
    )
    
    result = runner.run()
    
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
