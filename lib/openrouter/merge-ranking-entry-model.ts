import type { OpenRouterRankingEntry } from "@/lib/openrouter/api"
import type { OpenRouterModel } from "@/lib/openrouter/types"

/**
 * Merge a live catalog record with a category ranking row when available.
 * Used on /models so model cards show full details when the model exists in the catalog.
 */
export function mergeRankingEntryWithCatalog(
  entry: OpenRouterRankingEntry,
  byId: Map<string, OpenRouterModel>
): OpenRouterModel {
  const existing = byId.get(entry.model_id)
  const meta = entry.model_metadata
  if (existing) {
    return { ...existing, name: entry.model_name || existing.name }
  }
  const p = meta?.pricing
  return {
    id: entry.model_id,
    name: entry.model_name,
    description: undefined,
    context_length: meta?.context_length,
    top_provider_max_tokens: undefined,
    architecture: { modality: "text" },
    pricing: {
      per_1m_prompt: p?.prompt,
      per_1m_completion: p?.completion,
      prompt: p?.prompt,
      completion: p?.completion,
    },
    capabilities: {
      supports_tools: meta?.supports_tools ?? false,
      supports_structured: meta?.supports_structured ?? false,
      supports_streaming: true,
      multimodal_input: meta?.multimodal_input ?? false,
      multimodal_output: false,
    },
    is_free: (p?.prompt ?? 0) === 0,
    availability_score: meta?.availability_score ?? 0,
    is_active: true,
  }
}
