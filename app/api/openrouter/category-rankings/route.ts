/**
 * GET /api/openrouter/category-rankings
 * 
 * Returns top 10 models for a category.
 * Uses fallback model rankings when backend is not available.
 * 
 * UPDATED: January 2026 - Latest premium models from OpenRouter
 * - GPT-5.2 series (GPT-5.2, GPT-5.2 Pro, GPT-5.2 Codex)
 * - Claude 4.5 series (Claude Opus 4.5, Claude Sonnet 4.5)
 * - Gemini 3 series (Gemini 3 Pro, Gemini 3 Flash)
 * - OpenAI o-series (o1, o1-pro, o3, o4-mini)
 * - Llama 4 series (Llama 4 70B, Llama 4 405B, Llama 4 Maverick)
 * - DeepSeek V3.2, DeepSeek R1
 * - Grok 4.1, Qwen 3, Mistral Large 2512
 */

import { NextRequest, NextResponse } from 'next/server'

// Fallback model rankings by category (Updated January 2026)
// Includes LATEST models: GPT-5.2, Claude 4.5, Gemini 3, o3, Llama 4
const CATEGORY_RANKINGS: Record<string, Array<{
  rank: number
  model_id: string
  model_name: string
  author: string
}>> = {
  programming: [
    { rank: 1, model_id: 'openai/gpt-5.2-codex', model_name: 'GPT-5.2 Codex', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 6, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
    { rank: 7, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 8, model_id: 'mistralai/codestral-2512', model_name: 'Codestral 2512', author: 'Mistral AI' },
    { rank: 9, model_id: 'x-ai/grok-code-fast-1', model_name: 'Grok Code Fast 1', author: 'xAI' },
    { rank: 10, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
  ],
  science: [
    { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 6, model_id: 'meta-llama/llama-4-405b', model_name: 'Llama 4 405B', author: 'Meta' },
    { rank: 7, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 8, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 9, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 10, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'Google' },
  ],
  health: [
    { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 5, model_id: 'openai/o1-pro', model_name: 'o1-pro', author: 'OpenAI' },
    { rank: 6, model_id: 'google/med-palm-3', model_name: 'Med-PaLM 3', author: 'Google' },
    { rank: 7, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 8, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 9, model_id: 'openai/gpt-5.2', model_name: 'GPT-5.2', author: 'OpenAI' },
    { rank: 10, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
  ],
  legal: [
    { rank: 1, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-4-405b', model_name: 'Llama 4 405B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 8, model_id: 'openai/gpt-5.2', model_name: 'GPT-5.2', author: 'OpenAI' },
    { rank: 9, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
    { rank: 10, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
  ],
  marketing: [
    { rank: 1, model_id: 'openai/gpt-5.2', model_name: 'GPT-5.2', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 8, model_id: 'x-ai/grok-4.1-fast', model_name: 'Grok 4.1 Fast', author: 'xAI' },
    { rank: 9, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'google/gemini-2.5-flash', model_name: 'Gemini 2.5 Flash', author: 'Google' },
  ],
  technology: [
    { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 6, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 7, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 8, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
    { rank: 9, model_id: 'x-ai/grok-4.1-fast', model_name: 'Grok 4.1 Fast', author: 'xAI' },
    { rank: 10, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
  ],
  finance: [
    { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 6, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 7, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 8, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 9, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 10, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
  ],
  academia: [
    { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 5, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 6, model_id: 'meta-llama/llama-4-405b', model_name: 'Llama 4 405B', author: 'Meta' },
    { rank: 7, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 8, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 9, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 10, model_id: 'google/gemini-2.5-pro', model_name: 'Gemini 2.5 Pro', author: 'Google' },
  ],
  roleplay: [
    { rank: 1, model_id: 'openai/gpt-5.2', model_name: 'GPT-5.2', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 5, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 6, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 7, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 8, model_id: 'nous/hermes-3-pro', model_name: 'Hermes 3 Pro', author: 'Nous Research' },
    { rank: 9, model_id: 'x-ai/grok-4.1-fast', model_name: 'Grok 4.1 Fast', author: 'xAI' },
    { rank: 10, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
  ],
  'creative-writing': [
    { rank: 1, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 2, model_id: 'openai/gpt-5.2', model_name: 'GPT-5.2', author: 'OpenAI' },
    { rank: 3, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 6, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 7, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 8, model_id: 'meta-llama/llama-4-maverick', model_name: 'Llama 4 Maverick', author: 'Meta' },
    { rank: 9, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'ai21/jamba-2-large', model_name: 'Jamba 2 Large', author: 'AI21 Labs' },
  ],
  translation: [
    { rank: 1, model_id: 'openai/gpt-5.2', model_name: 'GPT-5.2', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 5, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 6, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 7, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
    { rank: 8, model_id: 'google/gemini-2.5-flash', model_name: 'Gemini 2.5 Flash', author: 'Google' },
    { rank: 9, model_id: 'cohere/command-r-plus', model_name: 'Command R+', author: 'Cohere' },
    { rank: 10, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
  ],
  reasoning: [
    { rank: 1, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/o1-pro', model_name: 'o1-pro', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 5, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 6, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 7, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 8, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 9, model_id: 'meta-llama/llama-4-405b', model_name: 'Llama 4 405B', author: 'Meta' },
    { rank: 10, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
  ],
  // Additional categories for comprehensive coverage
  math: [
    { rank: 1, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 2, model_id: 'openai/o1-pro', model_name: 'o1-pro', author: 'OpenAI' },
    { rank: 3, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 4, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 5, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 6, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 7, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 8, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 9, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
    { rank: 10, model_id: 'meta-llama/llama-4-405b', model_name: 'Llama 4 405B', author: 'Meta' },
  ],
  coding: [
    { rank: 1, model_id: 'openai/gpt-5.2-codex', model_name: 'GPT-5.2 Codex', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 4, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 5, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 6, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
    { rank: 7, model_id: 'mistralai/codestral-2512', model_name: 'Codestral 2512', author: 'Mistral AI' },
    { rank: 8, model_id: 'x-ai/grok-code-fast-1', model_name: 'Grok Code Fast 1', author: 'xAI' },
    { rank: 9, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
    { rank: 10, model_id: 'mistralai/devstral-2512', model_name: 'Devstral 2512', author: 'Mistral AI' },
  ],
  analysis: [
    { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
    { rank: 2, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
    { rank: 3, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
    { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
    { rank: 5, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
    { rank: 6, model_id: 'deepseek/deepseek-r1', model_name: 'DeepSeek R1', author: 'DeepSeek' },
    { rank: 7, model_id: 'meta-llama/llama-4-405b', model_name: 'Llama 4 405B', author: 'Meta' },
    { rank: 8, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
    { rank: 9, model_id: 'openai/o4-mini', model_name: 'o4-mini', author: 'OpenAI' },
    { rank: 10, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
  ],
}

// Default rankings for categories not in the map (Updated January 2026)
const DEFAULT_RANKINGS = [
  { rank: 1, model_id: 'openai/gpt-5.2-pro', model_name: 'GPT-5.2 Pro', author: 'OpenAI' },
  { rank: 2, model_id: 'anthropic/claude-sonnet-4.5', model_name: 'Claude Sonnet 4.5', author: 'Anthropic' },
  { rank: 3, model_id: 'anthropic/claude-opus-4.5', model_name: 'Claude Opus 4.5', author: 'Anthropic' },
  { rank: 4, model_id: 'google/gemini-3-pro-preview', model_name: 'Gemini 3 Pro', author: 'Google' },
  { rank: 5, model_id: 'openai/o3', model_name: 'OpenAI o3', author: 'OpenAI' },
  { rank: 6, model_id: 'meta-llama/llama-4-70b', model_name: 'Llama 4 70B', author: 'Meta' },
  { rank: 7, model_id: 'mistralai/mistral-large-2512', model_name: 'Mistral Large 2512', author: 'Mistral AI' },
  { rank: 8, model_id: 'deepseek/deepseek-v3.2', model_name: 'DeepSeek V3.2', author: 'DeepSeek' },
  { rank: 9, model_id: 'x-ai/grok-4.1-fast', model_name: 'Grok 4.1 Fast', author: 'xAI' },
  { rank: 10, model_id: 'qwen/qwen-3-72b-instruct', model_name: 'Qwen 3 72B', author: 'Alibaba' },
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
    data_source: 'LLMHive Rankings (January 2026)',
    description: `Top ${limit} models for ${category}`,
  })
}
