#!/usr/bin/env python3
"""
LLMHive ModelDB Refresh Runner - One-command pipeline execution.

This script orchestrates the complete ModelDB refresh workflow:
1. Archive the current Excel (timestamped backup)
2. Run update/enrichment from OpenRouter
3. Run pipeline to Firestore + Pinecone
4. Validate no data loss
5. Rollback if errors detected

Usage:
    python run_modeldb_refresh.py
    python run_modeldb_refresh.py --doctor          # Check environment
    python run_modeldb_refresh.py --dry-run         # Validate without changes
    python run_modeldb_refresh.py --skip-update     # Only run pipeline
    python run_modeldb_refresh.py --skip-pipeline   # Only update Excel

Guardrails:
- If row count decreases: FAIL and restore archive
- If required columns missing: FAIL
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

# Required columns for validation
REQUIRED_COLUMNS = ["openrouter_slug"]

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
        ("pandas", "Data manipulation"),
        ("openpyxl", "Excel read/write"),
        ("requests", "HTTP client"),
        ("tenacity", "Retry logic"),
        ("dotenv", "Environment loading"),
        ("google.cloud.firestore", "Firestore client"),
        ("pinecone", "Pinecone vector DB"),
    ]
    
    for module_name, desc in deps_to_check:
        try:
            __import__(module_name.replace(".", "_") if "." in module_name else module_name)
            print(f"   ✅ {module_name}: installed")
        except ImportError:
            print(f"   ❌ {module_name}: NOT INSTALLED ({desc})")
            issues.append(f"Missing dependency: {module_name}")
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


def validate_excel(path: Path, min_rows: int = 0, min_columns: int = 0) -> Tuple[bool, List[str]]:
    """Validate an Excel file meets requirements."""
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
    
    # Check column count
    if len(df.columns) < min_columns:
        errors.append(f"Column count decreased: {len(df.columns)} < {min_columns}")
    
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
        skip_pipeline: bool = False,
        allow_row_decrease: bool = False,
    ):
        self.excel_path = excel_path or DEFAULT_EXCEL
        self.archive_dir = archive_dir or DEFAULT_ARCHIVE_DIR
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.dry_run = dry_run
        self.skip_update = skip_update
        self.skip_pipeline = skip_pipeline
        self.allow_row_decrease = allow_row_decrease
        
        self.archive_path: Optional[Path] = None
        self.original_row_count = 0
        self.original_column_count = 0
        
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
        logger.info("Skip Pipeline: %s", self.skip_pipeline)
        logger.info("=" * 70)
        
        try:
            # Step 1: Validate existing file (if exists)
            self._step_validate_existing()
            
            # Step 2: Archive
            self._step_archive()
            
            # Step 3: Run update script (fetch OpenRouter, enrich)
            if not self.skip_update:
                self._step_update()
            else:
                logger.info("[SKIP] Update step skipped")
                self.run_log["steps"].append({"step": "update", "status": "skipped"})
            
            # Step 4: Validate updated file
            self._step_validate_updated()
            
            # Step 5: Run pipeline (Firestore + Pinecone)
            if not self.skip_pipeline:
                self._step_pipeline()
            else:
                logger.info("[SKIP] Pipeline step skipped")
                self.run_log["steps"].append({"step": "pipeline", "status": "skipped"})
            
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
        """Validate existing Excel file."""
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
            self.original_column_count = len(df.columns)
            logger.info("Existing file has %d rows, %d columns", 
                       self.original_row_count, self.original_column_count)
            
            step["status"] = "success"
            step["row_count"] = self.original_row_count
            step["column_count"] = self.original_column_count
            
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
    
    def _step_validate_updated(self) -> None:
        """Validate the updated file."""
        import pandas as pd
        
        step: Dict[str, Any] = {"step": "validate_updated", "status": "pending"}
        
        if self.dry_run:
            logger.info("[DRY RUN] Would validate updated file")
            step["status"] = "skipped"
            step["reason"] = "dry run"
            self.run_log["steps"].append(step)
            return
        
        min_rows = 0 if self.allow_row_decrease else self.original_row_count
        min_cols = self.original_column_count  # Never allow column decrease
        
        is_valid, errors = validate_excel(self.excel_path, min_rows=min_rows, min_columns=min_cols)
        
        step["is_valid"] = is_valid
        step["validation_errors"] = errors
        
        if is_valid:
            step["status"] = "success"
            df = pd.read_excel(self.excel_path)
            step["row_count"] = len(df)
            step["column_count"] = len(df.columns)
            logger.info("✅ Validation passed: %d rows, %d columns", len(df), len(df.columns))
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
        help="Skip OpenRouter update step (only run pipeline)",
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip Firestore/Pinecone pipeline step (only run update)",
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
        skip_pipeline=args.skip_pipeline,
        allow_row_decrease=args.allow_row_decrease,
    )
    
    result = runner.run()
    
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
