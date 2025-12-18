"""Cloud Scheduler integration for OpenRouter model sync.

Provides an API endpoint that Cloud Scheduler can call to trigger
regular model catalog synchronization.

Setup:
1. Deploy the API endpoint
2. Create Cloud Scheduler job via gcloud:
   
   gcloud scheduler jobs create http openrouter-sync \
     --location=us-east1 \
     --schedule="0 */6 * * *" \
     --uri="https://YOUR_SERVICE/api/openrouter/sync" \
     --http-method=POST \
     --oidc-service-account-email=YOUR_SERVICE_ACCOUNT \
     --headers="Content-Type=application/json"

This will sync models every 6 hours.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from .sync import OpenRouterModelSync, SyncReport
from ..db import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openrouter", tags=["openrouter-admin"])


class SyncRequest(BaseModel):
    """Sync request parameters."""
    dry_run: bool = False
    enrich_endpoints: bool = True
    force: bool = False  # Force sync even if recently synced


class SyncResponse(BaseModel):
    """Sync response."""
    status: str
    message: str
    report: Optional[dict] = None
    triggered_at: str


# Track last sync time to prevent too frequent syncs
_last_sync_time: Optional[datetime] = None
_min_sync_interval_minutes = 30


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
) -> SyncResponse:
    """Trigger OpenRouter model catalog sync.
    
    This endpoint is designed to be called by Cloud Scheduler.
    It runs the sync in the background and returns immediately.
    
    Args:
        request: Sync parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        SyncResponse with status
    """
    global _last_sync_time
    
    now = datetime.now(timezone.utc)
    
    # Check if we synced recently
    if not request.force and _last_sync_time is not None:
        elapsed_minutes = (now - _last_sync_time).total_seconds() / 60
        if elapsed_minutes < _min_sync_interval_minutes:
            return SyncResponse(
                status="skipped",
                message=f"Last sync was {elapsed_minutes:.1f} minutes ago. Use force=true to override.",
                triggered_at=now.isoformat(),
            )
    
    # Update last sync time
    _last_sync_time = now
    
    # Run sync in background
    background_tasks.add_task(
        _run_sync_task,
        dry_run=request.dry_run,
        enrich_endpoints=request.enrich_endpoints,
    )
    
    return SyncResponse(
        status="triggered",
        message="Sync started in background",
        triggered_at=now.isoformat(),
    )


@router.post("/sync/blocking", response_model=SyncResponse)
async def trigger_sync_blocking(
    request: SyncRequest,
) -> SyncResponse:
    """Trigger OpenRouter model catalog sync (blocking).
    
    This endpoint runs the sync synchronously and waits for completion.
    Use with caution as it may take several minutes.
    
    Args:
        request: Sync parameters
        
    Returns:
        SyncResponse with full report
    """
    now = datetime.now(timezone.utc)
    
    try:
        report = await _run_sync_task(
            dry_run=request.dry_run,
            enrich_endpoints=request.enrich_endpoints,
        )
        
        return SyncResponse(
            status="completed" if report.success else "completed_with_errors",
            message=f"Synced {report.models_fetched} models, {report.models_added} added, {report.models_updated} updated",
            report=report.to_dict(),
            triggered_at=now.isoformat(),
        )
        
    except Exception as e:
        logger.error("Sync failed: %s", e, exc_info=True)
        return SyncResponse(
            status="failed",
            message=str(e),
            triggered_at=now.isoformat(),
        )


@router.get("/sync/status")
async def get_sync_status() -> dict:
    """Get current sync status.
    
    Returns:
        Dictionary with sync status information
    """
    global _last_sync_time
    
    return {
        "last_sync_time": _last_sync_time.isoformat() if _last_sync_time else None,
        "min_sync_interval_minutes": _min_sync_interval_minutes,
    }


async def _run_sync_task(
    dry_run: bool = False,
    enrich_endpoints: bool = True,
) -> SyncReport:
    """Run the actual sync task.
    
    Args:
        dry_run: If True, don't commit changes
        enrich_endpoints: If True, fetch endpoint details
        
    Returns:
        SyncReport with results
    """
    logger.info("Starting OpenRouter sync (dry_run=%s, enrich_endpoints=%s)", dry_run, enrich_endpoints)
    
    # Get database session
    # Note: In production, this should use proper session management
    db_session = get_db_session()
    
    try:
        sync = OpenRouterModelSync(db_session)
        report = await sync.run(
            dry_run=dry_run,
            enrich_endpoints=enrich_endpoints,
        )
        
        logger.info(
            "Sync completed: %d fetched, %d added, %d updated, %d errors",
            report.models_fetched,
            report.models_added,
            report.models_updated,
            len(report.model_errors),
        )
        
        return report
        
    finally:
        db_session.close()


# Background sync runner for scheduled execution
async def run_scheduled_sync_loop(
    interval_hours: int = 6,
) -> None:
    """Run sync on a schedule (for non-Cloud Scheduler deployments).
    
    This can be used as an alternative to Cloud Scheduler for
    environments where scheduler is not available.
    
    Args:
        interval_hours: Hours between syncs
    """
    interval_seconds = interval_hours * 3600
    
    while True:
        try:
            logger.info("Running scheduled OpenRouter sync...")
            await _run_sync_task()
        except Exception as e:
            logger.error("Scheduled sync failed: %s", e, exc_info=True)
        
        await asyncio.sleep(interval_seconds)


# CLI command for manual sync
def cli_sync(dry_run: bool = False) -> None:
    """CLI command for manual sync.
    
    Usage:
        python -m llmhive.app.openrouter.scheduler --sync [--dry-run]
    """
    import asyncio
    
    async def _run():
        report = await _run_sync_task(dry_run=dry_run)
        print(f"\nSync Report:")
        print(f"  Models fetched: {report.models_fetched}")
        print(f"  Models added: {report.models_added}")
        print(f"  Models updated: {report.models_updated}")
        print(f"  Models unchanged: {report.models_unchanged}")
        print(f"  Models marked inactive: {report.models_marked_inactive}")
        print(f"  Duration: {report.duration_seconds:.2f}s")
        if report.model_errors:
            print(f"  Errors: {len(report.model_errors)}")
            for err in report.model_errors[:5]:
                print(f"    - {err}")
    
    asyncio.run(_run())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenRouter Model Sync")
    parser.add_argument("--sync", action="store_true", help="Run sync")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    
    args = parser.parse_args()
    
    if args.sync:
        cli_sync(dry_run=args.dry_run)
    else:
        parser.print_help()

