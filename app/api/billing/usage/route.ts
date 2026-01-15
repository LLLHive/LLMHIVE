import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

// =============================================================================
// PRODUCTION TIER LIMITS - Configured for 50% minimum profit margin
// =============================================================================
const TIER_LIMITS = {
  free: {
    requests: 50,         // 50 messages/month
    tokens: 50_000,       // 50K tokens/month
    messages: 50,
    modelTier: 'budget',  // Budget models only (Llama, DeepSeek)
  },
  starter: {
    requests: 500,        // 500 messages/month ($15/mo)
    tokens: 500_000,      // 500K tokens/month
    messages: 500,
    modelTier: 'standard', // Standard models (GPT-4o Mini, Claude Haiku)
  },
  basic: {  // Alias for starter
    requests: 500,
    tokens: 500_000,
    messages: 500,
    modelTier: 'standard',
  },
  pro: {
    requests: 1_000,      // 1,000 messages/month ($29.99/mo)
    tokens: 1_000_000,    // 1M tokens/month (reduced from 3M!)
    messages: 1_000,
    modelTier: 'premium', // Premium models with daily caps
  },
  enterprise: {
    requests: 5_000,      // 5,000 messages/month ($199.99/mo)
    tokens: 5_000_000,    // 5M tokens/month (was unlimited!)
    messages: 5_000,
    modelTier: 'flagship',// All models with caps
  },
}

// Usage thresholds for throttling (like OpenAI does)
const USAGE_THRESHOLDS = {
  WARNING: 0.50,          // 50% - Show warning
  THROTTLE_PREMIUM: 0.75, // 75% - Block premium models
  THROTTLE_STANDARD: 0.90,// 90% - Budget models only
  HARD_LIMIT: 1.0,        // 100% - Block or overage
}

type TierKey = keyof typeof TIER_LIMITS

export interface UsageResponse {
  requests: {
    used: number
    limit: number
  }
  tokens: {
    used: number
    limit: number
  }
  tier: string
  percentUsed: number
  status: 'normal' | 'warning' | 'throttled' | 'blocked'
  modelRestriction?: 'none' | 'premium_blocked' | 'standard_only' | 'budget_only'
  message?: string
  daysUntilReset: number
}

function calculateUsageStatus(percentUsed: number): UsageResponse['status'] {
  if (percentUsed >= USAGE_THRESHOLDS.HARD_LIMIT) return 'blocked'
  if (percentUsed >= USAGE_THRESHOLDS.THROTTLE_STANDARD) return 'throttled'
  if (percentUsed >= USAGE_THRESHOLDS.WARNING) return 'warning'
  return 'normal'
}

function getModelRestriction(percentUsed: number): UsageResponse['modelRestriction'] {
  if (percentUsed >= USAGE_THRESHOLDS.THROTTLE_STANDARD) return 'budget_only'
  if (percentUsed >= USAGE_THRESHOLDS.THROTTLE_PREMIUM) return 'premium_blocked'
  return 'none'
}

function getStatusMessage(status: UsageResponse['status'], percentUsed: number, daysUntilReset: number): string {
  switch (status) {
    case 'blocked':
      return `Monthly limit reached. Your usage resets in ${daysUntilReset} days. Upgrade for more access.`
    case 'throttled':
      return `High usage (${Math.round(percentUsed * 100)}%). Using cost-efficient models to preserve your allowance.`
    case 'warning':
      return `You've used ${Math.round(percentUsed * 100)}% of your monthly allowance.`
    default:
      return ''
  }
}

function getDaysUntilReset(): number {
  const now = new Date()
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  const diffTime = nextMonth.getTime() - now.getTime()
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

export async function GET() {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    // Call backend to get usage data
    const response = await fetch(`${BACKEND_URL}/api/v1/billing/usage/${userId}`, {
      headers: {
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      signal: AbortSignal.timeout(5000),
    })

    let data: Record<string, unknown> = {}
    if (response.ok) {
      data = await response.json()
    }
    
    // Extract usage data - handle various backend response formats
    const requestsUsed = (data.requests_used ?? data.requests_this_period ?? data.total_requests ?? 0) as number
    const tokensUsed = (data.tokens_used ?? data.tokens_this_period ?? data.total_tokens ?? 0) as number
    
    // Get limits based on tier
    const tierName = ((data.tier_name || data.tier || "free") as string).toLowerCase() as TierKey
    const tierLimits = TIER_LIMITS[tierName] || TIER_LIMITS.free
    
    // Calculate usage percentage (use the higher of requests or tokens)
    const requestPercent = tierLimits.requests > 0 ? requestsUsed / tierLimits.requests : 0
    const tokenPercent = tierLimits.tokens > 0 ? tokensUsed / tierLimits.tokens : 0
    const percentUsed = Math.max(requestPercent, tokenPercent)
    
    // Determine status and restrictions
    const status = calculateUsageStatus(percentUsed)
    const modelRestriction = getModelRestriction(percentUsed)
    const daysUntilReset = getDaysUntilReset()
    const message = getStatusMessage(status, percentUsed, daysUntilReset)
    
    const usageResponse: UsageResponse = {
      requests: {
        used: requestsUsed,
        limit: tierLimits.requests,
      },
      tokens: {
        used: tokensUsed,
        limit: tierLimits.tokens,
      },
      tier: tierName,
      percentUsed,
      status,
      modelRestriction,
      message: message || undefined,
      daysUntilReset,
    }
    
    return NextResponse.json(usageResponse)
  } catch (error) {
    console.error("Error getting usage:", error)
    // Return default limits as fallback
    const daysUntilReset = getDaysUntilReset()
    return NextResponse.json({
      requests: { used: 0, limit: TIER_LIMITS.free.requests },
      tokens: { used: 0, limit: TIER_LIMITS.free.tokens },
      tier: 'free',
      percentUsed: 0,
      status: 'normal',
      modelRestriction: 'none',
      daysUntilReset,
    } as UsageResponse)
  }
}

