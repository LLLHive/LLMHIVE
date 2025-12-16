/**
 * OpenRouter Model Tiers and Access Control
 * 
 * Defines which models are available for different subscription tiers
 * and how they integrate with the LLMHive orchestrator.
 */

// =============================================================================
// Tier Definitions
// =============================================================================

export type UserTier = 'free' | 'starter' | 'pro' | 'enterprise'

export interface TierConfig {
  name: string
  displayName: string
  description: string
  maxModelsInTeam: number
  maxConcurrentRequests: number
  monthlyTokenLimit: number | null  // null = unlimited
  features: {
    canUseTeams: boolean
    canUseAdvancedReasoning: boolean
    canUsePremiumModels: boolean
    canUseCustomPrompts: boolean
    canExportConversations: boolean
    prioritySupport: boolean
  }
}

// DEVELOPMENT MODE: Increased limits for beta testing
// TODO: Adjust limits when subscription system is live
const DEV_MODE_LIMITS = {
  maxModelsInTeam: 10,  // Allow up to 10 models during dev
  allFeaturesEnabled: true,
}

export const TIER_CONFIGS: Record<UserTier, TierConfig> = {
  free: {
    name: 'free',
    displayName: 'Free',
    description: 'Basic access to get started',
    maxModelsInTeam: DEV_MODE_LIMITS.maxModelsInTeam,  // Was: 2
    maxConcurrentRequests: 5,  // Was: 1
    monthlyTokenLimit: null,  // Was: 100000
    features: {
      canUseTeams: DEV_MODE_LIMITS.allFeaturesEnabled,
      canUseAdvancedReasoning: DEV_MODE_LIMITS.allFeaturesEnabled,
      canUsePremiumModels: DEV_MODE_LIMITS.allFeaturesEnabled,
      canUseCustomPrompts: DEV_MODE_LIMITS.allFeaturesEnabled,
      canExportConversations: DEV_MODE_LIMITS.allFeaturesEnabled,
      prioritySupport: false,
    },
  },
  starter: {
    name: 'starter',
    displayName: 'Starter',
    description: 'For individuals getting serious',
    maxModelsInTeam: DEV_MODE_LIMITS.maxModelsInTeam,
    maxConcurrentRequests: 5,
    monthlyTokenLimit: null,
    features: {
      canUseTeams: DEV_MODE_LIMITS.allFeaturesEnabled,
      canUseAdvancedReasoning: DEV_MODE_LIMITS.allFeaturesEnabled,
      canUsePremiumModels: DEV_MODE_LIMITS.allFeaturesEnabled,
      canUseCustomPrompts: DEV_MODE_LIMITS.allFeaturesEnabled,
      canExportConversations: DEV_MODE_LIMITS.allFeaturesEnabled,
      prioritySupport: false,
    },
  },
  pro: {
    name: 'pro',
    displayName: 'Pro',
    description: 'For power users and small teams',
    maxModelsInTeam: DEV_MODE_LIMITS.maxModelsInTeam,
    maxConcurrentRequests: 10,
    monthlyTokenLimit: null,
    features: {
      canUseTeams: true,
      canUseAdvancedReasoning: true,
      canUsePremiumModels: true,
      canUseCustomPrompts: true,
      canExportConversations: true,
      prioritySupport: false,
    },
  },
  enterprise: {
    name: 'enterprise',
    displayName: 'Enterprise',
    description: 'For organizations with advanced needs',
    maxModelsInTeam: 20,
    maxConcurrentRequests: 50,
    monthlyTokenLimit: null,
    features: {
      canUseTeams: true,
      canUseAdvancedReasoning: true,
      canUsePremiumModels: true,
      canUseCustomPrompts: true,
      canExportConversations: true,
      prioritySupport: true,
    },
  },
}

// =============================================================================
// Model Access Configuration
// =============================================================================

export type ModelAccessLevel = 'free' | 'starter' | 'pro' | 'enterprise'

export interface ModelAccessConfig {
  id: string
  requiredTier: ModelAccessLevel
  // Premium models cost more per token - factor applied to base price
  costMultiplier?: number
  // Some models have usage limits even for paying users
  dailyLimit?: number
  // Tags for UI display
  tags?: ('new' | 'popular' | 'fast' | 'powerful' | 'budget' | 'experimental')[]
}

// Models that are explicitly free tier accessible
const FREE_TIER_PATTERNS = [
  ':free',  // OpenRouter free variants
  'llama-3.1-8b',
  'llama-3.2-1b',
  'llama-3.2-3b',
  'gemma-2-9b',
  'phi-3-mini',
  'qwen2.5-7b',
  'mistral-7b',
]

// Models that require at least Starter tier
const STARTER_TIER_PATTERNS = [
  'llama-3.3-70b',
  'gemini-flash',
  'claude-3-haiku',
  'gpt-4o-mini',
  'mistral-small',
  'deepseek-chat',
  'qwen2.5-72b',
]

// Models that require Pro tier
const PRO_TIER_PATTERNS = [
  'gpt-4o',
  'gpt-4-turbo',
  'claude-3.5-sonnet',
  'claude-3-opus',
  'gemini-1.5-pro',
  'gemini-2.0',
  'mistral-large',
  'deepseek-r1',
  'llama-3.1-405b',
]

// Models that require Enterprise tier (flagship/experimental)
const ENTERPRISE_TIER_PATTERNS = [
  'gpt-5',
  'o1-preview',
  'o1-pro',
  'claude-4',
]

/**
 * Determine the required tier for a model based on its ID
 * 
 * NOTE: For now, all OpenRouter models are accessible to all tiers.
 * The tier system is designed for future monetization, but during 
 * development/beta, users with OpenRouter API keys can access everything.
 */
export function getModelRequiredTier(modelId: string): ModelAccessLevel {
  // DEVELOPMENT MODE: All models accessible
  // TODO: Re-enable tier restrictions when subscription system is live
  const BYPASS_TIER_RESTRICTIONS = true
  
  if (BYPASS_TIER_RESTRICTIONS) {
    return 'free'  // All models accessible to everyone
  }
  
  const lowerModelId = modelId.toLowerCase()
  
  // Check enterprise tier first (most restrictive)
  if (ENTERPRISE_TIER_PATTERNS.some(p => lowerModelId.includes(p.toLowerCase()))) {
    return 'enterprise'
  }
  
  // Check pro tier
  if (PRO_TIER_PATTERNS.some(p => lowerModelId.includes(p.toLowerCase()))) {
    return 'pro'
  }
  
  // Check starter tier
  if (STARTER_TIER_PATTERNS.some(p => lowerModelId.includes(p.toLowerCase()))) {
    return 'starter'
  }
  
  // Check free tier patterns
  if (FREE_TIER_PATTERNS.some(p => lowerModelId.includes(p.toLowerCase()))) {
    return 'free'
  }
  
  // Default: starter tier for unknown models
  return 'starter'
}

/**
 * Check if a user tier can access a model
 */
export function canAccessModel(userTier: UserTier, modelId: string): boolean {
  const requiredTier = getModelRequiredTier(modelId)
  const tierHierarchy: UserTier[] = ['free', 'starter', 'pro', 'enterprise']
  
  const userTierIndex = tierHierarchy.indexOf(userTier)
  const requiredTierIndex = tierHierarchy.indexOf(requiredTier)
  
  return userTierIndex >= requiredTierIndex
}

/**
 * Get tier badge color for display
 */
export function getTierBadgeColor(tier: ModelAccessLevel): string {
  switch (tier) {
    case 'free': return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
    case 'starter': return 'bg-blue-500/10 text-blue-600 border-blue-500/20'
    case 'pro': return 'bg-purple-500/10 text-purple-600 border-purple-500/20'
    case 'enterprise': return 'bg-amber-500/10 text-amber-600 border-amber-500/20'
    default: return 'bg-gray-500/10 text-gray-600 border-gray-500/20'
  }
}

/**
 * Get tier display name
 */
export function getTierDisplayName(tier: ModelAccessLevel): string {
  switch (tier) {
    case 'free': return 'Free'
    case 'starter': return 'Starter'
    case 'pro': return 'Pro'
    case 'enterprise': return 'Enterprise'
    default: return 'Unknown'
  }
}

// =============================================================================
// User Model Selection
// =============================================================================

export interface SelectedModelConfig {
  modelId: string
  enabled: boolean
  // Override the default role for this model
  preferredRole?: 'primary' | 'validator' | 'specialist' | 'fallback'
  // Custom settings for this model
  customSettings?: {
    temperature?: number
    maxTokens?: number
    systemPrompt?: string
  }
  // When was this model added
  addedAt: string
}

export interface UserModelPreferences {
  userId: string
  tier: UserTier
  selectedModels: SelectedModelConfig[]
  // Default model for single-model mode
  defaultModelId?: string
  // Preferred team configuration
  preferredTeamSize: number
  // Auto-select models based on task
  autoSelectEnabled: boolean
  updatedAt: string
}

// =============================================================================
// Default Model Recommendations by Task
// =============================================================================

export interface ModelRecommendation {
  taskType: string
  description: string
  recommendedModels: {
    primary: string[]
    validator?: string[]
    fallback?: string[]
  }
  minTierRequired: UserTier
}

export const MODEL_RECOMMENDATIONS: ModelRecommendation[] = [
  {
    taskType: 'coding',
    description: 'Code generation, debugging, and review',
    recommendedModels: {
      primary: ['anthropic/claude-3.5-sonnet', 'openai/gpt-4o', 'deepseek/deepseek-chat'],
      validator: ['anthropic/claude-3.5-sonnet'],
      fallback: ['openai/gpt-4o-mini', 'meta-llama/llama-3.3-70b-instruct'],
    },
    minTierRequired: 'pro',
  },
  {
    taskType: 'research',
    description: 'Deep research and analysis',
    recommendedModels: {
      primary: ['openai/gpt-5.2', 'anthropic/claude-3.5-sonnet'],
      validator: ['google/gemini-1.5-pro'],
      fallback: ['openai/gpt-4o'],
    },
    minTierRequired: 'enterprise',
  },
  {
    taskType: 'creative',
    description: 'Creative writing and brainstorming',
    recommendedModels: {
      primary: ['anthropic/claude-3.5-sonnet', 'openai/gpt-4o'],
      fallback: ['meta-llama/llama-3.3-70b-instruct'],
    },
    minTierRequired: 'pro',
  },
  {
    taskType: 'chat',
    description: 'General conversation and Q&A',
    recommendedModels: {
      primary: ['openai/gpt-4o-mini', 'anthropic/claude-3-haiku'],
      fallback: ['meta-llama/llama-3.2-3b-instruct:free'],
    },
    minTierRequired: 'free',
  },
  {
    taskType: 'analysis',
    description: 'Data analysis and reasoning',
    recommendedModels: {
      primary: ['openai/gpt-5.2-pro', 'anthropic/claude-3.5-sonnet'],
      validator: ['google/gemini-1.5-pro'],
      fallback: ['openai/gpt-4o'],
    },
    minTierRequired: 'enterprise',
  },
]

/**
 * Get model recommendations for a task, filtered by user tier
 */
export function getRecommendationsForTask(
  taskType: string,
  userTier: UserTier
): ModelRecommendation | null {
  const recommendation = MODEL_RECOMMENDATIONS.find(r => r.taskType === taskType)
  if (!recommendation) return null
  
  // Check if user tier meets minimum requirement
  const tierHierarchy: UserTier[] = ['free', 'starter', 'pro', 'enterprise']
  if (tierHierarchy.indexOf(userTier) < tierHierarchy.indexOf(recommendation.minTierRequired)) {
    return null
  }
  
  return recommendation
}

// =============================================================================
// Storage Keys
// =============================================================================

export const STORAGE_KEYS = {
  USER_MODEL_PREFERENCES: 'llmhive_user_model_preferences',
  SELECTED_MODELS: 'llmhive_selected_models',
  DEFAULT_MODEL: 'llmhive_default_model',
}

