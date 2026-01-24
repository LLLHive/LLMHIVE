import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

export async function GET() {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    // Call backend to get subscription status
    // Try the new endpoint first, fall back to the old one
    let response: Response
    try {
      response = await fetch(`${BACKEND_URL}/api/v1/billing/subscription/${userId}`, {
        headers: {
          "X-API-Key": process.env.LLMHIVE_API_KEY || "",
        },
        // Add timeout to prevent hanging
        signal: AbortSignal.timeout(10000),
      })
    } catch (fetchError) {
      // Network error or timeout - return free tier as fallback
      console.warn("[Billing] Failed to reach backend, defaulting to free tier:", fetchError)
      return NextResponse.json({
        subscription: {
          tier: "free",
          status: "active",
          billingCycle: null,
          currentPeriodEnd: null,
          cancelAtPeriodEnd: false,
        }
      })
    }

    if (!response.ok) {
      // If no subscription found OR backend error, return free tier
      // This handles both 404 (not found) and 500 (database issues)
      if (response.status === 404 || response.status >= 500) {
        console.log(`[Billing] Backend returned ${response.status}, defaulting to free tier`)
        return NextResponse.json({
          subscription: {
            tier: "free",
            status: "active",
            billingCycle: null,
            currentPeriodEnd: null,
            cancelAtPeriodEnd: false,
          }
        })
      }
      
      const error = await response.json().catch(() => ({ detail: "Unknown error" }))
      return NextResponse.json(
        { error: error.detail || "Failed to get subscription" },
        { status: response.status }
      )
    }

    const data = await response.json()
    
    return NextResponse.json({
      subscription: {
        tier: data.tier_name || data.tier || "free",
        status: data.status || "active",
        billingCycle: data.billing_cycle || null,
        currentPeriodEnd: data.current_period_end || null,
        cancelAtPeriodEnd: data.cancel_at_period_end || false,
      }
    })
  } catch (error) {
    console.error("Error getting subscription:", error)
    // Return free tier as fallback
    return NextResponse.json({
      subscription: {
        tier: "free",
        status: "active",
        billingCycle: null,
        currentPeriodEnd: null,
        cancelAtPeriodEnd: false,
      }
    })
  }
}

