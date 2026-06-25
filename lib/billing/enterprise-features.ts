/**
 * Enterprise-only product capabilities (billing / orchestration).
 */

export const ENTERPRISE_SINGLE_FLAGSHIP_PICK_LABEL =
  "Upgrade to Enterprise for single flagship pick"

export const ENTERPRISE_SINGLE_FLAGSHIP_PICK_FEATURE =
  "Single flagship model pick"

export function isEnterpriseSubscriptionTier(tier: string): boolean {
  const key = (tier || "free").toLowerCase().trim()
  return key === "enterprise" || key === "maximum"
}

/** Manual model pick and Single agent mode — Enterprise only. */
export function canUseSingleFlagshipPick(subscriptionTier: string): boolean {
  return isEnterpriseSubscriptionTier(subscriptionTier)
}

export function isExplicitModelSelection(
  selectedModels?: string[] | null,
): boolean {
  if (!selectedModels?.length) return false
  return !selectedModels.every(
    (m) => m === "automatic" || m === "auto" || !m?.trim(),
  )
}

export type ModelSelectionSanitizeResult = {
  agentMode: "team" | "single"
  selectedModels: string[]
  gated: boolean
}

/** Force Team + Automatic when the account is not Enterprise. */
export function sanitizeModelSelectionForTier(
  settings: {
    agentMode?: string | null
    selectedModels?: string[] | null
  },
  subscriptionTier: string,
): ModelSelectionSanitizeResult {
  if (canUseSingleFlagshipPick(subscriptionTier)) {
    const agentMode = settings.agentMode === "single" ? "single" : "team"
    const selectedModels =
      settings.selectedModels && settings.selectedModels.length > 0
        ? settings.selectedModels
        : ["automatic"]
    return { agentMode, selectedModels, gated: false }
  }

  const hadExplicit =
    settings.agentMode === "single" || isExplicitModelSelection(settings.selectedModels)

  return {
    agentMode: "team",
    selectedModels: ["automatic"],
    gated: hadExplicit,
  }
}
