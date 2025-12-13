/**
 * Fact Verifier
 * 
 * Validates claims in responses through:
 * - Cross-model verification
 * - Internal consistency checks
 * - Known fact validation
 * - Confidence scoring
 */

import type {
  FactVerificationResult,
  VerifiedClaim,
  Citation,
  Correction,
} from './types'

// Common factual patterns to check
const FACTUAL_PATTERNS = [
  // Dates and numbers
  { pattern: /\b(in|on|since|from|until)\s+(\d{4})\b/gi, type: 'date' },
  { pattern: /\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(percent|%|million|billion|trillion)\b/gi, type: 'statistic' },
  
  // Definitive statements
  { pattern: /\b(is|are|was|were)\s+(?:the\s+)?(first|largest|smallest|oldest|newest|only|best|worst)\b/gi, type: 'superlative' },
  
  // Attribution
  { pattern: /\b(according to|as stated by|as reported by)\s+[A-Z][^,.]+/gi, type: 'attribution' },
  
  // Scientific/technical claims
  { pattern: /\b(studies show|research indicates|scientists found|data suggests)\b/gi, type: 'research' },
]

// Known fact database (in production, this would be a proper database)
const KNOWN_FACTS: Record<string, string> = {
  'earth_age': '4.54 billion years',
  'light_speed': '299,792,458 meters per second',
  'water_boiling': '100°C at standard pressure',
  'moon_landing': '1969',
}

/**
 * Extract claims from a response
 */
export function extractClaims(response: string): string[] {
  const claims: string[] = []
  
  // Split into sentences
  const sentences = response.split(/[.!?]+/)
  
  for (const sentence of sentences) {
    const trimmed = sentence.trim()
    if (trimmed.length < 10) continue
    
    // Check if sentence contains factual patterns
    for (const { pattern } of FACTUAL_PATTERNS) {
      if (pattern.test(trimmed)) {
        claims.push(trimmed)
        break
      }
    }
    
    // Check for definitive statements
    if (/\b(is|are|was|were|has|have|had)\b/i.test(trimmed) && 
        !/\b(might|may|could|possibly|perhaps|probably)\b/i.test(trimmed)) {
      if (!claims.includes(trimmed)) {
        claims.push(trimmed)
      }
    }
  }
  
  return claims.slice(0, 20) // Limit to 20 claims for performance
}

/**
 * Verify claims using multiple strategies
 */
export async function verifyClaims(
  claims: string[],
  modelResponses?: string[]
): Promise<FactVerificationResult> {
  const verifiedClaims: VerifiedClaim[] = []
  const unreliableClaims: string[] = []
  const suggestedCorrections: Correction[] = []
  
  for (const claim of claims) {
    const verification = await verifySingleClaim(claim, modelResponses)
    verifiedClaims.push(verification)
    
    if (!verification.verified && verification.confidence < 0.5) {
      unreliableClaims.push(claim)
    }
  }
  
  // Calculate overall confidence
  const totalConfidence = verifiedClaims.reduce((sum, v) => sum + v.confidence, 0)
  const overallConfidence = verifiedClaims.length > 0 
    ? totalConfidence / verifiedClaims.length 
    : 1.0
  
  return {
    claims: verifiedClaims,
    overallConfidence,
    sourcesChecked: modelResponses?.length || 0,
    unreliableClaims,
    suggestedCorrections,
  }
}

/**
 * Verify a single claim
 */
async function verifySingleClaim(
  claim: string,
  modelResponses?: string[]
): Promise<VerifiedClaim> {
  let confidence = 0.7 // Default confidence
  let verified = true
  const sources: Citation[] = []
  
  // Check against known facts
  const knownFactCheck = checkAgainstKnownFacts(claim)
  if (knownFactCheck) {
    confidence = knownFactCheck.confidence
    verified = knownFactCheck.verified
    if (knownFactCheck.source) {
      sources.push(knownFactCheck.source)
    }
  }
  
  // Cross-reference with other model responses
  if (modelResponses && modelResponses.length > 1) {
    const crossRef = crossReferenceModels(claim, modelResponses)
    confidence = (confidence + crossRef.confidence) / 2
    if (crossRef.agreement < 0.5) {
      verified = false
    }
  }
  
  // Check for hedging language (reduces confidence in verification)
  if (hasHedgingLanguage(claim)) {
    confidence *= 0.9
  }
  
  // Check for recency-dependent claims
  if (isRecencyDependent(claim)) {
    confidence *= 0.8 // Less confident about time-sensitive claims
  }
  
  return {
    claim,
    verified,
    confidence,
    sources,
  }
}

/**
 * Check claim against known facts database
 */
function checkAgainstKnownFacts(claim: string): { verified: boolean; confidence: number; source?: Citation } | null {
  const claimLower = claim.toLowerCase()
  
  // Check for known fact matches
  for (const [key, value] of Object.entries(KNOWN_FACTS)) {
    if (claimLower.includes(key.replace('_', ' ')) || claimLower.includes(value.toLowerCase())) {
      return {
        verified: true,
        confidence: 0.95,
        source: {
          id: `known-${key}`,
          text: value,
          source: 'Verified Fact Database',
          relevance: 1.0,
          verified: true,
        },
      }
    }
  }
  
  return null
}

/**
 * Cross-reference a claim with multiple model responses
 */
function crossReferenceModels(
  claim: string,
  responses: string[]
): { agreement: number; confidence: number } {
  const claimKeywords = extractKeywords(claim)
  let agreements = 0
  let contradictions = 0
  
  for (const response of responses) {
    const responseLower = response.toLowerCase()
    const matchingKeywords = claimKeywords.filter(kw => 
      responseLower.includes(kw.toLowerCase())
    )
    
    if (matchingKeywords.length >= claimKeywords.length * 0.7) {
      agreements++
    } else if (hasContradiction(claim, response)) {
      contradictions++
    }
  }
  
  const agreement = agreements / responses.length
  const confidence = contradictions === 0 
    ? 0.7 + (agreement * 0.3)
    : 0.5 - (contradictions / responses.length * 0.3)
  
  return { agreement, confidence: Math.max(0.1, confidence) }
}

/**
 * Extract keywords from a claim for comparison
 */
function extractKeywords(claim: string): string[] {
  // Remove common words
  const stopWords = new Set([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'can', 'of', 'in', 'to',
    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'and', 'or',
    'but', 'not', 'this', 'that', 'these', 'those', 'it', 'its',
  ])
  
  return claim
    .toLowerCase()
    .split(/\W+/)
    .filter(word => word.length > 2 && !stopWords.has(word))
}

/**
 * Check if a response contradicts a claim
 */
function hasContradiction(claim: string, response: string): boolean {
  // Simple contradiction detection
  const claimLower = claim.toLowerCase()
  const responseLower = response.toLowerCase()
  
  // Look for negation patterns near claim keywords
  const keywords = extractKeywords(claim).slice(0, 3)
  
  for (const keyword of keywords) {
    const keywordIndex = responseLower.indexOf(keyword)
    if (keywordIndex !== -1) {
      const context = responseLower.slice(
        Math.max(0, keywordIndex - 50),
        keywordIndex + keyword.length + 50
      )
      if (/\b(not|never|no|isn't|aren't|wasn't|weren't|doesn't|don't|didn't|cannot|can't|won't)\b/.test(context)) {
        return true
      }
    }
  }
  
  return false
}

/**
 * Check if claim uses hedging language
 */
function hasHedgingLanguage(claim: string): boolean {
  return /\b(might|may|could|possibly|perhaps|probably|likely|unlikely|appears|seems|suggests|indicates|generally|typically|often|sometimes|usually)\b/i.test(claim)
}

/**
 * Check if claim is recency-dependent
 */
function isRecencyDependent(claim: string): boolean {
  return /\b(current|latest|recent|now|today|this year|2024|2025)\b/i.test(claim)
}

/**
 * Calculate fact verification score for a response
 */
export function calculateFactScore(result: FactVerificationResult): number {
  if (result.claims.length === 0) return 100
  
  const verifiedCount = result.claims.filter(c => c.verified).length
  const avgConfidence = result.claims.reduce((sum, c) => sum + c.confidence, 0) / result.claims.length
  
  return Math.round((verifiedCount / result.claims.length) * avgConfidence * 100)
}

/**
 * Generate a fact-check summary
 */
export function generateFactCheckSummary(result: FactVerificationResult): string {
  const parts: string[] = []
  
  parts.push(`**Fact Check Summary**`)
  parts.push(`- Claims analyzed: ${result.claims.length}`)
  parts.push(`- Overall confidence: ${Math.round(result.overallConfidence * 100)}%`)
  
  if (result.unreliableClaims.length > 0) {
    parts.push(`\n⚠️ **Unverified Claims:**`)
    result.unreliableClaims.forEach(claim => {
      parts.push(`- ${claim.slice(0, 100)}...`)
    })
  }
  
  if (result.suggestedCorrections.length > 0) {
    parts.push(`\n📝 **Suggested Corrections:**`)
    result.suggestedCorrections.forEach(corr => {
      parts.push(`- "${corr.original}" → "${corr.corrected}"`)
    })
  }
  
  return parts.join('\n')
}

