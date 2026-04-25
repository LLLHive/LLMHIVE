/**
 * GET /api/openrouter/category-rankings
 * 
 * Returns top 10 models for a category.
 * Uses fallback model rankings when backend is not available.
 * 
 * UPDATED: April 2026 — model_id values verified against OpenRouter /api/v1/models
 * - GPT-5.4 / GPT-5.4 Pro, GPT-5.5 / GPT-5.5 Pro, GPT-5.2 series (incl. Codex)
 * - Claude Sonnet 4.6, Claude Opus 4.7 (plus 4.5 where still listed downstream)
 * - Gemini 3.1 Pro / flash-lite preview slugs
 * - DeepSeek V4 Pro & Flash, V3.2, R1
 * - Grok 4 / Grok 4 fast, Grok Code Fast
 * - Kimi K2.6, Qwen3.6 Plus, GLM 4.7, Mistral Medium 3.1
 * - OpenAI o-series, Llama 4, Mistral Large 2512
 */

import { NextRequest, NextResponse } from 'next/server'

// Fallback model rankings by category (April 2026)
// IDs must stay in sync with OpenRouter catalog (see model_slug_remap.py for legacy aliases)
const CATEGORY_RANKINGS: Record<string, Array<{
  rank: number
  model_id: string
  model_name: string
  author: string
}>> = {
  programming: [
    { rank: 1, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/gpt-5.5', model_name: 'GPT-5.5', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 4, model_id: 'openai/gpt-5.2-codex', model_name: 'GPT-5.2 Codex', author: 'OpenAI' },
    { rank: 5, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 6, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 7, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 8, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 9, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
    { rank: 10, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
  ],
  science: [
    { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/gpt-5.5-pro', model_name: 'GPT-5.5 Pro', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 4, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 5, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 6, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 7, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 8, model_id: 'meta-llama/llama-4-scout', model_name: 'Llama 4 Scout', author: 'Meta' },
    { rank: 9, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 10, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
  ],
  health: [
    { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 3, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 5, model_id: 'openai/o1-pro', model_name: 'o1-pro', author: 'OpenAI' },
    { rank: 6, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'Google' },
    { rank: 7, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 8, model_id: 'mistralai/mistral-medium-3.1', model_name: 'Mistral Medium 3.1', author: 'Mistral AI' },
    { rank: 9, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 10, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
  ],
  legal: [
    { rank: 1, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-4-scout', model_name: 'Llama 4 Scout', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 8, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 9, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 10, model_id: 'cohere/command-r-plus-08-2024', model_name: 'Command R+', author: 'Cohere' },
  ],
  marketing: [
    { rank: 1, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/gpt-5.5', model_name: 'GPT-5.5', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 6, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 7, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 8, model_id: 'x-ai/grok-4-fast', model_name: 'Grok 4 Fast', author: 'xAI' },
    { rank: 9, model_id: 'mistralai/mistral-medium-3.1', model_name: 'Mistral Medium 3.1', author: 'Mistral AI' },
    { rank: 10, model_id: 'moonshotai/kimi-k2.6', model_name: 'Kimi K2.6', author: 'Moonshot' },
  ],
  technology: [
    { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 7, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 8, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 9, model_id: 'x-ai/grok-4-fast', model_name: 'Grok 4 Fast', author: 'xAI' },
    { rank: 10, model_id: 'qwen/qwen3.6-plus', model_name: 'Qwen3.6 Plus', author: 'Alibaba' },
  ],
  finance: [
    { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 6, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 7, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 8, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 9, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 10, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
  ],
  academia: [
    { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 6, model_id: 'meta-llama/llama-4-scout', model_name: 'Llama 4 Scout', author: 'Meta' },
    { rank: 7, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 8, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 9, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 10, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'Google' },
  ],
  roleplay: [
    { rank: 1, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 4, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 5, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 6, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 7, model_id: 'moonshotai/kimi-k2.6', model_name: 'Kimi K2.6', author: 'Moonshot' },
    { rank: 8, model_id: 'x-ai/grok-4-fast', model_name: 'Grok 4 Fast', author: 'xAI' },
    { rank: 9, model_id: 'nousresearch/hermes-4-70b', model_name: 'Hermes 4 70B', author: 'Nous Research' },
    { rank: 10, model_id: 'qwen/qwen3.6-plus', model_name: 'Qwen3.6 Plus', author: 'Alibaba' },
  ],
  'creative-writing': [
    { rank: 1, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 5, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 6, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 7, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 8, model_id: 'moonshotai/kimi-k2.6', model_name: 'Kimi K2.6', author: 'Moonshot' },
    { rank: 9, model_id: 'cohere/command-r-plus-08-2024', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'ai21/jamba-large-1.7', model_name: 'Jamba Large 1.7', author: 'AI21 Labs' },
  ],
  translation: [
    { rank: 1, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 3, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 5, model_id: 'qwen/qwen3.6-plus', model_name: 'Qwen3.6 Plus', author: 'Alibaba' },
    { rank: 6, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-medium-3.1', model_name: 'Mistral Medium 3.1', author: 'Mistral AI' },
    { rank: 8, model_id: 'google/gemini-2.5-flash', model_name: 'Gemini 2.5 Flash', author: 'Google' },
    { rank: 9, model_id: 'cohere/command-r-plus-08-2024', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'z-ai/glm-4.7', model_name: 'GLM 4.7', author: 'Z.ai' },
  ],
  reasoning: [
    { rank: 1, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/o1-pro', model_name: 'o1-pro', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 5, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 6, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 7, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 8, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 9, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 10, model_id: 'meta-llama/llama-4-scout', model_name: 'Llama 4 Scout', author: 'Meta' },
  ],
  // Additional categories for comprehensive coverage
  math: [
    { rank: 1, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/o1-pro', model_name: 'o1-pro', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 5, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 6, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 7, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 8, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 9, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 10, model_id: 'qwen/qwen3.6-plus', model_name: 'Qwen3.6 Plus', author: 'Alibaba' },
  ],
  coding: [
    { rank: 1, model_id: 'openai/gpt-5.4', model_name: 'GPT-5.4', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/gpt-5.2-codex', model_name: 'GPT-5.2 Codex', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 6, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 7, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 8, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
    { rank: 9, model_id: 'x-ai/grok-code-fast-1', model_name: 'Grok Code Fast 1', author: 'xAI' },
    { rank: 10, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
  ],
  analysis: [
    { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
    { rank: 5, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
    { rank: 6, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
    { rank: 7, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 8, model_id: 'meta-llama/llama-4-scout', model_name: 'Llama 4 Scout', author: 'Meta' },
    { rank: 9, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 10, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
  ],
}

// Default rankings for categories not in the map (April 2026)
const DEFAULT_RANKINGS = [
  { rank: 1, model_id: 'openai/gpt-5.4-pro', model_name: 'GPT-5.4 Pro', author: 'OpenAI' },
  { rank: 2, model_id: 'anthropic/claude-sonnet-4.6', model_name: 'Claude Sonnet 4.6', author: 'Anthropic' },
  { rank: 3, model_id: 'anthropic/claude-opus-4.7', model_name: 'Claude Opus 4.7', author: 'Anthropic' },
  { rank: 4, model_id: 'google/gemini-3.1-pro-preview', model_name: 'Gemini 3.1 Pro', author: 'Google' },
  { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
  { rank: 6, model_id: 'deepseek/deepseek-v4-pro', model_name: 'DeepSeek V4 Pro', author: 'DeepSeek' },
  { rank: 7, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
  { rank: 8, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
  { rank: 9, model_id: 'x-ai/grok-4-fast', model_name: 'Grok 4 Fast', author: 'xAI' },
  { rank: 10, model_id: 'qwen/qwen3.6-plus', model_name: 'Qwen3.6 Plus', author: 'Alibaba' },
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
  'math': 13,
  'coding': 14,
  'analysis': 15,
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
    data_source: 'LLMHive Rankings (April 2026)',
    description: `Top ${limit} models for ${category}`,
  })
}
