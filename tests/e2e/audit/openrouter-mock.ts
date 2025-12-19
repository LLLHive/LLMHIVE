/**
 * OpenRouter API Mocks for UI Audit
 * 
 * Provides deterministic mock data for testing OpenRouter integration.
 * This allows tests to run without external API dependencies.
 */

import { Page, Route } from '@playwright/test'

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

// Top 10 rankings for each category
export const MOCK_RANKINGS: Record<string, any> = {
  programming: {
    category: { slug: 'programming', display_name: 'Programming', group: 'usecase', depth: 0 },
    view: 'week',
    entries: [
      { rank: 1, model_id: 'anthropic/claude-sonnet-4-20250514', model_name: 'Claude Sonnet 4', author: 'anthropic', share_pct: 18.5, tokens: 15234567890, tokens_display: '15.2B' },
      { rank: 2, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'openai', share_pct: 15.2, tokens: 12345678901, tokens_display: '12.3B' },
      { rank: 3, model_id: 'anthropic/claude-3-5-sonnet-20241022', model_name: 'Claude 3.5 Sonnet', author: 'anthropic', share_pct: 12.1, tokens: 9876543210 },
      { rank: 4, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'openai', share_pct: 10.8, tokens: 8765432109 },
      { rank: 5, model_id: 'deepseek/deepseek-chat', model_name: 'DeepSeek Chat', author: 'deepseek', share_pct: 8.0, tokens: 6543210987 },
      { rank: 6, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'google', share_pct: 6.7, tokens: 5432109876 },
      { rank: 7, model_id: 'openai/o1', model_name: 'o1', author: 'openai', share_pct: 5.3, tokens: 4321098765 },
      { rank: 8, model_id: 'anthropic/claude-3-opus-20240229', model_name: 'Claude 3 Opus', author: 'anthropic', share_pct: 3.9, tokens: 3210987654 },
      { rank: 9, model_id: 'meta/llama-3.3-70b-instruct', model_name: 'Llama 3.3 70B', author: 'meta', share_pct: 2.6, tokens: 2109876543 },
      { rank: 10, model_id: 'qwen/qwen-2.5-coder-32b-instruct', model_name: 'Qwen 2.5 Coder 32B', author: 'qwen', share_pct: 1.3, tokens: 1098765432 },
    ],
    entry_count: 10,
    last_synced: new Date().toISOString(),
    data_source: 'openrouter_rankings',
  },
  science: {
    category: { slug: 'science', display_name: 'Science', group: 'usecase', depth: 0 },
    view: 'week',
    entries: [
      { rank: 1, model_id: 'openai/o1', model_name: 'o1', author: 'openai', share_pct: 22.5, tokens: 8765432109 },
      { rank: 2, model_id: 'anthropic/claude-sonnet-4-20250514', model_name: 'Claude Sonnet 4', author: 'anthropic', share_pct: 19.7, tokens: 7654321098 },
      { rank: 3, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'openai', share_pct: 16.8, tokens: 6543210987 },
      { rank: 4, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'google', share_pct: 11.1, tokens: 4321098765 },
      { rank: 5, model_id: 'anthropic/claude-3-5-sonnet-20241022', model_name: 'Claude 3.5 Sonnet', author: 'anthropic', share_pct: 8.2, tokens: 3210987654 },
      { rank: 6, model_id: 'deepseek/deepseek-reasoner', model_name: 'DeepSeek Reasoner', author: 'deepseek', share_pct: 5.4, tokens: 2109876543 },
      { rank: 7, model_id: 'openai/o1-mini', model_name: 'o1 Mini', author: 'openai', share_pct: 5.1, tokens: 1987654321 },
      { rank: 8, model_id: 'anthropic/claude-3-opus-20240229', model_name: 'Claude 3 Opus', author: 'anthropic', share_pct: 4.2, tokens: 1654321098 },
      { rank: 9, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'openai', share_pct: 3.4, tokens: 1321098765 },
      { rank: 10, model_id: 'meta/llama-3.3-70b-instruct', model_name: 'Llama 3.3 70B', author: 'meta', share_pct: 2.5, tokens: 987654321 },
    ],
    entry_count: 10,
    last_synced: new Date().toISOString(),
    data_source: 'openrouter_rankings',
  },
  health: {
    category: { slug: 'health', display_name: 'Health', group: 'usecase', depth: 0 },
    view: 'week',
    entries: [
      { rank: 1, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'openai', share_pct: 24.3, tokens: 5432109876 },
      { rank: 2, model_id: 'anthropic/claude-sonnet-4-20250514', model_name: 'Claude Sonnet 4', author: 'anthropic', share_pct: 20.1, tokens: 4321098765 },
      { rank: 3, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'google', share_pct: 15.5, tokens: 3210987654 },
      { rank: 4, model_id: 'openai/o1', model_name: 'o1', author: 'openai', share_pct: 12.2, tokens: 2109876543 },
      { rank: 5, model_id: 'anthropic/claude-3-5-sonnet-20241022', model_name: 'Claude 3.5 Sonnet', author: 'anthropic', share_pct: 9.1, tokens: 1876543210 },
      { rank: 6, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'openai', share_pct: 6.8, tokens: 1543210987 },
      { rank: 7, model_id: 'anthropic/claude-3-opus-20240229', model_name: 'Claude 3 Opus', author: 'anthropic', share_pct: 4.5, tokens: 1210987654 },
      { rank: 8, model_id: 'meta/llama-3.3-70b-instruct', model_name: 'Llama 3.3 70B', author: 'meta', share_pct: 3.2, tokens: 876543210 },
      { rank: 9, model_id: 'deepseek/deepseek-chat', model_name: 'DeepSeek Chat', author: 'deepseek', share_pct: 2.4, tokens: 543210987 },
      { rank: 10, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'mistralai', share_pct: 1.9, tokens: 210987654 },
    ],
    entry_count: 10,
    last_synced: new Date().toISOString(),
    data_source: 'openrouter_rankings',
  },
}

// Generate rankings for remaining categories
const defaultRankings = (category: string, displayName: string) => ({
  category: { slug: category, display_name: displayName, group: 'usecase', depth: category.includes('/') ? 1 : 0 },
  view: 'week',
  entries: [
    { rank: 1, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'openai', share_pct: 20.0 + Math.random() * 5 },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4-20250514', model_name: 'Claude Sonnet 4', author: 'anthropic', share_pct: 18.0 + Math.random() * 3 },
    { rank: 3, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'google', share_pct: 14.0 + Math.random() * 3 },
    { rank: 4, model_id: 'anthropic/claude-3-5-sonnet-20241022', model_name: 'Claude 3.5 Sonnet', author: 'anthropic', share_pct: 10.0 + Math.random() * 3 },
    { rank: 5, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'openai', share_pct: 8.0 + Math.random() * 2 },
    { rank: 6, model_id: 'deepseek/deepseek-chat', model_name: 'DeepSeek Chat', author: 'deepseek', share_pct: 6.0 + Math.random() * 2 },
    { rank: 7, model_id: 'openai/o1', model_name: 'o1', author: 'openai', share_pct: 4.0 + Math.random() * 2 },
    { rank: 8, model_id: 'meta/llama-3.3-70b-instruct', model_name: 'Llama 3.3 70B', author: 'meta', share_pct: 3.0 + Math.random() * 1 },
    { rank: 9, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'mistralai', share_pct: 2.0 + Math.random() * 1 },
    { rank: 10, model_id: 'qwen/qwen-2.5-72b-instruct', model_name: 'Qwen 2.5 72B', author: 'qwen', share_pct: 1.0 + Math.random() * 1 },
  ],
  entry_count: 10,
  last_synced: new Date().toISOString(),
  data_source: 'openrouter_rankings',
})

// Add default rankings for remaining categories
MOCK_RANKINGS.legal = defaultRankings('legal', 'Legal')
MOCK_RANKINGS.marketing = defaultRankings('marketing', 'Marketing')
MOCK_RANKINGS['marketing/seo'] = defaultRankings('marketing/seo', 'SEO')
MOCK_RANKINGS['marketing/content'] = defaultRankings('marketing/content', 'Content')
MOCK_RANKINGS.technology = defaultRankings('technology', 'Technology')
MOCK_RANKINGS.finance = defaultRankings('finance', 'Finance')
MOCK_RANKINGS.academia = defaultRankings('academia', 'Academia')
MOCK_RANKINGS.roleplay = defaultRankings('roleplay', 'Roleplay')
MOCK_RANKINGS['creative-writing'] = defaultRankings('creative-writing', 'Creative Writing')
MOCK_RANKINGS.translation = defaultRankings('translation', 'Translation')
MOCK_RANKINGS['customer-support'] = defaultRankings('customer-support', 'Customer Support')
MOCK_RANKINGS['data-analysis'] = defaultRankings('data-analysis', 'Data Analysis')

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

