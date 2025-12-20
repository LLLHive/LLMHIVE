"""OpenRouter Model Catalog Sync.

ETL pipeline to sync OpenRouter model catalog:
- Fetches full model list from OpenRouter API
- Enriches with endpoint/provider details
- Upserts to database with change detection
- Tracks lifecycle (added/updated/inactive)

Usage:
    from llmhive.app.openrouter import OpenRouterModelSync
    
    sync = OpenRouterModelSync()
    report = await sync.run()
    print(f"Synced: {report.added} added, {report.updated} updated")
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from .client import OpenRouterClient, OpenRouterConfig
from .models import OpenRouterModel, OpenRouterEndpoint, EndpointStatus

logger = logging.getLogger(__name__)


@dataclass
class SyncReport:
    """Report from a sync operation."""
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Model counts
    models_fetched: int = 0
    models_added: int = 0
    models_updated: int = 0
    models_unchanged: int = 0
    models_marked_inactive: int = 0
    
    # Endpoint counts
    endpoints_fetched: int = 0
    endpoints_added: int = 0
    endpoints_updated: int = 0
    endpoints_marked_inactive: int = 0
    
    # Errors
    model_errors: List[str] = field(default_factory=list)
    endpoint_errors: List[str] = field(default_factory=list)
    
    # Dry run flag
    dry_run: bool = False
    
    @property
    def success(self) -> bool:
        """Check if sync was successful."""
        return len(self.model_errors) == 0
    
    @property
    def duration_seconds(self) -> float:
        """Get sync duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "dry_run": self.dry_run,
            "models": {
                "fetched": self.models_fetched,
                "added": self.models_added,
                "updated": self.models_updated,
                "unchanged": self.models_unchanged,
                "marked_inactive": self.models_marked_inactive,
            },
            "endpoints": {
                "fetched": self.endpoints_fetched,
                "added": self.endpoints_added,
                "updated": self.endpoints_updated,
                "marked_inactive": self.endpoints_marked_inactive,
            },
            "errors": {
                "model_errors": self.model_errors[:10],  # Limit
                "endpoint_errors": self.endpoint_errors[:10],
            },
            "success": self.success,
        }


class OpenRouterModelSync:
    """Syncs OpenRouter model catalog to database.
    
    Features:
    - Idempotent upserts (safe to run multiple times)
    - Change detection via content hash
    - Endpoint enrichment with retry
    - Lifecycle tracking (marks inactive instead of delete)
    - Dry run mode for testing
    
    Usage:
        sync = OpenRouterModelSync(db_session)
        
        # Run full sync
        report = await sync.run()
        
        # Dry run (no database changes)
        report = await sync.run(dry_run=True)
        
        # Skip endpoint enrichment (faster)
        report = await sync.run(enrich_endpoints=False)
    """
    
    def __init__(
        self,
        db_session: Session,
        client: Optional[OpenRouterClient] = None,
        config: Optional[OpenRouterConfig] = None,
    ):
        """Initialize sync.
        
        Args:
            db_session: SQLAlchemy session
            client: OpenRouter client (created if not provided)
            config: Client config (loaded from env if not provided)
        """
        self.db = db_session
        self._client = client
        self._config = config
        self._owns_client = client is None
    
    async def _get_client(self) -> OpenRouterClient:
        """Get or create client."""
        if self._client is None:
            config = self._config or OpenRouterConfig.from_env()
            self._client = OpenRouterClient(config)
        return self._client
    
    async def run(
        self,
        *,
        dry_run: bool = False,
        enrich_endpoints: bool = True,
        endpoint_batch_size: int = 10,
        endpoint_delay_seconds: float = 0.1,
    ) -> SyncReport:
        """Run model catalog sync.
        
        Args:
            dry_run: If True, don't commit changes to database
            enrich_endpoints: If True, fetch endpoint details per model
            endpoint_batch_size: Number of concurrent endpoint fetches
            endpoint_delay_seconds: Delay between endpoint batches
            
        Returns:
            SyncReport with operation summary
        """
        report = SyncReport(
            started_at=datetime.now(timezone.utc),
            dry_run=dry_run,
        )
        
        try:
            client = await self._get_client()
            
            # Step 1: Fetch all models
            logger.info("Fetching OpenRouter model catalog...")
            api_models = await client.list_models(use_cache=False)
            report.models_fetched = len(api_models)
            logger.info("Fetched %d models from OpenRouter API", len(api_models))
            
            # Get existing models for comparison
            existing_models = {
                m.id: m for m in self.db.query(OpenRouterModel).all()
            }
            seen_model_ids: Set[str] = set()
            
            # Step 2: Process each model
            for api_model in api_models:
                try:
                    model_id = api_model.get("id")
                    if not model_id:
                        report.model_errors.append("Model missing ID")
                        continue
                    
                    seen_model_ids.add(model_id)
                    
                    # Create/update model
                    new_model = OpenRouterModel.from_api_response(api_model)
                    
                    if model_id in existing_models:
                        existing = existing_models[model_id]
                        
                        # Check if content changed
                        if existing.content_hash == new_model.content_hash:
                            # No changes - just update last_seen_at
                            existing.last_seen_at = datetime.now(timezone.utc)
                            report.models_unchanged += 1
                        else:
                            # Content changed - update all fields
                            self._update_model(existing, new_model)
                            report.models_updated += 1
                            logger.debug("Updated model: %s", model_id)
                    else:
                        # New model
                        if not dry_run:
                            self.db.add(new_model)
                        report.models_added += 1
                        logger.debug("Added model: %s", model_id)
                        
                except Exception as e:
                    report.model_errors.append(f"{api_model.get('id', 'unknown')}: {e}")
                    logger.warning("Error processing model: %s", e)
            
            # Step 3: Mark missing models as inactive
            for model_id, existing in existing_models.items():
                if model_id not in seen_model_ids and existing.is_active:
                    if not dry_run:
                        existing.is_active = False
                    report.models_marked_inactive += 1
                    logger.info("Marked model inactive: %s", model_id)
            
            # Step 4: Enrich with endpoints (if enabled)
            if enrich_endpoints:
                await self._enrich_endpoints(
                    client=client,
                    model_ids=list(seen_model_ids),
                    report=report,
                    dry_run=dry_run,
                    batch_size=endpoint_batch_size,
                    delay_seconds=endpoint_delay_seconds,
                )
            
            # Commit changes
            if not dry_run:
                self.db.commit()
                logger.info("Sync committed to database")
                
                # Step 5: Sync to Model Knowledge Store (Pinecone)
                # This populates the orchestrator's intelligence about models
                await self._sync_to_knowledge_store(api_models, report)
            else:
                self.db.rollback()
                logger.info("Dry run - changes rolled back")
            
        except Exception as e:
            self.db.rollback()
            report.model_errors.append(f"Fatal error: {e}")
            logger.error("Sync failed: %s", e, exc_info=True)
            
        finally:
            # Cleanup client if we created it
            if self._owns_client and self._client:
                await self._client.close()
                self._client = None
            
            report.completed_at = datetime.now(timezone.utc)
        
        # Log summary
        logger.info(
            "Sync complete: %d fetched, %d added, %d updated, %d unchanged, %d inactive",
            report.models_fetched,
            report.models_added,
            report.models_updated,
            report.models_unchanged,
            report.models_marked_inactive,
        )
        
        return report
    
    async def _sync_to_knowledge_store(
        self,
        api_models: List[Dict[str, Any]],
        report: SyncReport,
    ) -> None:
        """
        Sync model data to Model Knowledge Store (Pinecone).
        
        This populates the orchestrator's model intelligence with:
        - Model profiles (capabilities, strengths, weaknesses)
        - Reasoning model analysis
        - Best use cases for each model
        """
        try:
            from ..knowledge import MODEL_KNOWLEDGE_AVAILABLE, sync_openrouter_to_knowledge
            
            if not MODEL_KNOWLEDGE_AVAILABLE:
                logger.info("Model knowledge store not available, skipping knowledge sync")
                return
            
            knowledge_report = await sync_openrouter_to_knowledge(models=api_models)
            
            logger.info(
                "Model knowledge sync: %d profiles created, %d reasoning models",
                knowledge_report.get("models", {}).get("profiles_created", 0),
                knowledge_report.get("models", {}).get("reasoning_models_identified", 0),
            )
            
        except Exception as e:
            logger.warning("Model knowledge sync failed (non-fatal): %s", e)
    
    def _update_model(self, existing: OpenRouterModel, new: OpenRouterModel) -> None:
        """Update existing model with new data."""
        # Update all source fields
        existing.name = new.name
        existing.description = new.description
        existing.context_length = new.context_length
        existing.architecture_modality = new.architecture_modality
        existing.architecture_tokenizer = new.architecture_tokenizer
        existing.architecture_instruct = new.architecture_instruct
        existing.pricing_prompt = new.pricing_prompt
        existing.pricing_completion = new.pricing_completion
        existing.pricing_image = new.pricing_image
        existing.pricing_request = new.pricing_request
        existing.top_provider_context = new.top_provider_context
        existing.top_provider_max_tokens = new.top_provider_max_tokens
        existing.top_provider_moderation = new.top_provider_moderation
        existing.supported_params = new.supported_params
        existing.default_params = new.default_params
        existing.raw_json = new.raw_json
        
        # Recompute derived fields
        existing.compute_derived_fields()
        
        # Update timestamps
        existing.fetched_at = datetime.now(timezone.utc)
        existing.last_seen_at = datetime.now(timezone.utc)
        existing.is_active = True
    
    async def _enrich_endpoints(
        self,
        client: OpenRouterClient,
        model_ids: List[str],
        report: SyncReport,
        dry_run: bool,
        batch_size: int,
        delay_seconds: float,
    ) -> None:
        """Fetch and store endpoint details for models."""
        logger.info("Enriching endpoints for %d models...", len(model_ids))
        
        # Get existing endpoints
        existing_endpoints = {
            e.id: e for e in self.db.query(OpenRouterEndpoint).all()
        }
        seen_endpoint_ids: Set[str] = set()
        
        # Process in batches
        for i in range(0, len(model_ids), batch_size):
            batch = model_ids[i:i + batch_size]
            
            # Fetch endpoints concurrently
            tasks = [client.get_model_endpoints(mid) for mid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for model_id, result in zip(batch, results):
                if isinstance(result, Exception):
                    report.endpoint_errors.append(f"{model_id}: {result}")
                    continue
                
                endpoints = result
                report.endpoints_fetched += len(endpoints)
                
                for ep_data in endpoints:
                    try:
                        endpoint = OpenRouterEndpoint.from_api_response(model_id, ep_data)
                        seen_endpoint_ids.add(endpoint.id)
                        
                        if endpoint.id in existing_endpoints:
                            existing = existing_endpoints[endpoint.id]
                            self._update_endpoint(existing, endpoint)
                            report.endpoints_updated += 1
                        else:
                            if not dry_run:
                                self.db.add(endpoint)
                            report.endpoints_added += 1
                            
                    except Exception as e:
                        report.endpoint_errors.append(f"{model_id} endpoint: {e}")
            
            # Rate limit delay
            if i + batch_size < len(model_ids):
                await asyncio.sleep(delay_seconds)
        
        # Mark missing endpoints as inactive
        for endpoint_id, existing in existing_endpoints.items():
            if endpoint_id not in seen_endpoint_ids and existing.is_active:
                if not dry_run:
                    existing.is_active = False
                    existing.status = EndpointStatus.INACTIVE
                report.endpoints_marked_inactive += 1
        
        logger.info(
            "Endpoint enrichment complete: %d added, %d updated, %d inactive",
            report.endpoints_added,
            report.endpoints_updated,
            report.endpoints_marked_inactive,
        )
    
    def _update_endpoint(self, existing: OpenRouterEndpoint, new: OpenRouterEndpoint) -> None:
        """Update existing endpoint with new data."""
        existing.endpoint_pricing_prompt = new.endpoint_pricing_prompt
        existing.endpoint_pricing_completion = new.endpoint_pricing_completion
        existing.endpoint_pricing_image = new.endpoint_pricing_image
        existing.endpoint_pricing_request = new.endpoint_pricing_request
        existing.context_length = new.context_length
        existing.max_completion_tokens = new.max_completion_tokens
        existing.supported_params = new.supported_params
        existing.quantization = new.quantization
        existing.supports_caching = new.supports_caching
        existing.status = new.status
        existing.uptime_percent = new.uptime_percent
        existing.raw_json = new.raw_json
        existing.fetched_at = datetime.now(timezone.utc)
        existing.last_seen_at = datetime.now(timezone.utc)
        existing.is_active = True


async def run_scheduled_sync(
    db_session: Session,
    interval_seconds: int = 3600,
) -> None:
    """Run sync on a schedule.
    
    Args:
        db_session: Database session
        interval_seconds: Sync interval (default: 1 hour)
    """
    sync = OpenRouterModelSync(db_session)
    
    while True:
        try:
            logger.info("Starting scheduled OpenRouter sync...")
            report = await sync.run()
            
            if report.success:
                logger.info("Scheduled sync completed successfully")
            else:
                logger.warning("Scheduled sync completed with errors: %s", report.model_errors[:3])
                
        except Exception as e:
            logger.error("Scheduled sync failed: %s", e, exc_info=True)
        
        await asyncio.sleep(interval_seconds)

