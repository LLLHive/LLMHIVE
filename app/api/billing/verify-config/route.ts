import { NextResponse } from "next/server"
import Stripe from "stripe"

/**
 * Diagnostic endpoint to verify Stripe configuration
 * GET /api/billing/verify-config
 *
 * Resolves each logical price slot: canonical STANDARD_/PREMIUM_* first, then legacy BASIC_/PRO_*.
 */

function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) {
    return null
  }
  return new Stripe(process.env.STRIPE_SECRET_KEY)
}

type PriceSlot = {
  id: string
  description: string
  keys: string[]
  requireEnterpriseMeta?: boolean
}

const PRICE_SLOTS: PriceSlot[] = [
  {
    id: "standard_monthly",
    description: "Standard — monthly",
    keys: ["STRIPE_PRICE_ID_STANDARD_MONTHLY", "STRIPE_PRICE_ID_BASIC_MONTHLY"],
  },
  {
    id: "standard_annual",
    description: "Standard — annual",
    keys: ["STRIPE_PRICE_ID_STANDARD_ANNUAL", "STRIPE_PRICE_ID_BASIC_ANNUAL"],
  },
  {
    id: "premium_monthly",
    description: "Premium — monthly",
    keys: ["STRIPE_PRICE_ID_PREMIUM_MONTHLY", "STRIPE_PRICE_ID_PRO_MONTHLY"],
  },
  {
    id: "premium_annual",
    description: "Premium — annual",
    keys: ["STRIPE_PRICE_ID_PREMIUM_ANNUAL", "STRIPE_PRICE_ID_PRO_ANNUAL"],
  },
  {
    id: "enterprise_monthly",
    description: "Enterprise — monthly",
    keys: ["STRIPE_PRICE_ID_ENTERPRISE_MONTHLY"],
    requireEnterpriseMeta: true,
  },
  {
    id: "enterprise_annual",
    description: "Enterprise — annual",
    keys: ["STRIPE_PRICE_ID_ENTERPRISE_ANNUAL"],
    requireEnterpriseMeta: true,
  },
  {
    id: "maximum_monthly",
    description: "Maximum — monthly",
    keys: ["STRIPE_PRICE_ID_MAXIMUM_MONTHLY"],
  },
  {
    id: "maximum_annual",
    description: "Maximum — annual",
    keys: ["STRIPE_PRICE_ID_MAXIMUM_ANNUAL"],
  },
]

function resolveSlot(slot: PriceSlot): { envKey?: string; value?: string } {
  for (const k of slot.keys) {
    const v = process.env[k]
    if (v && v.trim()) return { envKey: k, value: v.trim() }
  }
  return {}
}

export async function GET() {
  const results: {
    stripe_configured: boolean
    env_vars: Record<
      string,
      { set: boolean; resolvedFrom?: string; value?: string }
    >
    price_validation: Record<string, { valid: boolean; error?: string; price_data?: object }>
    metadata_check: Record<string, { has_metadata: boolean; metadata?: object }>
    summary: { total: number; configured: number; valid: number; issues: string[] }
  } = {
    stripe_configured: false,
    env_vars: {},
    price_validation: {},
    metadata_check: {},
    summary: { total: PRICE_SLOTS.length, configured: 0, valid: 0, issues: [] },
  }

  const stripe = getStripe()
  if (!stripe) {
    results.summary.issues.push("STRIPE_SECRET_KEY not configured")
    return NextResponse.json(results, { status: 500 })
  }
  results.stripe_configured = true

  for (const slot of PRICE_SLOTS) {
    const { envKey, value } = resolveSlot(slot)
    results.env_vars[slot.id] = {
      set: !!value,
      resolvedFrom: envKey,
      value: value ? `${value.substring(0, 15)}...` : undefined,
    }

    if (!value) {
      results.summary.issues.push(`${slot.description}: no env set (tried ${slot.keys.join(", ")})`)
      continue
    }

    results.summary.configured++

    try {
      const price = await stripe.prices.retrieve(value, {
        expand: ["product"],
      })

      results.price_validation[slot.id] = {
        valid: true,
        price_data: {
          id: price.id,
          active: price.active,
          currency: price.currency,
          unit_amount: price.unit_amount,
          recurring: price.recurring,
          product_name:
            typeof price.product === "object"
              ? (price.product as Stripe.Product).name
              : price.product,
        },
      }

      if (typeof price.product === "object") {
        const product = price.product as Stripe.Product
        results.metadata_check[slot.id] = {
          has_metadata: Object.keys(product.metadata || {}).length > 0,
          metadata: product.metadata,
        }

        if (slot.requireEnterpriseMeta) {
          if (!product.metadata?.min_seats) {
            results.summary.issues.push(`${slot.description}: Missing 'min_seats' metadata`)
          }
          if (!product.metadata?.tier) {
            results.summary.issues.push(`${slot.description}: Missing 'tier' metadata`)
          }
        }
      }

      results.summary.valid++
    } catch (error) {
      results.price_validation[slot.id] = {
        valid: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }
      results.summary.issues.push(`${slot.description}: Invalid price ID — ${value}`)
    }
  }

  const allConfigured = results.summary.configured === results.summary.total
  const allValid = results.summary.valid === results.summary.total
  const status = allConfigured && allValid ? 200 : 400

  return NextResponse.json(
    {
      ...results,
      overall_status: allConfigured && allValid ? "✅ All configured correctly" : "⚠️ Issues found",
    },
    { status },
  )
}
