import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import Stripe from "stripe"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

/** List-price fallback (USD) when Stripe session amount is unavailable. */
const LIST_PRICES_USD: Record<string, Record<string, number>> = {
  lite: { monthly: 10, annual: 100 },
  pro: { monthly: 20, annual: 200 },
  enterprise: { monthly: 35, annual: 350 },
  maximum: { monthly: 0, annual: 0 },
}

function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) return null
  return new Stripe(process.env.STRIPE_SECRET_KEY)
}

async function buildPurchasePayload(
  sessionId: string,
  tier: string,
  billingCycle: string,
  isPaid: boolean
) {
  if (!isPaid) return null

  const stripe = getStripe()
  if (stripe) {
    try {
      const session = await stripe.checkout.sessions.retrieve(sessionId)
      return {
        transactionId: session.id,
        value: (session.amount_total ?? 0) / 100,
        currency: (session.currency ?? "usd").toUpperCase(),
        tier,
        billingCycle,
      }
    } catch (err) {
      console.warn("[verify-session] Stripe session retrieve failed:", err)
    }
  }

  const value = LIST_PRICES_USD[tier]?.[billingCycle] ?? 0
  return {
    transactionId: sessionId,
    value,
    currency: "USD",
    tier,
    billingCycle,
  }
}

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
    const paymentStatus = String(data.status || "").toLowerCase()
    const checkoutComplete =
      paymentStatus === "paid" || paymentStatus === "no_payment_required"

    // Synchronously upsert the Firestore subscription so the entitlement gate on /
    // sees status=trialing|active immediately, instead of waiting for the Stripe webhook
    let ensured = false
    if (checkoutComplete) {
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

    const tier = data.metadata?.tier || "pro"
    const billingCycle = data.metadata?.billing_cycle || "monthly"
    const isTrialStart =
      checkoutComplete && paymentStatus === "no_payment_required" && tier === "lite"
    const purchase = await buildPurchasePayload(
      sessionId,
      tier,
      billingCycle,
      paymentStatus === "paid"
    )

    return NextResponse.json({
      success: checkoutComplete,
      ensured,
      subscription: {
        tier,
        billingCycle,
        status: isTrialStart ? "trialing" : checkoutComplete ? "active" : "pending",
        isTrial: isTrialStart,
      },
      purchase,
    })
  } catch (error) {
    console.error("Error verifying session:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

