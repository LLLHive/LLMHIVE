import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import Stripe from "stripe"

/**
 * Diagnostic endpoint to verify Stripe configuration.
 * GET /api/billing/verify-config
 *
 * Auth: signed-in admin (ADMIN_USER_IDS) OR header `X-API-Key: <LLMHIVE_API_KEY>`.
 * Verifies each current customer-facing Stripe price slot + trial env vars.
 */

const ADMIN_USERS = (process.env.ADMIN_USER_IDS || "")
  .split(",")
  .map((id) => id.trim())
  .filter(Boolean)

function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) {
    return null
  }
  return new Stripe(process.env.STRIPE_SECRET_KEY)
}

async function authorize(request: NextRequest): Promise<boolean> {
  const apiKey = request.headers.get("x-api-key")
  const expectedKey = process.env.LLMHIVE_API_KEY
  if (apiKey && expectedKey && apiKey === expectedKey) {
    return true
  }
  const { userId } = await auth()
  if (userId && (ADMIN_USERS.length === 0 || ADMIN_USERS.includes(userId))) {
    return true
  }
  return false
}

function describeEnvValue(value: string | undefined): string | undefined {
  if (!value) return undefined
  const v = value.trim()
  if (v.startsWith("price_")) return `${v.slice(0, 15)}... (price id)`
  if (v.startsWith("sk_live_")) return `${v.slice(0, 15)}... (WRONG: secret key in price slot)`
  if (v.startsWith("sk_test_")) return `${v.slice(0, 15)}... (WRONG: secret key in price slot)`
  return `${v.slice(0, 15)}...`
}

function validatePriceIdFormat(envKey: string, value: string): string | null {
  if (value.startsWith("sk_live_") || value.startsWith("sk_test_")) {
    return `${envKey} contains a Stripe secret key (sk_...). Use a Price ID (price_...) from Stripe → Products → your Standard monthly price.`
  }
  if (!value.startsWith("price_")) {
    return `${envKey} must start with price_ (got ${value.slice(0, 8)}...)`
  }
  return null
}

const EXPECTED_ENTERPRISE_MIN_SEATS = "1"
const EXPECTED_ENTERPRISE_TIER = "enterprise"

type PriceSlot = {
  id: string
  description: string
  keys: string[]
  expectedUnitAmount: number
  expectedInterval: "month" | "year"
  requireEnterpriseMeta?: boolean
}

const PRICE_SLOTS: PriceSlot[] = [
  {
    id: "standard_monthly",
    description: "Standard — monthly",
    keys: ["STRIPE_PRICE_ID_STANDARD_MONTHLY"],
    expectedUnitAmount: 1000,
    expectedInterval: "month",
  },
  {
    id: "standard_annual",
    description: "Standard — annual",
    keys: ["STRIPE_PRICE_ID_STANDARD_ANNUAL"],
    expectedUnitAmount: 10000,
    expectedInterval: "year",
  },
  {
    id: "premium_monthly",
    description: "Premium — monthly",
    keys: ["STRIPE_PRICE_ID_PREMIUM_MONTHLY"],
    expectedUnitAmount: 2000,
    expectedInterval: "month",
  },
  {
    id: "premium_annual",
    description: "Premium — annual",
    keys: ["STRIPE_PRICE_ID_PREMIUM_ANNUAL"],
    expectedUnitAmount: 20000,
    expectedInterval: "year",
  },
  {
    id: "enterprise_monthly",
    description: "Enterprise — monthly",
    keys: ["STRIPE_PRICE_ID_ENTERPRISE_MONTHLY"],
    expectedUnitAmount: 3500,
    expectedInterval: "month",
    requireEnterpriseMeta: true,
  },
  {
    id: "enterprise_annual",
    description: "Enterprise — annual",
    keys: ["STRIPE_PRICE_ID_ENTERPRISE_ANNUAL"],
    expectedUnitAmount: 35000,
    expectedInterval: "year",
    requireEnterpriseMeta: true,
  },
  {
    id: "maximum_monthly",
    description: "Maximum — monthly",
    keys: ["STRIPE_PRICE_ID_MAXIMUM_MONTHLY"],
    expectedUnitAmount: 0,
    expectedInterval: "month",
  },
  {
    id: "maximum_annual",
    description: "Maximum — annual",
    keys: ["STRIPE_PRICE_ID_MAXIMUM_ANNUAL"],
    expectedUnitAmount: 0,
    expectedInterval: "year",
  },
]

function resolveSlot(slot: PriceSlot): { envKey?: string; value?: string } {
  for (const k of slot.keys) {
    const v = process.env[k]
    if (v && v.trim()) return { envKey: k, value: v.trim() }
  }
  return {}
}

export async function GET(request: NextRequest) {
  if (!(await authorize(request))) {
    return NextResponse.json(
      {
        error: "Authentication required. Sign in as admin or send X-API-Key header.",
        code: "session_required",
      },
      { status: 401 },
    )
  }

  const results: {
    stripe_configured: boolean
    trial_env: Record<string, { set: boolean; value?: string; ok?: boolean }>
    env_vars: Record<
      string,
      { set: boolean; resolvedFrom?: string; value?: string }
    >
    price_validation: Record<string, { valid: boolean; error?: string; price_data?: object }>
    metadata_check: Record<string, { has_metadata: boolean; metadata?: object }>
    summary: { total: number; configured: number; valid: number; issues: string[] }
  } = {
    stripe_configured: false,
    trial_env: {
      STANDARD_TRIAL_DAYS: {
        set: Boolean(process.env.STANDARD_TRIAL_DAYS),
        value: process.env.STANDARD_TRIAL_DAYS,
        ok: Number(process.env.STANDARD_TRIAL_DAYS || "0") === 3,
      },
      ELITE_SPEND_TRIAL_CAP_USD: {
        set: Boolean(process.env.ELITE_SPEND_TRIAL_CAP_USD),
        value: process.env.ELITE_SPEND_TRIAL_CAP_USD,
        ok: Number(process.env.ELITE_SPEND_TRIAL_CAP_USD || "0") === 3,
      },
    },
    env_vars: {},
    price_validation: {},
    metadata_check: {},
    summary: { total: PRICE_SLOTS.length, configured: 0, valid: 0, issues: [] },
  }

  if (!results.trial_env.STANDARD_TRIAL_DAYS.set) {
    results.summary.issues.push("STANDARD_TRIAL_DAYS not set (expected 3 on Vercel)")
  } else if (!results.trial_env.STANDARD_TRIAL_DAYS.ok) {
    results.summary.issues.push(
      `STANDARD_TRIAL_DAYS=${process.env.STANDARD_TRIAL_DAYS} (expected 3)`,
    )
  }
  if (!results.trial_env.ELITE_SPEND_TRIAL_CAP_USD.set) {
    results.summary.issues.push(
      "ELITE_SPEND_TRIAL_CAP_USD not set on this runtime (set on Vercel + Cloud Run)",
    )
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
      value: describeEnvValue(value),
    }

    if (!value) {
      results.summary.issues.push(`${slot.description}: no env set (tried ${slot.keys.join(", ")})`)
      continue
    }

    results.summary.configured++

    const formatError = envKey ? validatePriceIdFormat(envKey, value) : null
    if (formatError) {
      results.price_validation[slot.id] = { valid: false, error: formatError }
      results.summary.issues.push(formatError)
      continue
    }

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

      const amountMatches = slot.expectedUnitAmount === 0 || price.unit_amount === slot.expectedUnitAmount
      const intervalMatches = price.recurring?.interval === slot.expectedInterval
      if (!amountMatches) {
        results.price_validation[slot.id].valid = false
        results.summary.issues.push(
          `${slot.description}: expected ${slot.expectedUnitAmount} cents, got ${price.unit_amount ?? "null"}`,
        )
      }
      if (!intervalMatches) {
        results.price_validation[slot.id].valid = false
        results.summary.issues.push(
          `${slot.description}: expected interval ${slot.expectedInterval}, got ${price.recurring?.interval ?? "null"}`,
        )
      }

      if (typeof price.product === "object") {
        const product = price.product as Stripe.Product
        results.metadata_check[slot.id] = {
          has_metadata: Object.keys(product.metadata || {}).length > 0,
          metadata: product.metadata,
        }

        if (slot.requireEnterpriseMeta) {
          const minSeats = product.metadata?.min_seats
          if (!minSeats) {
            results.price_validation[slot.id].valid = false
            results.summary.issues.push(`${slot.description}: Missing 'min_seats' metadata`)
          } else if (minSeats !== EXPECTED_ENTERPRISE_MIN_SEATS) {
            results.price_validation[slot.id].valid = false
            results.summary.issues.push(
              `${slot.description}: min_seats=${minSeats} (expected ${EXPECTED_ENTERPRISE_MIN_SEATS})`,
            )
          }
          const tier = product.metadata?.tier
          if (!tier) {
            results.price_validation[slot.id].valid = false
            results.summary.issues.push(`${slot.description}: Missing 'tier' metadata`)
          } else if (tier !== EXPECTED_ENTERPRISE_TIER) {
            results.price_validation[slot.id].valid = false
            results.summary.issues.push(
              `${slot.description}: tier=${tier} (expected ${EXPECTED_ENTERPRISE_TIER})`,
            )
          }
        }
      }

      if (results.price_validation[slot.id].valid) {
        results.summary.valid++
      }
    } catch (error) {
      results.price_validation[slot.id] = {
        valid: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }
      results.summary.issues.push(`${slot.description}: Stripe could not load price — ${value.slice(0, 12)}...`)
    }
  }

  const allConfigured = results.summary.configured === results.summary.total
  const allValid = results.summary.valid === results.summary.total
  const trialOk =
    results.trial_env.STANDARD_TRIAL_DAYS.ok && results.trial_env.ELITE_SPEND_TRIAL_CAP_USD.set
  const status = allConfigured && allValid && trialOk ? 200 : 400

  return NextResponse.json(
    {
      ...results,
      overall_status:
        allConfigured && allValid && trialOk
          ? "✅ All configured correctly"
          : "⚠️ Issues found",
    },
    { status },
  )
}
