# Subscription Enforcement Implementation

This document describes the comprehensive subscription enforcement system implemented in LLMHive to support monetization with tier-based access control.

## Overview

The subscription enforcement system provides:
- Tier-based access control (Free, Pro, Enterprise)
- Usage limit enforcement (requests, tokens, models per request)
- Feature gating (advanced protocols, features)
- Rate limiting (requests per minute)
- Daily limits (separate from monthly)
- Payment hooks for future Stripe integration
- Comprehensive logging and monitoring

## Implementation Details

### 1. Subscription Tiers (`llmhive/src/llmhive/app/billing/pricing.py`)

**Already Implemented** with the following tiers:

#### Free Tier
- **Monthly Limits**:
  - 100 requests per month
  - 100,000 tokens per month
  - 2 models per request
  - 1 concurrent request
  - 10,000 tokens per query
- **Features**: Basic orchestration, memory, knowledge base
- **Advanced Features**: None (all disabled)

#### Pro Tier
- **Monthly Limits**:
  - 10,000 requests per month
  - 10,000,000 tokens per month
  - 5 models per request
  - 5 concurrent requests
  - 100,000 tokens per query
- **Features**: All advanced features enabled
- **Price**: $29.99/month or $299.99/year

#### Enterprise Tier
- **Monthly Limits**: Unlimited
- **Features**: All features + custom integrations, SSO, audit logs, SLA
- **Price**: $199.99/month or $1,999.99/year

### 2. Subscription Enforcement Module (`llmhive/src/llmhive/app/billing/enforcement.py`)

**New Module Created** with the following components:

#### `SubscriptionEnforcer` Class
- **Purpose**: Comprehensive enforcement of subscription limits
- **Features**:
  - Monthly request limit checking
  - Monthly token limit checking
  - Tokens per query limit checking
  - Models per request limit checking
  - Protocol/feature access checking
  - Daily limit checking

#### Key Methods:
- `enforce_request()`: Comprehensive enforcement check for a request
- `check_daily_limit()`: Check daily request limit (separate from monthly)
- `get_user_tier()`: Get user's tier name
- `can_access_feature()`: Check feature access

#### `EnforcementResult` Dataclass
- Stores enforcement decision:
  - `allowed`: Whether request is allowed
  - `reason`: Reason for denial (if any)
  - `tier_name`: User's tier
  - `limit_type`: Type of limit exceeded
  - `current_usage`: Current usage stats
  - `tier_limits`: Tier limit values
  - `upgrade_message`: User-friendly upgrade message

#### `PaymentHooks` Class
- **Purpose**: Hooks for future payment processing integration
- **Methods**:
  - `on_subscription_created()`: Called when subscription is created
  - `on_subscription_upgraded()`: Called when subscription is upgraded
  - `on_subscription_cancelled()`: Called when subscription is cancelled
  - `on_payment_recorded()`: Called when payment is recorded

### 3. Rate Limiting (`llmhive/src/llmhive/app/billing/rate_limiting.py`)

**Already Implemented** with:
- Per-tier rate limits (requests per 60 seconds):
  - Free: 5 requests/minute
  - Pro: 20 requests/minute
  - Enterprise: 100 requests/minute
- Rolling window tracking
- HTTP 429 responses with rate limit headers
- Middleware integration

### 4. API Integration (`llmhive/src/llmhive/app/api/orchestration.py`)

**Enhanced** with comprehensive enforcement:

#### Enforcement Flow:
1. **Daily Limit Check**: Check daily request limit first
2. **Comprehensive Enforcement**: Check all limits (monthly, tokens, models, features)
3. **Error Handling**: Return user-friendly error messages
4. **Usage Recording**: Record usage after successful orchestration

#### Error Responses:
- HTTP 403 Forbidden with detailed error information
- User-friendly upgrade messages
- Current usage and tier limits included

### 5. Subscription Service Integration

**Enhanced** with payment hooks:
- `create_subscription()`: Calls `PaymentHooks.on_subscription_created()`
- `upgrade_subscription()`: Calls `PaymentHooks.on_subscription_upgraded()`
- `cancel_subscription()`: Calls `PaymentHooks.on_subscription_cancelled()`

## Enforcement Checks

### 1. Monthly Request Limit
- **Check**: Current requests this month vs tier limit
- **Action**: Deny if exceeded
- **Message**: "You've reached your monthly request limit (X requests). Please upgrade to continue."

### 2. Monthly Token Limit
- **Check**: Projected tokens (current + estimated) vs tier limit
- **Action**: Deny if would exceed
- **Message**: "You've reached your monthly token limit (X tokens). Please upgrade to continue."

### 3. Tokens Per Query Limit
- **Check**: Estimated tokens for this query vs tier limit
- **Action**: Deny if exceeded
- **Message**: "This query exceeds your tier's token limit per query (X tokens). Please upgrade or simplify your query."

### 4. Models Per Request Limit
- **Check**: Number of models requested vs tier limit
- **Action**: Deny if exceeded
- **Message**: "Your tier allows up to X model(s) per request. Please upgrade to use more models."

### 5. Protocol/Feature Access
- **Check**: Protocol/feature availability for tier
- **Action**: Deny if not available
- **Message**: "The 'X' protocol/feature is not available for Y tier. Please upgrade to access advanced features."

### 6. Daily Request Limit
- **Check**: Requests today vs daily limit
- **Action**: Deny if exceeded
- **Message**: "You've reached your daily request limit (X requests). Please upgrade or try again tomorrow."

## Rate Limiting

### Per-Tier Limits:
- **Free**: 5 requests per 60 seconds
- **Pro**: 20 requests per 60 seconds
- **Enterprise**: 100 requests per 60 seconds

### Implementation:
- In-memory tracking (can be enhanced with Redis for distributed systems)
- Rolling 60-second window
- HTTP 429 Too Many Requests response
- Rate limit headers in response

## Frontend Error Handling

### Error Response Format:
```json
{
  "error": "subscription_limit_exceeded",
  "message": "Monthly request limit exceeded",
  "tier": "free",
  "limit_type": "requests",
  "upgrade_message": "You've reached your monthly request limit (100 requests). Please upgrade to continue.",
  "current_usage": {
    "requests_count": 100,
    "tokens_count": 50000
  },
  "tier_limits": {
    "max_requests_per_month": 100
  }
}
```

### Frontend Integration:
- Catch HTTP 403 responses
- Display upgrade message to user
- Show current usage vs limits
- Provide upgrade link/button

## Payment Hooks

### Hooks for Future Integration:
- `on_subscription_created()`: Integrate with Stripe to create subscription
- `on_subscription_upgraded()`: Integrate with Stripe to upgrade subscription
- `on_subscription_cancelled()`: Integrate with Stripe to cancel subscription
- `on_payment_recorded()`: Integrate with Stripe to record payment

### Usage:
```python
from llmhive.app.billing.enforcement import PaymentHooks

# In subscription service
PaymentHooks.on_subscription_created(user_id, tier_name, subscription_id)
```

## Logging and Monitoring

### Enforcement Events Logged:
- **Request Allowed**: User, tier, request details
- **Request Denied**: User, tier, limit type, reason
- **Daily Limit Exceeded**: User, tier, daily requests
- **Monthly Limit Exceeded**: User, tier, limit type
- **Feature Access Denied**: User, tier, feature name
- **Usage Recorded**: User, tier, tokens, requests

### Log Format:
```
Subscription Enforcement: User {user_id} (tier={tier}) request allowed
Subscription Enforcement: User {user_id} request denied: {reason} (limit_type={type})
Subscription Enforcement: Recorded usage for user {user_id} (tier={tier}): {tokens} tokens, {requests} requests
```

## Testing

### Manual Testing Steps:

1. **Free Tier Limit Test**:
   - Create free tier user
   - Make 100 requests (monthly limit)
   - Verify: 101st request is denied
   - Check error message and upgrade prompt

2. **Daily Limit Test**:
   - Create free tier user
   - Make 5 requests in one day (daily limit)
   - Verify: 6th request is denied
   - Check error message

3. **Feature Gating Test**:
   - Create free tier user
   - Request "hrm" protocol
   - Verify: Request is denied or protocol downgraded
   - Check error message

4. **Pro Tier Test**:
   - Create pro tier user
   - Make requests exceeding free tier limits
   - Verify: Requests are allowed
   - Check usage is recorded

5. **Rate Limiting Test**:
   - Create free tier user
   - Make 6 requests in 60 seconds
   - Verify: 6th request gets HTTP 429
   - Check rate limit headers

### Unit Tests (To Be Implemented):

```python
def test_free_tier_monthly_limit():
    enforcer = SubscriptionEnforcer(session)
    # Simulate 100 requests
    result = enforcer.enforce_request("free_user", requested_models=1, estimated_tokens=1000)
    assert result.allowed == False
    assert result.limit_type == "requests"

def test_protocol_gating():
    enforcer = SubscriptionEnforcer(session)
    result = enforcer.enforce_request("free_user", protocol="hrm")
    assert result.allowed == False
    assert result.limit_type == "feature"

def test_daily_limit():
    enforcer = SubscriptionEnforcer(session)
    result = enforcer.check_daily_limit("free_user")
    # After 5 requests today
    assert result.allowed == False
    assert result.limit_type == "daily_requests"
```

## Files Created/Modified

### New Files
- `llmhive/src/llmhive/app/billing/enforcement.py` - Comprehensive enforcement module
- `llmhive/src/llmhive/app/billing/__init__.py` - Billing module exports

### Modified Files
- `llmhive/src/llmhive/app/api/orchestration.py` - Integrated comprehensive enforcement
- `llmhive/src/llmhive/app/billing/subscription.py` - Added payment hooks

### Existing Files (Already Implemented)
- `llmhive/src/llmhive/app/billing/pricing.py` - Tier definitions
- `llmhive/src/llmhive/app/billing/usage.py` - Usage tracking
- `llmhive/src/llmhive/app/billing/rate_limiting.py` - Rate limiting middleware

## Configuration

### Tier Limits (in `pricing.py`):
- Configurable per tier
- Monthly limits (requests, tokens)
- Per-request limits (models, tokens per query)
- Feature flags (advanced features)

### Rate Limits (in `rate_limiting.py`):
- Configurable per tier
- Requests per 60 seconds

### Daily Limits (in `enforcement.py`):
- Configurable per tier
- Requests per day

## Future Enhancements

1. **Redis-Based Rate Limiting**: Distributed rate limiting for multi-instance deployments
2. **Daily Usage Table**: Dedicated table for daily usage tracking
3. **Usage Analytics Dashboard**: Visualize usage patterns and limits
4. **Automatic Tier Recommendations**: Suggest tier based on usage
5. **Grace Period**: Allow some overage before hard blocking
6. **Usage Alerts**: Notify users when approaching limits
7. **Stripe Integration**: Full payment processing integration
8. **Trial Periods**: Free trial for new users
9. **Usage Quotas Reset**: Automatic reset at billing period start
10. **Concurrent Request Tracking**: Track and enforce concurrent request limits

## Notes

- Enforcement is fail-open by default (logs errors but allows request if enforcement fails)
- In production, consider fail-closed for security
- Daily limits are approximate (based on usage records)
- Rate limiting is in-memory (not distributed)
- Payment hooks are placeholders for future Stripe integration
- Error messages are user-friendly and include upgrade prompts
- All enforcement events are logged for monitoring and analysis

