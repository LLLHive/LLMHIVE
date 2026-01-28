import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

// =============================================================================
// 5-TIER QUOTA SYSTEM (January 2026)
// Free, Lite, Pro, Enterprise
// =============================================================================
interface TierQuota {
  eliteQueries: number
  afterQuotaTier: string
  totalQueries: number
  tokens: number
  standardQueries?: number
  budgetQueries?: number
  perSeat?: boolean
  neverThrottle?: boolean
}

const TIER_QUOTAS: Record<string, TierQuota> = {
  free: {
    eliteQueries: 0,
    afterQuotaTier: "free",
    totalQueries: 50,
    tokens: 100_000,
  },
  lite: {
    eliteQueries: 100,
    afterQuotaTier: "free",
    totalQueries: 500,
    tokens: 500_000,
  },
  pro: {
    eliteQueries: 500,
    afterQuotaTier: "free",
    totalQueries: 2000,
    tokens: 4_000_000,
  },
  enterprise: {
    eliteQueries: 400,  // Per seat
    afterQuotaTier: "free",
    totalQueries: 800,  // Per seat
    tokens: 2_000_000,  // Per seat
    perSeat: true,
  },
}

type TierKey = keyof typeof TIER_QUOTAS

export interface QuotaUsageResponse {
  // Core quota info
  tier: string
  orchestrationMode: "elite" | "standard" | "budget" | "free"
  
  // ELITE quota (main quota for most tiers)
  elite: {
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
  status: "normal" | "warning" | "throttled"
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
  eliteUsed: number
): "elite" | "standard" | "budget" | "free" {
  const quotas = TIER_QUOTAS[tier]

  // Free tier: Always free orchestration
  if (tier === "free") {
    return "free"
  }
  
  // Check ELITE quota
  if (quotas.eliteQueries === 0 || eliteUsed < quotas.eliteQueries) {
    return "elite"
  }
  
  // ELITE exhausted - use after-quota tier
  return quotas.afterQuotaTier as "standard" | "budget" | "free"
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
    
    // Extract tier name (default to free for new signups)
    const tierName = ((data.tier_name || data.tier || "free") as string).toLowerCase() as TierKey
    const quotas = TIER_QUOTAS[tierName] || TIER_QUOTAS.free
    
    // Extract usage counts
    const eliteUsed = (data.elite_queries_used ?? data.elite_used ?? 0) as number
    const tokensUsed = (data.tokens_used ?? data.tokens_this_period ?? 0) as number
    
    // Calculate current orchestration mode
    const orchestrationMode = getOrchestrationMode(tierName, eliteUsed)
    
    // Calculate quotas
    const isUnlimited = quotas.neverThrottle
    const eliteRemaining = isUnlimited ? Infinity : Math.max(0, quotas.eliteQueries - eliteUsed)
    const elitePercentUsed = isUnlimited ? 0 : (quotas.eliteQueries > 0 ? eliteUsed / quotas.eliteQueries : 0)
    
    // Determine status
    let status: QuotaUsageResponse["status"] = "normal"
    let statusMessage: string | undefined
    let showUpgradePrompt = false
    let upgradeMessage: string | undefined
    
    // Enterprise tier with perSeat quotas
    if (isUnlimited) {
      status = "normal"
      statusMessage = "Enterprise tier - ELITE orchestration active"
    } else if (tierName === "free") {
      status = "normal"
      statusMessage = "Free tier active - upgrade for ELITE queries"
      showUpgradePrompt = true
      upgradeMessage = "Upgrade to Lite for ELITE queries and higher limits"
    } else if (eliteRemaining === 0) {
      status = "throttled"
      const afterTier = quotas.afterQuotaTier
      statusMessage = `ELITE quota exhausted. Using ${afterTier.toUpperCase()} mode (still great quality!)`
      showUpgradePrompt = true
      upgradeMessage = tierName === "lite" ? "Upgrade to Pro for 5x more ELITE queries" : "Upgrade to Enterprise for team features"
    } else if (elitePercentUsed >= 0.8) {
      status = "warning"
      statusMessage = `${eliteRemaining} ELITE queries remaining. They'll reset in ${getDaysUntilReset()} days.`
      showUpgradePrompt = elitePercentUsed >= 0.9
      if (showUpgradePrompt) {
        upgradeMessage = tierName === "lite" ? "Upgrade to Pro for 5x more ELITE queries" : "Upgrade for unlimited ELITE queries"
      }
    }
    
    // Build response
    const usageResponse: QuotaUsageResponse = {
      tier: tierName,
      orchestrationMode,
      elite: {
        used: eliteUsed,
        limit: isUnlimited ? -1 : quotas.eliteQueries,  // -1 = unlimited
        remaining: isUnlimited ? -1 : eliteRemaining as number,
        percentUsed: elitePercentUsed,
      },
      afterQuotaTier: quotas.afterQuotaTier,
      afterQuotaQueries: quotas.standardQueries || quotas.budgetQueries,
      tokens: {
        used: tokensUsed,
        limit: isUnlimited ? -1 : quotas.tokens,
      },
      status,
      statusMessage,
      daysUntilReset: getDaysUntilReset(),
      showUpgradePrompt,
      upgradeMessage,
    }
    
    return NextResponse.json(usageResponse)
  } catch (error) {
    console.error("Error getting usage:", error)
    // Return default Free response as fallback
    return NextResponse.json({
      tier: "free",
      orchestrationMode: "free",
      elite: {
        used: 0,
        limit: 0,
        remaining: 0,
        percentUsed: 0,
      },
      afterQuotaTier: "free",
      tokens: {
        used: 0,
        limit: 100_000,
      },
      status: "normal",
      daysUntilReset: getDaysUntilReset(),
      showUpgradePrompt: false,
    } as QuotaUsageResponse)
  }
}
