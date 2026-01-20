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

// ═══════════════════════════════════════════════════════════════════════════════
// SIMPLIFIED 4-TIER PRICING (January 2026)
// ═══════════════════════════════════════════════════════════════════════════════
const PRICE_IDS: Record<string, Record<string, string | undefined>> = {
  lite: {
    monthly: process.env.STRIPE_PRICE_ID_LITE_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_LITE_ANNUAL,
  },
  pro: {
    monthly: process.env.STRIPE_PRICE_ID_PRO_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_PRO_ANNUAL,
  },
  enterprise: {
    monthly: process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL,
  },
  maximum: {
    monthly: process.env.STRIPE_PRICE_ID_MAXIMUM_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_MAXIMUM_ANNUAL,
  },
}

// Tier quotas and constraints - SIMPLIFIED 4 TIERS
const TIER_CONFIG: Record<string, { 
  eliteQueries: number
  afterQuotaTier: string
  totalQueries: number
  minSeats: number  // 0 = not seat-based
  isPerSeat: boolean
}> = {
  lite: { 
    eliteQueries: 100, 
    afterQuotaTier: "budget", 
    totalQueries: 500, 
    minSeats: 0, 
    isPerSeat: false 
  },
  pro: { 
    eliteQueries: 500, 
    afterQuotaTier: "standard", 
    totalQueries: 2000, 
    minSeats: 0, 
    isPerSeat: false 
  },
  enterprise: { 
    eliteQueries: 400,  // Per seat
    afterQuotaTier: "standard", 
    totalQueries: 800,  // Per seat
    minSeats: 5, 
    isPerSeat: true 
  },
  maximum: { 
    eliteQueries: 0,  // Unlimited (never throttle)
    afterQuotaTier: "maximum",  // Never drops below maximum
    totalQueries: 0,  // Unlimited
    minSeats: 0, 
    isPerSeat: false 
  },
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
      console.error("Stripe env vars configured:", {
        lite_monthly: !!process.env.STRIPE_PRICE_ID_LITE_MONTHLY,
        lite_annual: !!process.env.STRIPE_PRICE_ID_LITE_ANNUAL,
        pro_monthly: !!process.env.STRIPE_PRICE_ID_PRO_MONTHLY,
        pro_annual: !!process.env.STRIPE_PRICE_ID_PRO_ANNUAL,
        enterprise_monthly: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY,
        enterprise_annual: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL,
        maximum_monthly: !!process.env.STRIPE_PRICE_ID_MAXIMUM_MONTHLY,
        maximum_annual: !!process.env.STRIPE_PRICE_ID_MAXIMUM_ANNUAL,
      })
      return NextResponse.json(
        { error: `Price not configured for ${tier} (${billingCycle}). Please contact support.` },
        { status: 400 }
      )
    }

    // Get tier configuration
    const tierConfig = TIER_CONFIG[tierLower] || { 
      eliteQueries: 0, 
      afterQuotaTier: "budget", 
      totalQueries: 0,
      minSeats: 0,
      isPerSeat: false
    }

    // Enforce minimum seats for seat-based tiers (Enterprise, Enterprise+)
    const seatQuantity = quantity || 1
    if (tierConfig.minSeats > 0 && seatQuantity < tierConfig.minSeats) {
      return NextResponse.json(
        { 
          error: `${tier} requires a minimum of ${tierConfig.minSeats} seats. You selected ${seatQuantity}.`,
          minSeats: tierConfig.minSeats,
          isPerSeat: tierConfig.isPerSeat
        },
        { status: 400 }
      )
    }

    // Calculate final seat count (already validated above)
    const finalQuantity = tierConfig.isPerSeat 
      ? Math.max(tierConfig.minSeats, seatQuantity) 
      : 1

    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      customer_email: userEmail,
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: finalQuantity,
          // For Enterprise: Allow quantity adjustment with minimum 5 seats
          ...(tierConfig.isPerSeat && {
            adjustable_quantity: {
              enabled: true,
              minimum: tierConfig.minSeats,  // 5 for Enterprise
              maximum: 500,
            },
          }),
        },
      ],
      client_reference_id: userId,
      metadata: {
        user_id: userId,
        tier: tierLower,
        billing_cycle: billingCycle.toLowerCase(),
        elite_queries: String(tierConfig.eliteQueries * finalQuantity),  // Scale with seats
        after_quota_tier: tierConfig.afterQuotaTier,
        total_queries: String(tierConfig.totalQueries * finalQuantity),  // Scale with seats
        seats: String(finalQuantity),
        is_per_seat: String(tierConfig.isPerSeat),
        min_seats_required: String(tierConfig.minSeats),
        pricing_version: "quota_based_jan2026",
      },
      success_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/pricing`,
      allow_promotion_codes: true,
      subscription_data: {
        metadata: {
          user_id: userId,
          tier: tierLower,
          elite_queries: String(tierConfig.eliteQueries * finalQuantity),
          after_quota_tier: tierConfig.afterQuotaTier,
          total_queries: String(tierConfig.totalQueries * finalQuantity),
          seats: String(finalQuantity),
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
