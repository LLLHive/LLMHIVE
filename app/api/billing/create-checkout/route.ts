import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    const body = await request.json()
    const { tier, billingCycle } = body

    if (!tier || !billingCycle) {
      return NextResponse.json(
        { error: "Missing tier or billingCycle" },
        { status: 400 }
      )
    }

    // Call backend to create Stripe checkout session
    const response = await fetch(`${BACKEND_URL}/api/v1/payments/create-checkout-session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      body: JSON.stringify({
        tier,
        billing_cycle: billingCycle,
        user_id: userId,
        // user_email could be fetched from Clerk if needed
      }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }))
      return NextResponse.json(
        { error: error.detail || "Failed to create checkout session" },
        { status: response.status }
      )
    }

    const data = await response.json()
    
    return NextResponse.json({
      url: data.url,
      sessionId: data.session_id,
    })
  } catch (error) {
    console.error("Error creating checkout session:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

