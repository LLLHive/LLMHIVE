import { NextRequest, NextResponse } from "next/server"
import { auth, currentUser } from "@clerk/nextjs/server"
import Stripe from "stripe"

// Initialize Stripe with secret key
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "")

// Price ID mapping
const PRICE_IDS: Record<string, Record<string, string | undefined>> = {
  basic: {
    monthly: process.env.STRIPE_PRICE_ID_BASIC_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_BASIC_ANNUAL,
  },
  pro: {
    monthly: process.env.STRIPE_PRICE_ID_PRO_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_PRO_ANNUAL,
  },
  enterprise: {
    monthly: process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY,
    annual: process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL,
  },
}

export async function POST(request: NextRequest) {
  try {
    // Check if Stripe is configured
    if (!process.env.STRIPE_SECRET_KEY) {
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

    // Get user email from Clerk
    const user = await currentUser()
    const userEmail = user?.emailAddresses?.[0]?.emailAddress

    const body = await request.json()
    const { tier, billingCycle } = body

    if (!tier || !billingCycle) {
      return NextResponse.json(
        { error: "Missing tier or billingCycle" },
        { status: 400 }
      )
    }

    // Get the price ID for the selected tier and billing cycle
    const priceId = PRICE_IDS[tier.toLowerCase()]?.[billingCycle.toLowerCase()]

    if (!priceId) {
      console.error(`Price ID not found for tier: ${tier}, cycle: ${billingCycle}`)
      console.error("Available env vars:", {
        basic_monthly: !!process.env.STRIPE_PRICE_ID_BASIC_MONTHLY,
        basic_annual: !!process.env.STRIPE_PRICE_ID_BASIC_ANNUAL,
        pro_monthly: !!process.env.STRIPE_PRICE_ID_PRO_MONTHLY,
        pro_annual: !!process.env.STRIPE_PRICE_ID_PRO_ANNUAL,
        enterprise_monthly: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY,
        enterprise_annual: !!process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL,
      })
      return NextResponse.json(
        { error: `Price not configured for ${tier} (${billingCycle}). Please contact support.` },
        { status: 400 }
      )
    }

    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      customer_email: userEmail,
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      client_reference_id: userId,
      metadata: {
        user_id: userId,
        tier: tier.toLowerCase(),
        billing_cycle: billingCycle.toLowerCase(),
      },
      success_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/pricing`,
      allow_promotion_codes: true,
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
