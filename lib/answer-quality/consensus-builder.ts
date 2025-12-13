/**
 * Consensus Builder
 * 
 * Synthesizes multiple model outputs into a single high-quality response:
 * - Identifies agreements and conflicts
 * - Weights contributions by model strengths
 * - Resolves contradictions intelligently
 * - Extracts the best parts from each response
 */

import type {
  ConsensusResult,
  ModelContribution,
  Conflict,
  QueryAnalysis,
} from './types'

// Model capabilities for weighting
const MODEL_WEIGHTS: Record<string, { base: number; domains: Record<string, number> }> = {
  'gpt-4o': {
    base: 0.9,
    domains: { 'general': 1.0, 'creative': 0.95, 'code': 0.9, 'analysis': 0.85 },
  },
  'claude-sonnet-4': {
    base: 0.9,
    domains: { 'analysis': 1.0, 'research': 0.95, 'safety': 1.0, 'general': 0.9 },
  },
  'deepseek-chat': {
    base: 0.85,
    domains: { 'code': 1.0, 'math': 0.95, 'technical': 0.9, 'general': 0.75 },
  },
  'gemini-1.5-pro': {
    base: 0.85,
    domains: { 'multimodal': 1.0, 'research': 0.9, 'general': 0.85 },
  },
}

export interface ModelResponse {
  model: string
  content: string
  role?: string
  latency?: number
}

/**
 * Build consensus from multiple model responses
 */
export function buildConsensus(
  responses: ModelResponse[],
  query: string,
  analysis?: QueryAnalysis
): ConsensusResult {
  if (responses.length === 0) {
    return {
      finalAnswer: '',
      agreement: 0,
      contributions: [],
      conflicts: [],
      synthesisMethod: 'none',
    }
  }
  
  if (responses.length === 1) {
    return {
      finalAnswer: responses[0].content,
      agreement: 1.0,
      contributions: [{
        model: responses[0].model,
        response: responses[0].content,
        role: 'primary',
        weight: 1.0,
        strengths: [],
        weaknesses: [],
      }],
      conflicts: [],
      synthesisMethod: 'single',
    }
  }
  
  // Analyze each response
  const contributions = analyzeContributions(responses, analysis)
  
  // Identify conflicts
  const conflicts = identifyConflicts(responses)
  
  // Calculate agreement score
  const agreement = calculateAgreement(responses)
  
  // Choose synthesis method based on agreement
  const synthesisMethod = chooseSynthesisMethod(agreement, conflicts.length)
  
  // Build the final answer
  const finalAnswer = synthesizeResponses(contributions, conflicts, synthesisMethod, analysis)
  
  return {
    finalAnswer,
    agreement,
    contributions,
    conflicts,
    synthesisMethod,
  }
}

/**
 * Analyze contributions from each model
 */
function analyzeContributions(
  responses: ModelResponse[],
  analysis?: QueryAnalysis
): ModelContribution[] {
  const domain = analysis?.domain || 'general'
  
  return responses.map(response => {
    const modelWeights = MODEL_WEIGHTS[response.model] || { base: 0.7, domains: {} }
    const domainWeight = modelWeights.domains[domain] || modelWeights.base
    
    const strengths = identifyStrengths(response.content)
    const weaknesses = identifyWeaknesses(response.content)
    
    return {
      model: response.model,
      response: response.content,
      role: response.role || determineRole(response.model, domain),
      weight: domainWeight * (1 - weaknesses.length * 0.1),
      strengths,
      weaknesses,
    }
  })
}

/**
 * Identify strengths in a response
 */
function identifyStrengths(content: string): string[] {
  const strengths: string[] = []
  
  // Well-structured
  if (/^#+\s/m.test(content) || /^\d+\.\s/m.test(content)) {
    strengths.push('Well-structured with clear sections')
  }
  
  // Includes examples
  if (/for example|e\.g\.|such as|like this/i.test(content)) {
    strengths.push('Provides examples')
  }
  
  // Detailed
  if (content.length > 500) {
    strengths.push('Comprehensive coverage')
  }
  
  // Includes code
  if (/```[\s\S]*```/.test(content)) {
    strengths.push('Includes code examples')
  }
  
  // Considers alternatives
  if (/however|alternatively|another approach|on the other hand/i.test(content)) {
    strengths.push('Considers multiple perspectives')
  }
  
  return strengths
}

/**
 * Identify weaknesses in a response
 */
function identifyWeaknesses(content: string): string[] {
  const weaknesses: string[] = []
  
  // Too short
  if (content.length < 100) {
    weaknesses.push('Too brief')
  }
  
  // Uncertainty without substance
  if (/I'm not sure|I don't know|I cannot|I am unable/i.test(content)) {
    weaknesses.push('Expresses uncertainty')
  }
  
  // Refusal to answer
  if (/I cannot help|I am not able|against my guidelines/i.test(content)) {
    weaknesses.push('Refusal to answer')
  }
  
  // Repetitive
  const words = content.toLowerCase().split(/\s+/)
  const uniqueRatio = new Set(words).size / words.length
  if (uniqueRatio < 0.4) {
    weaknesses.push('Repetitive content')
  }
  
  return weaknesses
}

/**
 * Determine the role of a model based on its strengths
 */
function determineRole(model: string, domain: string): string {
  const roles: Record<string, Record<string, string>> = {
    'gpt-4o': { default: 'primary', code: 'technical', creative: 'lead' },
    'claude-sonnet-4': { default: 'critic', analysis: 'lead', research: 'primary' },
    'deepseek-chat': { default: 'technical', code: 'lead', math: 'lead' },
    'gemini-1.5-pro': { default: 'verifier', research: 'primary' },
  }
  
  return roles[model]?.[domain] || roles[model]?.default || 'contributor'
}

/**
 * Identify conflicts between responses
 */
function identifyConflicts(responses: ModelResponse[]): Conflict[] {
  const conflicts: Conflict[] = []
  
  // Compare pairs of responses
  for (let i = 0; i < responses.length; i++) {
    for (let j = i + 1; j < responses.length; j++) {
      const conflictsFound = findConflicts(
        responses[i].content,
        responses[j].content,
        responses[i].model,
        responses[j].model
      )
      conflicts.push(...conflictsFound)
    }
  }
  
  return conflicts
}

/**
 * Find conflicts between two responses
 */
function findConflicts(
  content1: string,
  content2: string,
  model1: string,
  model2: string
): Conflict[] {
  const conflicts: Conflict[] = []
  
  // Extract key statements from each
  const statements1 = extractKeyStatements(content1)
  const statements2 = extractKeyStatements(content2)
  
  // Look for contradictions
  for (const s1 of statements1) {
    for (const s2 of statements2) {
      if (isContradiction(s1, s2)) {
        conflicts.push({
          topic: extractTopic(s1, s2),
          positions: [
            { model: model1, position: s1 },
            { model: model2, position: s2 },
          ],
          resolution: resolveConflict(s1, s2, model1, model2),
          confidence: 0.7,
        })
      }
    }
  }
  
  return conflicts
}

/**
 * Extract key statements from content
 */
function extractKeyStatements(content: string): string[] {
  const sentences = content.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 20)
  
  // Focus on definitive statements
  return sentences.filter(s => 
    /\b(is|are|should|must|always|never|definitely|certainly)\b/i.test(s) &&
    !/\b(might|may|could|possibly|perhaps|probably)\b/i.test(s)
  )
}

/**
 * Check if two statements contradict each other
 */
function isContradiction(s1: string, s2: string): boolean {
  const s1Lower = s1.toLowerCase()
  const s2Lower = s2.toLowerCase()
  
  // Simple negation check
  const words1 = new Set(s1Lower.split(/\W+/).filter(w => w.length > 3))
  const words2 = new Set(s2Lower.split(/\W+/).filter(w => w.length > 3))
  
  // Check for shared topic
  const sharedWords = [...words1].filter(w => words2.has(w))
  if (sharedWords.length < 2) return false
  
  // Check for negation
  const hasNegation1 = /\b(not|never|no|isn't|aren't|don't|doesn't|won't|can't|cannot)\b/.test(s1Lower)
  const hasNegation2 = /\b(not|never|no|isn't|aren't|don't|doesn't|won't|can't|cannot)\b/.test(s2Lower)
  
  // Different negation status suggests contradiction
  if (hasNegation1 !== hasNegation2) return true
  
  // Check for opposing adjectives
  const opposites = [
    ['good', 'bad'], ['better', 'worse'], ['best', 'worst'],
    ['increase', 'decrease'], ['more', 'less'], ['fast', 'slow'],
    ['easy', 'difficult'], ['simple', 'complex'], ['high', 'low'],
  ]
  
  for (const [a, b] of opposites) {
    if ((s1Lower.includes(a) && s2Lower.includes(b)) ||
        (s1Lower.includes(b) && s2Lower.includes(a))) {
      return true
    }
  }
  
  return false
}

/**
 * Extract the topic from contradicting statements
 */
function extractTopic(s1: string, s2: string): string {
  const words1 = s1.split(/\W+/).filter(w => w.length > 3)
  const words2 = s2.split(/\W+/).filter(w => w.length > 3)
  
  const shared = words1.filter(w => 
    words2.some(w2 => w2.toLowerCase() === w.toLowerCase())
  )
  
  return shared.slice(0, 3).join(' ') || 'Unidentified topic'
}

/**
 * Resolve a conflict by choosing the more reliable position
 */
function resolveConflict(s1: string, s2: string, model1: string, model2: string): string {
  const weight1 = MODEL_WEIGHTS[model1]?.base || 0.7
  const weight2 = MODEL_WEIGHTS[model2]?.base || 0.7
  
  // Prefer the more detailed statement
  if (s1.length > s2.length * 1.5) {
    return s1
  }
  if (s2.length > s1.length * 1.5) {
    return s2
  }
  
  // Prefer higher-weighted model
  return weight1 >= weight2 ? s1 : s2
}

/**
 * Calculate agreement between responses
 */
function calculateAgreement(responses: ModelResponse[]): number {
  if (responses.length < 2) return 1.0
  
  let totalSimilarity = 0
  let comparisons = 0
  
  for (let i = 0; i < responses.length; i++) {
    for (let j = i + 1; j < responses.length; j++) {
      totalSimilarity += calculateSimilarity(responses[i].content, responses[j].content)
      comparisons++
    }
  }
  
  return comparisons > 0 ? totalSimilarity / comparisons : 1.0
}

/**
 * Calculate similarity between two texts
 */
function calculateSimilarity(text1: string, text2: string): number {
  const words1 = new Set(text1.toLowerCase().split(/\W+/).filter(w => w.length > 3))
  const words2 = new Set(text2.toLowerCase().split(/\W+/).filter(w => w.length > 3))
  
  const intersection = [...words1].filter(w => words2.has(w)).length
  const union = new Set([...words1, ...words2]).size
  
  return union > 0 ? intersection / union : 0
}

/**
 * Choose synthesis method based on agreement level
 */
function chooseSynthesisMethod(agreement: number, conflictCount: number): string {
  if (agreement > 0.8 && conflictCount === 0) {
    return 'best-of' // Pick the best response
  } else if (agreement > 0.6) {
    return 'merge' // Merge complementary parts
  } else if (conflictCount > 2) {
    return 'arbitrate' // Need to resolve many conflicts
  } else {
    return 'synthesize' // Create new response from all inputs
  }
}

/**
 * Synthesize final response from contributions
 */
function synthesizeResponses(
  contributions: ModelContribution[],
  conflicts: Conflict[],
  method: string,
  analysis?: QueryAnalysis
): string {
  // Sort contributions by weight
  const sorted = [...contributions].sort((a, b) => b.weight - a.weight)
  
  switch (method) {
    case 'best-of':
      // Return the highest-weighted response
      return sorted[0]?.response || ''
    
    case 'merge':
      // Merge complementary sections
      return mergeResponses(sorted)
    
    case 'arbitrate':
      // Use conflict resolutions
      return arbitrateResponses(sorted, conflicts)
    
    case 'synthesize':
    default:
      // Full synthesis
      return fullSynthesis(sorted, conflicts, analysis)
  }
}

/**
 * Merge complementary parts from different responses
 */
function mergeResponses(contributions: ModelContribution[]): string {
  const primary = contributions[0]
  const sections: string[] = [primary.response]
  
  // Add unique sections from other responses
  for (let i = 1; i < contributions.length; i++) {
    const contrib = contributions[i]
    
    // Find sections not covered in primary
    const primaryTopics = new Set(extractKeyStatements(primary.response).map(s => extractTopic(s, s)))
    const contribStatements = extractKeyStatements(contrib.response)
    
    for (const statement of contribStatements) {
      const topic = extractTopic(statement, statement)
      if (!primaryTopics.has(topic) && statement.length > 50) {
        sections.push(`\n\n**Additional insight from ${contrib.model}:**\n${statement}`)
      }
    }
  }
  
  return sections.join('')
}

/**
 * Arbitrate between conflicting responses
 */
function arbitrateResponses(
  contributions: ModelContribution[],
  conflicts: Conflict[]
): string {
  let result = contributions[0].response
  
  // Replace conflicting statements with resolutions
  for (const conflict of conflicts) {
    for (const position of conflict.positions) {
      if (result.includes(position.position)) {
        result = result.replace(position.position, conflict.resolution)
      }
    }
  }
  
  return result
}

/**
 * Full synthesis creating new response from all inputs
 */
function fullSynthesis(
  contributions: ModelContribution[],
  conflicts: Conflict[],
  analysis?: QueryAnalysis
): string {
  const parts: string[] = []
  
  // Start with intro from best response
  const bestResponse = contributions[0].response
  const firstParagraph = bestResponse.split('\n\n')[0]
  parts.push(firstParagraph)
  
  // Add unique insights from each contribution
  const coveredTopics = new Set<string>()
  
  for (const contrib of contributions) {
    const statements = extractKeyStatements(contrib.response)
    for (const statement of statements) {
      const topic = extractTopic(statement, statement)
      if (!coveredTopics.has(topic)) {
        coveredTopics.add(topic)
        parts.push(`\n\n${statement}`)
      }
    }
  }
  
  // Add conflict note if needed
  if (conflicts.length > 0) {
    parts.push(`\n\n**Note:** There were ${conflicts.length} points where sources disagreed. The information above represents the most reliable consensus.`)
  }
  
  return parts.join('')
}

/**
 * Get consensus confidence score
 */
export function getConsensusConfidence(result: ConsensusResult): number {
  const baseConfidence = result.agreement * 100
  const conflictPenalty = result.conflicts.length * 5
  
  return Math.max(0, Math.min(100, baseConfidence - conflictPenalty))
}

