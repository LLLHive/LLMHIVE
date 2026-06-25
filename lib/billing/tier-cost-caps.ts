import caps from "@/data/billing/tier_cost_caps.json"

const TIER_ALIASES: Record<string, string> = {
  basic: "lite",
  starter: "lite",
  standard: "lite",
  premium: "pro",
  maximum: "pro",
}

function normalizeTier(tier: string): string {
  const key = (tier || "free").toLowerCase().trim()
  return TIER_ALIASES[key] ?? key
}

export function perRequestMaxCostUsd(tier: string): number {
  const key = normalizeTier(tier)
  const table = caps.per_request_max_cost_usd as Record<string, number>
  return table[key] ?? table.free ?? 0.1
}

export function preferCheaperDefault(tier: string): boolean {
  const key = normalizeTier(tier)
  const table = caps.prefer_cheaper_default as Record<string, boolean>
  return Boolean(table[key])
}

export function resolvePerRequestMaxCostUsd(
  tier: string,
  requested?: number | null,
): number {
  if (typeof requested === "number" && requested > 0) {
    return requested
  }
  return perRequestMaxCostUsd(tier)
}
