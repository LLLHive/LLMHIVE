import { NextRequest, NextResponse } from "next/server"
import { auth, currentUser } from "@clerk/nextjs/server"
import Stripe from "stripe"
import { getSiteUrl } from "@/lib/site-url"
import {
  stripeEnterpriseAnnualPriceId,
  stripeEnterpriseMonthlyPriceId,
  stripeMaximumAnnualPriceId,
  stripeMaximumMonthlyPriceId,
  stripePremiumAnnualPriceId,
  stripePremiumMonthlyPriceId,
  stripeStandardAnnualPriceId,
  stripeStandardMonthlyPriceId,
} from "@/lib/billing/stripe-price-ids"
import {
  campaignCancelUrl,
  resolveCheckoutPaymentMode,
  stripeTrialSettingsForNoCard,
} from "@/lib/billing/standard-trial-checkout"

// Lazy initialize Stripe
function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) {
    return null
  }
  return new Stripe(process.env.STRIPE_SECRET_KEY)
}

const BACKEND_URL =
  process.env.ORCHESTRATOR_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

const STANDARD_TRIAL_DAYS = Math.max(
  0,
  parseInt(process.env.STANDARD_TRIAL_DAYS || "3", 10) || 3
)

async function customerAlreadyUsedStandardTrial(
  stripe: Stripe,
  email: string | undefined,
  userId: string
): Promise<boolean> {
  const looksLikeTrial = (sub: Stripe.Subscription) =>
    Boolean(
      sub.trial_start ||
        sub.metadata?.is_trial === "true" ||
        sub.metadata?.trial_without_card === "true"
    )

  try {
    const safeId = userId.replace(/["\\]/g, "")
    const byMeta = await stripe.subscriptions.search({
      query: `metadata["user_id"]:"${safeId}"`,
      limit: 10,
    })
    if (byMeta.data.some(looksLikeTrial)) return true
  } catch {
    // Subscription search is not enabled on every Stripe account.
  }

  if (!email) return false
  try {
    const customers = await stripe.customers.list({ email, limit: 5 })
    for (const customer of customers.data) {
      const subs = await stripe.subscriptions.list({
        customer: customer.id,
        status: "all",
        limit: 20,
      })
      if (subs.data.some(looksLikeTrial)) return true
    }
  } catch (err) {
    console.warn("standard trial history lookup failed:", err)
  }
  return false
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIMPLIFIED 4-TIER PRICING (January 2026)
// ═══════════════════════════════════════════════════════════════════════════════
function getCheckoutPriceIds(): Record<string, Record<string, string | undefined>> {
  return {
    // "lite" / "pro" = internal tier keys; Stripe products are LLMHive Standard / Premium
    lite: {
      monthly: stripeStandardMonthlyPriceId(),
      annual: stripeStandardAnnualPriceId(),
    },
    pro: {
      monthly: stripePremiumMonthlyPriceId(),
      annual: stripePremiumAnnualPriceId(),
    },
    enterprise: {
      monthly: stripeEnterpriseMonthlyPriceId(),
      annual: stripeEnterpriseAnnualPriceId(),
    },
    maximum: {
      monthly: stripeMaximumMonthlyPriceId(),
      annual: stripeMaximumAnnualPriceId(),
    },
  }
}

// Tier quotas and constraints - SIMPLIFIED 4 TIERS
const TIER_CONFIG: Record<string, { 
  eliteQueries: number
  afterQuotaTier: string
  totalQueries: number
  minSeats: number  // 0 = not seat-based
  isPerSeat: boolean
}> = {
  // "lite" = Standard product in Stripe (marketing: Standard, $10/mo, Standard orchestration only)
  lite: {
    eliteQueries: 0,
    afterQuotaTier: "standard",
    totalQueries: 999_999,
    minSeats: 0,
    isPerSeat: false,
  },
  // "pro" = Premium product in Stripe (marketing: Premium, $20/mo, Premium query quota)
  pro: {
    eliteQueries: 500,
    afterQuotaTier: "standard",
    totalQueries: 2000,
    minSeats: 0,
    isPerSeat: false,
  },
  enterprise: { 
    eliteQueries: 400,  // Per seat
    afterQuotaTier: "standard", 
    totalQueries: 800,  // Per seat
    minSeats: 1, 
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
    const { tier, billingCycle, quantity = 1, trialWithoutCard = false, cancelPath } = body

    if (!tier || !billingCycle) {
      return NextResponse.json(
        { error: "Missing tier or billingCycle" },
        { status: 400 }
      )
    }

    const tierLower = tier.toLowerCase()
    const cycleLower = billingCycle.toLowerCase()

    const stripe = getStripe()
    if (!stripe) {
      console.warn("STRIPE_SECRET_KEY not configured on frontend; using orchestrator checkout fallback")
      const backendResponse = await fetch(`${BACKEND_URL}/api/v1/payments/create-checkout-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(process.env.LLMHIVE_API_KEY ? { "X-API-Key": process.env.LLMHIVE_API_KEY } : {}),
        },
        body: JSON.stringify({
          tier: tierLower,
          billing_cycle: cycleLower,
          user_id: userId,
          user_email: userEmail,
          trial_without_card: Boolean(trialWithoutCard),
          ...(campaignCancelUrl("https://llmhive.ai", cancelPath)
            ? { cancel_path: cancelPath }
            : {}),
        }),
      })

      const backendData = await backendResponse.json().catch(() => ({}))
      if (!backendResponse.ok || !backendData.url) {
        console.error("Orchestrator checkout fallback failed:", backendData)
        return NextResponse.json(
          { error: backendData.detail || backendData.error || "Stripe checkout is temporarily unavailable." },
          { status: backendResponse.status || 500 }
        )
      }

      return NextResponse.json({
        url: backendData.url,
        sessionId: backendData.session_id,
      })
    }

    const priceIds = getCheckoutPriceIds()
    const priceId = priceIds[tierLower]?.[cycleLower]

    if (!priceId) {
      console.error(`Price ID not found for tier: ${tier}, cycle: ${billingCycle}`)
      console.error("Available tiers:", Object.keys(priceIds))
      console.error("Stripe price ids resolved:", {
        lite_monthly: !!stripeStandardMonthlyPriceId(),
        lite_annual: !!stripeStandardAnnualPriceId(),
        pro_monthly: !!stripePremiumMonthlyPriceId(),
        pro_annual: !!stripePremiumAnnualPriceId(),
        enterprise_monthly: !!stripeEnterpriseMonthlyPriceId(),
        enterprise_annual: !!stripeEnterpriseAnnualPriceId(),
        maximum_monthly: !!stripeMaximumMonthlyPriceId(),
        maximum_annual: !!stripeMaximumAnnualPriceId(),
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
    const isStandardMonthlyTrial =
      (tierLower === "lite" || tierLower === "standard") &&
      cycleLower === "monthly" &&
      STANDARD_TRIAL_DAYS > 0

    const paymentMode = resolveCheckoutPaymentMode({
      tier: tierLower,
      billingCycle: cycleLower,
      trialDays: STANDARD_TRIAL_DAYS,
      trialWithoutCardRequested: Boolean(trialWithoutCard),
    })
    const noCardTrial = paymentMode === "no_card_trial"

    if (noCardTrial && (await customerAlreadyUsedStandardTrial(stripe, userEmail, userId))) {
      return NextResponse.json(
        {
          error:
            "A Standard trial was already used on this account. Start Standard with a payment method, or subscribe to Premium.",
          code: "trial_already_used",
        },
        { status: 409 }
      )
    }

    const subscriptionData: Stripe.Checkout.SessionCreateParams.SubscriptionData = {
      metadata: {
        user_id: userId,
        tier: tierLower,
        elite_queries: String(tierConfig.eliteQueries * finalQuantity),
        after_quota_tier: tierConfig.afterQuotaTier,
        total_queries: String(tierConfig.totalQueries * finalQuantity),
        seats: String(finalQuantity),
        pricing_version: "quota_based_jan2026",
        ...(isStandardMonthlyTrial ? { is_trial: "true", trial_cap_usd: "3" } : {}),
        ...(noCardTrial ? { trial_without_card: "true" } : {}),
      },
      ...(isStandardMonthlyTrial ? { trial_period_days: STANDARD_TRIAL_DAYS } : {}),
      ...(noCardTrial ? { trial_settings: stripeTrialSettingsForNoCard() } : {}),
    }

    const cancelUrl = campaignCancelUrl(getSiteUrl(), cancelPath) || `${getSiteUrl()}/pricing`

    const sessionParams: Stripe.Checkout.SessionCreateParams = {
      customer_email: userEmail,
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: finalQuantity,
          // Enterprise: per-seat quantity (minimum 1 seat)
          ...(tierConfig.isPerSeat && {
            adjustable_quantity: {
              enabled: true,
              minimum: tierConfig.minSeats,
              maximum: 500,
            },
          }),
        },
      ],
      client_reference_id: userId,
      metadata: {
        user_id: userId,
        tier: tierLower,
        billing_cycle: cycleLower,
        elite_queries: String(tierConfig.eliteQueries * finalQuantity),  // Scale with seats
        after_quota_tier: tierConfig.afterQuotaTier,
        total_queries: String(tierConfig.totalQueries * finalQuantity),  // Scale with seats
        seats: String(finalQuantity),
        is_per_seat: String(tierConfig.isPerSeat),
        min_seats_required: String(tierConfig.minSeats),
        pricing_version: "quota_based_jan2026",
        ...(isStandardMonthlyTrial ? { is_trial: "true" } : {}),
        ...(noCardTrial ? { trial_without_card: "true" } : {}),
      },
      success_url: `${getSiteUrl()}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl,
      allow_promotion_codes: true,
      subscription_data: subscriptionData,
    }

    if (noCardTrial) {
      sessionParams.payment_method_collection = "if_required"
    } else {
      sessionParams.payment_method_types = ["card"]
    }

    const session = await stripe.checkout.sessions.create(sessionParams)

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
