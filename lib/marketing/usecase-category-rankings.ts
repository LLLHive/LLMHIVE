/**
 * May 2026 Top-10 rankings for the 12 UI "Browse by Category" use-cases.
 *
 * Source: RANKINGS_MAY_2026 in benchmark_rankings_jan2026.py (research dated 2026-05-17).
 * Only OpenRouter-available slugs are included (preview-only models omitted).
 *
 * Benchmark mapping per category:
 * - programming  → CODING (SWE-Bench Verified)
 * - science      → GENERAL_REASONING (GPQA Diamond), science-weighted
 * - health       → GENERAL_REASONING (GPQA), health/clinical weighted
 * - legal        → GENERAL_REASONING + LONG_CONTEXT, legal-doc weighted
 * - marketing    → DIALOGUE (LMSYS Arena Elo), copy/persuasion weighted
 * - technology   → TOOL_USE (Tau2 / MCP Atlas)
 * - finance      → MATH (AIME 2025)
 * - academia     → RAG (MRCR retrieval)
 * - roleplay     → DIALOGUE (Arena Elo)
 * - creative-writing → DIALOGUE (Arena Elo)
 * - translation  → MULTILINGUAL (MMMLU)
 * - reasoning    → MATH (AIME 2025) + o-series reasoning leaders
 */

export type CategoryRankingEntry = {
  rank: number
  model_id: string
  model_name: string
  author: string
}

type ModelMeta = { model_name: string; author: string }

const MODEL_META: Record<string, ModelMeta> = {
  'openai/gpt-5.5-pro': { model_name: 'GPT-5.5 Pro', author: 'OpenAI' },
  'openai/gpt-5.5': { model_name: 'GPT-5.5', author: 'OpenAI' },
  'openai/gpt-5.4-pro': { model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
  'openai/gpt-5.4': { model_name: 'GPT-5.4', author: 'OpenAI' },
  'openai/gpt-5.3-codex': { model_name: 'GPT-5.3 Codex', author: 'OpenAI' },
  'openai/gpt-5.2-pro': { model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
  'openai/gpt-5.2': { model_name: 'GPT-5.2', author: 'OpenAI' },
  'openai/gpt-5.2-codex': { model_name: 'GPT-5.2 Codex', author: 'OpenAI' },
  'openai/gpt-5.1': { model_name: 'GPT-5.1', author: 'OpenAI' },
  'openai/o3': { model_name: 'OpenAI o3', author: 'OpenAI' },
  'openai/o1-pro': { model_name: 'o1-pro', author: 'OpenAI' },
  'openai/o4-mini': { model_name: 'o4-mini', author: 'OpenAI' },
  'anthropic/claude-opus-4.7': { model_name: 'Claude Opus 4.7', author: 'Anthropic' },
  'anthropic/claude-opus-4.6': { model_name: 'Claude Opus 4.6', author: 'Anthropic' },
  'anthropic/claude-opus-4.5': { model_name: 'Claude Opus 4.5', author: 'Anthropic' },
  'anthropic/claude-sonnet-4.6': { model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
  'google/gemini-3.1-pro-preview': { model_name: 'Gemini 3.1 Pro', author: 'Google' },
  'google/gemini-2.5-pro': { model_name: 'Gemini 2.5 Pro', author: 'Google' },
  'google/gemini-2.5-pro-preview': { model_name: 'Gemini 2.5 Pro', author: 'Google' },
  'google/gemini-2.5-flash': { model_name: 'Gemini 2.5 Flash', author: 'Google' },
  'deepseek/deepseek-v4-pro': { model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
  'deepseek/deepseek-r1': { model_name: 'DeepSeek R1', author: 'DeepSeek' },
  'deepseek/deepseek-v3.2': { model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
  'meta-llama/llama-4-scout': { model_name: 'Llama 4 Scout', author: 'Meta' },
  'meta-llama/llama-4-maverick': { model_name: 'Llama 4 Maverick', author: 'Meta' },
  'moonshotai/kimi-k2.6': { model_name: 'Kimi K2.6', author: 'Moonshot' },
  'moonshotai/kimi-k2.5': { model_name: 'Kimi K2.5', author: 'Moonshot' },
  'minimax/minimax-m2.5': { model_name: 'MiniMax M2.5', author: 'MiniMax' },
  'qwen/qwen3.6-plus': { model_name: 'Qwen3.6 Plus', author: 'Alibaba' },
  'mistralai/mistral-medium-3.1': { model_name: 'Mistral Medium 3.1', author: 'Mistral AI' },
  'mistralai/mistral-large-2512': { model_name: 'Mistral Large 2512', author: 'Mistral AI' },
  'x-ai/grok-4.20': { model_name: 'Grok 4 Fast', author: 'xAI' },
  'cohere/command-r-plus-08-2024': { model_name: 'Command R+', author: 'Cohere' },
  'z-ai/glm-4.7': { model_name: 'GLM 4.7', author: 'Z.ai' },
  'nousresearch/hermes-4-70b': { model_name: 'Hermes 4 70B', author: 'Nous Research' },
  'ai21/jamba-large-1.7': { model_name: 'Jamba Large 1.7', author: 'AI21 Labs' },
}

function buildRankings(modelIds: string[]): CategoryRankingEntry[] {
  return modelIds.map((model_id, index) => {
    const meta = MODEL_META[model_id]
    if (!meta) {
      throw new Error(`Missing MODEL_META for ${model_id}`)
    }
    return {
      rank: index + 1,
      model_id,
      model_name: meta.model_name,
      author: meta.author,
    }
  })
}

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

/**
 * May 2026 top-10 per use-case category.
 * Order follows the mapped benchmark table in benchmark_rankings_jan2026.py.
 */
export const USECASE_CATEGORY_RANKINGS: Record<UsecaseCategorySlug, CategoryRankingEntry[]> = {
  // CODING — SWE-Bench Verified
  programming: buildRankings([
    'openai/gpt-5.5',
    'anthropic/claude-opus-4.7',
    'openai/gpt-5.3-codex',
    'anthropic/claude-opus-4.5',
    'anthropic/claude-opus-4.6',
    'deepseek/deepseek-v4-pro',
    'google/gemini-3.1-pro-preview',
    'moonshotai/kimi-k2.6',
    'minimax/minimax-m2.5',
    'openai/gpt-5.2',
  ]),

  // GENERAL_REASONING — GPQA Diamond (science-weighted: o3 + R1 retained)
  science: buildRankings([
    'openai/gpt-5.5-pro',
    'openai/gpt-5.4-pro',
    'anthropic/claude-opus-4.7',
    'openai/o3',
    'google/gemini-3.1-pro-preview',
    'anthropic/claude-sonnet-4.6',
    'deepseek/deepseek-v4-pro',
    'meta-llama/llama-4-scout',
    'deepseek/deepseek-r1',
    'openai/o4-mini',
  ]),

  // GENERAL_REASONING — GPQA (health/clinical weighted)
  health: buildRankings([
    'openai/gpt-5.5-pro',
    'openai/gpt-5.4-pro',
    'anthropic/claude-opus-4.7',
    'google/gemini-3.1-pro-preview',
    'anthropic/claude-sonnet-4.6',
    'openai/o1-pro',
    'google/gemini-2.5-pro',
    'meta-llama/llama-4-maverick',
    'mistralai/mistral-medium-3.1',
    'deepseek/deepseek-v4-pro',
  ]),

  // GENERAL_REASONING + LONG_CONTEXT — legal analysis weighted
  legal: buildRankings([
    'anthropic/claude-opus-4.7',
    'openai/gpt-5.5-pro',
    'openai/gpt-5.4-pro',
    'anthropic/claude-sonnet-4.6',
    'google/gemini-3.1-pro-preview',
    'openai/o3',
    'meta-llama/llama-4-scout',
    'mistralai/mistral-large-2512',
    'deepseek/deepseek-v4-pro',
    'cohere/command-r-plus-08-2024',
  ]),

  // DIALOGUE — Arena Elo (marketing / persuasion weighted)
  marketing: buildRankings([
    'openai/gpt-5.4',
    'openai/gpt-5.5',
    'anthropic/claude-sonnet-4.6',
    'anthropic/claude-opus-4.7',
    'google/gemini-3.1-pro-preview',
    'openai/gpt-5.4-pro',
    'meta-llama/llama-4-maverick',
    'x-ai/grok-4.20',
    'mistralai/mistral-medium-3.1',
    'moonshotai/kimi-k2.6',
  ]),

  // TOOL_USE — Tau2 / MCP Atlas
  technology: buildRankings([
    'anthropic/claude-opus-4.7',
    'anthropic/claude-opus-4.5',
    'openai/gpt-5.5',
    'openai/gpt-5.2',
    'google/gemini-3.1-pro-preview',
    'openai/gpt-5.1',
    'openai/gpt-5.3-codex',
    'google/gemini-2.5-pro-preview',
    'deepseek/deepseek-v4-pro',
    'anthropic/claude-sonnet-4.6',
  ]),

  // MATH — AIME 2025
  finance: buildRankings([
    'openai/gpt-5.2',
    'google/gemini-3.1-pro-preview',
    'moonshotai/kimi-k2.5',
    'anthropic/claude-opus-4.7',
    'deepseek/deepseek-v4-pro',
    'qwen/qwen3.6-plus',
    'openai/gpt-5.5-pro',
    'openai/gpt-5.5',
    'openai/o4-mini',
    'deepseek/deepseek-r1',
  ]),

  // RAG — MRCR retrieval
  academia: buildRankings([
    'openai/gpt-5.5',
    'google/gemini-2.5-pro-preview',
    'openai/gpt-5.5-pro',
    'google/gemini-3.1-pro-preview',
    'anthropic/claude-opus-4.7',
    'openai/gpt-5.4-pro',
    'anthropic/claude-sonnet-4.6',
    'deepseek/deepseek-v4-pro',
    'meta-llama/llama-4-maverick',
    'qwen/qwen3.6-plus',
  ]),

  // DIALOGUE — Arena Elo
  roleplay: buildRankings([
    'anthropic/claude-opus-4.6',
    'google/gemini-3.1-pro-preview',
    'openai/gpt-5.4-pro',
    'x-ai/grok-4.20',
    'deepseek/deepseek-v4-pro',
    'anthropic/claude-sonnet-4.6',
    'openai/gpt-5.4',
    'google/gemini-2.5-pro-preview',
    'qwen/qwen3.6-plus',
    'meta-llama/llama-4-maverick',
  ]),

  // DIALOGUE — Arena Elo (creative writing weighted: Opus leads)
  'creative-writing': buildRankings([
    'anthropic/claude-opus-4.7',
    'anthropic/claude-opus-4.6',
    'openai/gpt-5.4',
    'anthropic/claude-sonnet-4.6',
    'google/gemini-3.1-pro-preview',
    'meta-llama/llama-4-maverick',
    'mistralai/mistral-large-2512',
    'openai/gpt-5.4-pro',
    'moonshotai/kimi-k2.6',
    'cohere/command-r-plus-08-2024',
  ]),

  // MULTILINGUAL — MMMLU
  translation: buildRankings([
    'google/gemini-3.1-pro-preview',
    'anthropic/claude-opus-4.7',
    'anthropic/claude-opus-4.6',
    'anthropic/claude-opus-4.5',
    'openai/gpt-5.2',
    'qwen/qwen3.6-plus',
    'anthropic/claude-sonnet-4.6',
    'openai/gpt-5.4',
    'openai/gpt-5.5-pro',
    'z-ai/glm-4.7',
  ]),

  // MATH + o-series — frontier reasoning (AIME leaders + dedicated reasoning models)
  reasoning: buildRankings([
    'openai/gpt-5.5-pro',
    'openai/o3',
    'openai/o1-pro',
    'openai/gpt-5.4-pro',
    'anthropic/claude-opus-4.7',
    'deepseek/deepseek-r1',
    'deepseek/deepseek-v4-pro',
    'openai/o4-mini',
    'anthropic/claude-sonnet-4.6',
    'google/gemini-3.1-pro-preview',
  ]),
}

/** Legacy / internal aliases that reuse the 12 primary lists. */
export const USECASE_CATEGORY_ALIASES: Record<string, UsecaseCategorySlug> = {
  coding: 'programming',
  math: 'reasoning',
  analysis: 'science',
}

export const DEFAULT_USECASE_RANKINGS: CategoryRankingEntry[] =
  USECASE_CATEGORY_RANKINGS.science

export function getUsecaseCategoryRankings(
  categorySlug: string
): CategoryRankingEntry[] {
  const resolved =
    (USECASE_CATEGORY_ALIASES[categorySlug] as UsecaseCategorySlug | undefined) ??
    (categorySlug as UsecaseCategorySlug)

  return USECASE_CATEGORY_RANKINGS[resolved] ?? DEFAULT_USECASE_RANKINGS
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
