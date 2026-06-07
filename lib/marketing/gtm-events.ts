import { isGtmEnabled } from "@/lib/marketing/gtm"

export type GtmPurchasePayload = {
  transactionId: string
  value: number
  currency: string
  tier: string
  billingCycle: string
}

const PURCHASE_DEDUP_PREFIX = "gtm_purchase_tracked:"

function planItemName(tier: string, billingCycle: string): string {
  const names: Record<string, string> = {
    lite: "Standard",
    pro: "Premium",
    enterprise: "Enterprise",
    maximum: "Maximum",
  }
  const plan = names[tier.toLowerCase()] ?? tier
  const cycle = billingCycle === "annual" ? "Annual" : "Monthly"
  return `${plan} ${cycle}`
}

/** Push GA4-compatible purchase event for GTM (Event Manager / conversion tags). */
export function pushGtmPurchase(payload: GtmPurchasePayload): void {
  if (typeof window === "undefined" || !isGtmEnabled()) return

  const dedupKey = `${PURCHASE_DEDUP_PREFIX}${payload.transactionId}`
  try {
    if (sessionStorage.getItem(dedupKey)) return
    sessionStorage.setItem(dedupKey, "1")
  } catch {
    // sessionStorage unavailable — still fire once per mount via component ref
  }

  const w = window as Window & { dataLayer?: Record<string, unknown>[] }
  w.dataLayer = w.dataLayer ?? []

  // GA4 ecommerce: clear prior object before a new purchase push
  w.dataLayer.push({ ecommerce: null })
  w.dataLayer.push({
    event: "purchase",
    ecommerce: {
      transaction_id: payload.transactionId,
      value: payload.value,
      currency: payload.currency,
      items: [
        {
          item_id: `${payload.tier}_${payload.billingCycle}`,
          item_name: planItemName(payload.tier, payload.billingCycle),
          item_category: "subscription",
          price: payload.value,
          quantity: 1,
        },
      ],
    },
    plan_tier: payload.tier,
    billing_cycle: payload.billingCycle,
  })
}
