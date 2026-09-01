import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/admin/auth"
import {
  UI_USECASE_CATEGORIES,
  getUsecaseCategoryRankings,
} from "@/lib/marketing/usecase-category-rankings"
import type { ModelRankingsDashboard, RankedModelEntry } from "@/lib/admin/types"

const CATEGORY_LABELS: Record<string, string> = {
  programming: "Programming",
  science: "Science",
  health: "Health",
  legal: "Legal",
  marketing: "Marketing",
  technology: "Technology",
  finance: "Finance",
  academia: "Academia",
  roleplay: "Roleplay",
  "creative-writing": "Creative Writing",
  translation: "Translation",
  reasoning: "Reasoning",
}

const KNOWN_MODELS_BASELINE = new Set([
  "anthropic/claude-sonnet-4",
  "openai/gpt-4o",
  "google/gemini-2.5-pro",
  "meta-llama/llama-3.3-70b-instruct",
  "deepseek/deepseek-chat-v3",
  "qwen/qwen-2.5-72b-instruct",
  "mistralai/mistral-large-2411",
])

function isFreeModel(modelId: string, modelName: string): boolean {
  const id = modelId.toLowerCase()
  const name = modelName.toLowerCase()
  return id.includes(":free") || id.includes("-free") || name.includes("free") || id.includes("/free")
}

function isNewModel(modelId: string): boolean {
  if (KNOWN_MODELS_BASELINE.has(modelId)) return false
  const lower = modelId.toLowerCase()
  return (
    lower.includes("2026") ||
    lower.includes("k2.6") ||
    lower.includes("qwen3") ||
    lower.includes("gemini-2.5") ||
    lower.includes("claude-4") ||
    lower.includes("gpt-5") ||
    lower.includes("deepseek-v3") ||
    !KNOWN_MODELS_BASELINE.has(modelId)
  )
}

export async function GET() {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const byCategory: ModelRankingsDashboard["byCategory"] = []
  const allNewModels: RankedModelEntry[] = []
  let freeCount = 0
  let paidCount = 0
  const seenNew = new Set<string>()

  for (const slug of UI_USECASE_CATEGORIES) {
    const rankings = getUsecaseCategoryRankings(slug)
    const entries: RankedModelEntry[] = rankings.slice(0, 10).map((entry) => {
      const free = isFreeModel(entry.model_id, entry.model_name)
      const isNew = isNewModel(entry.model_id)
      if (free) freeCount++
      else paidCount++

      const ranked: RankedModelEntry = {
        rank: entry.rank,
        modelId: entry.model_id,
        modelName: entry.model_name,
        author: entry.author,
        category: slug,
        categoryLabel: CATEGORY_LABELS[slug] ?? slug,
        score: entry.score,
        isFree: free,
        isNew,
      }

      if (isNew && !seenNew.has(entry.model_id)) {
        seenNew.add(entry.model_id)
        allNewModels.push(ranked)
      }

      return ranked
    })

    byCategory.push({
      slug,
      label: CATEGORY_LABELS[slug] ?? slug,
      entries,
      newCount: entries.filter((e) => e.isNew).length,
    })
  }

  const dashboard: ModelRankingsDashboard = {
    summary: {
      totalCategories: UI_USECASE_CATEGORIES.length,
      totalRankedModels: byCategory.reduce((s, c) => s + c.entries.length, 0),
      newModelsCount: allNewModels.length,
      freeInTop10: freeCount,
      paidInTop10: paidCount,
      lastSynced: new Date().toISOString(),
    },
    newModels: allNewModels.sort((a, b) => (b.score ?? 0) - (a.score ?? 0)),
    byCategory,
    freeVsPaid: { free: freeCount, paid: paidCount },
  }

  return NextResponse.json(dashboard)
}
