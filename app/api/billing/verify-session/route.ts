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

function resolveTrialFromStripeSession(session: Stripe.Checkout.Session): {
  isTrial: boolean
  subscriptionStatus: "trialing" | "active" | "pending"
  trialEnd: string | null
} {
  const metadata = session.metadata || {}
  const tier = (metadata.tier || "").toLowerCase()
  const billingCycle = (metadata.billing_cycle || "monthly").toLowerCase()
  const paymentStatus = (session.payment_status || "").toLowerCase()

  let subStatus: string | null = null
  let trialEnd: string | null = null
  const sub = session.subscription
  if (sub && typeof sub === "object" && !("deleted" in sub && sub.deleted)) {
    const subscription = sub as Stripe.Subscription
    subStatus = subscription.status
    if (subscription.trial_end) {
      trialEnd = new Date(subscription.trial_end * 1000).toISOString()
    }
  }

  const isStandardMonthlyTrial =
    tier === "lite" &&
    billingCycle === "monthly" &&
    (metadata.is_trial === "true" ||
      paymentStatus === "no_payment_required" ||
      subStatus === "trialing" ||
      (session.amount_total === 0 && paymentStatus !== "unpaid"))

  const isTrial = isStandardMonthlyTrial && (subStatus === "trialing" || paymentStatus === "no_payment_required" || metadata.is_trial === "true")

  const subscriptionStatus: "trialing" | "active" | "pending" = isTrial
    ? "trialing"
    : paymentStatus === "paid" || paymentStatus === "no_payment_required"
      ? "active"
      : "pending"

  return { isTrial, subscriptionStatus, trialEnd }
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
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const sessionId = request.nextUrl.searchParams.get("session_id")

    if (!sessionId) {
      return NextResponse.json({ error: "Missing session_id" }, { status: 400 })
    }

    const stripe = getStripe()
    let stripeSession: Stripe.Checkout.Session | null = null
    if (stripe) {
      try {
        stripeSession = await stripe.checkout.sessions.retrieve(sessionId, {
          expand: ["subscription"],
        })
      } catch (err) {
        console.warn("[verify-session] Stripe retrieve failed:", err)
      }
    }

    // Call backend for metadata fallback
    const response = await fetch(`${BACKEND_URL}/api/v1/payments/checkout-session/${sessionId}`, {
      headers: {
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })

    let backendData: Record<string, unknown> = {}
    if (response.ok) {
      backendData = await response.json()
    }

    const paymentStatus = String(
      stripeSession?.payment_status || backendData.status || ""
    ).toLowerCase()
    const checkoutComplete =
      paymentStatus === "paid" || paymentStatus === "no_payment_required"

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

    const metadata = (stripeSession?.metadata || backendData.metadata || {}) as Record<
      string,
      string
    >
    const tier = metadata.tier || "pro"
    const billingCycle = metadata.billing_cycle || "monthly"

    const trialInfo = stripeSession
      ? resolveTrialFromStripeSession(stripeSession)
      : {
          isTrial:
            checkoutComplete &&
            paymentStatus === "no_payment_required" &&
            tier === "lite" &&
            billingCycle === "monthly",
          subscriptionStatus: (checkoutComplete
            ? paymentStatus === "no_payment_required"
              ? "trialing"
              : "active"
            : "pending") as "trialing" | "active" | "pending",
          trialEnd: null as string | null,
        }

    const purchase = await buildPurchasePayload(
      sessionId,
      tier,
      billingCycle,
      paymentStatus === "paid" && (stripeSession?.amount_total ?? 0) > 0
    )

    return NextResponse.json({
      success: checkoutComplete,
      ensured,
      subscription: {
        tier,
        billingCycle,
        status: trialInfo.subscriptionStatus,
        isTrial: trialInfo.isTrial,
        trialEnd: trialInfo.trialEnd,
        amountDueToday: stripeSession ? (stripeSession.amount_total ?? 0) / 100 : null,
      },
      purchase,
    })
  } catch (error) {
    console.error("Error verifying session:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
