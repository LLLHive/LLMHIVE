# LLMHive Weekly Improvement System

## Overview

The Weekly Improvement System is a fully automated pipeline that keeps LLMHive's model catalog, rankings, and orchestration strategies up-to-date with the latest developments in AI.

## Schedule

| Job | Frequency | Time (UTC) | Trigger |
|-----|-----------|------------|---------|
| Full Weekly Sync | Weekly | Sunday 3:00 AM | Cloud Scheduler / GitHub Actions |
| Quick Sync | Every 6 hours | */6 * * * * | Cloud Scheduler |
| Research Scan | Daily | 2:00 AM | Background task |

## Components

### 1. OpenRouter Data Sync

#### Weekly Full Sync
- **Endpoint**: `POST /api/openrouter/rankings/sync?full=1`
- **Actions**:
  - Discover all categories (including nested like `marketing/seo`)
  - Sync top-10 rankings for each category
  - Mark inactive models
  - Update pricing and capabilities

#### 6-Hour Quick Sync
- **Endpoint**: `POST /api/openrouter/sync`
- **Actions**:
  - Refresh model availability
  - Update pricing
  - Check endpoint status

### 2. Research Agent

Monitors AI research sources for new developments:

- **Sources**:
  - arXiv (cs.CL, cs.AI, cs.LG)
  - HuggingFace model releases
  - OpenAI, Anthropic, Google AI blogs
  
- **Topics of Interest**:
  - Chain of thought improvements
  - Multi-agent orchestration
  - RAG techniques
  - Model evaluation methods

- **Output**:
  - Findings posted to blackboard
  - Integration proposals for high-impact items
  - Weekly summary in `research/findings/YYYY-MM-DD.md`

### 3. Benchmark Agent

Runs automated benchmarks to track performance:

- **Categories**:
  - Coding
  - Reasoning
  - Factual accuracy
  - Math
  - Multi-hop reasoning
  - Creative writing

- **Metrics**:
  - Overall score
  - Pass rate
  - Latency (avg, p95)
  - Category-specific scores

- **Regression Detection**:
  - 5% drop triggers alert
  - 15% drop is critical
  - Comparison against rolling baseline

### 4. Planning Agent

Coordinates improvements based on all inputs:

- **Inputs**:
  - Model catalog changes
  - Research proposals
  - Benchmark regressions
  - Ranking changes

- **Risk Assessment**:
  - **LOW**: Catalog updates, new categories
  - **MEDIUM**: Routing changes, fallback updates
  - **HIGH**: Prompt changes, strategy changes

- **Outputs**:
  - Upgrade plan with prioritized tasks
  - Auto-apply decisions for safe changes
  - Gated changes for manual review

### 5. Upgrade Agent

Applies safe improvements:

- **Auto-Apply (LOW risk)**:
  - New models added to catalog
  - New categories in UI
  - Pricing updates

- **Gated (MEDIUM/HIGH risk)**:
  - Model routing changes
  - Prompt template updates
  - New reasoning strategies

## Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OpenRouter    │────▶│   DB Tables     │────▶│   UI / API      │
│   API           │     │   - categories  │     │   - Models page │
│   - models      │     │   - rankings    │     │   - Chat dropdown│
│   - rankings    │     │   - models      │     │   - Orchestrator │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
┌─────────────────┐     ┌─────────────────┐
│ Research Agent  │────▶│   Blackboard    │
│ - arXiv scan    │     │   - findings    │
│ - model watch   │     │   - proposals   │
└─────────────────┘     └─────────────────┘
                              │
                              ▼
┌─────────────────┐     ┌─────────────────┐
│ Planning Agent  │◀────│ Benchmark Agent │
│ - prioritize    │     │ - run tests     │
│ - risk assess   │     │ - detect regress│
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │   Weekly Report │
                        │   - SAFE flag   │
                        │   - changes     │
                        │   - metrics     │
                        └─────────────────┘
```

## Weekly Report

Generated at: `llmhive/src/llmhive/app/weekly/reports/YYYY-MM-DD.md`

### Contents

1. **Summary**
   - Models added/removed
   - Category changes
   - Research findings count

2. **Top 3 Upgrades**
   - Most impactful changes this week

3. **Model Catalog Changes**
   - New models with capabilities
   - Removed/inactive models

4. **Benchmark Results**
   - Before/after comparison
   - Regression alerts

5. **Research Highlights**
   - High-impact findings
   - Integration proposals

6. **Safety Status**
   - `SAFE=true`: All tests passed, changes deployed
   - `SAFE=false`: Manual review required

## Cloud Scheduler Setup

### GCP Cloud Scheduler

```bash
# Weekly full sync (Sunday 3am UTC)
gcloud scheduler jobs create http openrouter-weekly-research \
  --location=us-east1 \
  --schedule="0 3 * * 0" \
  --uri="https://YOUR_SERVICE/api/weekly/run" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"full": true}' \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT

# 6-hour quick sync
gcloud scheduler jobs create http openrouter-sync \
  --location=us-east1 \
  --schedule="0 */6 * * *" \
  --uri="https://YOUR_SERVICE/api/openrouter/sync" \
  --http-method=POST \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT
```

### GitHub Actions

The `.github/workflows/weekly-improvement.yml` workflow runs:
- Every Sunday at 3am UTC (scheduled)
- On manual trigger (workflow_dispatch)

## Manual Triggers

### CLI

```bash
# Full weekly cycle
python -m llmhive.app.weekly_improvement --run --verbose

# Dry run (no changes)
python -m llmhive.app.weekly_improvement --run --dry-run

# Skip benchmarks (faster)
python -m llmhive.app.weekly_improvement --run --no-benchmarks

# OpenRouter sync only
python -m llmhive.app.openrouter.scheduler --sync
```

### API

```bash
# Trigger weekly cycle
curl -X POST https://YOUR_SERVICE/api/weekly/run \
  -H "Content-Type: application/json" \
  -d '{"full": true}'

# Check status
curl https://YOUR_SERVICE/api/weekly/status
```

## Safety Mechanisms

### Automatic Rollback
- If post-benchmark shows >5% regression, changes are rolled back
- SAFE=false flag prevents deployment

### Gating High-Risk Changes
- Prompt changes require manual review
- Routing changes create PR for review
- Strategy changes need A/B testing

### Test Requirements
- All E2E tests must pass
- Clarifying questions flow must work
- No console errors on core pages

## Monitoring

### Logs
- Weekly cycle logs at INFO level
- Errors logged with stack traces
- Summary logged at completion

### Alerts
- GitHub Issue created on SAFE=false
- Slack notification (if configured)
- Email to maintainers (if configured)

### Metrics
- Total cycle duration
- Sync duration
- Benchmark scores over time
- Upgrade success rate

## Drift Detection

The system detects drift between:
1. **DB ↔ OpenRouter**: Validates synced data against fresh fetches
2. **UI ↔ DB**: E2E tests verify UI shows correct data
3. **Orchestrator ↔ Rankings**: Checks model selection uses current rankings

### Validation Queries

```sql
-- Models not seen in 7 days
SELECT model_id, last_seen_at 
FROM openrouter_models 
WHERE last_seen_at < NOW() - INTERVAL '7 days'
AND is_active = TRUE;

-- Categories without rankings
SELECT c.slug 
FROM openrouter_categories c 
LEFT JOIN openrouter_ranking_snapshots s ON c.id = s.category_id
WHERE s.id IS NULL AND c.is_active = TRUE;
```

## Updating the System

### Adding a New Category
1. Add to `SEED_CATEGORIES` in `rankings_sync.py`
2. Run sync: `python -m llmhive.app.openrouter.scheduler --sync`
3. Verify in UI

### Changing Benchmark Cases
1. Update `BENCHMARK_CASES` in `benchmark_agent.py`
2. Run benchmarks to establish new baseline
3. Monitor for false regressions

### Adding New Research Source
1. Add URL to `RESEARCH_SOURCES` in `research_agent.py`
2. Add relevant topics to `RELEVANT_TOPICS`
3. Test with single scan cycle

## Troubleshooting

### Sync Fails
- Check OpenRouter API status
- Verify API key is valid
- Check network connectivity

### Benchmark Regression
- Review changed code since last pass
- Check if model availability changed
- Compare against historical baselines

### Research Agent Timeout
- Increase `max_runtime_seconds` in config
- Check if sources are responding
- Consider running in background

---

*Last updated: December 2025*
