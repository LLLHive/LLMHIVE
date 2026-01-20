import { NextRequest, NextResponse } from "next/server"
import { auth, currentUser } from "@clerk/nextjs/server"
import Stripe from "stripe"

// Lazy initialize Stripe
function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) {
    return null
  }
  return new Stripe(process.env.STRIPE_SECRET_KEY)
}

// Price ID mapping for all quota-based tiers
const PRICE_IDS: Record<string, Record<string, string | undefined>> = {
  lite: {
    monthly: process.env.STRIPE_PRICE_ID_LITE_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_LITE_ANNUAL,
  },
  pro: {
    monthly: process.env.STRIPE_PRICE_ID_PRO_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_PRO_ANNUAL,
  },
  team: {
    monthly: process.env.STRIPE_PRICE_ID_TEAM_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_TEAM_ANNUAL,
  },
  enterprise: {
    monthly: process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL,
  },
  enterprise_plus: {
    monthly: process.env.STRIPE_PRICE_ID_ENTERPRISE_PLUS_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_ENTERPRISE_PLUS_ANNUAL,
  },
  maximum: {
    monthly: process.env.STRIPE_PRICE_ID_MAXIMUM_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_MAXIMUM_ANNUAL,
  },
  // Legacy mappings for backward compatibility
  basic: {
    monthly: process.env.STRIPE_PRICE_ID_LITE_MONTHLY || process.env.STRIPE_PRICE_ID_BASIC_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_LITE_ANNUAL || process.env.STRIPE_PRICE_ID_BASIC_ANNUAL,
  },
}

// Tier quotas for metadata
const TIER_QUOTAS: Record<string, { eliteQueries: number; afterQuotaTier: string; totalQueries: number }> = {
  lite: { eliteQueries: 100, afterQuotaTier: "budget", totalQueries: 500 },
  pro: { eliteQueries: 400, afterQuotaTier: "standard", totalQueries: 1000 },
  team: { eliteQueries: 500, afterQuotaTier: "standard", totalQueries: 2000 },
  enterprise: { eliteQueries: 300, afterQuotaTier: "standard", totalQueries: 500 },
  enterprise_plus: { eliteQueries: 800, afterQuotaTier: "standard", totalQueries: 1500 },
  maximum: { eliteQueries: 500, afterQuotaTier: "elite", totalQueries: 700 },
}

export async function POST(request: NextRequest) {
  try {
    const stripe = getStripe()
    if (!stripe) {
      console.error("STRIPE_SECRET_KEY not configured")
      return NextResponse.json(
        { error: "Stripe not configured. Please contact support." },
        { status: 500 }
      )
    }

    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    const user = await currentUser()
    const userEmail = user?.emailAddresses?.[0]?.emailAddress

    const body = await request.json()
    const { tier, billingCycle, quantity = 1 } = body

    if (!tier || !billingCycle) {
      return NextResponse.json(
        { error: "Missing tier or billingCycle" },
        { status: 400 }
      )
    }

    const tierLower = tier.toLowerCase()
    const priceId = PRICE_IDS[tierLower]?.[billingCycle.toLowerCase()]

    if (!priceId) {
      console.error(`Price ID not found for tier: ${tier}, cycle: ${billingCycle}`)
      console.error("Available PRICE_IDS:", Object.keys(PRICE_IDS))
      console.error("Available env vars:", {
        lite_monthly: !!process.env.STRIPE_PRICE_ID_LITE_MONTHLY,
        lite_annual: !!process.env.STRIPE_PRICE_ID_LITE_ANNUAL,
        pro_monthly: !!process.env.STRIPE_PRICE_ID_PRO_MONTHLY,
        pro_annual: !!process.env.STRIPE_PRICE_ID_PRO_ANNUAL,
        team_monthly: !!process.env.STRIPE_PRICE_ID_TEAM_MONTHLY,
        team_annual: !!process.env.STRIPE_PRICE_ID_TEAM_ANNUAL,
        enterprise_monthly: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY,
        enterprise_annual: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL,
        enterprise_plus_monthly: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_PLUS_MONTHLY,
        enterprise_plus_annual: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_PLUS_ANNUAL,
        maximum_monthly: !!process.env.STRIPE_PRICE_ID_MAXIMUM_MONTHLY,
        maximum_annual: !!process.env.STRIPE_PRICE_ID_MAXIMUM_ANNUAL,
      })
      return NextResponse.json(
        { error: `Price not configured for ${tier} (${billingCycle}). Please contact support.` },
        { status: 400 }
      )
    }

    // Get quota info for this tier
    const quotaInfo = TIER_QUOTAS[tierLower] || { eliteQueries: 0, afterQuotaTier: "budget", totalQueries: 0 }

    // Determine if this is a per-seat tier
    const isPerSeat = ["enterprise", "enterprise_plus"].includes(tierLower)

    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      customer_email: userEmail,
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: isPerSeat ? Math.max(5, quantity) : 1, // Enterprise has min 5 seats
        },
      ],
      client_reference_id: userId,
      metadata: {
        user_id: userId,
        tier: tierLower,
        billing_cycle: billingCycle.toLowerCase(),
        elite_queries: String(quotaInfo.eliteQueries),
        after_quota_tier: quotaInfo.afterQuotaTier,
        total_queries: String(quotaInfo.totalQueries),
        pricing_version: "quota_based_jan2026",
      },
      success_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/pricing`,
      allow_promotion_codes: true,
      subscription_data: {
        metadata: {
          user_id: userId,
          tier: tierLower,
          elite_queries: String(quotaInfo.eliteQueries),
          after_quota_tier: quotaInfo.afterQuotaTier,
          pricing_version: "quota_based_jan2026",
        },
      },
    })

    return NextResponse.json({
      url: session.url,
      sessionId: session.id,
    })
  } catch (error) {
    console.error("Error creating checkout session:", error)
    const errorMessage = error instanceof Error ? error.message : "Unknown error"
    return NextResponse.json(
      { error: `Failed to create checkout: ${errorMessage}` },
      { status: 500 }
    )
  }
}
