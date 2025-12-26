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
    python run_modeldb_refresh.py --excel path/to/models.xlsx
    python run_modeldb_refresh.py --dry-run
    python run_modeldb_refresh.py --skip-update  # Only run pipeline, skip OpenRouter fetch

Guardrails:
- If row count decreases: FAIL and restore archive
- If required columns missing: FAIL
- If duplicate slugs detected: FAIL
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
from typing import Optional

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("modeldb_refresh")

# =============================================================================
# Constants
# =============================================================================

# Default paths (relative to this script's directory)
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_EXCEL = SCRIPT_DIR / "LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx"
DEFAULT_ARCHIVE_DIR = SCRIPT_DIR / "archives"
DEFAULT_CACHE_DIR = Path(".cache/llmhive_modeldb")

# Required columns for validation
REQUIRED_COLUMNS = ["openrouter_slug"]


# =============================================================================
# Helpers
# =============================================================================


def archive_file(source: Path, archive_dir: Path) -> Optional[Path]:
    """
    Create a timestamped archive copy of a file.
    
    Returns the archive path, or None if source doesn't exist.
    """
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


def validate_excel(path: Path, min_rows: int = 0) -> tuple[bool, list[str]]:
    """
    Validate an Excel file meets requirements.
    
    Returns (is_valid, list_of_errors)
    """
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
    
    # Check for duplicate slugs
    if "openrouter_slug" in df.columns:
        duplicates = df["openrouter_slug"].dropna().duplicated()
        if duplicates.any():
            dup_count = duplicates.sum()
            dup_examples = df.loc[duplicates, "openrouter_slug"].head(3).tolist()
            errors.append(f"Found {dup_count} duplicate slugs: {dup_examples}")
    
    return len(errors) == 0, errors


def run_script(script_path: Path, args: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """
    Run a Python script as subprocess.
    
    Returns (return_code, stdout, stderr)
    """
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
        
        self.run_log = {
            "started_at": None,
            "completed_at": None,
            "excel_path": str(self.excel_path),
            "dry_run": dry_run,
            "steps": [],
            "success": False,
            "errors": [],
        }
    
    def run(self) -> dict:
        """Execute the full refresh workflow."""
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
        step = {"step": "validate_existing", "status": "pending"}
        
        if not self.excel_path.exists():
            logger.info("No existing Excel file, will create new")
            step["status"] = "skipped"
            step["reason"] = "file not found"
            self.run_log["steps"].append(step)
            return
        
        try:
            df = pd.read_excel(self.excel_path)
            self.original_row_count = len(df)
            logger.info("Existing file has %d rows", self.original_row_count)
            
            step["status"] = "success"
            step["row_count"] = self.original_row_count
            step["column_count"] = len(df.columns)
            
        except Exception as e:
            step["status"] = "error"
            step["error"] = str(e)
            # Don't fail here, file might be corrupted and we want to replace it
            logger.warning("Could not read existing file: %s", e)
        
        self.run_log["steps"].append(step)
    
    def _step_archive(self) -> None:
        """Archive existing file."""
        step = {"step": "archive", "status": "pending"}
        
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
        step = {"step": "update", "status": "pending"}
        
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
        step = {"step": "validate_updated", "status": "pending"}
        
        if self.dry_run:
            logger.info("[DRY RUN] Would validate updated file")
            step["status"] = "skipped"
            step["reason"] = "dry run"
            self.run_log["steps"].append(step)
            return
        
        min_rows = 0 if self.allow_row_decrease else self.original_row_count
        is_valid, errors = validate_excel(self.excel_path, min_rows=min_rows)
        
        step["is_valid"] = is_valid
        step["validation_errors"] = errors
        
        if is_valid:
            step["status"] = "success"
            df = pd.read_excel(self.excel_path)
            step["row_count"] = len(df)
            step["column_count"] = len(df.columns)
            logger.info("Validation passed: %d rows, %d columns", len(df), len(df.columns))
        else:
            step["status"] = "error"
            for err in errors:
                logger.error("Validation error: %s", err)
            self.run_log["steps"].append(step)
            raise ValueError(f"Validation failed: {errors}")
        
        self.run_log["steps"].append(step)
    
    def _step_pipeline(self) -> None:
        """Run the pipeline script."""
        step = {"step": "pipeline", "status": "pending"}
        
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
    python run_modeldb_refresh.py
    python run_modeldb_refresh.py --dry-run
    python run_modeldb_refresh.py --skip-update
    python run_modeldb_refresh.py --excel custom/path/models.xlsx
        """,
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
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load .env if present
    try:
        from dotenv import load_dotenv
        env_path = SCRIPT_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment from %s", env_path)
    except ImportError:
        pass
    
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

