/**
 * GET /api/openrouter/category-rankings
 * 
 * Returns top 10 models for a category.
 * Uses fallback model rankings when backend is not available.
 */

import { NextRequest, NextResponse } from 'next/server'

// Fallback model rankings by category
// These are representative top models for each category
const CATEGORY_RANKINGS: Record<string, Array<{
  rank: number
  model_id: string
  model_name: string
  author: string
}>> = {
  programming: [
    { rank: 1, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 5, model_id: 'openai/o1-preview', model_name: 'o1-preview', author: 'OpenAI' },
    { rank: 6, model_id: 'deepseek/deepseek-coder', model_name: 'DeepSeek Coder', author: 'DeepSeek' },
    { rank: 7, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 8, model_id: 'mistralai/codestral-latest', model_name: 'Codestral', author: 'Mistral AI' },
    { rank: 9, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 10, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
  ],
  science: [
    { rank: 1, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 5, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-405b-instruct', model_name: 'Llama 3.1 405B', author: 'Meta' },
    { rank: 7, model_id: 'openai/o1-preview', model_name: 'o1-preview', author: 'OpenAI' },
    { rank: 8, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 9, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 10, model_id: 'google/gemini-ultra', model_name: 'Gemini Ultra', author: 'Google' },
  ],
  health: [
    { rank: 1, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 3, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 5, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 8, model_id: 'google/med-palm-2', model_name: 'Med-PaLM 2', author: 'Google' },
    { rank: 9, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 10, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
  ],
  legal: [
    { rank: 1, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 5, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 8, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 9, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 10, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
  ],
  marketing: [
    { rank: 1, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 5, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 8, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 9, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'openai/gpt-3.5-turbo', model_name: 'GPT-3.5 Turbo', author: 'OpenAI' },
  ],
  technology: [
    { rank: 1, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 5, model_id: 'openai/o1-preview', model_name: 'o1-preview', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 8, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 9, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 10, model_id: 'xai/grok-2', model_name: 'Grok-2', author: 'xAI' },
  ],
  finance: [
    { rank: 1, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 8, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 9, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 10, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
  ],
  academia: [
    { rank: 1, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 6, model_id: 'meta-llama/llama-3.1-405b-instruct', model_name: 'Llama 3.1 405B', author: 'Meta' },
    { rank: 7, model_id: 'openai/o1-preview', model_name: 'o1-preview', author: 'OpenAI' },
    { rank: 8, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 9, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 10, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
  ],
  roleplay: [
    { rank: 1, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 4, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 5, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 6, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 7, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 8, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 9, model_id: 'nous/hermes-2-pro', model_name: 'Hermes 2 Pro', author: 'Nous Research' },
    { rank: 10, model_id: 'pygmalionai/mythalion-13b', model_name: 'Mythalion 13B', author: 'Pygmalion AI' },
  ],
  'creative-writing': [
    { rank: 1, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 5, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 6, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 7, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 8, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 9, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'ai21/jamba-1.5-large', model_name: 'Jamba 1.5 Large', author: 'AI21 Labs' },
  ],
  translation: [
    { rank: 1, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 3, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 4, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 5, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
    { rank: 6, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 7, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
    { rank: 8, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
    { rank: 9, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'qwen/qwen-2-72b-instruct', model_name: 'Qwen 2 72B', author: 'Alibaba' },
  ],
  reasoning: [
    { rank: 1, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o1-preview', model_name: 'o1-preview', author: 'OpenAI' },
    { rank: 4, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 5, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
    { rank: 6, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
    { rank: 7, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
    { rank: 8, model_id: 'meta-llama/llama-3.1-405b-instruct', model_name: 'Llama 3.1 405B', author: 'Meta' },
    { rank: 9, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
    { rank: 10, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
  ],
}

// Default rankings for categories not in the map
const DEFAULT_RANKINGS = [
  { rank: 1, model_id: 'openai/gpt-4o', model_name: 'GPT-4o', author: 'OpenAI' },
  { rank: 2, model_id: 'anthropic/claude-sonnet-4', model_name: 'Claude Sonnet 4', author: 'Anthropic' },
  { rank: 3, model_id: 'anthropic/claude-opus-4', model_name: 'Claude Opus 4', author: 'Anthropic' },
  { rank: 4, model_id: 'google/gemini-pro-1.5', model_name: 'Gemini Pro 1.5', author: 'Google' },
  { rank: 5, model_id: 'meta-llama/llama-3.1-70b-instruct', model_name: 'Llama 3.1 70B', author: 'Meta' },
  { rank: 6, model_id: 'openai/o1', model_name: 'o1', author: 'OpenAI' },
  { rank: 7, model_id: 'mistralai/mistral-large', model_name: 'Mistral Large', author: 'Mistral AI' },
  { rank: 8, model_id: 'openai/gpt-4o-mini', model_name: 'GPT-4o Mini', author: 'OpenAI' },
  { rank: 9, model_id: 'anthropic/claude-3.5-sonnet', model_name: 'Claude 3.5 Sonnet', author: 'Anthropic' },
  { rank: 10, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
]

// Category slug to ID mapping
const CATEGORY_ID_MAP: Record<string, number> = {
  'programming': 1,
  'science': 2,
  'health': 3,
  'legal': 4,
  'marketing': 5,
  'technology': 6,
  'finance': 7,
  'academia': 8,
  'roleplay': 9,
  'creative-writing': 10,
  'translation': 11,
  'reasoning': 12,
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const category = searchParams.get('category') || 'programming'
  const view = searchParams.get('view') || 'week'
  const limit = parseInt(searchParams.get('limit') || '10', 10)
  
  // Get rankings for the requested category
  const rankings = CATEGORY_RANKINGS[category] || DEFAULT_RANKINGS
  const limitedRankings = rankings.slice(0, limit).map(entry => ({
    ...entry,
    is_others_bucket: false, // Required field
  }))
  
  const categoryId = CATEGORY_ID_MAP[category] || 1
  
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
    data_source: 'mock',
    description: `Top ${limit} models for ${category}`,
  })
}

