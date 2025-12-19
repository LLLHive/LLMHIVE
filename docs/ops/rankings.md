# Rankings - Ingestion & Validation

## Overview

Rankings are derived from two sources:
1. **Internal Telemetry**: Usage patterns within LLMHive
2. **OpenRouter API**: External rankings by category

Rankings power:
- Model selection in orchestration
- UI "Top Models" displays
- Strategy recommendations
- Cost-quality trade-off decisions

## Database Schema

### Table: `openrouter_rankings`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Auto-increment ID |
| category | VARCHAR(100) | Ranking category (programming, roleplay, etc.) |
| model_id | VARCHAR(255) FK | Model ID (references openrouter_models) |
| rank | INTEGER | Position in ranking (1 = best) |
| score | FLOAT | Normalized score (0-1) |
| token_share | FLOAT | Share of tokens in category (0-1) |
| time_range | VARCHAR(20) | Time range (24h, 7d, 30d, all) |
| captured_at | TIMESTAMP | When ranking was captured |
| source | VARCHAR(50) | Source (internal, openrouter) |

### Table: `openrouter_ranking_snapshots`

Historical snapshots for trend analysis:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Auto-increment ID |
| snapshot_id | VARCHAR(50) | Unique snapshot identifier |
| category | VARCHAR(100) | Category |
| model_id | VARCHAR(255) | Model ID |
| rank | INTEGER | Rank at snapshot time |
| score | FLOAT | Score at snapshot time |
| captured_at | TIMESTAMP | Snapshot timestamp |

## Ranking Categories

### Core Categories (Always Updated)

| Category | Description | Update Frequency |
|----------|-------------|------------------|
| leaderboard | Overall token usage | 6 hours |
| market_share | Usage by provider | 6 hours |
| trending | Growth in usage | 6 hours |
| most_used | Absolute usage | 6 hours |
| best_value | Quality/cost ratio | 6 hours |

### Domain Categories

| Category | Description | Update Frequency |
|----------|-------------|------------------|
| programming | Coding tasks | Weekly |
| roleplay | Creative roleplay | Weekly |
| marketing | Marketing content | Weekly |
| science | Scientific analysis | Weekly |
| translation | Language translation | Weekly |
| legal | Legal documents | Weekly |
| finance | Financial analysis | Weekly |
| health | Medical topics | Weekly |
| academia | Academic writing | Weekly |

### Technical Categories

| Category | Description | Update Frequency |
|----------|-------------|------------------|
| long_context | Large context windows | Weekly |
| tools_agents | Tool/function calling | Weekly |
| multimodal | Image/audio support | Weekly |
| fastest | Lowest latency | 6 hours |
| most_reliable | Highest success rate | 6 hours |
| lowest_cost | Cheapest models | 6 hours |

## Ingestion Process

### 6-Hour Sync (Existing)

```python
# Called by Cloud Scheduler every 6 hours
POST /api/openrouter/sync

# Updates:
# - Model availability and pricing
# - Core ranking dimensions (leaderboard, trending, etc.)
# - Internal telemetry-based rankings
```

### Weekly Research Sync (New)

```python
# Called by Cloud Scheduler weekly (Sunday 3am UTC)
POST /api/openrouter/sync/research

# Updates:
# - Full category rankings for all categories
# - New model discovery
# - Capability matrix refresh
# - Creates alerts for new models
```

## Validation Rules

### Ranking Consistency

```python
def validate_rankings(rankings: List[RankedModel]) -> bool:
    """Validate ranking list for consistency."""
    
    # Rule 1: Ranks must be contiguous starting at 1
    ranks = sorted([r.rank for r in rankings])
    expected = list(range(1, len(rankings) + 1))
    assert ranks == expected, "Ranks must be contiguous"
    
    # Rule 2: All referenced models must exist
    for r in rankings:
        assert model_exists(r.model_id), f"Model {r.model_id} not in catalog"
    
    # Rule 3: Scores must be in valid range
    for r in rankings:
        assert 0 <= r.score <= 1, f"Score out of range: {r.score}"
    
    return True
```

### Idempotent Updates

```python
def upsert_ranking(category: str, model_id: str, rank: int, score: float):
    """Idempotent ranking upsert."""
    
    existing = db.query(Ranking).filter(
        Ranking.category == category,
        Ranking.model_id == model_id,
        Ranking.time_range == "7d",
    ).first()
    
    if existing:
        existing.rank = rank
        existing.score = score
        existing.captured_at = datetime.utcnow()
    else:
        db.add(Ranking(
            category=category,
            model_id=model_id,
            rank=rank,
            score=score,
            time_range="7d",
            captured_at=datetime.utcnow(),
            source="openrouter",
        ))
    
    db.commit()
```

## API Endpoints

### Get Rankings

```http
GET /api/rankings?category=programming&limit=20&time_range=7d
```

Response:
```json
{
  "category": "programming",
  "time_range": "7d",
  "generated_at": "2025-12-18T10:00:00Z",
  "models": [
    {
      "rank": 1,
      "model_id": "anthropic/claude-sonnet-4",
      "score": 0.95,
      "token_share": 0.23,
      "model": {
        "name": "Claude Sonnet 4",
        "context_length": 200000,
        "pricing": {"prompt": 3.0, "completion": 15.0}
      }
    }
  ]
}
```

### Get Top Models Per Category

```http
GET /api/models/top?category=programming&limit=10
```

Returns models with full metadata + ranking info + logo_url.

## Troubleshooting

### Rankings Not Updating

1. Check Cloud Scheduler job status
2. Verify OpenRouter API connectivity
3. Check for rate limiting
4. Review sync logs for errors

### Missing Models in Rankings

1. Verify model exists in catalog
2. Check if model is marked active
3. Ensure category is being synced
4. Check for model ID format differences

### Ranking Drift

If internal rankings differ significantly from OpenRouter:
1. Increase sync frequency for that category
2. Check internal telemetry volume
3. Consider weighted averaging

