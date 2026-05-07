/**
 * Resolves Stripe Price IDs from environment variables.
 *
 * Customer-facing checkout must use the current product price IDs.
 * Do not fall back to legacy BASIC/PRO for Standard/Premium: those may point
 * at old price points and silently overcharge.
 */

function pickFirstPriceId(...candidates: (string | undefined)[]): string | undefined {
  for (const id of candidates) {
    if (id && id.trim().length > 0) return id.trim()
  }
  return undefined
}

export function stripeStandardMonthlyPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_STANDARD_MONTHLY)
}

export function stripeStandardAnnualPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_STANDARD_ANNUAL)
}

export function stripePremiumMonthlyPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_PREMIUM_MONTHLY)
}

export function stripePremiumAnnualPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_PREMIUM_ANNUAL)
}

export function stripeEnterpriseMonthlyPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY)
}

export function stripeEnterpriseAnnualPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL)
}

export function stripeMaximumMonthlyPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_MAXIMUM_MONTHLY)
}

export function stripeMaximumAnnualPriceId(): string | undefined {
  return pickFirstPriceId(process.env.STRIPE_PRICE_ID_MAXIMUM_ANNUAL)
}

/** Maps every configured Stripe price id → internal subscription tier key (lite/pro/enterprise/maximum). */
export function buildStripePriceIdToTierMap(): Record<string, string> {
  const map: Record<string, string> = {}
  const add = (id: string | undefined, tier: string) => {
    if (id) map[id] = tier
  }
  add(stripeStandardMonthlyPriceId(), "lite")
  add(stripeStandardAnnualPriceId(), "lite")
  add(stripePremiumMonthlyPriceId(), "pro")
  add(stripePremiumAnnualPriceId(), "pro")
  add(stripeEnterpriseMonthlyPriceId(), "enterprise")
  add(stripeEnterpriseAnnualPriceId(), "enterprise")
  add(stripeMaximumMonthlyPriceId(), "maximum")
  add(stripeMaximumAnnualPriceId(), "maximum")
  return map
}
