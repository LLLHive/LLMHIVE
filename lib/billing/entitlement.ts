const BACKEND_URL =
  process.env.ORCHESTRATOR_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

const PAID_TIERS = new Set(["lite", "basic", "starter", "standard", "pro", "premium", "enterprise", "maximum"])

export interface EntitlementResult {
  hasPaidAccess: boolean
  tier: string
  status: string
}

export async function getPaidEntitlement(userId: string): Promise<EntitlementResult> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/billing/subscription/${encodeURIComponent(userId)}`, {
      headers: {
        ...(process.env.LLMHIVE_API_KEY ? { "X-API-Key": process.env.LLMHIVE_API_KEY } : {}),
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    })

    if (!response.ok) {
      return { hasPaidAccess: false, tier: "free", status: "none" }
    }

    const data = await response.json()
    const tier = String(data.tier_name || data.tier || "free").toLowerCase()
    const status = String(data.status || "none").toLowerCase()

    return {
      hasPaidAccess: status === "active" && PAID_TIERS.has(tier),
      tier,
      status,
    }
  } catch (error) {
    console.error("[Entitlement] Failed to verify paid access:", error)
    return { hasPaidAccess: false, tier: "free", status: "unknown" }
  }
}

export function paymentRequiredResponse() {
  return {
    error: "Payment required",
    details: "Your account is not active yet. Complete checkout to use LLMHive.",
    checkoutUrl: "/pricing?subscribe=pro&cycle=monthly&payment_required=1",
  }
}
