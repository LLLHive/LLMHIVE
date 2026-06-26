import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

const SAFE_DEFAULTS = {
  is_throttled: false,
  subscription_tier: "free",
  current_orchestration: "free",
  elite_queries_limit: 0,
  elite_queries_used: 0,
  elite_queries_remaining: 0,
  throttle_message: null,
  upgrade_url: "/pricing",
}

/** Strip internal spend-guard fields and rewrite messages for customer-facing clients. */
function sanitizeThrottleStatus(data: Record<string, unknown>) {
  const isThrottled = Boolean(data.is_throttled)
  return {
    is_throttled: isThrottled,
    subscription_tier: data.subscription_tier ?? "free",
    current_orchestration: data.current_orchestration ?? "free",
    elite_queries_limit: data.elite_queries_limit ?? 0,
    elite_queries_used: data.elite_queries_used ?? 0,
    elite_queries_remaining: data.elite_queries_remaining ?? 0,
    throttle_message: isThrottled
      ? "Your premium orchestration limit for this billing period has been reached. You're on standard orchestration until it resets."
      : null,
    upgrade_url: data.upgrade_url ?? "/pricing",
  }
}

export async function GET(request: NextRequest) {
  try {
    const { userId } = await auth()
    const searchParams = request.nextUrl.searchParams
    const requestedUserId = searchParams.get("userId")
    
    // Use the authenticated user ID or fall back to the requested one
    const targetUserId = userId || requestedUserId
    
    if (!targetUserId) {
      return NextResponse.json(SAFE_DEFAULTS)
    }

    // Fetch throttle status from backend
    const response = await fetch(
      `${BACKEND_URL}/api/v1/billing/throttle-status/${targetUserId}`,
      {
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": targetUserId,
        },
        cache: "no-store",
      }
    )

    if (!response.ok) {
      return NextResponse.json(SAFE_DEFAULTS)
    }

    const data = await response.json()
    return NextResponse.json(sanitizeThrottleStatus(data))
    
  } catch (error) {
    console.error("Error fetching throttle status:", error)
    return NextResponse.json(SAFE_DEFAULTS)
  }
}
