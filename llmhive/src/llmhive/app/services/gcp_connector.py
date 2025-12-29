"""Google Cloud Platform integration connector for DevOps tool integration.

This module provides access to GCP services like BigQuery and Cloud Logging,
allowing the orchestrator to query data and retrieve logs for context-aware responses.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Google Cloud libraries
try:
    from google.cloud import bigquery
    from google.cloud import logging as cloud_logging
    from google.cloud import storage
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    bigquery = None  # type: ignore
    cloud_logging = None  # type: ignore
    storage = None  # type: ignore
    default = None  # type: ignore
    DefaultCredentialsError = None  # type: ignore
    logger.debug("Google Cloud libraries not available")


@dataclass(slots=True)
class BigQueryResult:
    """Represents the result of a BigQuery query."""

    rows: List[Dict[str, Any]]
    schema: List[Dict[str, str]]
    total_rows: int
    job_id: Optional[str] = None


@dataclass(slots=True)
class CloudLogEntry:
    """Represents a Cloud Logging entry."""

    timestamp: str
    severity: str
    message: str
    resource: Dict[str, Any]
    labels: Dict[str, str]


class GCPConnector:
    """Connector for interacting with Google Cloud Platform services.
    
    Provides operations to:
    - Execute BigQuery SQL queries
    - Retrieve Cloud Logging entries
    - List Cloud Storage buckets (proof of concept)
    
    Authentication:
    - Uses Application Default Credentials (ADC) - the recommended approach
    - On Cloud Run: Automatically uses the attached service account
    - Locally: Uses `gcloud auth application-default login`
    - Fallback: GOOGLE_APPLICATION_CREDENTIALS env var (not recommended)
    
    No service account key file is required!
    """

    def __init__(
        self,
        project_id: str | None = None,
        credentials_path: str | None = None,
    ) -> None:
        """Initialize GCP connector.
        
        Args:
            project_id: GCP project ID. If None, loads from GCP_PROJECT_ID env var.
            credentials_path: Optional path to service account JSON (not recommended).
                             Prefer ADC via gcloud auth or Cloud Run's built-in auth.
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self._enabled = bool(self.project_id) and GCP_AVAILABLE
        
        if not GCP_AVAILABLE:
            logger.debug("GCP connector disabled: Google Cloud libraries not installed")
            self._enabled = False
            return
        
        if not self.project_id:
            logger.debug("GCP connector disabled: GCP_PROJECT_ID not configured")
            self._enabled = False
            return
        
        # Initialize clients
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            
            # Test credentials
            credentials, _ = default()
            if credentials:
                logger.info("GCP connector initialized for project: %s", self.project_id)
            else:
                logger.warning("GCP connector: No credentials found, some operations may fail")
        except DefaultCredentialsError as exc:
            logger.warning("GCP connector: Failed to load credentials: %s", exc)
            self._enabled = False
        except Exception as exc:
            logger.warning("GCP connector: Error initializing: %s", exc)
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if GCP connector is enabled and configured."""
        return self._enabled

    def query_bigquery(
        self, query: str, use_legacy_sql: bool = False, max_results: int = 1000
    ) -> Optional[BigQueryResult]:
        """Execute a BigQuery SQL query.
        
        Args:
            query: SQL query string
            use_legacy_sql: Whether to use legacy SQL syntax. Defaults to False (standard SQL).
            max_results: Maximum number of rows to return. Defaults to 1000.
            
        Returns:
            BigQueryResult object with query results, or None if error.
        """
        if not self.enabled:
            logger.debug("GCP connector disabled, cannot execute BigQuery query")
            return None
        
        if not GCP_AVAILABLE:
            logger.warning("BigQuery not available: Google Cloud libraries not installed")
            return None
        
        try:
            client = bigquery.Client(project=self.project_id)
            
            # Configure job
            job_config = bigquery.QueryJobConfig(use_legacy_sql=use_legacy_sql)
            
            # Execute query
            query_job = client.query(query, job_config=job_config)
            
            # Wait for job to complete
            query_job.result()
            
            # Get results
            rows = []
            schema = []
            
            # Get schema
            for field in query_job.schema:
                schema.append({"name": field.name, "type": field.field_type})
            
            # Fetch rows (limit to max_results)
            for row in query_job.fetch(max_results=max_results):
                row_dict = {}
                for key, value in row.items():
                    # Convert complex types to JSON-serializable format
                    if hasattr(value, "isoformat"):  # datetime
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, (dict, list)):
                        row_dict[key] = json.dumps(value)
                    else:
                        row_dict[key] = value
                rows.append(row_dict)
            
            return BigQueryResult(
                rows=rows,
                schema=schema,
                total_rows=query_job.total_bytes_processed,  # Approximate
                job_id=query_job.job_id,
            )
            
        except Exception as exc:
            logger.error("Error executing BigQuery query: %s", exc, exc_info=True)
            return None

    def get_logs(
        self,
        filter_str: str,
        max_results: int = 100,
        order_by: str = "timestamp desc",
    ) -> List[CloudLogEntry]:
        """Retrieve logs from Cloud Logging.
        
        Args:
            filter_str: Cloud Logging filter string (e.g., "resource.type=cloud_run_revision")
            max_results: Maximum number of log entries to return. Defaults to 100.
            order_by: Ordering for results. Defaults to "timestamp desc".
            
        Returns:
            List of CloudLogEntry objects, or empty list if error.
        """
        if not self.enabled:
            logger.debug("GCP connector disabled, cannot retrieve logs")
            return []
        
        if not GCP_AVAILABLE:
            logger.warning("Cloud Logging not available: Google Cloud libraries not installed")
            return []
        
        try:
            client = cloud_logging.Client(project=self.project_id)
            
            # Build filter
            full_filter = f"{filter_str} AND resource.labels.project_id={self.project_id}"
            
            # Retrieve logs
            entries = client.list_entries(
                filter_=full_filter,
                max_results=max_results,
                order_by=order_by,
            )
            
            log_entries: List[CloudLogEntry] = []
            for entry in entries:
                log_entries.append(
                    CloudLogEntry(
                        timestamp=entry.timestamp.isoformat() if entry.timestamp else "",
                        severity=entry.severity or "INFO",
                        message=entry.payload if isinstance(entry.payload, str) else json.dumps(entry.payload),
                        resource=dict(entry.resource) if entry.resource else {},
                        labels=dict(entry.labels) if entry.labels else {},
                    )
                )
            
            return log_entries
            
        except Exception as exc:
            logger.error("Error retrieving Cloud Logging entries: %s", exc, exc_info=True)
            return []

    def list_buckets(self) -> List[str]:
        """List Cloud Storage buckets in the project.
        
        Returns:
            List of bucket names, or empty list if error.
        """
        if not self.enabled:
            logger.debug("GCP connector disabled, cannot list buckets")
            return []
        
        if not GCP_AVAILABLE:
            logger.warning("Cloud Storage not available: Google Cloud libraries not installed")
            return []
        
        try:
            client = storage.Client(project=self.project_id)
            buckets = client.list_buckets()
            return [bucket.name for bucket in buckets]
            
        except Exception as exc:
            logger.error("Error listing Cloud Storage buckets: %s", exc, exc_info=True)
            return []

