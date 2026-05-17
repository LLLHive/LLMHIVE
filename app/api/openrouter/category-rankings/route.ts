/**
 * GET /api/openrouter/category-rankings
 *
 * Returns top 10 models for a use-case category.
 * Rankings source: lib/marketing/usecase-category-rankings.ts (May 2026 benchmarks).
 */

import { NextRequest, NextResponse } from 'next/server'
import {
  getUsecaseCategoryRankings,
  USECASE_CATEGORY_ID_MAP,
  type UsecaseCategorySlug,
} from '@/lib/marketing/usecase-category-rankings'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const category = searchParams.get('category') || 'programming'
  const view = searchParams.get('view') || 'week'
  const limit = parseInt(searchParams.get('limit') || '10', 10)

  const rankings = getUsecaseCategoryRankings(category)
  const limitedRankings = rankings.slice(0, limit).map((entry) => ({
    ...entry,
    is_others_bucket: false,
  }))

  const categoryId =
    USECASE_CATEGORY_ID_MAP[category as UsecaseCategorySlug] ?? 1

  return NextResponse.json({
    category: {
      id: categoryId,
      slug: category,
      display_name: category.charAt(0).toUpperCase() + category.slice(1).replace(/-/g, ' '),
      group: 'usecase',
      depth: 0,
      is_active: true,
    },
    view,
    entries: limitedRankings,
    entry_count: limitedRankings.length,
    last_synced: new Date().toISOString(),
    data_source: 'LLMHive Rankings (May 2026)',
    description: `Top ${limit} models for ${category}`,
  })
}
