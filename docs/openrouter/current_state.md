# OpenRouter Integration - Current State Audit

**Date**: 2025-12-19  
**Status**: ✅ IMPLEMENTATION COMPLETE - All Phases Finished

## Implementation Status

All phases of the OpenRouter Rankings integration have been implemented:

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repo Audit | ✅ Complete |
| 1 | Canonical Data Model | ✅ `rankings_models.py` created |
| 2 | Rankings Sync | ✅ `rankings_sync.py` + `rankings_client.py` |
| 3 | Backend API | ✅ Category/rankings endpoints added |
| 4 | UI Fix | ✅ `rankings-insights.tsx` updated |
| 5 | Orchestrator | ✅ Dynamic high-accuracy model selection |
| 6 | Weekly Plan | ✅ `weekly_improvement_plan.md` created |
| 7 | Tests | ✅ Test fixtures and unit tests created |

---

## Original Problem (2025-12-18)

**Problem**: The UI rankings and categories DO NOT MATCH OpenRouter.ai because:
1. Categories are **hardcoded** in the frontend
2. Rankings are derived from **internal telemetry** only, not OpenRouter's actual rankings
3. There is **no sync mechanism** for OpenRouter's category rankings

**Root Cause**: The existing `RankingsAggregator` class in `rankings.py` builds rankings from our internal `OpenRouterUsageTelemetry` table, which reflects our own gateway usage - NOT OpenRouter's global rankings.

---

## What Currently Exists

### 1. Model Catalog Sync ✅ (Works)
- **File**: `openrouter/sync.py`
- **Source**: OpenRouter Models API (`GET /api/v1/models`)
- **Syncs**: Model IDs, names, descriptions, pricing, capabilities
- **Schedule**: 6-hour Cloud Scheduler job
- **Status**: Working correctly

### 2. Rankings Aggregator ⚠️ (Wrong Data Source)
- **File**: `openrouter/rankings.py`
- **Source**: Internal telemetry (`openrouter_usage_telemetry` table)
- **Dimensions**: trending, most_used, best_value, fastest, etc.
- **Problem**: These are OUR usage patterns, NOT OpenRouter's rankings

### 3. UI Categories 🔴 (Hardcoded)
- **File**: `components/openrouter/rankings-insights.tsx`
- **Categories**: Hardcoded in `DIMENSION_CATEGORIES` object
- **Problem**: Missing categories, wrong structure, no nested categories

### 4. Orchestrator Model Selection ⚠️ (Partially Dynamic)
- **File**: `orchestration/openrouter_selector.py`
- **Uses**: Our internal rankings, not OpenRouter's
- **Problem**: Model selection doesn't reflect OpenRouter's actual top models

## Data Flow Analysis

```
CURRENT (WRONG):
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Our Gateway   │ ──> │  Internal       │ ──> │   "Rankings"    │
│   Usage Data    │     │  Telemetry DB   │     │   (our data)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘

SHOULD BE:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  OpenRouter     │ ──> │  Rankings       │ ──> │   Rankings      │
│  Rankings API   │     │  Snapshots DB   │     │   (OR data)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## UI Surfaces Affected

| Surface | File | Issue |
|---------|------|-------|
| Rankings Tab | `rankings-insights.tsx` | Hardcoded categories, wrong rankings |
| Model Dropdown | `chat-area.tsx` | May use internal rankings |
| Chat Toolbar | `chat-toolbar.tsx` | Category references hardcoded |
| Models Page | `app/models/page.tsx` | Rankings section uses internal data |
| Home Screen | `home-screen.tsx` | May reference hardcoded categories |

## Categories Comparison

### Currently Hardcoded (Wrong):
```
core: [leaderboard, market_share, trending, most_used, best_value]
categories: [programming, roleplay, marketing, seo, technology, science, translation, legal, finance, health, academia]
technical: [long_context, tools_agents, multimodal, images, fastest, most_reliable, lowest_cost]
```

### OpenRouter Actual Categories (Need to Fetch):
- Nested categories like `marketing/seo`
- Additional categories we're missing
- Different grouping structure

## What Must Be Fixed

### Phase 1: Data Model
- [ ] Add `openrouter_category` table
- [ ] Add `openrouter_ranking_snapshot` table  
- [ ] Add `openrouter_ranking_entry` table

### Phase 2: Rankings Sync
- [ ] Create OpenRouter rankings client
- [ ] Implement category discovery
- [ ] Implement ranking sync for each category
- [ ] Validate against live OpenRouter data

### Phase 3: API Updates
- [ ] Add `/api/openrouter/categories` endpoint
- [ ] Add `/api/openrouter/rankings` endpoint (from sync)
- [ ] Add validation endpoint

### Phase 4: UI Updates
- [ ] Remove hardcoded categories
- [ ] Fetch categories from API
- [ ] Fetch rankings from synced data

### Phase 5: Orchestrator Updates
- [ ] Use OpenRouter rankings for model selection
- [ ] Remove hardcoded high-accuracy model lists

## Files to Modify

| File | Action |
|------|--------|
| `openrouter/models.py` | Add new tables |
| `openrouter/rankings_client.py` | NEW - fetch OpenRouter rankings |
| `openrouter/rankings_sync.py` | NEW - sync rankings to DB |
| `api/openrouter.py` | Add new endpoints |
| `components/openrouter/rankings-insights.tsx` | Remove hardcoded, use API |
| `orchestration/openrouter_selector.py` | Use synced rankings |
| `orchestration/adaptive_router.py` | Use synced rankings |

