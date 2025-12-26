#!/usr/bin/env python3
"""
LLMHive ModelDB Enrichment Orchestrator

Orchestrates all enrichers to add rankings, benchmarks, language skills,
and telemetry to the model catalog.

Usage:
    python llmhive_modeldb_enrich.py --excel path/to/file.xlsx
    python llmhive_modeldb_enrich.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("modeldb_enrich")


def load_dotenv_if_available() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_path = SCRIPT_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment from %s", env_path)
    except ImportError:
        pass


def load_schema_baseline(baseline_path: Path) -> Dict[str, Any]:
    """Load schema baseline for validation."""
    if not baseline_path.exists():
        logger.warning("No schema baseline found at %s", baseline_path)
        return {}
    
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_columns_superset(
    df: pd.DataFrame,
    required_columns: Set[str],
    context: str = "validation",
) -> List[str]:
    """
    Validate that df contains all required columns.
    
    Returns list of missing columns (empty if valid).
    """
    current_columns = set(df.columns)
    missing = required_columns - current_columns
    
    if missing:
        logger.error(
            "[%s] Missing %d required columns: %s",
            context, len(missing), sorted(missing)
        )
    
    return list(missing)


class EnrichmentOrchestrator:
    """Orchestrates all enrichers."""
    
    def __init__(
        self,
        excel_path: Path,
        output_path: Optional[Path] = None,
        dry_run: bool = False,
        evals_enabled: bool = True,
        telemetry_enabled: bool = True,
        evals_max_models: int = 0,
        telemetry_trials: int = 3,
        telemetry_max_models: int = 0,
        skip_expensive: bool = False,
    ):
        self.excel_path = excel_path
        self.output_path = output_path or excel_path
        self.dry_run = dry_run
        self.evals_enabled = evals_enabled
        self.telemetry_enabled = telemetry_enabled
        self.evals_max_models = evals_max_models
        self.telemetry_trials = telemetry_trials
        self.telemetry_max_models = telemetry_max_models
        self.skip_expensive = skip_expensive
        
        self.baseline_path = SCRIPT_DIR / "schema_baseline_columns.json"
        self.archives_dir = SCRIPT_DIR / "archives"
        self.archives_dir.mkdir(exist_ok=True)
        
        self._results: List[Dict[str, Any]] = []
    
    def load_excel(self) -> pd.DataFrame:
        """Load the canonical Excel file."""
        logger.info("Loading Excel: %s", self.excel_path)
        df = pd.read_excel(self.excel_path)
        logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
        return df
    
    def save_excel(self, df: pd.DataFrame) -> None:
        """Save the enriched Excel file."""
        if self.dry_run:
            logger.info("[DRY RUN] Would save to %s", self.output_path)
            return
        
        logger.info("Saving Excel: %s (%d rows, %d columns)", 
                   self.output_path, len(df), len(df.columns))
        df.to_excel(self.output_path, index=False)
    
    def run(self) -> Dict[str, Any]:
        """Run all enrichers and return summary."""
        
        # Load data
        df = self.load_excel()
        original_columns = set(df.columns)
        original_row_count = len(df)
        
        # Note: We do NOT validate baseline columns here.
        # Enrichment ADDS columns, it doesn't require them.
        # The runner script validates column superset on output.
        
        # Import and run enrichers
        enrichers_run = []
        
        # 1. OpenRouter Rankings
        try:
            from enrichers.openrouter_rankings import OpenRouterRankingsEnricher
            enricher = OpenRouterRankingsEnricher(dry_run=self.dry_run)
            df, result = enricher.enrich(df)
            self._results.append(result.to_dict())
            enrichers_run.append("openrouter_rankings")
            logger.info("OpenRouter Rankings: %s", "✓" if result.success else "✗")
        except Exception as e:
            logger.error("OpenRouter Rankings failed: %s", e)
        
        # 2. LMSYS Arena
        try:
            from enrichers.lmsys_arena import LMSYSArenaEnricher
            enricher = LMSYSArenaEnricher(dry_run=self.dry_run)
            df, result = enricher.enrich(df)
            self._results.append(result.to_dict())
            enrichers_run.append("lmsys_arena")
            logger.info("LMSYS Arena: %s", "✓" if result.success else "✗")
        except Exception as e:
            logger.warning("LMSYS Arena failed: %s", e)
        
        # 3. HuggingFace Leaderboard
        try:
            from enrichers.hf_open_llm_leaderboard import HFLeaderboardEnricher
            enricher = HFLeaderboardEnricher(dry_run=self.dry_run)
            df, result = enricher.enrich(df)
            self._results.append(result.to_dict())
            enrichers_run.append("hf_open_llm_leaderboard")
            logger.info("HF Leaderboard: %s", "✓" if result.success else "✗")
        except Exception as e:
            logger.warning("HF Leaderboard failed: %s", e)
        
        # 4. Provider Docs
        try:
            from enrichers.provider_docs_extract import ProviderDocsEnricher
            enricher = ProviderDocsEnricher(dry_run=self.dry_run)
            df, result = enricher.enrich(df)
            self._results.append(result.to_dict())
            enrichers_run.append("provider_docs")
            logger.info("Provider Docs: %s", "✓" if result.success else "✗")
        except Exception as e:
            logger.warning("Provider Docs failed: %s", e)
        
        # 5. Derived Rankings (always run - no external API)
        try:
            from enrichers.derived_rankings import DerivedRankingsEnricher
            enricher = DerivedRankingsEnricher(dry_run=self.dry_run)
            df, result = enricher.enrich(df)
            self._results.append(result.to_dict())
            enrichers_run.append("derived_rankings")
            logger.info("Derived Rankings: %s", "✓" if result.success else "✗")
        except Exception as e:
            logger.warning("Derived Rankings failed: %s", e)
        
        # 6. Eval Harness (optional, costs money)
        if self.evals_enabled and os.getenv("OPENROUTER_API_KEY"):
            try:
                from enrichers.eval_harness import EvalHarnessEnricher
                enricher = EvalHarnessEnricher(
                    dry_run=self.dry_run,
                    max_models=self.evals_max_models,
                    skip_expensive=self.skip_expensive,
                )
                df, result = enricher.enrich(df)
                self._results.append(result.to_dict())
                enrichers_run.append("eval_harness")
                logger.info("Eval Harness: %s", "✓" if result.success else "✗")
            except Exception as e:
                logger.warning("Eval Harness failed: %s", e)
        else:
            logger.info("Eval Harness: skipped (disabled or no API key)")
        
        # 7. Telemetry Probe (optional, costs money)
        if self.telemetry_enabled and os.getenv("OPENROUTER_API_KEY"):
            try:
                from enrichers.telemetry_probe import TelemetryProbeEnricher
                enricher = TelemetryProbeEnricher(
                    dry_run=self.dry_run,
                    trials=self.telemetry_trials,
                    max_models=self.telemetry_max_models,
                )
                df, result = enricher.enrich(df)
                self._results.append(result.to_dict())
                enrichers_run.append("telemetry_probe")
                logger.info("Telemetry Probe: %s", "✓" if result.success else "✗")
            except Exception as e:
                logger.warning("Telemetry Probe failed: %s", e)
        else:
            logger.info("Telemetry Probe: skipped (disabled or no API key)")
        
        # Validate output
        new_columns = set(df.columns)
        new_row_count = len(df)
        
        # Check no columns dropped
        missing_original = original_columns - new_columns
        if missing_original:
            raise ValueError(f"Enrichment dropped columns: {missing_original}")
        
        # Check no rows dropped
        if new_row_count < original_row_count:
            raise ValueError(
                f"Enrichment dropped rows: {new_row_count} < {original_row_count}"
            )
        
        # Save output
        self.save_excel(df)
        
        # Write run log
        run_log = self._generate_run_log(
            original_columns=list(original_columns),
            new_columns=list(new_columns),
            original_row_count=original_row_count,
            new_row_count=new_row_count,
            enrichers_run=enrichers_run,
        )
        
        self._save_run_log(run_log)
        
        return run_log
    
    def _generate_run_log(
        self,
        original_columns: List[str],
        new_columns: List[str],
        original_row_count: int,
        new_row_count: int,
        enrichers_run: List[str],
    ) -> Dict[str, Any]:
        """Generate a run log."""
        now = datetime.now(timezone.utc)
        
        return {
            "run_id": now.strftime("%Y%m%dT%H%M%SZ"),
            "timestamp": now.isoformat(),
            "dry_run": self.dry_run,
            "excel_path": str(self.excel_path),
            "output_path": str(self.output_path),
            "original_columns": len(original_columns),
            "new_columns": len(new_columns),
            "columns_added": sorted(set(new_columns) - set(original_columns)),
            "original_row_count": original_row_count,
            "new_row_count": new_row_count,
            "enrichers_run": enrichers_run,
            "enricher_results": self._results,
            "config": {
                "evals_enabled": self.evals_enabled,
                "telemetry_enabled": self.telemetry_enabled,
                "evals_max_models": self.evals_max_models,
                "telemetry_trials": self.telemetry_trials,
                "telemetry_max_models": self.telemetry_max_models,
                "skip_expensive": self.skip_expensive,
            },
        }
    
    def _save_run_log(self, run_log: Dict[str, Any]) -> None:
        """Save run log to archives."""
        if self.dry_run:
            logger.info("[DRY RUN] Would save run log")
            return
        
        log_path = self.archives_dir / f"enrich_runlog_{run_log['run_id']}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, indent=2, default=str)
        
        logger.info("Saved run log: %s", log_path)


def main():
    """Main entry point."""
    load_dotenv_if_available()
    
    parser = argparse.ArgumentParser(
        description="LLMHive ModelDB Enrichment Orchestrator"
    )
    parser.add_argument(
        "--excel",
        type=str,
        default=str(SCRIPT_DIR / "LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx"),
        help="Path to the canonical Excel file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (defaults to input path, in-place update)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't make any changes, just show what would happen",
    )
    parser.add_argument(
        "--evals-enabled",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Enable eval harness (costs API credits)",
    )
    parser.add_argument(
        "--telemetry-enabled",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Enable telemetry probes (costs API credits)",
    )
    parser.add_argument(
        "--evals-max-models",
        type=int,
        default=0,
        help="Limit number of models to evaluate (0 = no limit)",
    )
    parser.add_argument(
        "--telemetry-trials",
        type=int,
        default=3,
        help="Number of telemetry trials per model",
    )
    parser.add_argument(
        "--telemetry-max-models",
        type=int,
        default=0,
        help="Limit number of models to probe (0 = no limit)",
    )
    parser.add_argument(
        "--skip-expensive",
        action="store_true",
        help="Skip expensive models in evals",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    excel_path = Path(args.excel)
    if not excel_path.exists():
        logger.error("Excel file not found: %s", excel_path)
        sys.exit(1)
    
    output_path = Path(args.output) if args.output else None
    
    orchestrator = EnrichmentOrchestrator(
        excel_path=excel_path,
        output_path=output_path,
        dry_run=args.dry_run,
        evals_enabled=args.evals_enabled.lower() == "true",
        telemetry_enabled=args.telemetry_enabled.lower() == "true",
        evals_max_models=args.evals_max_models,
        telemetry_trials=args.telemetry_trials,
        telemetry_max_models=args.telemetry_max_models,
        skip_expensive=args.skip_expensive,
    )
    
    try:
        run_log = orchestrator.run()
        
        # Print summary
        print("\n" + "=" * 60)
        print("ENRICHMENT COMPLETE")
        print("=" * 60)
        print(f"Rows: {run_log['original_row_count']} → {run_log['new_row_count']}")
        print(f"Columns: {run_log['original_columns']} → {run_log['new_columns']}")
        print(f"Columns added: {len(run_log['columns_added'])}")
        print(f"Enrichers run: {', '.join(run_log['enrichers_run'])}")
        
        if run_log['columns_added']:
            print("\nNew columns:")
            for col in sorted(run_log['columns_added'])[:20]:
                print(f"  + {col}")
            if len(run_log['columns_added']) > 20:
                print(f"  ... and {len(run_log['columns_added']) - 20} more")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error("Enrichment failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

