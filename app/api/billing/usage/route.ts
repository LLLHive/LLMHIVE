import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

// =============================================================================
// Quotas (April 2026 GTM): Standard (Stripe key "lite"), Premium ("pro"), Enterprise
// Unauthenticated / no sub: "free" (displayed as Standard in UI)
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
    eliteQueries: 0,
    afterQuotaTier: "standard",
    totalQueries: 999_999,
    tokens: 500_000,
  },
  pro: {
    eliteQueries: 500,
    afterQuotaTier: "standard",
    totalQueries: 2000,
    tokens: 4_000_000,
  },
  enterprise: {
    eliteQueries: 400,  // Per seat
    afterQuotaTier: "standard",
    totalQueries: 800,  // Per seat
    tokens: 2_000_000,  // Per seat
    perSeat: true,
  },
}

type TierKey = keyof typeof TIER_QUOTAS

/** Map API/marketing tier names onto internal quota keys */
function resolveInternalTierKey(raw: string): TierKey {
  const t = raw.toLowerCase()
  if (t === "standard") return "lite"
  if (t === "premium") return "pro"
  if (t in TIER_QUOTAS) return t as TierKey
  return "free"
}

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

  if (tier === "free") {
    return "free"
  }

  // Standard product (internal key "lite"): Standard orchestration only
  if (tier === "lite") {
    return "standard"
  }

  // Premium / Enterprise: in Premium quota → elite orchestration
  if (quotas.eliteQueries === 0 || eliteUsed < quotas.eliteQueries) {
    return "elite"
  }

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
    
    const tierRaw = ((data.tier_name || data.tier || "free") as string).toLowerCase()
    const tierName = resolveInternalTierKey(tierRaw)
    const quotas = TIER_QUOTAS[tierName] || TIER_QUOTAS.free
    
    // Extract usage counts
    const eliteUsed = (data.elite_queries_used ?? data.elite_used ?? 0) as number
    const tokensUsed = (data.tokens_used ?? data.tokens_this_period ?? 0) as number
    
    // Calculate current orchestration mode
    const orchestrationMode = getOrchestrationMode(tierName, eliteUsed)
    
    // Calculate quotas
    const isUnlimited = quotas.neverThrottle
    const eliteRemaining = isUnlimited ? Infinity : Math.max(0, quotas.eliteQueries - eliteUsed)
    const elitePercentUsed = isUnlimited
      ? 0
      : quotas.eliteQueries > 0
        ? eliteUsed / quotas.eliteQueries
        : 0
    
    // Determine status
    let status: QuotaUsageResponse["status"] = "normal"
    let statusMessage: string | undefined
    let showUpgradePrompt = false
    let upgradeMessage: string | undefined
    
    // Enterprise tier with perSeat quotas
    if (isUnlimited) {
      status = "normal"
      statusMessage = "Enterprise tier — Premium orchestration active"
    } else if (tierName === "free") {
      status = "normal"
      statusMessage = "No active subscription — Standard routing on applicable trials"
      showUpgradePrompt = true
      upgradeMessage = "Subscribe to Standard ($10/mo) or Premium ($20/mo) for full access"
    } else if (eliteRemaining === 0 && quotas.eliteQueries > 0) {
      status = "throttled"
      const afterTier = quotas.afterQuotaTier
      const afterLabel =
        afterTier === "free" ? "Standard" : afterTier === "standard" ? "Standard" : afterTier === "budget" ? "Budget" : afterTier
      statusMessage = `Premium quota exhausted. Using ${afterLabel} orchestration (still great quality!)`
      showUpgradePrompt = true
      upgradeMessage =
        tierName === "pro"
          ? "Upgrade to Enterprise for higher per-seat Premium quotas and team controls"
          : "Upgrade to Premium for more Premium queries"
    } else if (elitePercentUsed >= 0.8 && quotas.eliteQueries > 0) {
      status = "warning"
      statusMessage = `${eliteRemaining} Premium queries remaining. They'll reset in ${getDaysUntilReset()} days.`
      showUpgradePrompt = elitePercentUsed >= 0.9
      if (showUpgradePrompt) {
        upgradeMessage =
          tierName === "lite"
            ? "Move up to Premium ($20/mo) for 500 Premium queries / month"
            : "Upgrade to Enterprise for team features and higher quotas"
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
