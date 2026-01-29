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

// =============================================================================
// PRODUCTION LIMITS - Configured for 50% minimum profit margin
// =============================================================================

// Set to false to enable production limits
const DEV_MODE = false

export const TIER_CONFIGS: Record<UserTier, TierConfig> = {
  free: {
    name: 'free',
    displayName: 'Free',
    description: 'Basic access to get started',
    maxModelsInTeam: 2,
    maxConcurrentRequests: 1,
    monthlyTokenLimit: null,  // UNLIMITED for Free tier (Jan 2026)
    features: {
      canUseTeams: false,
      canUseAdvancedReasoning: false,
      canUsePremiumModels: false,  // Budget models only!
      canUseCustomPrompts: false,
      canExportConversations: false,
      prioritySupport: false,
    },
  },
  starter: {
    name: 'starter',
    displayName: 'Starter',
    description: 'For individuals getting serious ($15/mo)',
    maxModelsInTeam: 5,
    maxConcurrentRequests: 3,
    monthlyTokenLimit: DEV_MODE ? null : 500_000,  // 500K tokens
    features: {
      canUseTeams: false,
      canUseAdvancedReasoning: false,
      canUsePremiumModels: false,  // Standard models only!
      canUseCustomPrompts: true,
      canExportConversations: true,
      prioritySupport: false,
    },
  },
  pro: {
    name: 'pro',
    displayName: 'Pro',
    description: 'For power users and small teams ($29.99/mo)',
    maxModelsInTeam: 10,
    maxConcurrentRequests: 10,
    monthlyTokenLimit: DEV_MODE ? null : 1_000_000,  // 1M tokens (reduced from 3M!)
    features: {
      canUseTeams: true,
      canUseAdvancedReasoning: true,
      canUsePremiumModels: true,  // Premium access with caps
      canUseCustomPrompts: true,
      canExportConversations: true,
      prioritySupport: false,
    },
  },
  enterprise: {
    name: 'enterprise',
    displayName: 'Enterprise',
    description: 'For organizations with advanced needs ($199.99/mo)',
    maxModelsInTeam: 20,
    maxConcurrentRequests: 50,
    monthlyTokenLimit: DEV_MODE ? null : 5_000_000,  // 5M base (was unlimited!)
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
// Premium Model Cost Controls - Prevent runaway costs
// =============================================================================

export interface PremiumModelLimits {
  modelPattern: string
  dailyTokenLimit: number
  monthlyTokenLimit: number
  costPer1MTokens: number  // For tracking
  requiredTier: ModelAccessLevel
}

// CRITICAL: These models can bankrupt us if uncapped!
export const PREMIUM_MODEL_LIMITS: PremiumModelLimits[] = [
  // Flagship models - STRICT limits
  {
    modelPattern: 'o1-pro',
    dailyTokenLimit: 10_000,      // $6/day max
    monthlyTokenLimit: 100_000,   // $60/month max
    costPer1MTokens: 600,
    requiredTier: 'enterprise',
  },
  {
    modelPattern: 'gpt-5.2-pro',
    dailyTokenLimit: 25_000,      // ~$4.20/day
    monthlyTokenLimit: 250_000,   // ~$42/month max
    costPer1MTokens: 168,
    requiredTier: 'enterprise',
  },
  {
    modelPattern: 'o3',
    dailyTokenLimit: 50_000,
    monthlyTokenLimit: 500_000,
    costPer1MTokens: 8,
    requiredTier: 'pro',
  },
  {
    modelPattern: 'claude-opus-4.5',
    dailyTokenLimit: 100_000,
    monthlyTokenLimit: 1_000_000,
    costPer1MTokens: 25,
    requiredTier: 'enterprise',
  },
  {
    modelPattern: 'claude-sonnet-4.5',
    dailyTokenLimit: 200_000,
    monthlyTokenLimit: 2_000_000,
    costPer1MTokens: 15,
    requiredTier: 'pro',
  },
  {
    modelPattern: 'claude-3.5-sonnet',
    dailyTokenLimit: 150_000,
    monthlyTokenLimit: 1_500_000,
    costPer1MTokens: 30,
    requiredTier: 'pro',
  },
]

// =============================================================================
// Usage Thresholds for Throttling
// =============================================================================

export interface UsageThreshold {
  percentUsed: number
  action: 'warning' | 'throttle' | 'block'
  message: string
  modelRestriction?: 'premium_blocked' | 'standard_only' | 'budget_only'
}

export const USAGE_THRESHOLDS: UsageThreshold[] = [
  {
    percentUsed: 50,
    action: 'warning',
    message: 'You have used 50% of your monthly token allowance.',
  },
  {
    percentUsed: 75,
    action: 'throttle',
    message: 'High usage detected. Switching to cost-effective models to preserve your allowance.',
    modelRestriction: 'premium_blocked',  // Block premium, allow standard
  },
  {
    percentUsed: 90,
    action: 'throttle',
    message: 'Approaching limit. Using budget-efficient models only.',
    modelRestriction: 'budget_only',  // Only free/cheap models
  },
  {
    percentUsed: 100,
    action: 'block',
    message: 'Monthly token limit reached. Upgrade your plan or wait for next billing cycle.',
  },
]

// =============================================================================
// Cost-Effective Model Routing
// =============================================================================

export interface ModelCostTier {
  tier: 'budget' | 'standard' | 'premium' | 'flagship'
  costPer1MRange: [number, number]  // [min, max] output cost
  models: string[]
}

export const MODEL_COST_TIERS: ModelCostTier[] = [
  {
    tier: 'budget',
    costPer1MRange: [0, 2],
    models: [
      'meta-llama/llama-3.3-70b-instruct',
      'deepseek/deepseek-chat',
      'google/gemini-2.5-flash',
      'openai/gpt-4o-mini',
      'anthropic/claude-3-haiku',
    ],
  },
  {
    tier: 'standard',
    costPer1MRange: [2, 10],
    models: [
      'anthropic/claude-haiku-4.5',
      'google/gemini-2.5-pro',
      'openai/gpt-4o',
      'openai/o3',
    ],
  },
  {
    tier: 'premium',
    costPer1MRange: [10, 50],
    models: [
      'anthropic/claude-sonnet-4.5',
      'anthropic/claude-3.5-sonnet',
      'anthropic/claude-opus-4.5',
      'google/gemini-3-pro-preview',
    ],
  },
  {
    tier: 'flagship',
    costPer1MRange: [50, 1000],
    models: [
      'openai/gpt-5.2-pro',
      'openai/o1-pro',
    ],
  },
]

/**
 * Get the cost tier for a model
 */
export function getModelCostTier(modelId: string): ModelCostTier['tier'] {
  const lowerModelId = modelId.toLowerCase()
  
  for (const costTier of MODEL_COST_TIERS) {
    if (costTier.models.some(m => lowerModelId.includes(m.split('/')[1]))) {
      return costTier.tier
    }
  }
  
  return 'standard'  // Default to standard if unknown
}

/**
 * Get allowed model cost tier based on usage percentage
 */
export function getAllowedModelTier(usagePercent: number): ModelCostTier['tier'][] {
  if (usagePercent < 50) {
    return ['budget', 'standard', 'premium', 'flagship']
  } else if (usagePercent < 75) {
    return ['budget', 'standard', 'premium']  // No flagship
  } else if (usagePercent < 90) {
    return ['budget', 'standard']  // No premium
  } else {
    return ['budget']  // Budget only
  }
}

/**
 * Check if a user can use a specific model based on their usage
 */
export function canUseModelWithUsage(
  modelId: string,
  usagePercent: number,
  userTier: UserTier
): { allowed: boolean; reason?: string; alternative?: string } {
  const modelCostTier = getModelCostTier(modelId)
  const allowedTiers = getAllowedModelTier(usagePercent)
  
  if (!allowedTiers.includes(modelCostTier)) {
    // Find alternative model
    const budgetAlternatives: Record<string, string> = {
      'gpt-5.2-pro': 'openai/gpt-4o-mini',
      'o1-pro': 'openai/o3',
      'claude-opus-4.5': 'anthropic/claude-haiku-4.5',
      'claude-sonnet-4.5': 'anthropic/claude-haiku-4.5',
      'claude-3.5-sonnet': 'anthropic/claude-3-haiku',
    }
    
    const modelName = modelId.split('/')[1] || modelId
    const alternative = budgetAlternatives[modelName]
    
    return {
      allowed: false,
      reason: `High usage (${usagePercent.toFixed(0)}%). Using cost-effective models to preserve allowance.`,
      alternative,
    }
  }
  
  return { allowed: true }
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

// Models that are explicitly free tier accessible (Budget tier - ~$0-2/1M)
const FREE_TIER_PATTERNS = [
  ':free',  // OpenRouter free variants
  'llama-3.1-8b',
  'llama-3.2-1b',
  'llama-3.2-3b',
  'llama-3.3-70b',  // Great value
  'gemma-2-9b',
  'gemma-3-4b',
  'phi-3-mini',
  'qwen2.5-7b',
  'mistral-7b',
  'deepseek-chat',  // Very cost effective
  'mimo-v2-flash',  // Xiaomi free model
]

// Models that require at least Starter tier (Standard tier - ~$2-10/1M)
const STARTER_TIER_PATTERNS = [
  'gemini-2.5-flash',
  'gemini-flash',
  'claude-3-haiku',
  'claude-haiku-4.5',
  'gpt-4o-mini',
  'mistral-small',
  'qwen2.5-72b',
  'qwen3-72b',
  'glm-4.7',
  'grok-4.1-fast',  // Fast variant
]

// Models that require Pro tier (Premium tier - ~$10-50/1M)
const PRO_TIER_PATTERNS = [
  'gpt-4o',
  'gpt-4-turbo',
  'o3',  // OpenAI o3
  'claude-3.5-sonnet',
  'claude-sonnet-4.5',
  'claude-3-opus',
  'gemini-1.5-pro',
  'gemini-2.0',
  'gemini-2.5-pro',
  'gemini-3-flash',  // Gemini 3 flash is Pro
  'mistral-large',
  'deepseek-r1',
  'deepseek-v3',
  'llama-4',  // Llama 4 series
  'grok-code-fast',
]

// Models that require Enterprise tier (Flagship tier - ~$50-600+/1M)
const ENTERPRISE_TIER_PATTERNS = [
  'gpt-5.2-pro',    // $168/1M output!
  'gpt-5.2-codex',
  'gpt-5.1',
  'gpt-5',
  'o1-preview',
  'o1-pro',         // $600/1M output! DANGER
  'o3-deep-research',
  'claude-opus-4.5',  // $25/1M but heavy usage
  'claude-opus-4',
  'claude-4',
  'gemini-3-pro',   // Gemini 3 Pro is Enterprise
]

/**
 * Determine the required tier for a model based on its ID
 * 
 * PRODUCTION: Tier restrictions are now ENFORCED to protect profitability.
 */
export function getModelRequiredTier(modelId: string): ModelAccessLevel {
  // PRODUCTION MODE: Enforce tier restrictions for profitability
  const BYPASS_TIER_RESTRICTIONS = false
  
  if (BYPASS_TIER_RESTRICTIONS) {
    return 'free'  // Dev mode - all accessible
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
 * 
 * NOTE: We now only display 2 tiers to users: "Elite" and "Free"
 * - Free: Green badge (free models)
 * - Elite: Gold/amber badge (all paid tier models - starter, pro, enterprise)
 */
export function getTierBadgeColor(tier: ModelAccessLevel): string {
  switch (tier) {
    case 'free': 
      return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30'
    case 'starter':
    case 'pro':
    case 'enterprise':
      // All paid tiers display as "Elite" with gold/amber styling
      return 'bg-amber-500/10 text-amber-500 border-amber-500/30'
    default: 
      return 'bg-gray-500/10 text-gray-600 border-gray-500/20'
  }
}

/**
 * Get tier display name
 * 
 * NOTE: We now only display 2 tiers to users: "Elite" and "Free"
 * - Free tier models → "Free"
 * - All other tiers (starter, pro, enterprise) → "Elite"
 */
export function getTierDisplayName(tier: ModelAccessLevel): string {
  switch (tier) {
    case 'free': 
      return 'Free'
    case 'starter':
    case 'pro':
    case 'enterprise':
      // All paid tiers display as "Elite"
      return 'Elite'
    default: 
      return 'Unknown'
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

