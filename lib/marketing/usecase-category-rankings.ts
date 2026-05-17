/**
 * May 2026 Top-10 rankings for the 12 UI "Browse by Category" use-cases.
 *
 * Generated from benchmark_rankings_jan2026.py (RANKINGS_MAY_2026).
 * Regenerate: python3 scripts/sync_usecase_category_rankings.py
 */
import generated from './usecase-category-rankings.generated.json'

export type CategoryRankingEntry = {
  rank: number
  model_id: string
  model_name: string
  author: string
  score?: number
  benchmark?: string
  benchmark_category?: string
}

type GeneratedCategoryEntry = CategoryRankingEntry & {
  is_others_bucket: boolean
}

type GeneratedPayload = {
  categories: Record<string, GeneratedCategoryEntry[]>
  benchmark_mapping: Record<string, string>
}

const payload = generated as GeneratedPayload

/** Primary 12 UI categories (matches app/api/openrouter/categories/route.ts). */
export const UI_USECASE_CATEGORIES = [
  'programming',
  'science',
  'health',
  'legal',
  'marketing',
  'technology',
  'finance',
  'academia',
  'roleplay',
  'creative-writing',
  'translation',
  'reasoning',
] as const

export type UsecaseCategorySlug = (typeof UI_USECASE_CATEGORIES)[number]

function toEntry(row: GeneratedCategoryEntry): CategoryRankingEntry {
  return {
    rank: row.rank,
    model_id: row.model_id,
    model_name: row.model_name,
    author: row.author,
    score: row.score,
    benchmark: row.benchmark,
    benchmark_category: row.benchmark_category,
  }
}

/** Top-10 per use-case category, sorted strictly by benchmark score. */
export const USECASE_CATEGORY_RANKINGS: Record<UsecaseCategorySlug, CategoryRankingEntry[]> =
  Object.fromEntries(
    UI_USECASE_CATEGORIES.map((slug) => [
      slug,
      (payload.categories[slug] ?? []).map(toEntry),
    ])
  ) as Record<UsecaseCategorySlug, CategoryRankingEntry[]>

/** Legacy / internal aliases that reuse the 12 primary lists. */
export const USECASE_CATEGORY_ALIASES: Record<string, UsecaseCategorySlug> = {
  coding: 'programming',
  math: 'reasoning',
  analysis: 'science',
  code_generation: 'programming',
  debugging: 'programming',
  health_medical: 'health',
  legal_analysis: 'legal',
  financial_analysis: 'finance',
  science_research: 'science',
  creative_writing: 'creative-writing',
  research_analysis: 'academia',
  math_problem: 'reasoning',
}

export const USECASE_BENCHMARK_MAPPING = payload.benchmark_mapping

export const DEFAULT_USECASE_RANKINGS: CategoryRankingEntry[] =
  USECASE_CATEGORY_RANKINGS.science

export function getUsecaseCategoryRankings(
  categorySlug: string
): CategoryRankingEntry[] {
  const resolved =
    USECASE_CATEGORY_ALIASES[categorySlug] ??
    (categorySlug as UsecaseCategorySlug)

  return USECASE_CATEGORY_RANKINGS[resolved as UsecaseCategorySlug] ??
    DEFAULT_USECASE_RANKINGS
}

export const USECASE_CATEGORY_ID_MAP: Record<UsecaseCategorySlug, number> = {
  programming: 1,
  science: 2,
  health: 3,
  legal: 4,
  marketing: 5,
  technology: 6,
  finance: 7,
  academia: 8,
  roleplay: 9,
  'creative-writing': 10,
  translation: 11,
  reasoning: 12,
}
