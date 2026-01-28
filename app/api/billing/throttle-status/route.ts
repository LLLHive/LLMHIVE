import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

export async function GET(request: NextRequest) {
  try {
    const { userId } = await auth()
    const searchParams = request.nextUrl.searchParams
    const requestedUserId = searchParams.get("userId")
    
    // Use the authenticated user ID or fall back to the requested one
    const targetUserId = userId || requestedUserId
    
    if (!targetUserId) {
      return NextResponse.json({
        is_throttled: false,
        subscription_tier: "free",
        current_orchestration: "free",
        elite_queries_limit: 0,
        elite_queries_used: 0,
        elite_queries_remaining: 0,
        throttle_message: null,
        upgrade_url: "/pricing",
      })
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
      // Return safe defaults if backend fails
      return NextResponse.json({
        is_throttled: false,
        subscription_tier: "free",
        current_orchestration: "free",
        elite_queries_limit: 0,
        elite_queries_used: 0,
        elite_queries_remaining: 0,
        throttle_message: null,
        upgrade_url: "/pricing",
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error("Error fetching throttle status:", error)
    // Return safe defaults
    return NextResponse.json({
      is_throttled: false,
      subscription_tier: "free",
      current_orchestration: "free",
      elite_queries_limit: 0,
      elite_queries_used: 0,
      elite_queries_remaining: 0,
      throttle_message: null,
      upgrade_url: "/pricing",
    })
  }
}
