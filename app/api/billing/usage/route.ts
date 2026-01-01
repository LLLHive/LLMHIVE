import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

// Default limits per tier
const TIER_LIMITS = {
  free: { requests: 100, tokens: 100000 },
  pro: { requests: 10000, tokens: 10000000 },
  enterprise: { requests: 0, tokens: 0 }, // 0 = unlimited
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

    if (!response.ok) {
      // Return default free tier limits if error
      return NextResponse.json({
        requests: { used: 0, limit: TIER_LIMITS.free.requests },
        tokens: { used: 0, limit: TIER_LIMITS.free.tokens },
      })
    }

    const data = await response.json()
    
    // Extract usage data - handle various backend response formats
    const requestsUsed = data.requests_used ?? data.requests_this_period ?? data.total_requests ?? 0
    const tokensUsed = data.tokens_used ?? data.tokens_this_period ?? data.total_tokens ?? 0
    
    // Get limits based on tier
    const tierName = (data.tier_name || data.tier || "free").toLowerCase()
    const tierLimits = TIER_LIMITS[tierName as keyof typeof TIER_LIMITS] || TIER_LIMITS.free
    
    return NextResponse.json({
      requests: {
        used: requestsUsed,
        limit: data.requests_limit ?? tierLimits.requests,
      },
      tokens: {
        used: tokensUsed,
        limit: data.tokens_limit ?? tierLimits.tokens,
      },
    })
  } catch (error) {
    console.error("Error getting usage:", error)
    // Return default limits as fallback
    return NextResponse.json({
      requests: { used: 0, limit: TIER_LIMITS.free.requests },
      tokens: { used: 0, limit: TIER_LIMITS.free.tokens },
    })
  }
}

