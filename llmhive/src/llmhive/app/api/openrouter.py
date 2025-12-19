"""OpenRouter API Routes.

FastAPI routes for:
- Model catalog browsing
- Rankings and insights
- Inference gateway
- Prompt templates management
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..database import get_db
from ..openrouter import (
    OpenRouterClient,
    OpenRouterModelSync,
    OpenRouterInferenceGateway,
    RankingsAggregator,
)
from ..openrouter.models import OpenRouterModel, PromptTemplate
from ..openrouter.gateway import GatewayConstraints, ChatMessage
from ..openrouter.rankings import RankingDimension, TimeRange

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openrouter", tags=["openrouter"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ModelListFilters(BaseModel):
    """Filters for model list."""
    search: Optional[str] = None
    min_context: Optional[int] = None
    max_context: Optional[int] = None
    max_price_per_1m: Optional[float] = None
    is_free: Optional[bool] = None
    supports_tools: Optional[bool] = None
    supports_structured: Optional[bool] = None
    multimodal_input: Optional[bool] = None
    multimodal_output: Optional[bool] = None
    category: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""
    model: str = Field(..., description="OpenRouter model ID")
    messages: List[Dict[str, Any]] = Field(..., description="Chat messages")
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    
    # Orchestrator constraints
    max_cost_usd: Optional[float] = None
    save_run: bool = False


class CreateTemplateRequest(BaseModel):
    """Create prompt template request."""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: str
    variables: Optional[List[Dict[str, Any]]] = None
    default_model_id: Optional[str] = None
    default_params: Optional[Dict[str, Any]] = None
    visibility: str = "private"


class UpdateTemplateRequest(BaseModel):
    """Update prompt template request."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    variables: Optional[List[Dict[str, Any]]] = None
    default_model_id: Optional[str] = None
    default_params: Optional[Dict[str, Any]] = None
    visibility: Optional[str] = None
    version_notes: Optional[str] = None


# =============================================================================
# Model Catalog Routes
# =============================================================================

@router.get("/models")
async def list_models(
    search: Optional[str] = None,
    min_context: Optional[int] = None,
    max_context: Optional[int] = None,
    max_price_per_1m: Optional[float] = None,
    is_free: Optional[bool] = None,
    supports_tools: Optional[bool] = None,
    supports_structured: Optional[bool] = None,
    multimodal_input: Optional[bool] = None,
    sort_by: str = Query("name", regex="^(name|context_length|price_per_1m_prompt|availability_score)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db = Depends(get_db),
) -> Dict[str, Any]:
    """List models from catalog with filtering.
    
    Data Source: OpenRouter official API via sync pipeline.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    query = db.query(OpenRouterModel).filter(OpenRouterModel.is_active == True)
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            OpenRouterModel.name.ilike(search_pattern) |
            OpenRouterModel.id.ilike(search_pattern) |
            OpenRouterModel.description.ilike(search_pattern)
        )
    
    if min_context:
        query = query.filter(OpenRouterModel.context_length >= min_context)
    if max_context:
        query = query.filter(OpenRouterModel.context_length <= max_context)
    if max_price_per_1m:
        query = query.filter(OpenRouterModel.price_per_1m_prompt <= max_price_per_1m)
    if is_free is not None:
        query = query.filter(OpenRouterModel.is_free == is_free)
    if supports_tools is not None:
        query = query.filter(OpenRouterModel.supports_tools == supports_tools)
    if supports_structured is not None:
        query = query.filter(OpenRouterModel.supports_structured == supports_structured)
    if multimodal_input is not None:
        query = query.filter(OpenRouterModel.multimodal_input == multimodal_input)
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    sort_col = getattr(OpenRouterModel, sort_by)
    if sort_order == "desc":
        sort_col = sort_col.desc()
    query = query.order_by(sort_col)
    
    # Apply pagination
    models = query.offset(offset).limit(limit).all()
    
    return {
        "data": [m.to_dict() for m in models],
        "total": total,
        "limit": limit,
        "offset": offset,
        "data_source": "openrouter_api",
        "last_sync": models[0].last_seen_at.isoformat() if models else None,
    }


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Get single model details.
    
    Data Source: OpenRouter official API via sync pipeline.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    # Handle URL encoding
    model_id = model_id.replace("%2F", "/")
    
    model = db.query(OpenRouterModel).filter(
        OpenRouterModel.id == model_id,
    ).first()
    
    if not model:
        raise HTTPException(404, f"Model not found: {model_id}")
    
    result = model.to_dict()
    result["endpoints"] = [
        {
            "provider": e.provider_name,
            "tag": e.endpoint_tag,
            "context_length": e.context_length,
            "max_completion_tokens": e.max_completion_tokens,
            "status": e.status.value if e.status else "unknown",
            "uptime_percent": e.uptime_percent,
        }
        for e in model.endpoints if e.is_active
    ]
    result["data_source"] = "openrouter_api"
    
    return result


@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    enrich_endpoints: bool = True,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger model catalog sync.
    
    Fetches latest data from OpenRouter API.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    async def run_sync():
        try:
            sync = OpenRouterModelSync(db)
            report = await sync.run(
                dry_run=dry_run,
                enrich_endpoints=enrich_endpoints,
            )
            logger.info("Sync completed: %s", report.to_dict())
        except Exception as e:
            logger.error("Sync failed: %s", e, exc_info=True)
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "sync_started",
        "dry_run": dry_run,
        "message": "Sync running in background. Check logs for results.",
    }


# =============================================================================
# Rankings Routes
# =============================================================================

@router.get("/rankings/{dimension}")
async def get_rankings(
    dimension: str,
    time_range: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_context: Optional[int] = None,
    max_price_per_1m: Optional[float] = None,
    supports_tools: Optional[bool] = None,
    tenant_id: Optional[str] = None,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Get model rankings.
    
    Dimensions:
    - trending: Usage growth
    - most_used: Total usage volume
    - best_value: Quality/cost ratio
    - long_context: Context length
    - tools_agents: Tool calling capability
    - multimodal: Image/audio support
    - fastest: Response latency
    - most_reliable: Success rate
    - lowest_cost: Pricing
    
    Data Source: Internal telemetry (our gateway usage).
    Rankings are NOT scraped from OpenRouter.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    try:
        dim = RankingDimension(dimension)
    except ValueError:
        raise HTTPException(400, f"Invalid dimension: {dimension}")
    
    try:
        tr = TimeRange(time_range)
    except ValueError:
        raise HTTPException(400, f"Invalid time range: {time_range}")
    
    filters = {}
    if min_context:
        filters["min_context"] = min_context
    if max_price_per_1m:
        filters["max_price_per_1m"] = max_price_per_1m
    if supports_tools is not None:
        filters["supports_tools"] = supports_tools
    
    aggregator = RankingsAggregator(db)
    result = aggregator.get_ranking(
        dimension=dim,
        time_range=tr,
        limit=limit,
        offset=offset,
        filters=filters if filters else None,
        tenant_id=tenant_id,
    )
    
    return result.to_dict()


@router.get("/rankings")
async def list_ranking_dimensions() -> Dict[str, Any]:
    """List available ranking dimensions with descriptions."""
    return {
        "dimensions": [
            {
                "id": "trending",
                "name": "Trending",
                "description": "Models with growing usage",
                "metric": "usage_growth_pct",
            },
            {
                "id": "most_used",
                "name": "Most Used",
                "description": "Models with highest usage volume",
                "metric": "usage_count",
            },
            {
                "id": "best_value",
                "name": "Best Value",
                "description": "Best quality/cost ratio",
                "metric": "value_score",
            },
            {
                "id": "long_context",
                "name": "Long Context",
                "description": "Largest context windows",
                "metric": "context_length",
            },
            {
                "id": "tools_agents",
                "name": "Tools & Agents",
                "description": "Best for function calling",
                "metric": "tool_success_rate",
            },
            {
                "id": "multimodal",
                "name": "Multimodal",
                "description": "Image and audio support",
                "metric": "multimodal_score",
            },
            {
                "id": "fastest",
                "name": "Fastest",
                "description": "Lowest response latency",
                "metric": "avg_latency_ms",
            },
            {
                "id": "most_reliable",
                "name": "Most Reliable",
                "description": "Highest success rate",
                "metric": "success_rate",
            },
            {
                "id": "lowest_cost",
                "name": "Lowest Cost",
                "description": "Most affordable models",
                "metric": "cost_per_1m_tokens",
            },
        ],
        "time_ranges": ["24h", "7d", "30d", "all"],
        "data_source": "internal_telemetry",
        "data_source_description": "Rankings are derived from our internal usage data through the inference gateway. They are NOT scraped from OpenRouter.",
    }


# =============================================================================
# Inference Routes
# =============================================================================

@router.post("/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    user_id: Optional[str] = None,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Run chat completion through OpenRouter.
    
    Supports:
    - All OpenRouter models
    - Streaming (stream=true)
    - Tool/function calling
    - Structured output (JSON mode)
    
    The model must exist in our synced catalog.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    gateway = OpenRouterInferenceGateway(db)
    
    # Build constraints
    constraints = GatewayConstraints(
        max_cost_usd=request.max_cost_usd,
        tenant_id=user_id,
    )
    
    # Build params
    params = {}
    if request.temperature is not None:
        params["temperature"] = request.temperature
    if request.max_tokens is not None:
        params["max_tokens"] = request.max_tokens
    if request.top_p is not None:
        params["top_p"] = request.top_p
    if request.frequency_penalty is not None:
        params["frequency_penalty"] = request.frequency_penalty
    if request.presence_penalty is not None:
        params["presence_penalty"] = request.presence_penalty
    if request.stop:
        params["stop"] = request.stop
    
    try:
        if request.stream:
            # Streaming response
            async def generate():
                try:
                    async for chunk in await gateway.run_chat(
                        model_id=request.model,
                        messages=request.messages,
                        tools=request.tools,
                        response_format=request.response_format,
                        stream=True,
                        constraints=constraints,
                        save_run=request.save_run,
                        user_id=user_id,
                        **params,
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                finally:
                    await gateway.close()
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
            )
        
        # Non-streaming
        response = await gateway.run_chat(
            model_id=request.model,
            messages=request.messages,
            tools=request.tools,
            response_format=request.response_format,
            stream=False,
            constraints=constraints,
            save_run=request.save_run,
            user_id=user_id,
            **params,
        )
        
        await gateway.close()
        return response.to_dict()
        
    except Exception as e:
        await gateway.close()
        logger.error("Chat completion failed: %s", e, exc_info=True)
        raise HTTPException(500, str(e))


# =============================================================================
# Prompt Templates Routes
# =============================================================================

@router.get("/templates")
async def list_templates(
    user_id: str,
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db = Depends(get_db),
) -> Dict[str, Any]:
    """List prompt templates for user."""
    if not db:
        raise HTTPException(503, "Database not available")
    
    query = db.query(PromptTemplate).filter(
        PromptTemplate.user_id == user_id
    )
    
    if category:
        query = query.filter(PromptTemplate.category == category)
    if visibility:
        query = query.filter(PromptTemplate.visibility == visibility)
    
    total = query.count()
    templates = query.order_by(PromptTemplate.updated_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "system_prompt": t.system_prompt,
                "user_prompt_template": t.user_prompt_template,
                "variables": t.variables,
                "default_model_id": t.default_model_id,
                "default_params": t.default_params,
                "visibility": t.visibility.value if t.visibility else "private",
                "version": t.version,
                "use_count": t.use_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in templates
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    user_id: str,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new prompt template."""
    if not db:
        raise HTTPException(503, "Database not available")
    
    import uuid
    from ..openrouter.models import TemplateVisibility
    
    template = PromptTemplate(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=request.name,
        description=request.description,
        category=request.category,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        variables=request.variables,
        default_model_id=request.default_model_id,
        default_params=request.default_params,
        visibility=TemplateVisibility(request.visibility),
    )
    
    db.add(template)
    db.commit()
    
    return {"id": template.id, "message": "Template created"}


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    user_id: str,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Update a prompt template (creates new version)."""
    if not db:
        raise HTTPException(503, "Database not available")
    
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id,
        PromptTemplate.user_id == user_id,
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Update fields
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.category is not None:
        template.category = request.category
    if request.system_prompt is not None:
        template.system_prompt = request.system_prompt
    if request.user_prompt_template is not None:
        template.user_prompt_template = request.user_prompt_template
    if request.variables is not None:
        template.variables = request.variables
    if request.default_model_id is not None:
        template.default_model_id = request.default_model_id
    if request.default_params is not None:
        template.default_params = request.default_params
    if request.visibility is not None:
        from ..openrouter.models import TemplateVisibility
        template.visibility = TemplateVisibility(request.visibility)
    
    # Increment version
    template.version += 1
    if request.version_notes:
        template.version_notes = request.version_notes
    
    db.commit()
    
    return {"id": template.id, "version": template.version, "message": "Template updated"}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    user_id: str,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a prompt template."""
    if not db:
        raise HTTPException(503, "Database not available")
    
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id,
        PromptTemplate.user_id == user_id,
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted"}


# =============================================================================
# OpenRouter Rankings (FROM OPENROUTER - Source of Truth)
# =============================================================================

@router.get("/categories")
async def list_categories(
    group: str = Query("usecase", regex="^(usecase|language|programming)$"),
    include_inactive: bool = False,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """List all OpenRouter ranking categories.
    
    This returns categories synced from OpenRouter rankings.
    Categories are discovered dynamically from OpenRouter.
    
    Data Source: OpenRouter Rankings (synced to local DB)
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    try:
        from ..openrouter.rankings_models import OpenRouterCategory, CategoryGroup
        
        query = db.query(OpenRouterCategory).filter(
            OpenRouterCategory.group == CategoryGroup(group),
        )
        
        if not include_inactive:
            query = query.filter(OpenRouterCategory.is_active == True)
        
        categories = query.order_by(
            OpenRouterCategory.depth,
            OpenRouterCategory.slug,
        ).all()
        
        # Build hierarchy
        result = []
        parents = {}
        
        for cat in categories:
            cat_dict = cat.to_dict()
            
            if cat.depth == 0:
                result.append(cat_dict)
                parents[cat.slug] = cat_dict
            else:
                # Nested category
                if cat.parent_slug in parents:
                    parent = parents[cat.parent_slug]
                    if "children" not in parent:
                        parent["children"] = []
                    parent["children"].append(cat_dict)
                else:
                    result.append(cat_dict)
        
        return {
            "group": group,
            "categories": result,
            "total": len(categories),
            "data_source": "openrouter_rankings",
            "description": "Categories synced from OpenRouter rankings. Updated weekly.",
        }
        
    except Exception as e:
        logger.error("Failed to list categories: %s", e)
        raise HTTPException(500, str(e))


@router.get("/category-rankings")
async def get_category_rankings(
    category: str = Query(..., description="Category slug (e.g., 'programming', 'marketing/seo')"),
    view: str = Query("week", regex="^(week|month|day|all)$"),
    limit: int = Query(10, ge=1, le=50),
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Get top models for a category from OpenRouter rankings.
    
    This returns the EXACT ranking from OpenRouter, not internal telemetry.
    Rankings are synced from OpenRouter and stored locally.
    
    Data Source: OpenRouter Rankings (synced to local DB)
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    try:
        from ..openrouter.rankings_models import (
            OpenRouterCategory,
            OpenRouterRankingSnapshot,
            OpenRouterRankingEntry,
            SnapshotStatus,
        )
        from ..openrouter.models import OpenRouterModel
        
        # Get category
        category_obj = db.query(OpenRouterCategory).filter(
            OpenRouterCategory.slug == category,
        ).first()
        
        if not category_obj:
            raise HTTPException(404, f"Category not found: {category}")
        
        # Get latest successful snapshot
        snapshot = db.query(OpenRouterRankingSnapshot).filter(
            OpenRouterRankingSnapshot.category_slug == category,
            OpenRouterRankingSnapshot.status == SnapshotStatus.SUCCESS,
        ).order_by(OpenRouterRankingSnapshot.fetched_at.desc()).first()
        
        if not snapshot:
            return {
                "category": category_obj.to_dict(),
                "view": view,
                "entries": [],
                "last_synced": None,
                "error": "No rankings data available. Trigger a sync.",
            }
        
        # Get entries with model metadata
        entries = sorted(snapshot.entries, key=lambda e: e.rank)[:limit]
        
        # Enrich with model metadata
        enriched_entries = []
        for entry in entries:
            entry_dict = entry.to_dict()
            
            # Try to get model metadata
            if entry.model_id:
                model = db.query(OpenRouterModel).filter(
                    OpenRouterModel.id == entry.model_id,
                ).first()
                
                if model:
                    entry_dict["model_metadata"] = {
                        "context_length": model.context_length,
                        "pricing": {
                            "prompt": float(model.price_per_1m_prompt) if model.price_per_1m_prompt else None,
                            "completion": float(model.price_per_1m_completion) if model.price_per_1m_completion else None,
                        },
                        "supports_tools": model.supports_tools,
                        "supports_structured": model.supports_structured,
                        "multimodal_input": model.multimodal_input,
                        "availability_score": model.availability_score,
                    }
            
            enriched_entries.append(entry_dict)
        
        return {
            "category": category_obj.to_dict(),
            "view": view,
            "entries": enriched_entries,
            "entry_count": len(enriched_entries),
            "last_synced": snapshot.fetched_at.isoformat() if snapshot.fetched_at else None,
            "parse_version": snapshot.parse_version,
            "source_url": snapshot.source_url,
            "data_source": "openrouter_rankings",
            "description": "Rankings synced from OpenRouter. Order matches OpenRouter exactly.",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get category rankings: %s", e, exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/rankings/sync")
async def trigger_rankings_sync(
    background_tasks: BackgroundTasks,
    full: bool = Query(False, description="Run full sync with category discovery"),
    categories: Optional[str] = Query(None, description="Comma-separated category slugs"),
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger OpenRouter rankings sync.
    
    Fetches latest rankings from OpenRouter.
    
    Args:
        full: Run full sync with category discovery
        categories: Specific categories to sync (comma-separated)
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    async def run_sync():
        try:
            from ..openrouter.rankings_sync import RankingsSync
            
            sync = RankingsSync(db, api_key)
            
            if full:
                report = await sync.run_full_sync()
            else:
                cat_list = categories.split(",") if categories else None
                report = await sync.run_quick_sync(categories=cat_list)
            
            logger.info("Rankings sync completed: %s", report.to_dict())
        except Exception as e:
            logger.error("Rankings sync failed: %s", e, exc_info=True)
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "sync_started",
        "full": full,
        "message": "Rankings sync running in background. Check logs for results.",
    }


@router.post("/rankings/validate")
async def validate_rankings(
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Validate stored rankings against live OpenRouter data.
    
    Compares our stored rankings with current OpenRouter data
    to detect drift or data issues.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    try:
        from ..openrouter.rankings_sync import RankingsSync
        
        sync = RankingsSync(db, api_key)
        passed, errors = await sync.validate()
        
        return {
            "passed": passed,
            "errors": errors,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error("Validation failed: %s", e, exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/rankings/status")
async def get_rankings_status(
    db = Depends(get_db),
) -> Dict[str, Any]:
    """Get rankings sync status.
    
    Returns last sync times and status for monitoring.
    """
    if not db:
        raise HTTPException(503, "Database not available")
    
    try:
        from ..openrouter.rankings_models import (
            OpenRouterCategory,
            OpenRouterRankingSnapshot,
            OpenRouterSyncStatus,
            SnapshotStatus,
        )
        
        # Get category counts
        total_categories = db.query(OpenRouterCategory).count()
        active_categories = db.query(OpenRouterCategory).filter(
            OpenRouterCategory.is_active == True,
        ).count()
        
        # Get snapshot counts
        total_snapshots = db.query(OpenRouterRankingSnapshot).count()
        successful_snapshots = db.query(OpenRouterRankingSnapshot).filter(
            OpenRouterRankingSnapshot.status == SnapshotStatus.SUCCESS,
        ).count()
        
        # Get last sync
        last_sync = db.query(OpenRouterSyncStatus).filter(
            OpenRouterSyncStatus.sync_type.like("rankings%"),
        ).order_by(OpenRouterSyncStatus.started_at.desc()).first()
        
        # Get last successful snapshot
        last_snapshot = db.query(OpenRouterRankingSnapshot).filter(
            OpenRouterRankingSnapshot.status == SnapshotStatus.SUCCESS,
        ).order_by(OpenRouterRankingSnapshot.fetched_at.desc()).first()
        
        return {
            "categories": {
                "total": total_categories,
                "active": active_categories,
            },
            "snapshots": {
                "total": total_snapshots,
                "successful": successful_snapshots,
            },
            "last_sync": last_sync.to_dict() if last_sync else None,
            "last_snapshot_at": last_snapshot.fetched_at.isoformat() if last_snapshot else None,
        }
        
    except Exception as e:
        logger.error("Failed to get status: %s", e)
        raise HTTPException(500, str(e))

