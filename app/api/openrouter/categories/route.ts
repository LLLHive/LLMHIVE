/**
 * GET /api/openrouter/categories
 * 
 * Returns OpenRouter categories for model browsing.
 * Uses fallback categories when backend is not available.
 */

import { NextRequest, NextResponse } from 'next/server'

// Fallback categories matching OpenRouter's category structure
const FALLBACK_CATEGORIES = [
  { id: 1, slug: 'programming', display_name: 'Programming', group: 'usecase', depth: 0, is_active: true },
  { id: 2, slug: 'science', display_name: 'Science', group: 'usecase', depth: 0, is_active: true },
  { id: 3, slug: 'health', display_name: 'Health', group: 'usecase', depth: 0, is_active: true },
  { id: 4, slug: 'legal', display_name: 'Legal', group: 'usecase', depth: 0, is_active: true },
  { id: 5, slug: 'marketing', display_name: 'Marketing', group: 'usecase', depth: 0, is_active: true },
  { id: 6, slug: 'technology', display_name: 'Technology', group: 'usecase', depth: 0, is_active: true },
  { id: 7, slug: 'finance', display_name: 'Finance', group: 'usecase', depth: 0, is_active: true },
  { id: 8, slug: 'academia', display_name: 'Academia', group: 'usecase', depth: 0, is_active: true },
  { id: 9, slug: 'roleplay', display_name: 'Roleplay', group: 'usecase', depth: 0, is_active: true },
  { id: 10, slug: 'creative-writing', display_name: 'Creative Writing', group: 'usecase', depth: 0, is_active: true },
  { id: 11, slug: 'translation', display_name: 'Translation', group: 'usecase', depth: 0, is_active: true },
  { id: 12, slug: 'reasoning', display_name: 'Reasoning', group: 'usecase', depth: 0, is_active: true },
]

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const group = searchParams.get('group') || 'usecase'
  
  // Filter categories by group
  const filteredCategories = FALLBACK_CATEGORIES.filter(cat => cat.group === group)
  
  return NextResponse.json({
    group,
    categories: filteredCategories,
    total: filteredCategories.length,
  })
}

