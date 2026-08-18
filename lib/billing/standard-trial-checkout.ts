/**
 * Standard (lite) monthly trial Checkout flags.
 *
 * Default: card required (historic Stripe Checkout with payment_method_types=["card"]).
 * No-card campaign: payment_method_collection=if_required and cancel at trial end
 * if no payment method was collected.
 */

export type CheckoutPaymentMode = "card_required" | "no_card_trial"

export function isStandardMonthlyTrial(
  tier: string | undefined,
  billingCycle: string | undefined,
  trialDays: number
): boolean {
  const t = (tier || "").toLowerCase()
  const cycle = (billingCycle || "").toLowerCase()
  return (
    trialDays > 0 &&
    cycle === "monthly" &&
    (t === "lite" || t === "standard" || t === "basic" || t === "starter")
  )
}

export function resolveCheckoutPaymentMode(opts: {
  tier: string
  billingCycle: string
  trialDays: number
  trialWithoutCardRequested: boolean
}): CheckoutPaymentMode {
  if (
    opts.trialWithoutCardRequested &&
    isStandardMonthlyTrial(opts.tier, opts.billingCycle, opts.trialDays)
  ) {
    return "no_card_trial"
  }
  return "card_required"
}

export function stripeTrialSettingsForNoCard(): {
  end_behavior: { missing_payment_method: "cancel" }
} {
  return {
    end_behavior: { missing_payment_method: "cancel" },
  }
}

export function campaignCancelUrl(siteUrl: string, cancelPath: unknown): string | null {
  if (typeof cancelPath !== "string") return null
  if (!cancelPath.startsWith("/") || cancelPath.startsWith("//")) return null
  if (cancelPath.includes("://") || cancelPath.includes("\\")) return null
  const origin = siteUrl.replace(/\/$/, "")
  return `${origin}${cancelPath}`
}
