const BACKEND_URL =
  process.env.ORCHESTRATOR_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

const PAID_TIERS = new Set(["lite", "basic", "starter", "standard", "pro", "premium", "enterprise", "maximum"])

export interface EntitlementResult {
  /** Active paid plan (Standard, Premium, Enterprise, …). */
  hasPaidAccess: boolean
  /** App + free orchestration — paid plan or explicitly provisioned free tier. */
  hasAppAccess: boolean
  tier: string
  status: string
}

function buildEntitlement(tier: string, status: string): EntitlementResult {
  const tierLower = tier.toLowerCase()
  const statusLower = status.toLowerCase()
  const isActive = statusLower === "active"
  const hasPaidAccess = isActive && PAID_TIERS.has(tierLower)
  const hasAppAccess = isActive && (PAID_TIERS.has(tierLower) || tierLower === "free")
  return { hasPaidAccess, hasAppAccess, tier: tierLower, status: statusLower }
}

async function fetchEntitlementOnce(userId: string): Promise<EntitlementResult> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/billing/subscription/${encodeURIComponent(userId)}`, {
      headers: {
        ...(process.env.LLMHIVE_API_KEY ? { "X-API-Key": process.env.LLMHIVE_API_KEY } : {}),
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    })

    if (!response.ok) {
      return buildEntitlement("free", "none")
    }

    const data = await response.json()
    const tier = String(data.tier_name || data.tier || "free")
    const status = String(data.status || "none")
    return buildEntitlement(tier, status)
  } catch (error) {
    console.error("[Entitlement] Failed to verify paid access:", error)
    return buildEntitlement("free", "unknown")
  }
}

// Webhook delivery from Stripe is async and can lag the user's redirect back
// to the app by a few seconds. The synchronous "ensure-subscription" call on
// the success page closes most of that gap, but a single short retry here is a
// cheap safety net that prevents any residual race from bouncing a paying user
// to /pricing. Cost: only paid loads with a stale Firestore read hit the
// retry; unpaid users hit it once before being redirected, which is fine.
export async function getPaidEntitlement(userId: string): Promise<EntitlementResult> {
  const first = await fetchEntitlementOnce(userId)
  if (first.hasAppAccess) return first

  // Only retry when the failure looks like "subscription not visible yet",
  // not when the user has an explicit paid-but-bad status (past_due, canceled).
  const racey = first.status === "none" || first.status === "inactive" || first.status === "unknown"
  if (!racey) return first

  await new Promise((r) => setTimeout(r, 1500))
  return fetchEntitlementOnce(userId)
}

/**
 * Lightweight entitlement check intended for public marketing pages where
 * latency matters (most visitors are anonymous). Single fetch, short timeout,
 * fails open as "no paid access" so the page always renders quickly.
 *
 * Use this on `/` (landing) so the CTA can be tailored:
 *   - signed-in + app access (paid or free) -> "Open app" / redirect to /app
 *   - signed-in + no subscription -> "Choose a plan"
 *   - not signed-in -> "Get started"
 */
export async function getPaidEntitlementFast(userId: string): Promise<EntitlementResult> {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/v1/billing/subscription/${encodeURIComponent(userId)}`,
      {
        headers: {
          ...(process.env.LLMHIVE_API_KEY ? { "X-API-Key": process.env.LLMHIVE_API_KEY } : {}),
        },
        cache: "no-store",
        signal: AbortSignal.timeout(2_500),
      },
    )

    if (!response.ok) {
      return buildEntitlement("free", "none")
    }

    const data = await response.json()
    const tier = String(data.tier_name || data.tier || "free")
    const status = String(data.status || "none")
    return buildEntitlement(tier, status)
  } catch {
    return buildEntitlement("free", "unknown")
  }
}

export function paymentRequiredResponse(status?: string) {
  const statusLower = (status || "").toLowerCase()
  const isPastDue = statusLower === "past_due"
  const checkoutUrl = isPastDue
    ? "/pricing?payment_required=1&reason=past_due"
    : "/pricing?payment_required=1"

  return {
    error: "Subscription required",
    details: isPastDue
      ? "Your latest renewal payment failed. Update your payment method to restore access."
      : "Your account does not have app access yet. Subscribe on Pricing or contact support if you were invited with free access.",
    checkoutUrl,
    status: statusLower || "none",
  }
}

export function paidAccessRedirectUrl(status?: string): string {
  const statusLower = (status || "").toLowerCase()
  if (statusLower === "past_due") {
    return "/pricing?payment_required=1&reason=past_due"
  }
  return "/pricing?payment_required=1"
}
