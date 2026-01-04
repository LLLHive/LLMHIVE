# Stage 4 Production Readiness Checklist

This document provides a comprehensive checklist for deploying LLMHive Stage 4 in production.

## Required Environment Variables

### Core Configuration
```bash
# Application
PYTHONPATH=/app/src
LOG_LEVEL=INFO

# Stage 4 Specific
S4_COREF_TIMEOUT=5.0          # Coreference resolution timeout (seconds)
S4_LLM_TIMEOUT=30.0           # LLM call timeout (seconds)
S4_MAX_ITERATIONS=10          # Max refinement iterations per request
S4_MAX_WALL_CLOCK=120.0       # Max request duration (seconds)
S4_TRIAL_COUNTER_PATH=/data/trial_counters.json  # Trial counter persistence
```

### Stripe Configuration
```bash
STRIPE_SECRET_KEY=sk_live_...        # Stripe API secret key (NEVER commit)
STRIPE_WEBHOOK_SECRET=whsec_...      # Webhook endpoint secret
STRIPE_PRICE_ID_BASIC_MONTHLY=price_...
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
STRIPE_PRICE_ID_ENTERPRISE_MONTHLY=price_...
```

### Redis (Required for Distributed Rate Limiting)
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10
RATE_LIMIT_REDIS_PREFIX=llmhive:ratelimit:
```

### External APIs
```bash
# Search Providers (at least one required)
TAVILY_API_KEY=...
BING_API_KEY=...

# Live Data (optional)
COINGECKO_API_KEY=...
OPENWEATHER_API_KEY=...

# LLM Providers
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
```

## Secrets Management

### ❌ Never Do
- Hardcode secrets in source code
- Log secrets or API keys
- Include secrets in error messages
- Commit secrets to git

### ✅ Always Do
- Use environment variables or secret managers
- Rotate secrets regularly (quarterly minimum)
- Use different keys for test/staging/production
- Audit secret access logs

### Recommended Secret Managers
- **Google Cloud**: Secret Manager
- **AWS**: Secrets Manager or SSM Parameter Store
- **Azure**: Key Vault
- **Kubernetes**: External Secrets Operator

## Redis Requirements

### Minimum Configuration
```yaml
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
```

### High Availability (Production)
```yaml
# Use Redis Cluster or Sentinel
# Minimum 3 nodes for HA
# Enable persistence (RDB + AOF)
# Configure proper memory limits
```

### Rate Limiting Keys
The system uses the following Redis key patterns:
```
llmhive:ratelimit:{user_id}:{window_start}  # Sliding window counters
llmhive:circuit:{service_name}              # Circuit breaker states
llmhive:trials:{user_id}:{feature}          # Trial counters
```

## Stripe Webhook Setup

### 1. Create Webhook Endpoint
```
Dashboard -> Developers -> Webhooks -> Add endpoint
```

### 2. Configure Events
Subscribe to these events:
- `invoice.paid`
- `invoice.payment_failed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

### 3. Set Webhook URL
```
https://your-domain.com/api/billing/webhooks
```

### 4. Copy Webhook Secret
Save the `whsec_...` value to `STRIPE_WEBHOOK_SECRET`

### 5. Verify Webhook Health
```bash
# Check webhook logs in Stripe Dashboard
# Verify signature verification is working
# Confirm idempotent processing (duplicate events skipped)
```

## Provider Quotas and Limits

### OpenAI
| Tier | TPM (gpt-4) | RPM |
|------|-------------|-----|
| Free | 40,000 | 3 |
| Tier 1 | 90,000 | 500 |
| Tier 5 | 10,000,000 | 10,000 |

### Anthropic
| Tier | RPM | TPM |
|------|-----|-----|
| Free | 5 | 20,000 |
| Build | 50 | 40,000 |
| Scale | 4,000 | 400,000 |

### Tavily Search
| Plan | Searches/Month |
|------|----------------|
| Free | 1,000 |
| Basic | 10,000 |
| Pro | 50,000 |

### CoinGecko
| Plan | Calls/Month |
|------|-------------|
| Demo | 10,000 |
| Analyst | 500,000 |

## Monitoring Checklist

### Metrics to Track
- [ ] Request latency (P50, P95, P99)
- [ ] Error rates by type
- [ ] Circuit breaker states
- [ ] Cache hit rates
- [ ] Rate limit blocks
- [ ] Token usage per request
- [ ] Memory usage

### Alerts to Configure
- [ ] Error rate > 5% for 5 minutes
- [ ] P99 latency > 30s for 5 minutes
- [ ] Circuit breaker opened
- [ ] Redis connection failures
- [ ] Stripe webhook failures
- [ ] Memory usage > 80%

### Log Aggregation
- Configure structured JSON logging
- Ship logs to centralized system (e.g., CloudWatch, Datadog)
- Enable request tracing with `request_id`

## Security Hardening

### Input Validation
- [ ] All user inputs sanitized
- [ ] Injection detection enabled
- [ ] Moderation applied to inputs
- [ ] File uploads restricted by size/type

### Authentication
- [ ] API key validation on all endpoints
- [ ] Rate limiting per user
- [ ] Token expiration configured
- [ ] Session management hardened

### Data Protection
- [ ] PII not logged
- [ ] Secrets not exposed in errors
- [ ] HTTPS enforced
- [ ] CORS properly configured

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing
- [ ] Coverage > 70%
- [ ] Linting clean (ruff)
- [ ] Type checking clean (mypy)
- [ ] Security scan clean (bandit)

### Configuration
- [ ] All env vars documented
- [ ] Secrets in secret manager
- [ ] Feature flags configured
- [ ] Logging level appropriate

### Infrastructure
- [ ] Redis deployed and healthy
- [ ] Database migrations applied
- [ ] SSL certificates valid
- [ ] DNS configured

### Integration
- [ ] Stripe webhook verified
- [ ] External API keys valid
- [ ] Circuit breakers tested
- [ ] Fallback paths verified

## Post-Deployment Verification

```bash
# Health check
curl https://your-domain.com/api/health

# Metrics endpoint
curl https://your-domain.com/api/metrics

# Test a simple query
curl -X POST https://your-domain.com/api/chat \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"message": "Hello, test"}'
```

## Known Limitations

1. **Coreference Resolution**: Falls back to heuristics if transformers unavailable
2. **Trial Counters**: File-based by default; use Redis for distributed deployments
3. **Learned Weights**: In-memory by default; configure persistence for production
4. **Rate Limiting**: Per-process by default; requires Redis for multi-worker

## Emergency Procedures

### Circuit Breaker Reset
```python
from llmhive.app.orchestration.stage4_hardening import CircuitBreakerRegistry

registry = CircuitBreakerRegistry.get_instance()
breaker = registry.get("service_name")
# Manual reset if needed (use with caution)
breaker._state = CircuitState.CLOSED
breaker._failure_count = 0
```

### Rate Limit Override
```python
# Temporarily increase limits for a user
# Update in database or Redis directly
```

### Rollback Procedure
1. Revert to previous deployment
2. Clear any corrupted state in Redis
3. Verify webhook processing resumes
4. Monitor for errors

## Contact

For Stage 4 issues, check:
1. Application logs with `request_id`
2. Circuit breaker states
3. Redis connectivity
4. External API status pages

