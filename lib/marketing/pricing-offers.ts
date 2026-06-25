/**
 * Canonical GTM offer copy: Standard, Premium, and Enterprise only.
 * Use these lists everywhere user-facing plans are described (pricing, landing, promo, etc.).
 */

export const OFFER_STANDARD_FEATURES: readonly string[] = [
  "Elite orchestration while the spend guard allows, then free orchestration",
  "Multi-model consensus routing",
  "Knowledge Base access",
  "Calculator & hosted reranker",
  "90-day conversation memory",
]

export const OFFER_PREMIUM_FEATURES: readonly string[] = [
  "Elite orchestration while the spend guard allows, then free orchestration",
  "Benchmark-leading routing on Premium workloads",
  "DeepConf, adaptive ensemble & advanced strategies",
  "90-day conversation memory",
]

export const OFFER_ENTERPRISE_FEATURES: readonly string[] = [
  "Single flagship model pick — choose one frontier model per request",
  "400 Premium orchestration queries / seat / month, then unlimited Standard",
  "Minimum 5 seats ($175+/mo)",
  "SSO / SAML & org-level admin",
  "1-year retention, audit logs & compliance tooling",
  "Team workspaces, shared memory & admin tools",
  "Dedicated account manager",
]

/** Shorter lists for dense marketing cards (e.g. promo grid). */
export const OFFER_PROMO_BULLET_CAP = 6

export function offerPromoBullets(features: readonly string[]): string[] {
  return features.slice(0, OFFER_PROMO_BULLET_CAP)
}
