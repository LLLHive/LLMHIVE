/**
 * OpenRouter Orchestrator Integration
 * 
 * Connects selected OpenRouter models to the LLMHive orchestration system.
 * This module bridges the gap between OpenRouter's model catalog and
 * our internal orchestrator.
 */

import type { OpenRouterModel } from './types'
import type { SelectedModelConfig, UserTier } from './tiers'
import { TIER_CONFIGS, canAccessModel, getModelRequiredTier } from './tiers'

// =============================================================================
// Types for Orchestrator Integration
// =============================================================================

export interface OrchestrationModelConfig {
  id: string
  provider: 'openrouter'
  displayName: string
  role: 'primary' | 'validator' | 'specialist' | 'fallback'
  enabled: boolean
  
  // Capabilities
  capabilities: {
    supportsTools: boolean
    supportsStreaming: boolean
    supportsVision: boolean
    supportsJson: boolean
    maxContextLength: number
  }
  
  // Cost info for budget management
  pricing: {
    promptPer1M: number
    completionPer1M: number
  }
  
  // Custom settings
  settings: {
    temperature: number
    maxTokens: number
    systemPrompt?: string
  }
  
  // Metadata
  openRouterId: string
  addedAt: string
}

export interface OrchestrationTeam {
  id: string
  name: string
  description?: string
  models: OrchestrationModelConfig[]
  strategy: 'sequential' | 'parallel' | 'debate' | 'cascade' | 'ensemble'
  createdAt: string
  updatedAt: string
}

export interface OrchestrationRequest {
  prompt: string
  systemPrompt?: string
  teamId?: string
  // If no teamId, use these models directly
  models?: string[]
  // Request settings
  settings?: {
    maxBudget?: number
    timeoutMs?: number
    requireConsensus?: boolean
    minConfidence?: number
  }
}

// =============================================================================
// Model Conversion
// =============================================================================

/**
 * Convert an OpenRouter model + selection config to an orchestration config
 */
export function toOrchestrationConfig(
  model: OpenRouterModel,
  config: SelectedModelConfig
): OrchestrationModelConfig {
  return {
    id: `openrouter:${model.id}`,
    provider: 'openrouter',
    displayName: model.name,
    role: config.preferredRole || 'primary',
    enabled: config.enabled,
    
    capabilities: {
      supportsTools: model.capabilities?.supports_tools ?? false,
      supportsStreaming: model.capabilities?.supports_streaming ?? true,
      supportsVision: model.capabilities?.multimodal_input ?? false,
      supportsJson: model.capabilities?.supports_structured ?? false,
      maxContextLength: model.context_length || 8192,
    },
    
    pricing: {
      promptPer1M: (model.pricing?.per_1m_prompt || model.pricing?.prompt || 0) * 1000000,
      completionPer1M: (model.pricing?.per_1m_completion || model.pricing?.completion || 0) * 1000000,
    },
    
    settings: {
      temperature: config.customSettings?.temperature ?? 0.7,
      maxTokens: config.customSettings?.maxTokens ?? 4096,
      systemPrompt: config.customSettings?.systemPrompt,
    },
    
    openRouterId: model.id,
    addedAt: config.addedAt,
  }
}

/**
 * Build an orchestration team from selected models
 */
export function buildOrchestrationTeam(
  models: OpenRouterModel[],
  configs: SelectedModelConfig[],
  teamName: string = 'Default Team'
): OrchestrationTeam {
  const orchestrationModels: OrchestrationModelConfig[] = []
  
  for (const config of configs) {
    const model = models.find(m => m.id === config.modelId)
    if (model && config.enabled) {
      orchestrationModels.push(toOrchestrationConfig(model, config))
    }
  }
  
  // Sort by role priority: primary first, then validators, specialists, fallbacks
  const rolePriority = { primary: 0, validator: 1, specialist: 2, fallback: 3 }
  orchestrationModels.sort((a, b) => rolePriority[a.role] - rolePriority[b.role])
  
  // Determine strategy based on team composition
  let strategy: OrchestrationTeam['strategy'] = 'sequential'
  
  const primaryCount = orchestrationModels.filter(m => m.role === 'primary').length
  const validatorCount = orchestrationModels.filter(m => m.role === 'validator').length
  
  if (validatorCount > 0 && primaryCount > 0) {
    strategy = 'cascade'  // Primary generates, validators check
  } else if (primaryCount >= 2) {
    strategy = 'ensemble'  // Multiple primaries vote
  } else if (orchestrationModels.some(m => m.role === 'specialist')) {
    strategy = 'parallel'  // Specialists work in parallel
  }
  
  return {
    id: `team_${Date.now()}`,
    name: teamName,
    models: orchestrationModels,
    strategy,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

// =============================================================================
// Model Recommendations
// =============================================================================

export interface TaskRecommendation {
  task: string
  recommendedTeam: {
    primary: string[]
    validator: string[]
    fallback: string[]
  }
  explanation: string
}

/**
 * Get recommended models for a specific task
 */
export function getRecommendedTeam(
  taskType: 'coding' | 'research' | 'creative' | 'analysis' | 'chat',
  availableModels: OpenRouterModel[],
  userTier: UserTier
): TaskRecommendation {
  const tierConfig = TIER_CONFIGS[userTier]
  const maxModels = tierConfig.maxModelsInTeam
  
  // Model preferences by task
  const taskPreferences: Record<string, { keywords: string[], preferred: string[] }> = {
    coding: {
      keywords: ['code', 'programming', 'developer', 'engineer'],
      preferred: [
        'anthropic/claude-3.5-sonnet',
        'openai/gpt-4o',
        'deepseek/deepseek-chat',
        'meta-llama/llama-3.3-70b-instruct',
      ],
    },
    research: {
      keywords: ['research', 'analysis', 'academic'],
      preferred: [
        'openai/gpt-5.2',
        'anthropic/claude-3.5-sonnet',
        'google/gemini-1.5-pro',
      ],
    },
    creative: {
      keywords: ['creative', 'writing', 'story'],
      preferred: [
        'anthropic/claude-3.5-sonnet',
        'openai/gpt-4o',
        'meta-llama/llama-3.3-70b-instruct',
      ],
    },
    analysis: {
      keywords: ['analyze', 'data', 'reasoning'],
      preferred: [
        'openai/gpt-5.2-pro',
        'anthropic/claude-3.5-sonnet',
        'openai/o1-preview',
      ],
    },
    chat: {
      keywords: ['chat', 'conversation', 'assistant'],
      preferred: [
        'openai/gpt-4o-mini',
        'anthropic/claude-3-haiku',
        'meta-llama/llama-3.2-3b-instruct:free',
      ],
    },
  }
  
  const prefs = taskPreferences[taskType] || taskPreferences.chat
  
  // Filter available models by user tier
  const accessibleModels = availableModels.filter(m => canAccessModel(userTier, m.id))
  
  // Find best matches from preferred list
  const findModel = (id: string) => accessibleModels.find(m => 
    m.id.toLowerCase().includes(id.toLowerCase().split('/')[1])
  )
  
  const primary: string[] = []
  const validator: string[] = []
  const fallback: string[] = []
  
  // Build team respecting max models limit
  for (const preferred of prefs.preferred) {
    if (primary.length + validator.length + fallback.length >= maxModels) break
    
    const model = findModel(preferred)
    if (model) {
      if (primary.length < Math.ceil(maxModels / 2)) {
        primary.push(model.id)
      } else if (validator.length < 1 && tierConfig.features.canUseTeams) {
        validator.push(model.id)
      } else if (fallback.length < 1) {
        fallback.push(model.id)
      }
    }
  }
  
  // Fill remaining slots with accessible models if needed
  if (primary.length === 0) {
    const firstAccessible = accessibleModels[0]
    if (firstAccessible) primary.push(firstAccessible.id)
  }
  
  return {
    task: taskType,
    recommendedTeam: { primary, validator, fallback },
    explanation: `Recommended ${primary.length + validator.length + fallback.length} models for ${taskType}. ` +
      `Primary: ${primary.length}, Validators: ${validator.length}, Fallback: ${fallback.length}`,
  }
}

// =============================================================================
// Cost Estimation
// =============================================================================

export interface CostEstimate {
  estimatedPromptTokens: number
  estimatedCompletionTokens: number
  estimatedCostUsd: number
  breakdown: {
    modelId: string
    promptCost: number
    completionCost: number
    total: number
  }[]
}

/**
 * Estimate the cost of running a request through a team
 */
export function estimateTeamCost(
  team: OrchestrationTeam,
  estimatedPromptTokens: number = 1000,
  estimatedCompletionTokens: number = 500
): CostEstimate {
  const breakdown: CostEstimate['breakdown'] = []
  let totalCost = 0
  
  for (const model of team.models) {
    if (!model.enabled) continue
    
    const promptCost = (estimatedPromptTokens / 1000000) * model.pricing.promptPer1M
    const completionCost = (estimatedCompletionTokens / 1000000) * model.pricing.completionPer1M
    const modelTotal = promptCost + completionCost
    
    breakdown.push({
      modelId: model.id,
      promptCost,
      completionCost,
      total: modelTotal,
    })
    
    totalCost += modelTotal
  }
  
  return {
    estimatedPromptTokens,
    estimatedCompletionTokens,
    estimatedCostUsd: totalCost,
    breakdown,
  }
}

// =============================================================================
// Storage Keys
// =============================================================================

export const ORCHESTRATION_STORAGE_KEYS = {
  TEAMS: 'llmhive_orchestration_teams',
  ACTIVE_TEAM: 'llmhive_active_team',
  USAGE_HISTORY: 'llmhive_orchestration_usage',
}

/**
 * Load saved teams from localStorage
 */
export function loadSavedTeams(): OrchestrationTeam[] {
  try {
    const stored = localStorage.getItem(ORCHESTRATION_STORAGE_KEYS.TEAMS)
    if (stored) {
      return JSON.parse(stored) as OrchestrationTeam[]
    }
  } catch (e) {
    console.error('Failed to load saved teams:', e)
  }
  return []
}

/**
 * Save teams to localStorage
 */
export function saveTeams(teams: OrchestrationTeam[]): void {
  try {
    localStorage.setItem(ORCHESTRATION_STORAGE_KEYS.TEAMS, JSON.stringify(teams))
  } catch (e) {
    console.error('Failed to save teams:', e)
  }
}

/**
 * Get the active team ID
 */
export function getActiveTeamId(): string | null {
  try {
    return localStorage.getItem(ORCHESTRATION_STORAGE_KEYS.ACTIVE_TEAM)
  } catch (e) {
    return null
  }
}

/**
 * Set the active team ID
 */
export function setActiveTeamId(teamId: string): void {
  try {
    localStorage.setItem(ORCHESTRATION_STORAGE_KEYS.ACTIVE_TEAM, teamId)
  } catch (e) {
    console.error('Failed to set active team:', e)
  }
}

