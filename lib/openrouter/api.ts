/**
 * OpenRouter API Client
 * 
 * Frontend client for OpenRouter integration:
 * - Model catalog fetching
 * - Rankings queries
 * - Inference requests
 * - Template management
 */

import type {
  OpenRouterModel,
  ModelListResponse,
  ModelFilters,
  RankingDimension,
  TimeRange,
  RankingResult,
  RankingDimensionInfo,
  ChatCompletionRequest,
  ChatCompletionResponse,
  StreamChunk,
  PromptTemplate,
  TemplateListResponse,
  CreateTemplateRequest,
} from './types'

const API_BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_API_BASE_URL || ''

// =============================================================================
// Utilities
// =============================================================================

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API Error ${response.status}: ${error}`)
  }
  
  return response.json()
}

function buildQueryString(params: Record<string, unknown>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      query.append(key, String(value))
    }
  }
  return query.toString()
}

// =============================================================================
// Model Catalog API
// =============================================================================

export async function listModels(filters: ModelFilters = {}): Promise<ModelListResponse> {
  const query = buildQueryString(filters as Record<string, unknown>)
  return fetchJson<ModelListResponse>(
    `${API_BASE}/openrouter/models${query ? `?${query}` : ''}`
  )
}

export async function getModel(modelId: string): Promise<OpenRouterModel> {
  const encodedId = encodeURIComponent(modelId)
  return fetchJson<OpenRouterModel>(`${API_BASE}/openrouter/models/${encodedId}`)
}

export async function searchModels(
  query: string,
  options: Partial<ModelFilters> = {}
): Promise<ModelListResponse> {
  return listModels({ ...options, search: query })
}

export async function triggerSync(
  dryRun = false,
  enrichEndpoints = true
): Promise<{ status: string; message: string }> {
  return fetchJson(`${API_BASE}/openrouter/sync?dry_run=${dryRun}&enrich_endpoints=${enrichEndpoints}`, {
    method: 'POST',
  })
}

// =============================================================================
// Rankings API
// =============================================================================

export async function getRankings(
  dimension: RankingDimension,
  options: {
    timeRange?: TimeRange
    limit?: number
    offset?: number
    minContext?: number
    maxPricePer1m?: number
    supportsTools?: boolean
    tenantId?: string
  } = {}
): Promise<RankingResult> {
  const params: Record<string, unknown> = {
    time_range: options.timeRange || '7d',
    limit: options.limit || 20,
    offset: options.offset || 0,
  }
  
  if (options.minContext) params.min_context = options.minContext
  if (options.maxPricePer1m) params.max_price_per_1m = options.maxPricePer1m
  if (options.supportsTools !== undefined) params.supports_tools = options.supportsTools
  if (options.tenantId) params.tenant_id = options.tenantId
  
  const query = buildQueryString(params)
  return fetchJson<RankingResult>(`${API_BASE}/openrouter/rankings/${dimension}?${query}`)
}

export async function listRankingDimensions(): Promise<{
  dimensions: RankingDimensionInfo[]
  time_ranges: TimeRange[]
  data_source: string
  data_source_description: string
}> {
  return fetchJson(`${API_BASE}/openrouter/rankings`)
}

// =============================================================================
// Inference API
// =============================================================================

export async function chatCompletion(
  request: ChatCompletionRequest
): Promise<ChatCompletionResponse> {
  return fetchJson<ChatCompletionResponse>(`${API_BASE}/openrouter/chat/completions`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function* streamChatCompletion(
  request: ChatCompletionRequest
): AsyncGenerator<StreamChunk, void, unknown> {
  const response = await fetch(`${API_BASE}/openrouter/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ...request, stream: true }),
  })
  
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API Error ${response.status}: ${error}`)
  }
  
  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')
  
  const decoder = new TextDecoder()
  let buffer = ''
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    
    for (const line of lines) {
      if (!line.trim()) continue
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data.trim() === '[DONE]') return
        try {
          yield JSON.parse(data) as StreamChunk
        } catch {
          console.warn('Failed to parse SSE chunk:', data)
        }
      }
    }
  }
}

export function estimateCost(
  model: OpenRouterModel,
  promptTokens: number,
  completionTokens: number
): number {
  const promptCost = ((model.pricing.per_1m_prompt || 0) / 1_000_000) * promptTokens
  const completionCost = ((model.pricing.per_1m_completion || 0) / 1_000_000) * completionTokens
  return promptCost + completionCost
}

export function estimateTokens(text: string): number {
  // Rough estimate: ~4 chars per token
  return Math.ceil(text.length / 4)
}

// =============================================================================
// Templates API
// =============================================================================

export async function listTemplates(
  userId: string,
  options: {
    category?: string
    visibility?: string
    limit?: number
    offset?: number
  } = {}
): Promise<TemplateListResponse> {
  const params: Record<string, unknown> = {
    user_id: userId,
    limit: options.limit || 50,
    offset: options.offset || 0,
  }
  
  if (options.category) params.category = options.category
  if (options.visibility) params.visibility = options.visibility
  
  const query = buildQueryString(params)
  return fetchJson<TemplateListResponse>(`${API_BASE}/openrouter/templates?${query}`)
}

export async function createTemplate(
  userId: string,
  template: CreateTemplateRequest
): Promise<{ id: string; message: string }> {
  return fetchJson(`${API_BASE}/openrouter/templates?user_id=${userId}`, {
    method: 'POST',
    body: JSON.stringify(template),
  })
}

export async function updateTemplate(
  templateId: string,
  userId: string,
  updates: Partial<CreateTemplateRequest> & { version_notes?: string }
): Promise<{ id: string; version: number; message: string }> {
  return fetchJson(`${API_BASE}/openrouter/templates/${templateId}?user_id=${userId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  })
}

export async function deleteTemplate(
  templateId: string,
  userId: string
): Promise<{ message: string }> {
  return fetchJson(`${API_BASE}/openrouter/templates/${templateId}?user_id=${userId}`, {
    method: 'DELETE',
  })
}

// =============================================================================
// Template Rendering
// =============================================================================

export function renderTemplate(
  template: PromptTemplate,
  variables: Record<string, string | number>
): string {
  let result = template.user_prompt_template
  
  for (const [name, value] of Object.entries(variables)) {
    const pattern = new RegExp(`\\{\\{\\s*${name}\\s*\\}\\}`, 'g')
    result = result.replace(pattern, String(value))
  }
  
  return result
}

export function extractVariables(templateText: string): string[] {
  const pattern = /\{\{\s*(\w+)\s*\}\}/g
  const variables: string[] = []
  let match
  
  while ((match = pattern.exec(templateText)) !== null) {
    if (!variables.includes(match[1])) {
      variables.push(match[1])
    }
  }
  
  return variables
}

// =============================================================================
// Model Comparison Helpers
// =============================================================================

export interface ModelComparison {
  models: OpenRouterModel[]
  comparison: {
    dimension: string
    values: (string | number | boolean | undefined)[]
    winner?: number  // Index of best model
  }[]
}

export function compareModels(models: OpenRouterModel[]): ModelComparison {
  type DimensionDef = {
    dimension: string
    getValue: (m: OpenRouterModel) => number | boolean | undefined
    higherBetter: boolean
  }
  
  const dimensions: DimensionDef[] = [
    {
      dimension: 'Context Length',
      getValue: (m: OpenRouterModel) => m.context_length,
      higherBetter: true,
    },
    {
      dimension: 'Input Cost ($/M)',
      getValue: (m: OpenRouterModel) => m.pricing.per_1m_prompt,
      higherBetter: false,
    },
    {
      dimension: 'Output Cost ($/M)',
      getValue: (m: OpenRouterModel) => m.pricing.per_1m_completion,
      higherBetter: false,
    },
    {
      dimension: 'Tool Support',
      getValue: (m: OpenRouterModel) => m.capabilities.supports_tools,
      higherBetter: true,
    },
    {
      dimension: 'Structured Output',
      getValue: (m: OpenRouterModel) => m.capabilities.supports_structured,
      higherBetter: true,
    },
    {
      dimension: 'Multimodal Input',
      getValue: (m: OpenRouterModel) => m.capabilities.multimodal_input,
      higherBetter: true,
    },
    {
      dimension: 'Availability',
      getValue: (m: OpenRouterModel) => m.availability_score,
      higherBetter: true,
    },
  ]
  
  const comparison = dimensions.map(({ dimension, getValue, higherBetter }) => {
    const values = models.map(m => getValue(m))
    
    // Find winner
    let winnerIdx: number | undefined
    let bestValue: number | boolean | undefined
    
    for (let i = 0; i < values.length; i++) {
      const val = values[i]
      if (val === undefined) continue
      
      if (bestValue === undefined) {
        bestValue = val as number | boolean
        winnerIdx = i
      } else if (typeof val === 'number' && typeof bestValue === 'number') {
        if (higherBetter ? val > bestValue : val < bestValue) {
          bestValue = val
          winnerIdx = i
        }
      } else if (typeof val === 'boolean') {
        if (higherBetter && val && !bestValue) {
          bestValue = val
          winnerIdx = i
        }
      }
    }
    
    return { dimension, values, winner: winnerIdx }
  })
  
  return { models, comparison }
}

