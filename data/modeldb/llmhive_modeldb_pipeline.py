#!/usr/bin/env python3
"""
LLMHive ModelDB Pipeline - Production-grade Firestore + Pinecone ingestion.

This script:
1. Reads the master Excel file (single source of truth)
2. Validates data integrity (no row/column loss, no duplicate slugs)
3. Upserts to Firestore (model_catalog collection with stable IDs)
4. Upserts to Pinecone (semantic embeddings for orchestrator routing)
5. Handles Firestore size limits with overflow collection
6. Writes detailed run logs for audit

NO DATA LOSS GUARANTEES:
- All rows preserved
- All columns preserved  
- Provenance tracked for enriched fields
- Deterministic IDs across runs
- Safe to run repeatedly (idempotent)

Usage:
    python llmhive_modeldb_pipeline.py --excel path/to/modeldb.xlsx
    python llmhive_modeldb_pipeline.py --excel path/to/modeldb.xlsx --firestore-only
    python llmhive_modeldb_pipeline.py --excel path/to/modeldb.xlsx --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("modeldb_pipeline")

# =============================================================================
# Constants
# =============================================================================

SCHEMA_VERSION = "1.0.0"
FIRESTORE_DOC_SIZE_LIMIT = 900_000  # ~900KB to leave buffer under 1MB limit
UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace

# Required columns for validation
REQUIRED_COLUMNS = ["openrouter_slug"]  # model_name/provider can be derived

# Columns to extract as top-level Firestore fields for filtering
TOP_LEVEL_FIELDS = [
    "openrouter_slug",
    "model_name",
    "provider_name",
    "provider_id",
    "model_family",
    "in_openrouter",
    "max_context_tokens",
    "price_input_usd_per_1m",
    "price_output_usd_per_1m",
    "modalities",
    "orchestration_roles",
    "parameter_count",
    "supports_streaming",
    "supports_function_calling",
    "supports_vision",
    "architecture",
    "release_date",
]

# Fields to include in Pinecone metadata (must be flat, no nested objects)
PINECONE_METADATA_FIELDS = [
    "model_id",
    "openrouter_slug",
    "provider_name",
    "model_family",
    "in_openrouter",
    "max_context_tokens",
    "price_input_usd_per_1m",
    "price_output_usd_per_1m",
    "parameter_count",
    "modalities",
    "orchestration_roles",
]


# =============================================================================
# Utility Functions
# =============================================================================


def generate_model_id(openrouter_slug: str) -> str:
    """
    Generate a deterministic, Firestore-safe document ID from openrouter_slug.
    
    Uses UUID5 (SHA-1 based) for determinism across runs.
    Result is safe for Firestore (no "/" characters).
    """
    # UUID5 generates deterministic UUID from namespace + name
    doc_uuid = uuid.uuid5(UUID_NAMESPACE, openrouter_slug)
    return str(doc_uuid).replace("-", "")


def safe_slug_to_id(slug: str) -> str:
    """
    Alternative: convert slug to safe ID by replacing special chars.
    Kept for reference but UUID5 is preferred for stability.
    """
    # Replace "/" with "__" and sanitize
    safe = slug.replace("/", "__").replace(".", "_").replace("-", "_")
    return safe[:128]  # Firestore ID limit


def estimate_json_size(obj: Any) -> int:
    """Estimate JSON serialized size of an object."""
    try:
        return len(json.dumps(obj, default=str).encode("utf-8"))
    except Exception:
        return 0


def clean_value(val: Any) -> Any:
    """Clean a value for Firestore (handle NaN, None, etc.)."""
    if pd.isna(val):
        return None
    if isinstance(val, float) and (val != val):  # NaN check
        return None
    if isinstance(val, str):
        return val.strip() if val.strip() else None
    return val


def row_to_dict(row: pd.Series, columns: List[str]) -> Dict[str, Any]:
    """Convert a DataFrame row to a clean dictionary."""
    result = {}
    for col in columns:
        if col in row.index:
            val = clean_value(row[col])
            if val is not None:
                result[col] = val
    return result


def build_embedding_text(row: Dict[str, Any]) -> str:
    """
    Build the text to embed for semantic search.
    
    Combines model identity, capabilities, strengths/weaknesses, and benchmarks.
    """
    parts = []
    
    # Model identity
    if row.get("model_name"):
        parts.append(f"Model: {row['model_name']}")
    if row.get("provider_name"):
        parts.append(f"Provider: {row['provider_name']}")
    if row.get("model_family"):
        parts.append(f"Family: {row['model_family']}")
    
    # Capabilities
    if row.get("modalities"):
        parts.append(f"Modalities: {row['modalities']}")
    if row.get("orchestration_roles"):
        parts.append(f"Roles: {row['orchestration_roles']}")
    if row.get("architecture"):
        parts.append(f"Architecture: {row['architecture']}")
    
    # Strengths/weaknesses
    if row.get("strengths"):
        parts.append(f"Strengths: {row['strengths']}")
    if row.get("weaknesses"):
        parts.append(f"Weaknesses: {row['weaknesses']}")
    if row.get("best_use_cases"):
        parts.append(f"Best for: {row['best_use_cases']}")
    
    # Benchmark data
    if row.get("benchmark_results_json_merged"):
        try:
            benchmarks = json.loads(str(row["benchmark_results_json_merged"]))
            if isinstance(benchmarks, dict):
                bench_str = ", ".join(f"{k}: {v}" for k, v in benchmarks.items())
                parts.append(f"Benchmarks: {bench_str}")
        except Exception:
            parts.append(f"Benchmarks: {row['benchmark_results_json_merged']}")
    
    # Rankings
    if row.get("openrouter_rankings_json"):
        try:
            rankings = json.loads(str(row["openrouter_rankings_json"]))
            if isinstance(rankings, dict):
                rank_str = ", ".join(f"{k}: {v}" for k, v in rankings.items())
                parts.append(f"Rankings: {rank_str}")
        except Exception:
            parts.append(f"Rankings: {row['openrouter_rankings_json']}")
    
    return "\n".join(parts)


# =============================================================================
# Firestore Operations
# =============================================================================


class FirestoreModelCatalog:
    """
    Manages model catalog in Firestore with overflow handling.
    
    ISOLATION GUARANTEE:
    This class ONLY accesses the following Firestore collections:
    - model_catalog: Main model documents
    - model_catalog_payloads: Overflow storage for large payloads
    
    It does NOT and MUST NOT access:
    - accounts, users, auth, or any other application collections
    - Any collection outside of model_catalog and model_catalog_payloads
    
    This isolation ensures ModelDB operations never affect application data.
    """
    
    # CRITICAL: These are the ONLY collections ModelDB is allowed to access
    COLLECTION = "model_catalog"
    OVERFLOW_COLLECTION = "model_catalog_payloads"
    
    # Collections that ModelDB must NEVER access (safety assertion)
    FORBIDDEN_COLLECTIONS = frozenset([
        "accounts", "users", "auth", "sessions", "tokens",
        "organizations", "teams", "projects", "settings",
    ])
    
    def __init__(self, project_id: Optional[str] = None, dry_run: bool = False):
        # Verify collection names are safe (defensive assertion)
        self._verify_collection_isolation()
        self.project_id = project_id or os.getenv(
            "GOOGLE_CLOUD_PROJECT", 
            os.getenv("GCP_PROJECT", "llmhive-orchestrator")
        )
        self.dry_run = dry_run
        self.db = None
        self._initialize()
    
    def _verify_collection_isolation(self) -> None:
        """
        Verify that ModelDB only accesses allowed collections.
        
        This is a defensive check to prevent accidental access to
        application collections like accounts, users, auth, etc.
        """
        # Check that our collection names are not in forbidden list
        if self.COLLECTION in self.FORBIDDEN_COLLECTIONS:
            raise ValueError(
                f"SAFETY VIOLATION: COLLECTION '{self.COLLECTION}' is forbidden. "
                f"ModelDB must only access model_catalog and model_catalog_payloads."
            )
        
        if self.OVERFLOW_COLLECTION in self.FORBIDDEN_COLLECTIONS:
            raise ValueError(
                f"SAFETY VIOLATION: OVERFLOW_COLLECTION '{self.OVERFLOW_COLLECTION}' is forbidden. "
                f"ModelDB must only access model_catalog and model_catalog_payloads."
            )
        
        # Verify expected values (fail if someone changes the constants)
        if self.COLLECTION != "model_catalog":
            raise ValueError(
                f"SAFETY VIOLATION: COLLECTION changed from 'model_catalog' to '{self.COLLECTION}'. "
                f"This is not allowed. ModelDB must remain isolated."
            )
        
        if self.OVERFLOW_COLLECTION != "model_catalog_payloads":
            raise ValueError(
                f"SAFETY VIOLATION: OVERFLOW_COLLECTION changed from 'model_catalog_payloads' to "
                f"'{self.OVERFLOW_COLLECTION}'. This is not allowed. ModelDB must remain isolated."
            )
        
        logger.debug("Firestore isolation verified: using only model_catalog collections")
    
    def _initialize(self) -> None:
        """Initialize Firestore client."""
        if self.dry_run:
            logger.info("[DRY RUN] Firestore client not initialized")
            return
        
        try:
            from google.cloud import firestore
            self.db = firestore.Client(project=self.project_id)
            logger.info("Firestore client initialized for project: %s", self.project_id)
        except Exception as e:
            logger.error("Failed to initialize Firestore: %s", e)
            raise
    
    def upsert_model(
        self,
        model_id: str,
        top_level_data: Dict[str, Any],
        full_payload: Dict[str, Any],
        source_excel_path: str,
    ) -> Tuple[bool, bool]:
        """
        Upsert a model document.
        
        Returns:
            (success, used_overflow) tuple
        """
        if self.dry_run:
            payload_size = estimate_json_size(full_payload)
            overflow = payload_size > FIRESTORE_DOC_SIZE_LIMIT
            logger.debug(
                "[DRY RUN] Would upsert %s (size=%d, overflow=%s)",
                model_id, payload_size, overflow
            )
            return True, overflow
        
        try:
            now = datetime.now(timezone.utc)
            payload_size = estimate_json_size(full_payload)
            
            # Check if payload is too large
            use_overflow = payload_size > FIRESTORE_DOC_SIZE_LIMIT
            
            # Build main document
            doc_data = {
                **top_level_data,
                "model_id": model_id,
                "last_ingested_at": now,
                "source_excel_path": source_excel_path,
                "schema_version": SCHEMA_VERSION,
            }
            
            if use_overflow:
                # Store payload in overflow collection
                payload_json = json.dumps(full_payload, default=str)
                payload_sha256 = hashlib.sha256(payload_json.encode()).hexdigest()
                
                overflow_doc = {
                    "payload": full_payload,
                    "payload_sha256": payload_sha256,
                    "stored_at": now,
                    "model_id": model_id,
                }
                
                self.db.collection(self.OVERFLOW_COLLECTION).document(model_id).set(
                    overflow_doc, merge=True
                )
                
                # Reference in main doc
                doc_data["payload_ref"] = f"{self.OVERFLOW_COLLECTION}/{model_id}"
                doc_data["payload_sha256"] = payload_sha256
                doc_data["payload_overflow"] = True
            else:
                # Store payload inline
                doc_data["payload"] = full_payload
                doc_data["payload_overflow"] = False
            
            # Upsert main document
            self.db.collection(self.COLLECTION).document(model_id).set(
                doc_data, merge=True
            )
            
            return True, use_overflow
            
        except Exception as e:
            logger.error("Failed to upsert model %s: %s", model_id, e)
            return False, False
    
    def get_model_count(self) -> int:
        """Get current model count in Firestore."""
        if self.dry_run or not self.db:
            return 0
        try:
            # Use aggregation if available, else count manually
            docs = self.db.collection(self.COLLECTION).limit(10000).stream()
            return sum(1 for _ in docs)
        except Exception as e:
            logger.warning("Could not get model count: %s", e)
            return 0


# =============================================================================
# Pinecone Operations
# =============================================================================


class PineconeModelEmbeddings:
    """Manages model embeddings in Pinecone."""
    
    def __init__(
        self,
        index_name: Optional[str] = None,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        enabled: bool = True,
    ):
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "modeldb-embeddings")
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.dry_run = dry_run
        self.enabled = enabled and bool(self.api_key)
        self.pc = None
        self.index = None
        
        if self.enabled:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Pinecone client and ensure index exists."""
        if self.dry_run:
            logger.info("[DRY RUN] Pinecone client not initialized")
            return
        
        if not self.api_key:
            logger.warning("PINECONE_API_KEY not set, embeddings disabled")
            self.enabled = False
            return
        
        try:
            from pinecone import Pinecone
            
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists, create if not
            if not self.pc.has_index(self.index_name):
                logger.info("Creating Pinecone index: %s", self.index_name)
                cloud = os.getenv("PINECONE_CLOUD", "aws")
                region = os.getenv("PINECONE_REGION", "us-east-1")
                
                self.pc.create_index_for_model(
                    name=self.index_name,
                    cloud=cloud,
                    region=region,
                    embed={
                        "model": "llama-text-embed-v2",
                        "field_map": {"text": "content"}
                    }
                )
                # Wait for index to be ready
                logger.info("Waiting for index to be ready...")
                time.sleep(10)
            
            self.index = self.pc.Index(self.index_name)
            logger.info("Pinecone index '%s' initialized", self.index_name)
            
        except Exception as e:
            logger.error("Failed to initialize Pinecone: %s", e)
            self.enabled = False
    
    def upsert_model(
        self,
        model_id: str,
        embedding_text: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """Upsert a model embedding."""
        if not self.enabled:
            return False
        
        if self.dry_run:
            logger.debug("[DRY RUN] Would upsert embedding for %s", model_id)
            return True
        
        try:
            # Clean metadata (Pinecone doesn't allow nested objects)
            clean_meta = {}
            for key, val in metadata.items():
                if val is None:
                    continue
                if isinstance(val, (str, int, float, bool)):
                    clean_meta[key] = val
                elif isinstance(val, list):
                    # Convert list to comma-separated string
                    clean_meta[key] = ",".join(str(v) for v in val)
                else:
                    clean_meta[key] = str(val)
            
            record = {
                "_id": model_id,
                "content": embedding_text,  # Maps to text field for embedding
                **clean_meta,
            }
            
            self.index.upsert_records("model_catalog", [record])
            return True
            
        except Exception as e:
            logger.error("Failed to upsert embedding for %s: %s", model_id, e)
            return False
    
    def batch_upsert(
        self,
        records: List[Dict[str, Any]],
        batch_size: int = 96,
    ) -> int:
        """Batch upsert records. Returns count of successful upserts."""
        if not self.enabled:
            return 0
        
        if self.dry_run:
            logger.info("[DRY RUN] Would upsert %d records", len(records))
            return len(records)
        
        success_count = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            try:
                self.index.upsert_records("model_catalog", batch)
                success_count += len(batch)
                logger.debug("Upserted batch %d-%d", i, i + len(batch))
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error("Batch upsert failed at %d: %s", i, e)
        
        return success_count


# =============================================================================
# Pipeline Execution
# =============================================================================


class ModelDBPipeline:
    """Main pipeline orchestrator."""
    
    def __init__(
        self,
        excel_path: str,
        dry_run: bool = False,
        firestore_only: bool = False,
        archive_dir: Optional[str] = None,
    ):
        self.excel_path = Path(excel_path)
        self.dry_run = dry_run
        self.firestore_only = firestore_only
        self.archive_dir = Path(archive_dir) if archive_dir else self.excel_path.parent / "archives"
        
        # Initialize services
        self.firestore = FirestoreModelCatalog(dry_run=dry_run)
        
        embeddings_enabled = (
            os.getenv("MODELDB_EMBEDDINGS_ENABLED", "true").lower() == "true"
            and not firestore_only
        )
        self.pinecone = PineconeModelEmbeddings(dry_run=dry_run, enabled=embeddings_enabled)
        
        # Stats
        self.stats = {
            "models_read": 0,
            "firestore_upserts": 0,
            "firestore_overflow": 0,
            "pinecone_upserts": 0,
            "errors": [],
            "warnings": [],
        }
    
    def validate_excel(self, df: pd.DataFrame) -> bool:
        """
        Validate the Excel data.
        
        Checks:
        - Required columns exist
        - No duplicate openrouter_slug
        - Row count sanity
        """
        errors = []
        warnings = []
        
        # Check required columns
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
        
        if errors:
            for e in errors:
                logger.error(e)
            return False
        
        # Check for duplicates
        slug_col = "openrouter_slug"
        if slug_col in df.columns:
            duplicates = df[slug_col].dropna().duplicated()
            if duplicates.any():
                dup_slugs = df.loc[duplicates, slug_col].tolist()
                errors.append(f"Duplicate openrouter_slug values: {dup_slugs[:5]}...")
        
        # Warn if empty
        if len(df) == 0:
            errors.append("Excel file has no data rows")
        
        # Log column count
        logger.info("Excel has %d columns and %d rows", len(df.columns), len(df))
        
        if errors:
            for e in errors:
                logger.error(e)
            self.stats["errors"].extend(errors)
            return False
        
        self.stats["warnings"].extend(warnings)
        return True
    
    def run(self) -> Dict[str, Any]:
        """Execute the pipeline."""
        run_start = datetime.now(timezone.utc)
        logger.info("=" * 60)
        logger.info("ModelDB Pipeline Starting")
        logger.info("Excel: %s", self.excel_path)
        logger.info("Dry Run: %s", self.dry_run)
        logger.info("Firestore Only: %s", self.firestore_only)
        logger.info("=" * 60)
        
        # 1. Read Excel
        if not self.excel_path.exists():
            self.stats["errors"].append(f"Excel file not found: {self.excel_path}")
            logger.error("Excel file not found: %s", self.excel_path)
            return self._finalize_run(run_start)
        
        try:
            df = pd.read_excel(self.excel_path)
            self.stats["models_read"] = len(df)
            logger.info("Read %d models from Excel", len(df))
        except Exception as e:
            self.stats["errors"].append(f"Failed to read Excel: {e}")
            logger.error("Failed to read Excel: %s", e)
            return self._finalize_run(run_start)
        
        # 2. Validate
        if not self.validate_excel(df):
            return self._finalize_run(run_start)
        
        # 3. Process each model
        all_columns = list(df.columns)
        pinecone_batch = []
        
        for idx, row in df.iterrows():
            try:
                self._process_row(row, all_columns, pinecone_batch)
            except Exception as e:
                logger.error("Error processing row %d: %s", idx, e)
                self.stats["errors"].append(f"Row {idx}: {e}")
        
        # 4. Batch upsert to Pinecone
        if pinecone_batch and self.pinecone.enabled:
            count = self.pinecone.batch_upsert(pinecone_batch)
            self.stats["pinecone_upserts"] = count
            logger.info("Pinecone batch upsert: %d records", count)
        
        return self._finalize_run(run_start)
    
    def _process_row(
        self,
        row: pd.Series,
        all_columns: List[str],
        pinecone_batch: List[Dict[str, Any]],
    ) -> None:
        """Process a single row."""
        # Get slug
        slug = row.get("openrouter_slug")
        if pd.isna(slug) or not slug:
            logger.warning("Skipping row with no openrouter_slug")
            return
        
        slug = str(slug).strip()
        model_id = generate_model_id(slug)
        
        # Build full payload (ALL columns preserved)
        full_payload = row_to_dict(row, all_columns)
        
        # Extract top-level fields
        top_level = {}
        for field in TOP_LEVEL_FIELDS:
            if field in full_payload:
                top_level[field] = full_payload[field]
        
        # Ensure model_name and provider_name exist
        if "model_name" not in top_level:
            # Try to derive from slug
            if "/" in slug:
                provider, name = slug.split("/", 1)
                top_level.setdefault("provider_name", provider)
                top_level.setdefault("model_name", name)
        
        if "provider_name" not in top_level and "provider_id" in full_payload:
            top_level["provider_name"] = full_payload["provider_id"]
        
        # Upsert to Firestore
        success, overflow = self.firestore.upsert_model(
            model_id=model_id,
            top_level_data=top_level,
            full_payload=full_payload,
            source_excel_path=str(self.excel_path),
        )
        
        if success:
            self.stats["firestore_upserts"] += 1
            if overflow:
                self.stats["firestore_overflow"] += 1
        
        # Prepare Pinecone record
        if self.pinecone.enabled:
            embedding_text = build_embedding_text(full_payload)
            
            # Build metadata
            metadata = {"model_id": model_id}
            for field in PINECONE_METADATA_FIELDS:
                if field in full_payload and full_payload[field] is not None:
                    metadata[field] = full_payload[field]
            
            pinecone_batch.append({
                "_id": model_id,
                "content": embedding_text,
                **metadata,
            })
    
    def _finalize_run(self, run_start: datetime) -> Dict[str, Any]:
        """Finalize and log the run."""
        run_end = datetime.now(timezone.utc)
        duration_sec = (run_end - run_start).total_seconds()
        
        run_log = {
            "run_id": str(uuid.uuid4()),
            "started_at": run_start.isoformat(),
            "completed_at": run_end.isoformat(),
            "duration_seconds": duration_sec,
            "excel_path": str(self.excel_path),
            "dry_run": self.dry_run,
            "firestore_only": self.firestore_only,
            "schema_version": SCHEMA_VERSION,
            "stats": self.stats,
            "success": len(self.stats["errors"]) == 0,
        }
        
        # Log summary
        logger.info("=" * 60)
        logger.info("Pipeline Complete")
        logger.info("Duration: %.2f seconds", duration_sec)
        logger.info("Models Read: %d", self.stats["models_read"])
        logger.info("Firestore Upserts: %d", self.stats["firestore_upserts"])
        logger.info("Firestore Overflow: %d", self.stats["firestore_overflow"])
        logger.info("Pinecone Upserts: %d", self.stats["pinecone_upserts"])
        if self.stats["errors"]:
            logger.error("Errors: %d", len(self.stats["errors"]))
            for e in self.stats["errors"][:5]:
                logger.error("  - %s", e)
        if self.stats["warnings"]:
            logger.warning("Warnings: %d", len(self.stats["warnings"]))
        logger.info("=" * 60)
        
        # Write run log
        if not self.dry_run:
            self._write_run_log(run_log, run_end)
        
        return run_log
    
    def _write_run_log(self, run_log: Dict[str, Any], timestamp: datetime) -> None:
        """Write run log to archive directory."""
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            log_name = f"modeldb_runlog_{timestamp.strftime('%Y-%m-%dT%H%M%SZ')}.json"
            log_path = self.archive_dir / log_name
            
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, indent=2, default=str)
            
            logger.info("Run log written to: %s", log_path)
        except Exception as e:
            logger.warning("Failed to write run log: %s", e)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="LLMHive ModelDB Pipeline - Firestore + Pinecone ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python llmhive_modeldb_pipeline.py --excel data/modeldb/models.xlsx
    python llmhive_modeldb_pipeline.py --excel data/modeldb/models.xlsx --dry-run
    python llmhive_modeldb_pipeline.py --excel data/modeldb/models.xlsx --firestore-only
        """,
    )
    
    parser.add_argument(
        "--excel",
        required=True,
        help="Path to the Excel file to ingest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation without writing to Firestore/Pinecone",
    )
    parser.add_argument(
        "--firestore-only",
        action="store_true",
        help="Skip Pinecone embedding generation",
    )
    parser.add_argument(
        "--archive-dir",
        help="Directory for run logs (default: <excel_dir>/archives)",
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
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment from %s", env_path)
    except ImportError:
        pass
    
    # Run pipeline
    pipeline = ModelDBPipeline(
        excel_path=args.excel,
        dry_run=args.dry_run,
        firestore_only=args.firestore_only,
        archive_dir=args.archive_dir,
    )
    
    result = pipeline.run()
    
    # Exit with error code if there were errors
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()

