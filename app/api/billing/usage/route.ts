import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

// =============================================================================
// QUOTA-BASED TIER LIMITS (Jan 2026)
// All tiers get ELITE quality - differs by quota
// =============================================================================
const TIER_QUOTAS = {
  free: {
    eliteQueries: 50,
    afterQuotaTier: "end",  // Trial ends
    totalQueries: 50,
    tokens: 50_000,
  },
  lite: {
    eliteQueries: 100,
    budgetQueries: 400,
    afterQuotaTier: "budget",
    totalQueries: 500,
    tokens: 500_000,
  },
  pro: {
    eliteQueries: 400,
    standardQueries: 600,
    afterQuotaTier: "standard",
    totalQueries: 1000,
    tokens: 2_000_000,
  },
  team: {
    eliteQueries: 500,
    standardQueries: 1500,
    afterQuotaTier: "standard",
    totalQueries: 2000,
    tokens: 4_000_000,
    isPooled: true,
  },
  enterprise: {
    eliteQueries: 300,  // Per seat
    standardQueries: 200,
    afterQuotaTier: "standard",
    totalQueries: 500,  // Per seat
    tokens: 1_000_000,  // Per seat
    perSeat: true,
  },
  enterprise_plus: {
    eliteQueries: 800,  // Per seat
    standardQueries: 700,
    afterQuotaTier: "standard",
    totalQueries: 1500,  // Per seat
    tokens: 3_000_000,  // Per seat
    perSeat: true,
  },
  maximum: {
    maximumQueries: 200,
    eliteQueries: 500,
    afterQuotaTier: "elite",  // Falls back to elite (still #1)
    totalQueries: 700,
    tokens: 10_000_000,
  },
}

type TierKey = keyof typeof TIER_QUOTAS

export interface QuotaUsageResponse {
  // Core quota info
  tier: string
  orchestrationMode: "maximum" | "elite" | "standard" | "budget"
  
  // ELITE quota (main quota for most tiers)
  elite: {
    used: number
    limit: number
    remaining: number
    percentUsed: number
  }
  
  // MAXIMUM quota (Maximum tier only)
  maximum?: {
    used: number
    limit: number
    remaining: number
    percentUsed: number
  }
  
  // After-quota tier info
  afterQuotaTier: string
  afterQuotaQueries?: number  // How many after-quota queries available
  
  // Token usage (for display)
  tokens: {
    used: number
    limit: number
  }
  
  // Status messaging
  status: "normal" | "warning" | "throttled" | "trial_ended"
  statusMessage?: string
  daysUntilReset: number
  
  // Upgrade prompt
  showUpgradePrompt: boolean
  upgradeMessage?: string
}

function getDaysUntilReset(): number {
  const now = new Date()
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  const diffTime = nextMonth.getTime() - now.getTime()
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

function getOrchestrationMode(
  tier: TierKey,
  eliteUsed: number,
  maximumUsed: number = 0
): "maximum" | "elite" | "standard" | "budget" {
  const quotas = TIER_QUOTAS[tier]
  
  // Maximum tier: check MAXIMUM first
  if (tier === "maximum" && quotas.maximumQueries) {
    if (maximumUsed < quotas.maximumQueries) {
      return "maximum"
    }
  }
  
  // Check ELITE quota
  if (eliteUsed < quotas.eliteQueries) {
    return "elite"
  }
  
  // ELITE exhausted - use after-quota tier
  return quotas.afterQuotaTier as "standard" | "budget"
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
    let data: Record<string, unknown> = {}
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/billing/usage/${userId}`, {
        headers: {
          "X-API-Key": process.env.LLMHIVE_API_KEY || "",
        },
        signal: AbortSignal.timeout(5000),
      })

      if (response.ok) {
        data = await response.json()
      }
    } catch (fetchError) {
      console.warn("Could not fetch usage from backend, using defaults:", fetchError)
    }
    
    // Extract tier name
    const tierName = ((data.tier_name || data.tier || "free") as string).toLowerCase() as TierKey
    const quotas = TIER_QUOTAS[tierName] || TIER_QUOTAS.free
    
    // Extract usage counts
    const eliteUsed = (data.elite_queries_used ?? data.elite_used ?? 0) as number
    const maximumUsed = (data.maximum_queries_used ?? data.maximum_used ?? 0) as number
    const tokensUsed = (data.tokens_used ?? data.tokens_this_period ?? 0) as number
    
    // Calculate current orchestration mode
    const orchestrationMode = getOrchestrationMode(tierName, eliteUsed, maximumUsed)
    
    // Calculate quotas
    const eliteRemaining = Math.max(0, quotas.eliteQueries - eliteUsed)
    const elitePercentUsed = quotas.eliteQueries > 0 ? eliteUsed / quotas.eliteQueries : 0
    
    const maximumRemaining = quotas.maximumQueries 
      ? Math.max(0, quotas.maximumQueries - maximumUsed)
      : undefined
    const maximumPercentUsed = quotas.maximumQueries 
      ? maximumUsed / quotas.maximumQueries 
      : 0
    
    // Determine status
    let status: QuotaUsageResponse["status"] = "normal"
    let statusMessage: string | undefined
    let showUpgradePrompt = false
    let upgradeMessage: string | undefined
    
    if (tierName === "free" && eliteRemaining === 0) {
      status = "trial_ended"
      statusMessage = "Your free trial has ended. Upgrade to continue using LLMHive!"
      showUpgradePrompt = true
      upgradeMessage = "Upgrade to Lite for just $9.99/month"
    } else if (eliteRemaining === 0) {
      status = "throttled"
      const afterTier = quotas.afterQuotaTier
      statusMessage = `ELITE quota exhausted. Using ${afterTier.toUpperCase()} mode (still great quality!)`
      showUpgradePrompt = true
      upgradeMessage = "Upgrade for more ELITE queries"
    } else if (elitePercentUsed >= 0.8) {
      status = "warning"
      statusMessage = `${eliteRemaining} ELITE queries remaining. They'll reset in ${getDaysUntilReset()} days.`
      showUpgradePrompt = elitePercentUsed >= 0.9
      if (showUpgradePrompt) {
        upgradeMessage = "Running low? Upgrade for more ELITE queries"
      }
    }
    
    // Build response
    const usageResponse: QuotaUsageResponse = {
      tier: tierName,
      orchestrationMode,
      elite: {
        used: eliteUsed,
        limit: quotas.eliteQueries,
        remaining: eliteRemaining,
        percentUsed: elitePercentUsed,
      },
      afterQuotaTier: quotas.afterQuotaTier,
      afterQuotaQueries: quotas.standardQueries || quotas.budgetQueries,
      tokens: {
        used: tokensUsed,
        limit: quotas.tokens,
      },
      status,
      statusMessage,
      daysUntilReset: getDaysUntilReset(),
      showUpgradePrompt,
      upgradeMessage,
    }
    
    // Add Maximum quota if applicable
    if (quotas.maximumQueries) {
      usageResponse.maximum = {
        used: maximumUsed,
        limit: quotas.maximumQueries,
        remaining: maximumRemaining!,
        percentUsed: maximumPercentUsed,
      }
    }
    
    return NextResponse.json(usageResponse)
  } catch (error) {
    console.error("Error getting usage:", error)
    // Return default response as fallback
    return NextResponse.json({
      tier: "free",
      orchestrationMode: "elite",
      elite: {
        used: 0,
        limit: 50,
        remaining: 50,
        percentUsed: 0,
      },
      afterQuotaTier: "end",
      tokens: {
        used: 0,
        limit: 50_000,
      },
      status: "normal",
      daysUntilReset: getDaysUntilReset(),
      showUpgradePrompt: false,
    } as QuotaUsageResponse)
  }
}
