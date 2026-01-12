"""Centralized Pinecone Registry for LLMHive.

This module provides a single source of truth for all Pinecone connections.
It reads PINECONE_API_KEY and PINECONE_HOST_* environment variables and
provides index handles via get_index().

IMPORTANT: This module uses HOST-based connections which is required for
indexes in different regions. The legacy name-based fallback is only
available when REQUIRE_PINECONE_HOSTS=false (development mode).

REGION ALIGNMENT:
All LLMHive Pinecone indexes should be in the same region (us-east-1 AWS).
If indexes are in different regions, use HOST-based connections to ensure
proper routing. The PINECONE_ENVIRONMENT variable is deprecated in favor
of per-index HOST URLs.

Environment Variables Required:
- PINECONE_API_KEY: API key for authentication
- PINECONE_HOST_ORCHESTRATOR_KB: Host URL for orchestrator-kb index
- PINECONE_HOST_MODEL_KNOWLEDGE: Host URL for model-knowledge index
- PINECONE_HOST_MEMORY: Host URL for memory index
- PINECONE_HOST_RLHF_FEEDBACK: Host URL for rlhf-feedback index
- PINECONE_HOST_AGENTIC_QUICKSTART_TEST: Host URL for agentic quickstart (optional)

Optional:
- REQUIRE_PINECONE_HOSTS: If "true", fail if host vars missing (default: false)
- PINECONE_EXPECTED_REGION: Expected region for validation (default: us-east-1)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import Pinecone
try:
    from pinecone import Pinecone
    PINECONE_SDK_AVAILABLE = True
except ImportError:
    PINECONE_SDK_AVAILABLE = False
    Pinecone = None  # type: ignore
    logger.warning("Pinecone SDK not installed. Run: pip install pinecone")


class IndexKind(str, Enum):
    """Known Pinecone index types in LLMHive."""
    ORCHESTRATOR_KB = "orchestrator_kb"
    MODEL_KNOWLEDGE = "model_knowledge"
    MEMORY = "memory"
    RLHF_FEEDBACK = "rlhf_feedback"
    AGENTIC_TEST = "agentic_test"
    ANSWER_CACHE = "answer_cache"  # Uses ORCHESTRATOR_KB with different namespace


@dataclass
class IndexConfig:
    """Configuration for a Pinecone index."""
    host_env_var: str
    index_name: str  # Fallback name for dev mode
    description: str
    required: bool = True  # Whether this index is required for operation


# Expected region for all indexes (for validation/logging)
EXPECTED_REGION = os.getenv("PINECONE_EXPECTED_REGION", "us-east-1")

# Index configurations - maps IndexKind to its config
INDEX_CONFIGS: Dict[IndexKind, IndexConfig] = {
    IndexKind.ORCHESTRATOR_KB: IndexConfig(
        host_env_var="PINECONE_HOST_ORCHESTRATOR_KB",
        index_name="llmhive-orchestrator-kb",
        description="Orchestrator knowledge base for RAG",
        required=True,
    ),
    IndexKind.MODEL_KNOWLEDGE: IndexConfig(
        host_env_var="PINECONE_HOST_MODEL_KNOWLEDGE",
        index_name="llmhive-model-knowledge",
        description="Model intelligence and rankings",
        required=True,
    ),
    IndexKind.MEMORY: IndexConfig(
        host_env_var="PINECONE_HOST_MEMORY",
        index_name="llmhive-memory",
        description="Persistent memory across sessions",
        required=True,
    ),
    IndexKind.RLHF_FEEDBACK: IndexConfig(
        host_env_var="PINECONE_HOST_RLHF_FEEDBACK",
        index_name="llmhive-rlhf-feedback",
        description="RLHF feedback storage",
        required=True,
    ),
    IndexKind.AGENTIC_TEST: IndexConfig(
        host_env_var="PINECONE_HOST_AGENTIC_QUICKSTART_TEST",
        index_name="agentic-quickstart-test",
        description="Agentic quickstart test index",
        required=False,  # Optional index
    ),
    # ANSWER_CACHE reuses ORCHESTRATOR_KB with a different namespace
    IndexKind.ANSWER_CACHE: IndexConfig(
        host_env_var="PINECONE_HOST_ORCHESTRATOR_KB",
        index_name="llmhive-orchestrator-kb",
        description="Answer cache (shares orchestrator-kb index)",
        required=True,
    ),
}


def extract_region_from_host(host: str) -> Optional[str]:
    """Extract the region from a Pinecone host URL.
    
    Host format examples:
    - Legacy: llmhive-memory-abc123.svc.us-east-1.pinecone.io
    - Legacy: index-name.svc.us-central1-gcp.pinecone.io
    - Serverless: index-name-aped-4627-b74a.svc.aped-4627-b74a.pinecone.io
    
    Note: Serverless URLs use project IDs (aped-xxxx-xxxx) instead of regions.
    The actual region is determined at index creation time.
    
    Returns:
        Region string, "serverless" for serverless URLs, or None if not parseable
    """
    if not host:
        return None
    try:
        # Remove protocol if present
        host = host.replace("https://", "").replace("http://", "")
        # Format: index-id.svc.REGION_OR_PROJECT.pinecone.io
        parts = host.split(".")
        if len(parts) >= 4 and parts[1] == "svc":
            region_or_project = parts[2]
            # Serverless project IDs match pattern: aped-xxxx-xxxx or similar
            # They are NOT regions - they're project identifiers
            if _is_serverless_project_id(region_or_project):
                return "serverless"
            return region_or_project
    except Exception:
        pass
    return None


def _is_serverless_project_id(identifier: str) -> bool:
    """Check if an identifier is a Pinecone serverless project ID.
    
    Serverless project IDs have patterns like:
    - aped-xxxx-xxxx (e.g., aped-4627-b74a)
    - Various alphanumeric patterns that don't match known region formats
    
    Known region formats:
    - us-east-1, us-west-2 (AWS)
    - us-central1-gcp, europe-west1-gcp (GCP)
    - eastus-azure (Azure)
    """
    if not identifier:
        return False
    
    # Known region prefixes
    region_prefixes = (
        "us-", "eu-", "ap-", "sa-", "ca-", "me-", "af-",  # AWS-style
        "asia-", "europe-", "australia-", "northamerica-", "southamerica-",  # GCP-style
        "eastus", "westus", "centralus", "northeurope", "westeurope",  # Azure-style
    )
    
    # Check if it looks like a known region
    if any(identifier.startswith(prefix) for prefix in region_prefixes):
        return False
    
    # Serverless project IDs typically:
    # - Start with 'aped-', 'gcp-', 'aws-' followed by hex-like segments
    # - Don't match any known region pattern
    # - Often have format: xxxx-xxxx-xxxx
    serverless_patterns = ("aped-", "gcp-", "aws-", "azure-")
    if any(identifier.startswith(prefix) for prefix in serverless_patterns):
        return True
    
    # If it has multiple dashes and doesn't look like a region, assume serverless
    dash_count = identifier.count("-")
    if dash_count >= 2 and not any(identifier.startswith(p) for p in region_prefixes):
        return True
    
    return False


class PineconeRegistryError(Exception):
    """Raised when Pinecone registry encounters an error."""
    pass


class PineconeRegistry:
    """Centralized Pinecone connection registry.
    
    Provides a single Pinecone client and manages index connections.
    Uses HOST-based connections for production (supports mixed regions).
    
    Usage:
        registry = get_pinecone_registry()
        index = registry.get_index(IndexKind.ORCHESTRATOR_KB)
        if index:
            results = index.query(...)
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._client: Optional[Pinecone] = None
        self._indexes: Dict[IndexKind, Any] = {}
        self._initialized = False
        self._init_errors: Dict[IndexKind, str] = {}
        
        # Configuration
        self._api_key = os.getenv("PINECONE_API_KEY")
        self._require_hosts = os.getenv("REQUIRE_PINECONE_HOSTS", "false").lower() == "true"
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize the Pinecone client."""
        if not PINECONE_SDK_AVAILABLE:
            logger.error("Pinecone SDK not available")
            return
        
        if not self._api_key:
            logger.warning("PINECONE_API_KEY not set - Pinecone features disabled")
            return
        
        try:
            self._client = Pinecone(api_key=self._api_key)
            self._initialized = True
            logger.info("Pinecone registry initialized")
        except Exception as e:
            logger.error("Failed to initialize Pinecone client: %s", e)
            self._initialized = False
    
    @property
    def is_available(self) -> bool:
        """Check if Pinecone is available."""
        return self._initialized and self._client is not None
    
    def get_index(self, kind: IndexKind) -> Optional[Any]:
        """Get a Pinecone index handle.
        
        Args:
            kind: The type of index to get
            
        Returns:
            Pinecone Index object or None if unavailable
            
        Raises:
            PineconeRegistryError: If REQUIRE_PINECONE_HOSTS=true and host is missing
        """
        if not self.is_available:
            return None
        
        # Return cached index if available
        if kind in self._indexes:
            return self._indexes[kind]
        
        config = INDEX_CONFIGS.get(kind)
        if not config:
            logger.error("Unknown index kind: %s", kind)
            return None
        
        # Try host-based connection first (required for production)
        host = os.getenv(config.host_env_var)
        
        if host:
            try:
                # Connect by host (supports any region)
                index = self._client.Index(host=host)
                self._indexes[kind] = index
                logger.info(
                    "Connected to Pinecone index %s via host",
                    kind.value,
                )
                return index
            except Exception as e:
                error_msg = f"Failed to connect to {kind.value} via host: {e}"
                logger.error(error_msg)
                self._init_errors[kind] = error_msg
                return None
        
        # Host not set - check if we should fail or fallback
        if self._require_hosts:
            error_msg = (
                f"REQUIRE_PINECONE_HOSTS=true but {config.host_env_var} is not set. "
                f"Cannot connect to {kind.value} index."
            )
            logger.error(error_msg)
            self._init_errors[kind] = error_msg
            raise PineconeRegistryError(error_msg)
        
        # Development fallback: try name-based connection
        logger.warning(
            "%s not set, falling back to name-based connection for %s (dev mode only)",
            config.host_env_var,
            kind.value,
        )
        
        try:
            # Check if index exists
            if not self._client.has_index(config.index_name):
                error_msg = f"Index {config.index_name} does not exist"
                logger.warning(error_msg)
                self._init_errors[kind] = error_msg
                return None
            
            index = self._client.Index(name=config.index_name)
            self._indexes[kind] = index
            logger.info(
                "Connected to Pinecone index %s via name (dev fallback)",
                kind.value,
            )
            return index
            
        except Exception as e:
            error_msg = f"Failed to connect to {kind.value} via name: {e}"
            logger.error(error_msg)
            self._init_errors[kind] = error_msg
            return None
    
    def get_index_stats(self, kind: IndexKind) -> Optional[Dict[str, Any]]:
        """Get stats for a specific index.
        
        Returns:
            Dict with index stats or None if unavailable
        """
        index = self.get_index(kind)
        if not index:
            return None
        
        try:
            stats = index.describe_index_stats()
            return dict(stats) if hasattr(stats, '__iter__') else {"raw": str(stats)}
        except Exception as e:
            logger.warning("Failed to get stats for %s: %s", kind.value, e)
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for all indexes.
        
        Returns:
            Dict with per-index status including region detection
        """
        status = {
            "sdk_available": PINECONE_SDK_AVAILABLE,
            "api_key_set": bool(self._api_key),
            "client_initialized": self._initialized,
            "require_hosts": self._require_hosts,
            "expected_region": EXPECTED_REGION,
            "indexes": {},
            "region_warnings": [],
        }
        
        for kind in IndexKind:
            config = INDEX_CONFIGS.get(kind)
            if not config:
                continue
            
            host = os.getenv(config.host_env_var)
            host_set = bool(host)
            index = self._indexes.get(kind)
            
            # Detect region from host URL
            detected_region = extract_region_from_host(host) if host else None
            
            index_status = {
                "host_env_var": config.host_env_var,
                "host_configured": host_set,
                "connected": index is not None,
                "error": self._init_errors.get(kind),
                "required": config.required,
                "detected_region": detected_region,
            }
            
            # Check for region mismatch (skip for serverless - they don't have region in URL)
            if detected_region and detected_region != "serverless" and EXPECTED_REGION and detected_region != EXPECTED_REGION:
                warning = (
                    f"{kind.value} index appears to be in region '{detected_region}' "
                    f"but expected region is '{EXPECTED_REGION}'. "
                    "This may cause connectivity issues."
                )
                index_status["region_warning"] = warning
                status["region_warnings"].append(warning)
            elif detected_region == "serverless":
                # Serverless indexes use project IDs, not regions in URL
                index_status["index_type"] = "serverless"
            
            # Get vector count if connected
            if index:
                try:
                    stats = index.describe_index_stats()
                    index_status["vector_count"] = getattr(stats, 'total_vector_count', 0)
                    index_status["dimension"] = getattr(stats, 'dimension', None)
                except Exception as e:
                    index_status["stats_error"] = str(e)
            
            status["indexes"][kind.value] = index_status
        
        return status
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """Validate Pinecone configuration.
        
        Checks:
        - API key is set
        - All required host env vars are set
        - Regions are consistent (if detectable)
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not self._api_key:
            errors.append("PINECONE_API_KEY is not set")
        
        detected_regions = set()
        
        for kind in IndexKind:
            config = INDEX_CONFIGS.get(kind)
            if not config:
                continue
            
            host = os.getenv(config.host_env_var)
            
            if config.required and not host:
                errors.append(f"{config.host_env_var} is not set (required)")
            
            if host:
                region = extract_region_from_host(host)
                if region:
                    detected_regions.add(region)
        
        # Warn if multiple regions detected
        if len(detected_regions) > 1:
            errors.append(
                f"Multiple regions detected: {detected_regions}. "
                "All indexes should be in the same region for consistency."
            )
        
        return len(errors) == 0, errors
    
    def close(self) -> None:
        """Close all connections."""
        self._indexes.clear()
        self._client = None
        self._initialized = False


# Global singleton
_registry: Optional[PineconeRegistry] = None


def get_pinecone_registry() -> PineconeRegistry:
    """Get the global Pinecone registry instance."""
    global _registry
    if _registry is None:
        _registry = PineconeRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    if _registry:
        _registry.close()
    _registry = None


# Convenience functions
def get_index(kind: IndexKind) -> Optional[Any]:
    """Get a Pinecone index handle."""
    return get_pinecone_registry().get_index(kind)


def is_pinecone_available() -> bool:
    """Check if Pinecone is available."""
    return get_pinecone_registry().is_available

