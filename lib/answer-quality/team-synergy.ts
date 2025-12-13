/**
 * Team Synergy Optimization System
 * 
 * Creates optimal model teams based on:
 * - Individual model strengths/weaknesses
 * - Synergy patterns between models
 * - Task requirements
 * - Cost/performance tradeoffs
 */

import type { QueryAnalysis } from './types'
import { 
  MODEL_PROFILES, 
  getModelProfile, 
  getBestModelsForCapability,
  getSynergyPairs,
  calculateModelFitScore,
  type ModelProfile,
  type ModelCapabilities,
} from './model-profiles'

export interface OptimizedTeam {
  name: string
  description: string
  
  // Team members with roles
  members: TeamMember[]
  
  // Workflow configuration
  workflow: SynergyWorkflow
  
  // Expected performance
  expectedPerformance: {
    qualityBoost: number  // % improvement over single model
    latency: 'fast' | 'medium' | 'slow'
    estimatedCost: number
    reliability: number
  }
  
  // Rationale for this team composition
  rationale: string[]
}

export interface TeamMember {
  modelId: string
  profile: ModelProfile
  role: TeamRole
  systemPrompt: string
  temperature: number
  priority: number
}

export type TeamRole = 
  | 'lead'           // Primary responder
  | 'specialist'     // Domain expert
  | 'critic'         // Challenges and verifies
  | 'synthesizer'    // Combines insights
  | 'optimizer'      // Refines output
  | 'fact-checker'   // Verifies claims
  | 'creative'       // Adds creative elements

export interface SynergyWorkflow {
  type: 'parallel' | 'sequential' | 'debate' | 'cascade' | 'ensemble'
  steps: WorkflowStep[]
  consensusMethod: 'vote' | 'synthesize' | 'lead-decides' | 'weighted'
  maxRounds: number
}

export interface WorkflowStep {
  stepNumber: number
  participants: string[]  // Model IDs
  action: 'generate' | 'critique' | 'refine' | 'verify' | 'synthesize'
  dependsOn: number[]
  timeout: number
}

// Pre-defined team templates for common scenarios
export const SYNERGY_TEAM_TEMPLATES: Record<string, Partial<OptimizedTeam>> = {
  'code-excellence': {
    name: 'Code Excellence Team',
    description: 'Optimal team for high-quality code generation',
    workflow: {
      type: 'cascade',
      steps: [
        { stepNumber: 1, participants: ['deepseek-chat'], action: 'generate', dependsOn: [], timeout: 30000 },
        { stepNumber: 2, participants: ['claude-3-5-sonnet'], action: 'critique', dependsOn: [1], timeout: 20000 },
        { stepNumber: 3, participants: ['deepseek-chat'], action: 'refine', dependsOn: [2], timeout: 25000 },
        { stepNumber: 4, participants: ['gpt-4o'], action: 'verify', dependsOn: [3], timeout: 15000 },
      ],
      consensusMethod: 'synthesize',
      maxRounds: 1,
    },
    rationale: [
      'DeepSeek leads with best-in-class code generation',
      'Claude provides nuanced code review and edge case detection',
      'DeepSeek incorporates critique for improved version',
      'GPT-4o does final verification and format polish',
    ],
  },
  
  'research-depth': {
    name: 'Deep Research Team',
    description: 'Maximum depth for research and analysis tasks',
    workflow: {
      type: 'parallel',
      steps: [
        { stepNumber: 1, participants: ['claude-3-5-sonnet', 'gpt-4o', 'gemini-1-5-pro'], action: 'generate', dependsOn: [], timeout: 40000 },
        { stepNumber: 2, participants: ['claude-3-5-sonnet'], action: 'synthesize', dependsOn: [1], timeout: 30000 },
        { stepNumber: 3, participants: ['gpt-4o'], action: 'verify', dependsOn: [2], timeout: 20000 },
      ],
      consensusMethod: 'synthesize',
      maxRounds: 1,
    },
    rationale: [
      'Three perspectives for comprehensive coverage',
      'Claude synthesizes diverse insights',
      'GPT-4o verifies and polishes final output',
    ],
  },
  
  'complex-reasoning': {
    name: 'Complex Reasoning Team',
    description: 'For problems requiring deep logical reasoning',
    workflow: {
      type: 'cascade',
      steps: [
        { stepNumber: 1, participants: ['o1-preview'], action: 'generate', dependsOn: [], timeout: 120000 },
        { stepNumber: 2, participants: ['claude-3-5-sonnet'], action: 'critique', dependsOn: [1], timeout: 30000 },
        { stepNumber: 3, participants: ['gpt-4o'], action: 'refine', dependsOn: [2], timeout: 25000 },
      ],
      consensusMethod: 'lead-decides',
      maxRounds: 1,
    },
    rationale: [
      'o1 provides unmatched reasoning depth',
      'Claude catches nuances and potential errors',
      'GPT-4o formats for accessibility',
    ],
  },
  
  'balanced-quality': {
    name: 'Balanced Quality Team',
    description: 'Good balance of quality, speed, and cost',
    workflow: {
      type: 'parallel',
      steps: [
        { stepNumber: 1, participants: ['gpt-4o', 'claude-3-5-sonnet'], action: 'generate', dependsOn: [], timeout: 25000 },
        { stepNumber: 2, participants: ['gpt-4o'], action: 'synthesize', dependsOn: [1], timeout: 20000 },
      ],
      consensusMethod: 'synthesize',
      maxRounds: 1,
    },
    rationale: [
      'Two top-tier models for diverse perspectives',
      'GPT-4o synthesizes for clean output',
      'Balanced cost-performance ratio',
    ],
  },
  
  'debate-format': {
    name: 'Debate Team',
    description: 'Models debate to find best answer',
    workflow: {
      type: 'debate',
      steps: [
        { stepNumber: 1, participants: ['gpt-4o'], action: 'generate', dependsOn: [], timeout: 25000 },
        { stepNumber: 2, participants: ['claude-3-5-sonnet'], action: 'critique', dependsOn: [1], timeout: 20000 },
        { stepNumber: 3, participants: ['gpt-4o'], action: 'refine', dependsOn: [2], timeout: 25000 },
        { stepNumber: 4, participants: ['claude-3-5-sonnet'], action: 'critique', dependsOn: [3], timeout: 20000 },
        { stepNumber: 5, participants: ['gpt-4o'], action: 'synthesize', dependsOn: [4], timeout: 20000 },
      ],
      consensusMethod: 'synthesize',
      maxRounds: 2,
    },
    rationale: [
      'Back-and-forth refinement catches errors',
      'Different perspectives strengthen answer',
      'Multiple rounds ensure thorough exploration',
    ],
  },
  
  'cost-effective': {
    name: 'Cost-Effective Team',
    description: 'High quality at minimal cost',
    workflow: {
      type: 'cascade',
      steps: [
        { stepNumber: 1, participants: ['deepseek-chat'], action: 'generate', dependsOn: [], timeout: 25000 },
        { stepNumber: 2, participants: ['llama-3-3-70b'], action: 'verify', dependsOn: [1], timeout: 20000 },
      ],
      consensusMethod: 'lead-decides',
      maxRounds: 1,
    },
    rationale: [
      'DeepSeek provides excellent quality at low cost',
      'Llama verifies without cloud API costs',
      'Minimal token usage',
    ],
  },
  
  'creative-excellence': {
    name: 'Creative Excellence Team',
    description: 'For creative writing and ideation',
    workflow: {
      type: 'sequential',
      steps: [
        { stepNumber: 1, participants: ['gpt-4o'], action: 'generate', dependsOn: [], timeout: 30000 },
        { stepNumber: 2, participants: ['claude-3-5-sonnet'], action: 'critique', dependsOn: [1], timeout: 20000 },
        { stepNumber: 3, participants: ['gpt-4o'], action: 'refine', dependsOn: [2], timeout: 25000 },
      ],
      consensusMethod: 'synthesize',
      maxRounds: 1,
    },
    rationale: [
      'GPT-4o excels at creative, engaging content',
      'Claude provides nuanced critique',
      'Final refinement for polish',
    ],
  },
}

/**
 * Build optimal team for a given task
 */
export function buildOptimalTeam(
  analysis: QueryAnalysis,
  availableModels: string[],
  constraints: {
    maxModels?: number
    maxCost?: number
    maxLatency?: 'fast' | 'medium' | 'slow'
    prioritizeQuality?: boolean
  } = {}
): OptimizedTeam {
  const { maxModels = 3, prioritizeQuality = true } = constraints
  
  // Determine required capabilities
  const requiredCapabilities = getRequiredCapabilities(analysis)
  
  // Score all available models
  const modelScores = availableModels.map(modelId => {
    const profile = getModelProfile(modelId)
    if (!profile) return { modelId, profile: null, score: 0 }
    
    const score = calculateModelFitScore(profile, {
      capabilities: requiredCapabilities,
      latency: constraints.maxLatency,
      maxCost: constraints.maxCost,
    })
    
    return { modelId, profile, score }
  }).filter(m => m.profile !== null) as { modelId: string; profile: ModelProfile; score: number }[]
  
  // Sort by score
  modelScores.sort((a, b) => b.score - a.score)
  
  // Select team members
  const members: TeamMember[] = []
  
  // Lead: highest scoring model
  if (modelScores.length > 0) {
    members.push(createTeamMember(modelScores[0].profile, 'lead', analysis))
  }
  
  // Add specialists based on task needs
  if (analysis.intent === 'code' && members.length < maxModels) {
    const codeSpecialist = modelScores.find(m => 
      m.profile.capabilities.coding >= 90 && 
      !members.some(mem => mem.modelId === m.modelId)
    )
    if (codeSpecialist) {
      members.push(createTeamMember(codeSpecialist.profile, 'specialist', analysis))
    }
  }
  
  // Add critic if quality is prioritized
  if (prioritizeQuality && members.length < maxModels) {
    const critic = modelScores.find(m => 
      m.profile.capabilities.analysis >= 85 &&
      !members.some(mem => mem.modelId === m.modelId)
    )
    if (critic) {
      members.push(createTeamMember(critic.profile, 'critic', analysis))
    }
  }
  
  // Determine workflow based on team composition
  const workflow = determineWorkflow(members, analysis)
  
  // Calculate expected performance
  const expectedPerformance = calculateExpectedPerformance(members, workflow)
  
  // Generate rationale
  const rationale = generateRationale(members, analysis)
  
  return {
    name: `${analysis.intent} Optimized Team`,
    description: `Team optimized for ${analysis.intent} tasks with ${analysis.complexity} complexity`,
    members,
    workflow,
    expectedPerformance,
    rationale,
  }
}

/**
 * Get required capabilities for a task
 */
function getRequiredCapabilities(
  analysis: QueryAnalysis
): Partial<Record<keyof ModelCapabilities, number>> {
  const baseCapabilities: Partial<Record<keyof ModelCapabilities, number>> = {
    reasoning: 70,
    instruction: 80,
  }
  
  // Intent-specific requirements
  switch (analysis.intent) {
    case 'code':
      baseCapabilities.coding = 90
      baseCapabilities.structuredOutput = 85
      break
    case 'analytical':
      baseCapabilities.analysis = 85
      baseCapabilities.reasoning = 85
      break
    case 'research':
      baseCapabilities.analysis = 90
      baseCapabilities.factualAccuracy = 85
      break
    case 'creative':
      baseCapabilities.creativity = 90
      break
    case 'factual':
      baseCapabilities.factualAccuracy = 90
      break
    case 'troubleshooting':
      baseCapabilities.coding = 85
      baseCapabilities.reasoning = 85
      break
  }
  
  // Complexity adjustments
  if (analysis.complexity === 'expert') {
    for (const key of Object.keys(baseCapabilities) as (keyof ModelCapabilities)[]) {
      baseCapabilities[key] = Math.min(100, (baseCapabilities[key] || 70) + 10)
    }
  }
  
  return baseCapabilities
}

/**
 * Create a team member from a profile
 */
function createTeamMember(
  profile: ModelProfile,
  role: TeamRole,
  analysis: QueryAnalysis
): TeamMember {
  const systemPrompts: Record<TeamRole, string> = {
    lead: `You are the lead expert responsible for providing a comprehensive, high-quality response. Focus on accuracy, clarity, and completeness.`,
    specialist: `You are a specialist in ${analysis.domain}. Provide deep, expert-level insights focusing on technical accuracy and best practices.`,
    critic: `You are a critical reviewer. Your job is to identify potential issues, missing information, edge cases, and areas for improvement. Be constructively critical.`,
    synthesizer: `You are responsible for synthesizing multiple perspectives into a coherent, unified response. Combine the best elements from all inputs.`,
    optimizer: `You are responsible for refining and optimizing the response for clarity, conciseness, and impact. Polish the output without changing the core content.`,
    'fact-checker': `You are a fact checker. Verify claims, identify unsupported statements, and flag potential inaccuracies. Provide corrections with sources.`,
    creative: `You are a creative specialist. Add engaging elements, unique perspectives, and creative flourishes while maintaining accuracy.`,
  }
  
  return {
    modelId: profile.id,
    profile,
    role,
    systemPrompt: systemPrompts[role],
    temperature: profile.temperatureGuide[analysis.intent === 'creative' ? 'creative' : 'analysis'] || 0.3,
    priority: role === 'lead' ? 1 : role === 'specialist' ? 2 : 3,
  }
}

/**
 * Determine optimal workflow for team
 */
function determineWorkflow(
  members: TeamMember[],
  analysis: QueryAnalysis
): SynergyWorkflow {
  // Single member: simple workflow
  if (members.length === 1) {
    return {
      type: 'sequential',
      steps: [
        { stepNumber: 1, participants: [members[0].modelId], action: 'generate', dependsOn: [], timeout: 30000 },
      ],
      consensusMethod: 'lead-decides',
      maxRounds: 1,
    }
  }
  
  // Two members: cascade or debate based on roles
  if (members.length === 2) {
    const hasCritic = members.some(m => m.role === 'critic')
    
    return {
      type: hasCritic ? 'cascade' : 'parallel',
      steps: hasCritic ? [
        { stepNumber: 1, participants: [members.find(m => m.role === 'lead')!.modelId], action: 'generate', dependsOn: [], timeout: 30000 },
        { stepNumber: 2, participants: [members.find(m => m.role === 'critic')!.modelId], action: 'critique', dependsOn: [1], timeout: 20000 },
        { stepNumber: 3, participants: [members.find(m => m.role === 'lead')!.modelId], action: 'refine', dependsOn: [2], timeout: 25000 },
      ] : [
        { stepNumber: 1, participants: members.map(m => m.modelId), action: 'generate', dependsOn: [], timeout: 30000 },
        { stepNumber: 2, participants: [members[0].modelId], action: 'synthesize', dependsOn: [1], timeout: 20000 },
      ],
      consensusMethod: 'synthesize',
      maxRounds: 1,
    }
  }
  
  // Three+ members: full collaborative workflow
  const lead = members.find(m => m.role === 'lead')!
  const specialists = members.filter(m => m.role === 'specialist' || m.role === 'lead')
  const critics = members.filter(m => m.role === 'critic')
  
  const steps: WorkflowStep[] = [
    { 
      stepNumber: 1, 
      participants: specialists.map(m => m.modelId), 
      action: 'generate', 
      dependsOn: [], 
      timeout: 35000 
    },
  ]
  
  if (critics.length > 0) {
    steps.push({
      stepNumber: 2,
      participants: critics.map(m => m.modelId),
      action: 'critique',
      dependsOn: [1],
      timeout: 25000,
    })
    steps.push({
      stepNumber: 3,
      participants: [lead.modelId],
      action: 'refine',
      dependsOn: [2],
      timeout: 30000,
    })
  }
  
  steps.push({
    stepNumber: steps.length + 1,
    participants: [lead.modelId],
    action: 'synthesize',
    dependsOn: [steps.length],
    timeout: 20000,
  })
  
  return {
    type: 'cascade',
    steps,
    consensusMethod: 'synthesize',
    maxRounds: 1,
  }
}

/**
 * Calculate expected performance
 */
function calculateExpectedPerformance(
  members: TeamMember[],
  workflow: SynergyWorkflow
): OptimizedTeam['expectedPerformance'] {
  // Calculate quality boost
  const avgCapability = members.reduce((sum, m) => {
    const caps = m.profile.capabilities
    return sum + (caps.reasoning + caps.analysis + caps.factualAccuracy) / 3
  }, 0) / members.length
  
  const qualityBoost = Math.round((avgCapability - 75) / 75 * 100) + (members.length - 1) * 5
  
  // Estimate latency
  const slowestModel = members.reduce((slowest, m) => {
    const lat = m.profile.performance.latency
    if (lat === 'slow') return 'slow'
    if (lat === 'medium' && slowest !== 'slow') return 'medium'
    return slowest
  }, 'fast' as 'fast' | 'medium' | 'slow')
  
  const latency = workflow.type === 'parallel' ? slowestModel :
    workflow.steps.length > 3 ? 'slow' : slowestModel
  
  // Estimate cost (per million tokens)
  const estimatedCost = members.reduce((sum, m) => 
    sum + m.profile.performance.costPerMillion, 0
  )
  
  // Calculate reliability
  const reliability = members.reduce((min, m) => 
    Math.min(min, m.profile.performance.reliability), 100
  )
  
  return {
    qualityBoost,
    latency,
    estimatedCost,
    reliability,
  }
}

/**
 * Generate rationale for team composition
 */
function generateRationale(
  members: TeamMember[],
  analysis: QueryAnalysis
): string[] {
  const rationale: string[] = []
  
  for (const member of members) {
    const profile = member.profile
    
    switch (member.role) {
      case 'lead':
        rationale.push(
          `${profile.name} leads with ${profile.strengths[0].toLowerCase()}`
        )
        break
      case 'specialist':
        rationale.push(
          `${profile.name} provides specialized ${analysis.domain} expertise (${profile.capabilities.coding}% coding score)`
        )
        break
      case 'critic':
        rationale.push(
          `${profile.name} catches nuances with ${profile.capabilities.analysis}% analysis capability`
        )
        break
      case 'synthesizer':
        rationale.push(
          `${profile.name} synthesizes diverse perspectives`
        )
        break
    }
  }
  
  // Add synergy notes
  for (let i = 0; i < members.length; i++) {
    for (let j = i + 1; j < members.length; j++) {
      const synergy = members[i].profile.synergies.find(
        s => s.partnerId === members[j].profile.id
      )
      if (synergy && synergy.effectiveness >= 85) {
        rationale.push(
          `${members[i].profile.name} + ${members[j].profile.name}: ${synergy.description}`
        )
      }
    }
  }
  
  return rationale
}

/**
 * Get recommended team for a specific scenario
 */
export function getTeamRecommendation(
  scenario: 'code' | 'research' | 'reasoning' | 'creative' | 'balanced' | 'cost-effective'
): Partial<OptimizedTeam> {
  const templates: Record<string, string> = {
    'code': 'code-excellence',
    'research': 'research-depth',
    'reasoning': 'complex-reasoning',
    'creative': 'creative-excellence',
    'balanced': 'balanced-quality',
    'cost-effective': 'cost-effective',
  }
  
  return SYNERGY_TEAM_TEMPLATES[templates[scenario]] || SYNERGY_TEAM_TEMPLATES['balanced-quality']
}

/**
 * Analyze synergies between available models
 */
export function analyzeModelSynergies(
  modelIds: string[]
): {
  bestPairs: { model1: string; model2: string; effectiveness: number; workflow: string }[]
  recommendations: string[]
} {
  const pairs: { model1: string; model2: string; effectiveness: number; workflow: string }[] = []
  const recommendations: string[] = []
  
  for (const id1 of modelIds) {
    const profile1 = getModelProfile(id1)
    if (!profile1) continue
    
    for (const synergy of profile1.synergies) {
      if (modelIds.some(id => id.includes(synergy.partnerId) || synergy.partnerId.includes(id))) {
        pairs.push({
          model1: profile1.name,
          model2: synergy.partnerId,
          effectiveness: synergy.effectiveness,
          workflow: synergy.bestWorkflow,
        })
      }
    }
  }
  
  // Sort by effectiveness
  pairs.sort((a, b) => b.effectiveness - a.effectiveness)
  
  // Generate recommendations
  if (pairs.length > 0) {
    const best = pairs[0]
    recommendations.push(
      `Best pairing: ${best.model1} + ${best.model2} (${best.effectiveness}% effectiveness)`
    )
    recommendations.push(`Recommended workflow: ${best.workflow}`)
  }
  
  // Check for missing synergies
  const hasGPT = modelIds.some(id => id.includes('gpt'))
  const hasClaude = modelIds.some(id => id.includes('claude'))
  const hasDeepSeek = modelIds.some(id => id.includes('deepseek'))
  
  if (!hasGPT && !hasClaude) {
    recommendations.push('Consider adding GPT-4o or Claude for broader coverage')
  }
  
  if (modelIds.some(id => id.includes('code')) && !hasDeepSeek) {
    recommendations.push('Consider DeepSeek for optimal code generation')
  }
  
  return { bestPairs: pairs.slice(0, 5), recommendations }
}

