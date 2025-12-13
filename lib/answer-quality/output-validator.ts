/**
 * Output Validation & Error Recovery System
 * 
 * Validates model outputs and recovers from errors to ensure
 * high-quality, safe, and complete responses.
 */

import type { QueryAnalysis, OutputFormat } from './types'

export interface ValidationResult {
  isValid: boolean
  score: number
  issues: ValidationIssue[]
  suggestions: string[]
  canRecover: boolean
  recoveryStrategies: RecoveryStrategy[]
}

export interface ValidationIssue {
  type: IssueType
  severity: 'critical' | 'major' | 'minor'
  description: string
  location?: string
  suggestedFix?: string
}

export type IssueType = 
  | 'empty-response'
  | 'truncated'
  | 'refusal'
  | 'hallucination-indicator'
  | 'format-violation'
  | 'missing-content'
  | 'unsafe-content'
  | 'repetition'
  | 'incoherent'
  | 'off-topic'
  | 'code-error'
  | 'outdated-info'

export interface RecoveryStrategy {
  type: RecoveryType
  description: string
  priority: number
  estimatedSuccess: number
}

export type RecoveryType = 
  | 'retry-same-model'
  | 'retry-different-model'
  | 'retry-with-clarification'
  | 'partial-response'
  | 'fallback-response'
  | 'escalate-to-human'

// Validation rules
const VALIDATION_RULES = {
  minLength: 50,
  maxRepetitionRatio: 0.3,
  requiredFormatElements: {
    code: ['```'],
    list: [/^\d+\.|^[-•*]/m],
    structured: [/^#{1,3}\s/m],
  },
}

// Patterns indicating potential issues
const ISSUE_PATTERNS = {
  refusal: [
    /I cannot|I can't|I am unable to|I'm not able to/i,
    /against my (guidelines|policies|programming)/i,
    /I don't have (the ability|access|permission)/i,
    /as an AI (language model|assistant), I/i,
  ],
  hallucination: [
    /I don't actually know|I'm not sure if that's accurate/i,
    /I may be making this up|I might be wrong/i,
    /I cannot verify|this information may be outdated/i,
  ],
  truncation: [
    /\.\.\.$/,
    /\[continued\]/i,
    /\[truncated\]/i,
  ],
  repetition: [
    /(\b\w{4,}\b)\s+\1\s+\1/i, // Same word 3+ times
  ],
  incoherent: [
    /^\s*[A-Z][a-z]+\s*$/m, // Single word lines
    /[.!?]\s*[a-z]/g, // Missing capitalization
  ],
}

// Unsafe content patterns
const UNSAFE_PATTERNS = [
  /\b(password|secret|api[_-]?key)\s*[:=]\s*['"]?[\w-]{8,}/gi,
  /\b\d{16}\b/, // Credit card numbers
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email (potential PII)
]

/**
 * Validate a model response
 */
export function validateOutput(
  response: string,
  query: string,
  analysis: QueryAnalysis,
  expectedFormat?: OutputFormat
): ValidationResult {
  const issues: ValidationIssue[] = []
  const suggestions: string[] = []
  
  // Check for empty response
  if (!response || response.trim().length === 0) {
    issues.push({
      type: 'empty-response',
      severity: 'critical',
      description: 'Response is empty',
    })
  }
  
  // Check minimum length
  if (response.length < VALIDATION_RULES.minLength) {
    issues.push({
      type: 'truncated',
      severity: 'major',
      description: `Response is too short (${response.length} chars, minimum ${VALIDATION_RULES.minLength})`,
      suggestedFix: 'Request a more detailed response',
    })
  }
  
  // Check for refusal patterns
  for (const pattern of ISSUE_PATTERNS.refusal) {
    if (pattern.test(response)) {
      issues.push({
        type: 'refusal',
        severity: 'major',
        description: 'Response appears to be a refusal or decline',
        suggestedFix: 'Rephrase the query or try a different model',
      })
      break
    }
  }
  
  // Check for hallucination indicators
  for (const pattern of ISSUE_PATTERNS.hallucination) {
    if (pattern.test(response)) {
      issues.push({
        type: 'hallucination-indicator',
        severity: 'minor',
        description: 'Response contains uncertainty markers that may indicate hallucination',
        suggestedFix: 'Verify facts with additional sources',
      })
      break
    }
  }
  
  // Check for truncation
  for (const pattern of ISSUE_PATTERNS.truncation) {
    if (pattern.test(response)) {
      issues.push({
        type: 'truncated',
        severity: 'major',
        description: 'Response appears to be truncated',
        suggestedFix: 'Request continuation or increase token limit',
      })
      break
    }
  }
  
  // Check for repetition
  const repetitionIssue = checkRepetition(response)
  if (repetitionIssue) {
    issues.push(repetitionIssue)
  }
  
  // Check format compliance
  if (expectedFormat) {
    const formatIssues = checkFormatCompliance(response, expectedFormat)
    issues.push(...formatIssues)
  }
  
  // Check for unsafe content
  const unsafeIssues = checkUnsafeContent(response)
  issues.push(...unsafeIssues)
  
  // Check relevance to query
  const relevanceIssue = checkRelevance(response, query, analysis)
  if (relevanceIssue) {
    issues.push(relevanceIssue)
  }
  
  // Check code validity if applicable
  if (analysis.intent === 'code') {
    const codeIssues = checkCodeValidity(response)
    issues.push(...codeIssues)
  }
  
  // Calculate overall score
  let score = 100
  for (const issue of issues) {
    if (issue.severity === 'critical') score -= 40
    else if (issue.severity === 'major') score -= 20
    else if (issue.severity === 'minor') score -= 5
  }
  score = Math.max(0, score)
  
  // Determine if recovery is possible
  const hasCritical = issues.some(i => i.severity === 'critical')
  const canRecover = score > 20 || !hasCritical
  
  // Generate recovery strategies
  const recoveryStrategies = generateRecoveryStrategies(issues)
  
  // Generate suggestions
  for (const issue of issues) {
    if (issue.suggestedFix) {
      suggestions.push(issue.suggestedFix)
    }
  }
  
  return {
    isValid: score >= 70 && !hasCritical,
    score,
    issues,
    suggestions,
    canRecover,
    recoveryStrategies,
  }
}

/**
 * Check for repetitive content
 */
function checkRepetition(response: string): ValidationIssue | null {
  const words = response.toLowerCase().split(/\s+/)
  const wordCounts: Record<string, number> = {}
  
  for (const word of words) {
    if (word.length > 4) {
      wordCounts[word] = (wordCounts[word] || 0) + 1
    }
  }
  
  // Find words that appear too frequently
  const totalWords = words.length
  for (const [word, count] of Object.entries(wordCounts)) {
    const ratio = count / totalWords
    if (ratio > VALIDATION_RULES.maxRepetitionRatio && count > 5) {
      return {
        type: 'repetition',
        severity: 'major',
        description: `Excessive repetition detected: "${word}" appears ${count} times`,
        suggestedFix: 'Request a revision with more varied language',
      }
    }
  }
  
  // Check for repeated sentences
  const sentences = response.split(/[.!?]+/)
  const sentenceSet = new Set<string>()
  
  for (const sentence of sentences) {
    const normalized = sentence.trim().toLowerCase()
    if (normalized.length > 20) {
      if (sentenceSet.has(normalized)) {
        return {
          type: 'repetition',
          severity: 'major',
          description: 'Duplicate sentences detected',
          suggestedFix: 'Remove repeated content',
        }
      }
      sentenceSet.add(normalized)
    }
  }
  
  return null
}

/**
 * Check format compliance
 */
function checkFormatCompliance(response: string, format: OutputFormat): ValidationIssue[] {
  const issues: ValidationIssue[] = []
  
  if (format.type === 'code') {
    if (!response.includes('```')) {
      issues.push({
        type: 'format-violation',
        severity: 'major',
        description: 'Code format expected but no code blocks found',
        suggestedFix: 'Request code to be formatted in code blocks',
      })
    }
  }
  
  if (format.type === 'list') {
    if (!/^\d+\.|^[-•*]/m.test(response)) {
      issues.push({
        type: 'format-violation',
        severity: 'minor',
        description: 'List format expected but no list markers found',
        suggestedFix: 'Request response as a numbered or bulleted list',
      })
    }
  }
  
  if (format.type === 'structured' && format.sections) {
    const missingSecetions = format.sections.filter(section => 
      !new RegExp(section, 'i').test(response)
    )
    
    if (missingSecetions.length > 0) {
      issues.push({
        type: 'missing-content',
        severity: 'minor',
        description: `Missing expected sections: ${missingSecetions.join(', ')}`,
        suggestedFix: 'Request the missing sections to be included',
      })
    }
  }
  
  if (format.includeSources) {
    if (!/\[\d+\]|source:|reference:|according to/i.test(response)) {
      issues.push({
        type: 'missing-content',
        severity: 'minor',
        description: 'Sources/citations expected but not found',
        suggestedFix: 'Request citations to be added',
      })
    }
  }
  
  return issues
}

/**
 * Check for unsafe content
 */
function checkUnsafeContent(response: string): ValidationIssue[] {
  const issues: ValidationIssue[] = []
  
  for (const pattern of UNSAFE_PATTERNS) {
    const matches = response.match(pattern)
    if (matches) {
      issues.push({
        type: 'unsafe-content',
        severity: 'critical',
        description: 'Potentially sensitive information detected',
        location: matches[0].slice(0, 20) + '...',
        suggestedFix: 'Remove or redact sensitive information',
      })
    }
  }
  
  return issues
}

/**
 * Check relevance to query
 */
function checkRelevance(
  response: string,
  query: string,
  analysis: QueryAnalysis
): ValidationIssue | null {
  // Extract key terms from query
  const queryTerms = new Set(
    query.toLowerCase()
      .split(/\W+/)
      .filter(w => w.length > 3)
  )
  
  // Check how many query terms appear in response
  const responseTerms = new Set(
    response.toLowerCase()
      .split(/\W+/)
      .filter(w => w.length > 3)
  )
  
  let matchCount = 0
  for (const term of queryTerms) {
    if (responseTerms.has(term)) {
      matchCount++
    }
  }
  
  const matchRatio = queryTerms.size > 0 ? matchCount / queryTerms.size : 1
  
  if (matchRatio < 0.3 && queryTerms.size > 3) {
    return {
      type: 'off-topic',
      severity: 'major',
      description: 'Response may not be relevant to the query',
      suggestedFix: 'Ensure the response addresses the specific question asked',
    }
  }
  
  return null
}

/**
 * Check code validity
 */
function checkCodeValidity(response: string): ValidationIssue[] {
  const issues: ValidationIssue[] = []
  
  // Extract code blocks
  const codeBlocks = response.match(/```[\s\S]*?```/g) || []
  
  for (const block of codeBlocks) {
    const code = block.replace(/```\w*\n?/g, '').trim()
    
    // Check for common syntax issues
    const openBraces = (code.match(/\{/g) || []).length
    const closeBraces = (code.match(/\}/g) || []).length
    
    if (openBraces !== closeBraces) {
      issues.push({
        type: 'code-error',
        severity: 'major',
        description: 'Code has mismatched braces',
        suggestedFix: 'Fix the brace mismatch in the code',
      })
    }
    
    const openParens = (code.match(/\(/g) || []).length
    const closeParens = (code.match(/\)/g) || []).length
    
    if (openParens !== closeParens) {
      issues.push({
        type: 'code-error',
        severity: 'major',
        description: 'Code has mismatched parentheses',
        suggestedFix: 'Fix the parenthesis mismatch in the code',
      })
    }
    
    // Check for placeholder comments
    if (/\/\/\s*(TODO|FIXME|XXX|HACK)/i.test(code)) {
      issues.push({
        type: 'code-error',
        severity: 'minor',
        description: 'Code contains TODO/FIXME comments',
        suggestedFix: 'Complete the placeholder code sections',
      })
    }
    
    // Check for incomplete code
    if (/\.\.\.|# more code|\/\/ continue/i.test(code)) {
      issues.push({
        type: 'code-error',
        severity: 'minor',
        description: 'Code appears to be incomplete',
        suggestedFix: 'Request complete implementation',
      })
    }
  }
  
  return issues
}

/**
 * Generate recovery strategies based on issues
 */
function generateRecoveryStrategies(issues: ValidationIssue[]): RecoveryStrategy[] {
  const strategies: RecoveryStrategy[] = []
  
  const issueTypes = new Set(issues.map(i => i.type))
  
  if (issueTypes.has('empty-response') || issueTypes.has('truncated')) {
    strategies.push({
      type: 'retry-same-model',
      description: 'Retry with same model (may be transient issue)',
      priority: 1,
      estimatedSuccess: 0.7,
    })
    strategies.push({
      type: 'retry-different-model',
      description: 'Try a different model',
      priority: 2,
      estimatedSuccess: 0.85,
    })
  }
  
  if (issueTypes.has('refusal')) {
    strategies.push({
      type: 'retry-with-clarification',
      description: 'Rephrase the query to avoid triggering refusal',
      priority: 1,
      estimatedSuccess: 0.6,
    })
    strategies.push({
      type: 'retry-different-model',
      description: 'Try a model with different guidelines',
      priority: 2,
      estimatedSuccess: 0.75,
    })
  }
  
  if (issueTypes.has('off-topic')) {
    strategies.push({
      type: 'retry-with-clarification',
      description: 'Add more specific instructions to stay on topic',
      priority: 1,
      estimatedSuccess: 0.8,
    })
  }
  
  if (issueTypes.has('format-violation') || issueTypes.has('missing-content')) {
    strategies.push({
      type: 'partial-response',
      description: 'Use the response but add missing elements',
      priority: 1,
      estimatedSuccess: 0.9,
    })
  }
  
  if (strategies.length === 0) {
    strategies.push({
      type: 'fallback-response',
      description: 'Use a generic fallback response',
      priority: 3,
      estimatedSuccess: 0.5,
    })
  }
  
  return strategies.sort((a, b) => a.priority - b.priority)
}

/**
 * Attempt to recover from validation issues
 */
export function attemptRecovery(
  response: string,
  validation: ValidationResult,
  strategy: RecoveryStrategy
): { recovered: boolean; result: string } {
  switch (strategy.type) {
    case 'partial-response':
      // Try to salvage usable parts
      const cleaned = cleanResponse(response)
      if (cleaned.length > VALIDATION_RULES.minLength) {
        return { recovered: true, result: cleaned }
      }
      break
      
    case 'fallback-response':
      return {
        recovered: true,
        result: generateFallbackResponse(validation.issues),
      }
  }
  
  return { recovered: false, result: response }
}

/**
 * Clean a response by removing problematic content
 */
function cleanResponse(response: string): string {
  let cleaned = response
  
  // Remove refusal prefixes
  cleaned = cleaned.replace(/^(I cannot|I can't|I am unable to|As an AI)[^.!?]*[.!?]\s*/gi, '')
  
  // Remove truncation indicators
  cleaned = cleaned.replace(/\[continued\]|\[truncated\]|\.\.\.$/gi, '')
  
  // Remove excessive whitespace
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
  
  return cleaned.trim()
}

/**
 * Generate a fallback response
 */
function generateFallbackResponse(issues: ValidationIssue[]): string {
  const issueTypes = issues.map(i => i.type)
  
  if (issueTypes.includes('refusal')) {
    return "I apologize, but I wasn't able to fully address your question. Could you try rephrasing it or providing more context?"
  }
  
  if (issueTypes.includes('empty-response') || issueTypes.includes('truncated')) {
    return "I encountered an issue while generating my response. Please try asking your question again."
  }
  
  return "I apologize, but my response didn't meet quality standards. Please try asking your question again, and I'll do my best to provide a helpful answer."
}

/**
 * Validate multiple responses and select the best one
 */
export function selectBestResponse(
  responses: { response: string; model: string }[],
  query: string,
  analysis: QueryAnalysis
): { response: string; model: string; validation: ValidationResult } | null {
  const validatedResponses = responses.map(r => ({
    ...r,
    validation: validateOutput(r.response, query, analysis),
  }))
  
  // Filter to only valid responses
  const validResponses = validatedResponses.filter(r => r.validation.isValid)
  
  if (validResponses.length === 0) {
    // No valid responses, try to recover from best invalid one
    const best = validatedResponses.sort((a, b) => b.validation.score - a.validation.score)[0]
    if (best && best.validation.canRecover) {
      return best
    }
    return null
  }
  
  // Return highest scoring valid response
  return validResponses.sort((a, b) => b.validation.score - a.validation.score)[0]
}

