/**
 * OpenRouter Integration Types
 * 
 * Type definitions for the OpenRouter integration:
 * - Model catalog
 * - Rankings
 * - Inference
 * - Prompt templates
 */

// =============================================================================
// Model Types
// =============================================================================

export interface OpenRouterModel {
  id: string
  name: string
  description?: string
  context_length?: number
  top_provider_max_tokens?: number
  
  architecture: {
    modality?: string
    tokenizer?: string
    instruct_type?: string
  }
  
  pricing: {
    prompt?: number
    completion?: number
    image?: number
    request?: number
    per_1m_prompt?: number
    per_1m_completion?: number
  }
  
  capabilities: {
    supports_tools: boolean
    supports_structured: boolean
    supports_streaming: boolean
    multimodal_input: boolean
    multimodal_output: boolean
  }
  
  is_free: boolean
  availability_score: number
  
  // Derived (non-authoritative, labeled as such)
  strengths?: string[]
  weaknesses?: string[]
  
  categories?: string[]
  is_active: boolean
  last_updated?: string
  
  // Endpoints (from detail view)
  endpoints?: ModelEndpoint[]
}

export interface ModelEndpoint {
  provider: string
  tag?: string
  context_length?: number
  max_completion_tokens?: number
  status: 'active' | 'inactive' | 'degraded' | 'unknown'
  uptime_percent?: number
}

export interface ModelListResponse {
  data: OpenRouterModel[]
  total: number
  limit: number
  offset: number
  data_source: string
  last_sync?: string
}

export interface ModelFilters {
  search?: string
  min_context?: number
  max_context?: number
  max_price_per_1m?: number
  is_free?: boolean
  supports_tools?: boolean
  supports_structured?: boolean
  multimodal_input?: boolean
  sort_by?: 'name' | 'context_length' | 'price_per_1m_prompt' | 'availability_score'
  sort_order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

// =============================================================================
// Rankings Types
// =============================================================================

export type RankingDimension =
  | 'trending'
  | 'most_used'
  | 'best_value'
  | 'long_context'
  | 'tools_agents'
  | 'multimodal'
  | 'fastest'
  | 'most_reliable'
  | 'lowest_cost'

export type TimeRange = '24h' | '7d' | '30d' | 'all'

export interface RankedModel {
  model: OpenRouterModel
  rank: number
  score: number
  metrics: Record<string, number | string>
  data_source: string
}

export interface RankingResult {
  dimension: RankingDimension
  time_range: TimeRange
  count: number
  models: RankedModel[]
  generated_at: string
  data_source: string
  metric_definitions: Record<string, string>
}

export interface RankingDimensionInfo {
  id: RankingDimension
  name: string
  description: string
  metric: string
}

// =============================================================================
// Inference Types
// =============================================================================

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content?: string
  name?: string
  tool_calls?: ToolCall[]
  tool_call_id?: string
}

export interface ToolCall {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

export interface ToolDefinition {
  type: 'function'
  function: {
    name: string
    description?: string
    parameters?: Record<string, unknown>
  }
}

export interface ChatCompletionRequest {
  model: string
  messages: ChatMessage[]
  tools?: ToolDefinition[]
  response_format?: { type: 'json_object' | 'text' }
  stream?: boolean
  temperature?: number
  max_tokens?: number
  top_p?: number
  frequency_penalty?: number
  presence_penalty?: number
  stop?: string[]
  max_cost_usd?: number
  save_run?: boolean
}

export interface ChatCompletionResponse {
  id: string
  model: string
  choices: {
    index: number
    message: ChatMessage
    finish_reason?: string
  }[]
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  created: number
  provider?: string
  latency_ms?: number
  cost_usd?: number
  generation_id?: string
}

export interface StreamChunk {
  id: string
  model: string
  choices: {
    index: number
    delta: Partial<ChatMessage>
    finish_reason?: string
  }[]
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

// =============================================================================
// Prompt Template Types
// =============================================================================

export interface TemplateVariable {
  name: string
  type: 'text' | 'number' | 'select' | 'multiline'
  default?: string | number
  description?: string
  options?: string[]  // For select type
  required?: boolean
}

export interface PromptTemplate {
  id: string
  name: string
  description?: string
  category?: string
  system_prompt?: string
  user_prompt_template: string
  variables?: TemplateVariable[]
  default_model_id?: string
  default_params?: Record<string, unknown>
  visibility: 'private' | 'workspace' | 'public'
  version: number
  use_count: number
  created_at?: string
  updated_at?: string
}

export interface TemplateListResponse {
  data: PromptTemplate[]
  total: number
  limit: number
  offset: number
}

export interface CreateTemplateRequest {
  name: string
  description?: string
  category?: string
  system_prompt?: string
  user_prompt_template: string
  variables?: TemplateVariable[]
  default_model_id?: string
  default_params?: Record<string, unknown>
  visibility?: 'private' | 'workspace' | 'public'
}

// =============================================================================
// UI State Types
// =============================================================================

export interface ModelExplorerState {
  models: OpenRouterModel[]
  loading: boolean
  error?: string
  filters: ModelFilters
  total: number
  selectedModels: string[]  // For comparison
}

export interface RankingsState {
  dimension: RankingDimension
  timeRange: TimeRange
  result?: RankingResult
  loading: boolean
  error?: string
}

export interface PlaygroundState {
  selectedModel?: OpenRouterModel
  messages: ChatMessage[]
  systemPrompt: string
  params: {
    temperature: number
    maxTokens: number
    topP: number
  }
  running: boolean
  response?: ChatCompletionResponse
  error?: string
  estimatedCost?: number
}

// =============================================================================
// Helper Types
// =============================================================================

export type PriceTier = 'free' | 'budget' | 'standard' | 'premium'

export function getPriceTier(pricePerMillion?: number): PriceTier {
  if (!pricePerMillion || pricePerMillion === 0) return 'free'
  if (pricePerMillion < 0.5) return 'budget'
  if (pricePerMillion < 5) return 'standard'
  return 'premium'
}

export function formatPrice(pricePerMillion?: number): string {
  if (!pricePerMillion || pricePerMillion === 0) return 'Free'
  if (pricePerMillion < 0.01) return `$${(pricePerMillion * 1000).toFixed(3)}/1K tokens`
  return `$${pricePerMillion.toFixed(2)}/M tokens`
}

export function formatContextLength(length?: number): string {
  if (!length) return 'Unknown'
  if (length >= 1000000) return `${(length / 1000000).toFixed(1)}M`
  if (length >= 1000) return `${(length / 1000).toFixed(0)}K`
  return `${length}`
}

export function formatLatency(ms?: number): string {
  if (!ms) return 'Unknown'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

