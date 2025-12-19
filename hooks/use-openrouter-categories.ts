/**
 * Shared Hook for OpenRouter Categories and Rankings
 * 
 * Single source of truth for category/ranking data across all UI surfaces.
 * Ensures parity between Models page, Chat dropdown, and any other consumers.
 */

import * as React from "react"
import { 
  listCategories, 
  getCategoryRankings,
  type OpenRouterCategory,
  type CategoryRankingsResponse,
  type OpenRouterRankingEntry,
} from "@/lib/openrouter/api"

// =============================================================================
// Types
// =============================================================================

export interface CategoryWithIcon {
  slug: string
  displayName: string
  group: string
  depth: number
  parentSlug?: string
  isActive: boolean
  children?: CategoryWithIcon[]
}

export interface UseCategoriesResult {
  categories: CategoryWithIcon[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export interface UseRankingsResult {
  rankings: OpenRouterRankingEntry[]
  category: OpenRouterCategory | null
  loading: boolean
  error: string | null
  lastSynced: string | null
  refresh: () => Promise<void>
}

// =============================================================================
// Category Icons Mapping (shared across all components)
// =============================================================================

export const CATEGORY_ICON_MAP: Record<string, string> = {
  // Use Lucide icon names as strings
  'programming': 'Code',
  'science': 'FlaskConical',
  'health': 'Heart',
  'legal': 'Scale',
  'marketing': 'Megaphone',
  'marketing/seo': 'Search',
  'marketing/content': 'MessageSquare',
  'marketing/social-media': 'Users',
  'technology': 'Cpu',
  'finance': 'Landmark',
  'academia': 'GraduationCap',
  'roleplay': 'Users',
  'creative-writing': 'MessageSquare',
  'customer-support': 'Users',
  'translation': 'Languages',
  'data-analysis': 'BarChart3',
  'long-context': 'MessageSquare',
  'tool-use': 'Wrench',
  'vision': 'Image',
  'reasoning': 'FlaskConical',
  // Legacy dimension mappings for compatibility
  'leaderboard': 'BarChart3',
  'market_share': 'PieChart',
  'trending': 'TrendingUp',
  'tools_agents': 'Wrench',
  'images': 'Image',
  'long_context': 'MessageSquare',
  'fastest': 'Zap',
  'lowest_cost': 'DollarSign',
}

export const CATEGORY_COLOR_MAP: Record<string, string> = {
  'programming': 'text-violet-500',
  'science': 'text-cyan-500',
  'health': 'text-red-500',
  'legal': 'text-gray-500',
  'marketing': 'text-orange-500',
  'marketing/seo': 'text-teal-500',
  'technology': 'text-slate-500',
  'finance': 'text-emerald-500',
  'academia': 'text-amber-600',
  'roleplay': 'text-pink-500',
  'creative-writing': 'text-purple-500',
  'translation': 'text-sky-500',
}

// =============================================================================
// Fallback Categories (used when API is unavailable)
// =============================================================================

const FALLBACK_CATEGORIES: CategoryWithIcon[] = [
  { slug: 'programming', displayName: 'Programming', group: 'usecase', depth: 0, isActive: true },
  { slug: 'science', displayName: 'Science', group: 'usecase', depth: 0, isActive: true },
  { slug: 'health', displayName: 'Health', group: 'usecase', depth: 0, isActive: true },
  { slug: 'legal', displayName: 'Legal', group: 'usecase', depth: 0, isActive: true },
  { slug: 'marketing', displayName: 'Marketing', group: 'usecase', depth: 0, isActive: true },
  { slug: 'technology', displayName: 'Technology', group: 'usecase', depth: 0, isActive: true },
  { slug: 'finance', displayName: 'Finance', group: 'usecase', depth: 0, isActive: true },
  { slug: 'academia', displayName: 'Academia', group: 'usecase', depth: 0, isActive: true },
  { slug: 'roleplay', displayName: 'Roleplay', group: 'usecase', depth: 0, isActive: true },
  { slug: 'creative-writing', displayName: 'Creative Writing', group: 'usecase', depth: 0, isActive: true },
  { slug: 'translation', displayName: 'Translation', group: 'usecase', depth: 0, isActive: true },
]

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook for fetching OpenRouter categories.
 * Caches categories in memory and provides consistent data across components.
 */
export function useOpenRouterCategories(
  options: { 
    group?: 'usecase' | 'language' | 'programming'
    autoFetch?: boolean
  } = {}
): UseCategoriesResult {
  const { group = 'usecase', autoFetch = true } = options
  
  const [categories, setCategories] = React.useState<CategoryWithIcon[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  
  const fetchCategories = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await listCategories({ group })
      
      // Transform API response to CategoryWithIcon format
      const transformed: CategoryWithIcon[] = response.categories.map(cat => ({
        slug: cat.slug,
        displayName: cat.display_name,
        group: cat.group,
        depth: cat.depth,
        parentSlug: cat.parent_slug,
        isActive: cat.is_active,
        children: cat.children?.map(child => ({
          slug: child.slug,
          displayName: child.display_name,
          group: child.group,
          depth: child.depth,
          parentSlug: child.parent_slug,
          isActive: child.is_active,
        })),
      }))
      
      setCategories(transformed)
    } catch (e) {
      console.error('Failed to fetch OpenRouter categories:', e)
      setError(e instanceof Error ? e.message : 'Failed to fetch categories')
      // Use fallback categories on error
      setCategories(FALLBACK_CATEGORIES)
    } finally {
      setLoading(false)
    }
  }, [group])
  
  React.useEffect(() => {
    if (autoFetch) {
      fetchCategories()
    }
  }, [autoFetch, fetchCategories])
  
  return {
    categories,
    loading,
    error,
    refresh: fetchCategories,
  }
}

/**
 * Hook for fetching rankings for a specific category.
 * Uses OpenRouter's category rankings API (not internal telemetry).
 */
export function useCategoryRankings(
  categorySlug: string | null,
  options: {
    view?: 'week' | 'month' | 'day' | 'all'
    limit?: number
    autoFetch?: boolean
  } = {}
): UseRankingsResult {
  const { view = 'week', limit = 10, autoFetch = true } = options
  
  const [rankings, setRankings] = React.useState<OpenRouterRankingEntry[]>([])
  const [category, setCategory] = React.useState<OpenRouterCategory | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [lastSynced, setLastSynced] = React.useState<string | null>(null)
  
  const fetchRankings = React.useCallback(async () => {
    if (!categorySlug) {
      setRankings([])
      setCategory(null)
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await getCategoryRankings(categorySlug, { view, limit })
      setRankings(response.entries || [])
      setCategory(response.category)
      setLastSynced(response.last_synced || null)
    } catch (e) {
      console.error('Failed to fetch category rankings:', e)
      setError(e instanceof Error ? e.message : 'Failed to fetch rankings')
      setRankings([])
    } finally {
      setLoading(false)
    }
  }, [categorySlug, view, limit])
  
  React.useEffect(() => {
    if (autoFetch && categorySlug) {
      fetchRankings()
    }
  }, [autoFetch, categorySlug, fetchRankings])
  
  return {
    rankings,
    category,
    loading,
    error,
    lastSynced,
    refresh: fetchRankings,
  }
}

/**
 * Combined hook for category selection with auto-loaded rankings.
 * Convenience hook for UIs that need both category list and rankings.
 */
export function useOpenRouterCategoriesWithRankings(
  options: {
    defaultCategory?: string
    group?: 'usecase' | 'language' | 'programming'
    view?: 'week' | 'month' | 'day' | 'all'
    limit?: number
  } = {}
) {
  const { defaultCategory = 'programming', group = 'usecase', view = 'week', limit = 10 } = options
  
  const [selectedCategory, setSelectedCategory] = React.useState<string>(defaultCategory)
  
  const categoriesResult = useOpenRouterCategories({ group })
  const rankingsResult = useCategoryRankings(selectedCategory, { view, limit })
  
  return {
    // Categories
    categories: categoriesResult.categories,
    categoriesLoading: categoriesResult.loading,
    categoriesError: categoriesResult.error,
    refreshCategories: categoriesResult.refresh,
    
    // Selected category state
    selectedCategory,
    setSelectedCategory,
    
    // Rankings for selected category
    rankings: rankingsResult.rankings,
    rankingsLoading: rankingsResult.loading,
    rankingsError: rankingsResult.error,
    lastSynced: rankingsResult.lastSynced,
    refreshRankings: rankingsResult.refresh,
  }
}

