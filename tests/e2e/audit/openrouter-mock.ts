/**
 * OpenRouter API Mocks for UI Audit
 * 
 * Provides deterministic mock data for testing OpenRouter integration.
 * This allows tests to run without external API dependencies.
 */

import { Page, Route } from '@playwright/test'
import {
  getUsecaseCategoryRankings,
  UI_USECASE_CATEGORIES,
} from '@/lib/marketing/usecase-category-rankings'

function buildBenchmarkRankings(category: string, displayName: string) {
  const entries = getUsecaseCategoryRankings(category).map((entry) => ({
    rank: entry.rank,
    model_id: entry.model_id,
    model_name: entry.model_name,
    author: entry.author.toLowerCase(),
    score: entry.score,
    benchmark: entry.benchmark,
    is_others_bucket: false,
  }))

  return {
    category: {
      slug: category,
      display_name: displayName,
      group: 'usecase',
      depth: category.includes('/') ? 1 : 0,
    },
    view: 'week',
    entries,
    entry_count: entries.length,
    last_synced: new Date().toISOString(),
    data_source: 'LLMHive Rankings (May 2026)',
  }
}

const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  programming: 'Programming',
  science: 'Science',
  health: 'Health',
  legal: 'Legal',
  marketing: 'Marketing',
  technology: 'Technology',
  finance: 'Finance',
  academia: 'Academia',
  roleplay: 'Roleplay',
  'creative-writing': 'Creative Writing',
  translation: 'Translation',
  reasoning: 'Reasoning',
}

// Complete category list matching OpenRouter
export const MOCK_CATEGORIES = {
  group: 'usecase',
  categories: [
    { id: 1, slug: 'programming', display_name: 'Programming', group: 'usecase', depth: 0, is_active: true },
    { id: 2, slug: 'science', display_name: 'Science', group: 'usecase', depth: 0, is_active: true },
    { id: 3, slug: 'health', display_name: 'Health', group: 'usecase', depth: 0, is_active: true },
    { id: 4, slug: 'legal', display_name: 'Legal', group: 'usecase', depth: 0, is_active: true },
    { id: 5, slug: 'marketing', display_name: 'Marketing', group: 'usecase', depth: 0, is_active: true, children: [
      { id: 6, slug: 'marketing/seo', display_name: 'SEO', group: 'usecase', parent_slug: 'marketing', depth: 1, is_active: true },
      { id: 7, slug: 'marketing/content', display_name: 'Content', group: 'usecase', parent_slug: 'marketing', depth: 1, is_active: true },
    ]},
    { id: 8, slug: 'technology', display_name: 'Technology', group: 'usecase', depth: 0, is_active: true },
    { id: 9, slug: 'finance', display_name: 'Finance', group: 'usecase', depth: 0, is_active: true },
    { id: 10, slug: 'academia', display_name: 'Academia', group: 'usecase', depth: 0, is_active: true },
    { id: 11, slug: 'roleplay', display_name: 'Roleplay', group: 'usecase', depth: 0, is_active: true },
    { id: 12, slug: 'creative-writing', display_name: 'Creative Writing', group: 'usecase', depth: 0, is_active: true },
    { id: 13, slug: 'translation', display_name: 'Translation', group: 'usecase', depth: 0, is_active: true },
    { id: 14, slug: 'customer-support', display_name: 'Customer Support', group: 'usecase', depth: 0, is_active: true },
    { id: 15, slug: 'data-analysis', display_name: 'Data Analysis', group: 'usecase', depth: 0, is_active: true },
  ],
  total: 15,
  data_source: 'openrouter_rankings',
}

// Expected categories as a flat list for validation
export const EXPECTED_CATEGORY_SLUGS = [
  'programming', 'science', 'health', 'legal', 'marketing',
  'marketing/seo', 'marketing/content', 'technology', 'finance',
  'academia', 'roleplay', 'creative-writing', 'translation',
  'customer-support', 'data-analysis',
]

// Top 10 rankings for each category (benchmark score order)
export const MOCK_RANKINGS: Record<string, any> = Object.fromEntries(
  UI_USECASE_CATEGORIES.map((slug) => [
    slug,
    buildBenchmarkRankings(slug, CATEGORY_DISPLAY_NAMES[slug] ?? slug),
  ])
)

// Sub-categories inherit parent marketing benchmark order
MOCK_RANKINGS['marketing/seo'] = buildBenchmarkRankings('marketing', 'SEO')
MOCK_RANKINGS['marketing/content'] = buildBenchmarkRankings('marketing', 'Content')
MOCK_RANKINGS['customer-support'] = buildBenchmarkRankings('roleplay', 'Customer Support')
MOCK_RANKINGS['data-analysis'] = buildBenchmarkRankings('science', 'Data Analysis')

// Mock models list
export const MOCK_MODELS = {
  models: [
    { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'openai', context_length: 128000, pricing: { per_1m_prompt: 2.5, per_1m_completion: 10 } },
    { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'openai', context_length: 128000, pricing: { per_1m_prompt: 0.15, per_1m_completion: 0.6 } },
    { id: 'openai/o1', name: 'o1', provider: 'openai', context_length: 128000, pricing: { per_1m_prompt: 15, per_1m_completion: 60 } },
    { id: 'anthropic/claude-sonnet-4-20250514', name: 'Claude Sonnet 4', provider: 'anthropic', context_length: 200000, pricing: { per_1m_prompt: 3, per_1m_completion: 15 } },
    { id: 'anthropic/claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', provider: 'anthropic', context_length: 200000, pricing: { per_1m_prompt: 3, per_1m_completion: 15 } },
    { id: 'anthropic/claude-3-opus-20240229', name: 'Claude 3 Opus', provider: 'anthropic', context_length: 200000, pricing: { per_1m_prompt: 15, per_1m_completion: 75 } },
    { id: 'google/gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'google', context_length: 1000000, pricing: { per_1m_prompt: 2.5, per_1m_completion: 10 } },
    { id: 'deepseek/deepseek-chat', name: 'DeepSeek Chat', provider: 'deepseek', context_length: 128000, pricing: { per_1m_prompt: 0.14, per_1m_completion: 0.28 } },
    { id: 'meta/llama-3.3-70b-instruct', name: 'Llama 3.3 70B', provider: 'meta', context_length: 128000, pricing: { per_1m_prompt: 0.4, per_1m_completion: 0.4 } },
  ],
  total: 9,
}

/**
 * Sets up all OpenRouter API mocks for the page
 */
export async function setupOpenRouterMocks(page: Page): Promise<void> {
  // Mock categories endpoint
  await page.route('**/api/openrouter/categories*', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_CATEGORIES),
    })
  })

  // Mock category rankings endpoint
  await page.route('**/api/openrouter/category-rankings*', async (route: Route) => {
    const url = new URL(route.request().url())
    const category = url.searchParams.get('category') || 'programming'
    const rankings = MOCK_RANKINGS[category] || MOCK_RANKINGS.programming
    
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(rankings),
    })
  })

  // Mock legacy rankings endpoint (internal telemetry)
  await page.route('**/api/openrouter/rankings*', async (route: Route) => {
    const url = route.request().url()
    if (url.includes('/rankings/')) {
      // Dimension-based ranking
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          dimension: 'trending',
          time_range: '7d',
          data: MOCK_RANKINGS.programming.entries,
          generated_at: new Date().toISOString(),
        }),
      })
    } else {
      // Rankings list
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          dimensions: ['trending', 'most_used', 'best_value'],
          time_ranges: ['24h', '7d', '30d', 'all'],
          data_source: 'internal_telemetry',
        }),
      })
    }
  })

  // Mock models endpoint
  await page.route('**/api/openrouter/models*', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_MODELS),
    })
  })

  // Mock rankings sync endpoint (return success without mutation)
  await page.route('**/api/openrouter/rankings/sync*', async (route: Route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'mocked',
          message: 'Sync mocked for testing - no changes made',
        }),
      })
    } else {
      await route.continue()
    }
  })

  // Mock rankings status endpoint
  await page.route('**/api/openrouter/rankings/status*', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        categories: { total: 15, active: 15 },
        snapshots: { total: 150, successful: 148 },
        last_sync: {
          sync_type: 'rankings_full',
          status: 'success',
          started_at: new Date(Date.now() - 3600000).toISOString(),
          completed_at: new Date(Date.now() - 3500000).toISOString(),
          duration_seconds: 100,
        },
        last_snapshot_at: new Date().toISOString(),
      }),
    })
  })
}

/**
 * Sets up chat API mock for clarifying questions flow
 */
export async function setupClarifyingQuestionsMock(page: Page): Promise<void> {
  let questionAsked = false
  
  await page.route('**/api/chat', async (route: Route) => {
    const body = route.request().postDataJSON()
    const message = body?.messages?.slice(-1)[0]?.content || ''
    
    // First message triggers clarifying question
    if (!questionAsked && message.toLowerCase().includes('ambiguous')) {
      questionAsked = true
      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Clarifying-Question': 'true',
          'X-Models-Used': '["gpt-4o"]',
        },
        body: 'I need some clarification. Could you please specify which aspect you\'re interested in?\n\n1. Technical details\n2. Business implications\n3. General overview',
      })
    } else {
      // Follow-up gets full response
      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '250',
        },
        body: 'Thank you for the clarification! Here is a detailed response based on your preference...',
      })
    }
  })
}

