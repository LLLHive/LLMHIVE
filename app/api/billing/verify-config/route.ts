import { NextResponse } from "next/server"
import Stripe from "stripe"

/**
 * Diagnostic endpoint to verify Stripe configuration
 * GET /api/billing/verify-config
 * 
 * This endpoint checks:
 * 1. Stripe API key is configured
 * 2. All price IDs are set as environment variables
 * 3. All price IDs are valid in Stripe
 * 4. Metadata is correctly configured
 */

function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) {
    return null
  }
  return new Stripe(process.env.STRIPE_SECRET_KEY)
}

// Expected environment variables for 4-tier pricing
// Note: "Lite" tier uses BASIC env vars for backwards compatibility with existing secrets
const EXPECTED_PRICE_IDS = {
  STRIPE_PRICE_ID_BASIC_MONTHLY: "Lite Monthly (uses BASIC)",
  STRIPE_PRICE_ID_BASIC_ANNUAL: "Lite Annual (uses BASIC)",
  STRIPE_PRICE_ID_PRO_MONTHLY: "Pro Monthly",
  STRIPE_PRICE_ID_PRO_ANNUAL: "Pro Annual",
  STRIPE_PRICE_ID_ENTERPRISE_MONTHLY: "Enterprise Monthly",
  STRIPE_PRICE_ID_ENTERPRISE_ANNUAL: "Enterprise Annual",
  STRIPE_PRICE_ID_MAXIMUM_MONTHLY: "Maximum Monthly",
  STRIPE_PRICE_ID_MAXIMUM_ANNUAL: "Maximum Annual",
}

export async function GET() {
  const results: {
    stripe_configured: boolean
    env_vars: Record<string, { set: boolean; value?: string }>
    price_validation: Record<string, { valid: boolean; error?: string; price_data?: object }>
    metadata_check: Record<string, { has_metadata: boolean; metadata?: object }>
    summary: { total: number; configured: number; valid: number; issues: string[] }
  } = {
    stripe_configured: false,
    env_vars: {},
    price_validation: {},
    metadata_check: {},
    summary: { total: 8, configured: 0, valid: 0, issues: [] },
  }

  // Check Stripe API key
  const stripe = getStripe()
  if (!stripe) {
    results.summary.issues.push("STRIPE_SECRET_KEY not configured")
    return NextResponse.json(results, { status: 500 })
  }
  results.stripe_configured = true

  // Check each environment variable
  for (const [envVar, description] of Object.entries(EXPECTED_PRICE_IDS)) {
    const value = process.env[envVar]
    results.env_vars[envVar] = {
      set: !!value,
      value: value ? `${value.substring(0, 15)}...` : undefined, // Truncate for security
    }

    if (value) {
      results.summary.configured++

      // Validate price in Stripe
      try {
        const price = await stripe.prices.retrieve(value, {
          expand: ["product"],
        })

        results.price_validation[envVar] = {
          valid: true,
          price_data: {
            id: price.id,
            active: price.active,
            currency: price.currency,
            unit_amount: price.unit_amount,
            recurring: price.recurring,
            product_name: typeof price.product === "object" ? (price.product as Stripe.Product).name : price.product,
          },
        }

        // Check metadata on product
        if (typeof price.product === "object") {
          const product = price.product as Stripe.Product
          results.metadata_check[envVar] = {
            has_metadata: Object.keys(product.metadata || {}).length > 0,
            metadata: product.metadata,
          }

          // Check for specific metadata issues
          if (envVar.includes("ENTERPRISE")) {
            if (!product.metadata?.min_seats) {
              results.summary.issues.push(`${description}: Missing 'min_seats' metadata`)
            }
            if (!product.metadata?.tier) {
              results.summary.issues.push(`${description}: Missing 'tier' metadata`)
            }
          }
        }

        results.summary.valid++
      } catch (error) {
        results.price_validation[envVar] = {
          valid: false,
          error: error instanceof Error ? error.message : "Unknown error",
        }
        results.summary.issues.push(`${description}: Invalid price ID - ${value}`)
      }
    } else {
      results.summary.issues.push(`${description}: Environment variable not set`)
    }
  }

  // Overall status
  const allConfigured = results.summary.configured === results.summary.total
  const allValid = results.summary.valid === results.summary.total
  const status = allConfigured && allValid ? 200 : 400

  return NextResponse.json({
    ...results,
    overall_status: allConfigured && allValid ? "✅ All configured correctly" : "⚠️ Issues found",
  }, { status })
}
