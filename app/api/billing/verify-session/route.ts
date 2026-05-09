import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

export async function GET(request: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    const sessionId = request.nextUrl.searchParams.get("session_id")

    if (!sessionId) {
      return NextResponse.json(
        { error: "Missing session_id" },
        { status: 400 }
      )
    }

    // Call backend to verify the checkout session
    const response = await fetch(`${BACKEND_URL}/api/v1/payments/checkout-session/${sessionId}`, {
      headers: {
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }))
      return NextResponse.json(
        { error: error.detail || "Failed to verify session" },
        { status: response.status }
      )
    }

    const data = await response.json()
    const isPaid = data.status === "paid" || data.status === "complete"

    // Synchronously upsert the Firestore subscription so the entitlement gate on /
    // sees status=active immediately, instead of waiting for the Stripe webhook
    // to fire. The webhook still runs (idempotent), this just closes the race.
    let ensured = false
    if (isPaid) {
      try {
        const ensureRes = await fetch(
          `${BACKEND_URL}/api/v1/payments/checkout-session/${sessionId}/ensure-subscription`,
          {
            method: "POST",
            headers: {
              "X-API-Key": process.env.LLMHIVE_API_KEY || "",
              "Content-Type": "application/json",
            },
          }
        )
        if (ensureRes.ok) {
          ensured = true
        } else {
          const body = await ensureRes.text().catch(() => "")
          console.warn(
            "[verify-session] ensure-subscription returned",
            ensureRes.status,
            body.slice(0, 200)
          )
        }
      } catch (err) {
        console.warn("[verify-session] ensure-subscription request failed:", err)
      }
    }

    return NextResponse.json({
      success: isPaid,
      ensured,
      subscription: {
        tier: data.metadata?.tier || "pro",
        billingCycle: data.metadata?.billing_cycle || "monthly",
      },
    })
  } catch (error) {
    console.error("Error verifying session:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

