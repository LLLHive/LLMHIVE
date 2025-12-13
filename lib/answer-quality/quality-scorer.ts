/**
 * Quality Scorer
 * 
 * Evaluates response quality across multiple dimensions and tracks
 * improvements over time to ensure continuous quality enhancement.
 */

import type {
  QualityDimensions,
  QualityReport,
  QueryAnalysis,
} from './types'

// Quality dimension weights (must sum to 1.0)
const DIMENSION_WEIGHTS: Record<keyof QualityDimensions, number> = {
  accuracy: 0.20,
  completeness: 0.15,
  clarity: 0.15,
  relevance: 0.15,
  structure: 0.10,
  actionability: 0.10,
  sources: 0.05,
  depth: 0.10,
}

// Baseline scores for comparison (average single-model performance)
const BASELINE_SCORES: QualityDimensions = {
  accuracy: 75,
  completeness: 70,
  clarity: 72,
  relevance: 78,
  structure: 65,
  actionability: 60,
  sources: 40,
  depth: 68,
}

/**
 * Calculate overall quality score from dimensions
 */
export function calculateOverallScore(dimensions: QualityDimensions): number {
  let score = 0
  
  for (const [key, weight] of Object.entries(DIMENSION_WEIGHTS)) {
    const dimension = key as keyof QualityDimensions
    score += dimensions[dimension] * weight
  }
  
  return Math.round(score)
}

/**
 * Score a response on all quality dimensions
 */
export function scoreResponse(
  response: string,
  analysis: QueryAnalysis,
  modelCount: number = 1
): QualityDimensions {
  return {
    accuracy: scoreAccuracy(response, analysis),
    completeness: scoreCompleteness(response, analysis),
    clarity: scoreClarity(response),
    relevance: scoreRelevance(response, analysis),
    structure: scoreStructure(response),
    actionability: scoreActionability(response, analysis),
    sources: scoreSources(response),
    depth: scoreDepth(response, analysis),
  }
}

/**
 * Score accuracy - factual correctness indicators
 */
function scoreAccuracy(response: string, analysis: QueryAnalysis): number {
  let score = 70 // Base score
  
  // Positive indicators
  if (/according to|research shows|studies indicate/i.test(response)) score += 10
  if (/\[\d+\]|\[citation\]/i.test(response)) score += 8
  if (!/I think|I believe|probably|maybe/i.test(response)) score += 5
  
  // Negative indicators
  if (/I'm not sure|I don't know exactly/i.test(response)) score -= 15
  if (/hallucin/i.test(response)) score -= 20 // Self-awareness of limitations
  
  // Domain-specific accuracy indicators
  if (analysis.domain === 'technology' || analysis.domain === 'science') {
    if (/```[\s\S]*```/.test(response)) score += 5 // Code examples for tech
    if (/\d+(\.\d+)?%|\d+ percent/i.test(response)) score += 3 // Specific numbers
  }
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score completeness - how thoroughly the query is addressed
 */
function scoreCompleteness(response: string, analysis: QueryAnalysis): number {
  let score = 60 // Base score
  
  // Length-based scoring
  const wordCount = response.split(/\s+/).length
  if (wordCount > 300) score += 15
  else if (wordCount > 150) score += 10
  else if (wordCount > 75) score += 5
  else if (wordCount < 30) score -= 20
  
  // Multi-part response
  const sectionCount = (response.match(/^#{1,3}\s/gm) || []).length
  score += Math.min(15, sectionCount * 3)
  
  // Addresses key entities from query
  for (const entity of analysis.keyEntities.slice(0, 5)) {
    if (response.toLowerCase().includes(entity.name.toLowerCase())) {
      score += 3
    }
  }
  
  // Has conclusion/summary
  if (/in summary|in conclusion|to summarize|overall/i.test(response)) score += 5
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score clarity - readability and understandability
 */
function scoreClarity(response: string): number {
  let score = 75 // Base score
  
  // Sentence length analysis
  const sentences = response.split(/[.!?]+/).filter(s => s.trim().length > 0)
  const avgWordsPerSentence = sentences.reduce((sum, s) => 
    sum + s.split(/\s+/).length, 0
  ) / sentences.length
  
  if (avgWordsPerSentence < 15) score += 10
  else if (avgWordsPerSentence < 20) score += 5
  else if (avgWordsPerSentence > 30) score -= 10
  else if (avgWordsPerSentence > 40) score -= 20
  
  // Formatting aids readability
  if (/^[-•*]\s/m.test(response)) score += 5 // Bullet points
  if (/^\d+\.\s/m.test(response)) score += 5 // Numbered lists
  if (/\*\*[^*]+\*\*/m.test(response)) score += 3 // Bold text
  
  // Transition words improve flow
  if (/\b(first|second|third|finally|however|therefore|additionally)\b/i.test(response)) {
    score += 5
  }
  
  // Paragraph breaks
  const paragraphs = response.split(/\n\n+/).length
  if (paragraphs >= 3 && paragraphs <= 10) score += 5
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score relevance - how on-topic the response is
 */
function scoreRelevance(response: string, analysis: QueryAnalysis): number {
  let score = 70 // Base score
  
  // Check if key entities from query appear in response
  const responseWords = new Set(response.toLowerCase().split(/\W+/))
  const queryKeywords = analysis.keyEntities.map(e => e.name.toLowerCase())
  
  let keywordMatches = 0
  for (const keyword of queryKeywords) {
    if (responseWords.has(keyword) || response.toLowerCase().includes(keyword)) {
      keywordMatches++
    }
  }
  
  if (queryKeywords.length > 0) {
    const matchRatio = keywordMatches / queryKeywords.length
    score += matchRatio * 20
  }
  
  // Intent alignment
  if (analysis.intent === 'procedural' && /step|first|then|next/i.test(response)) score += 10
  if (analysis.intent === 'comparative' && /vs|versus|compared|difference/i.test(response)) score += 10
  if (analysis.intent === 'code' && /```/m.test(response)) score += 15
  if (analysis.intent === 'factual' && /is|are|was|were/i.test(response)) score += 5
  
  // Deductions for tangential content
  if (response.length > 1000) {
    const tangentIndicators = (response.match(/\b(by the way|incidentally|as an aside|off topic)\b/gi) || []).length
    score -= tangentIndicators * 5
  }
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score structure - organization and formatting
 */
function scoreStructure(response: string): number {
  let score = 50 // Base score
  
  // Headers
  const h1Count = (response.match(/^#\s/gm) || []).length
  const h2Count = (response.match(/^##\s/gm) || []).length
  const h3Count = (response.match(/^###\s/gm) || []).length
  
  if (h2Count >= 2) score += 15
  if (h3Count >= 1) score += 5
  if (h1Count === 1) score += 5
  
  // Lists
  const bulletCount = (response.match(/^[-•*]\s/gm) || []).length
  const numberedCount = (response.match(/^\d+\.\s/gm) || []).length
  
  if (bulletCount >= 3) score += 10
  if (numberedCount >= 3) score += 10
  
  // Code blocks
  if (/```[\s\S]+```/m.test(response)) score += 10
  
  // Logical flow indicators
  if (/\b(first|second|third)\b[\s\S]*\b(next|then|finally)\b/i.test(response)) score += 5
  
  // Not a wall of text
  const paragraphs = response.split(/\n\n+/)
  if (paragraphs.length >= 3) score += 5
  if (paragraphs.every(p => p.length < 500)) score += 5
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score actionability - how useful/actionable the response is
 */
function scoreActionability(response: string, analysis: QueryAnalysis): number {
  let score = 50 // Base score
  
  // For non-actionable intents, base is higher
  if (['factual', 'opinion', 'conversational'].includes(analysis.intent)) {
    score = 70
  }
  
  // Action verbs
  const actionVerbs = (response.match(/\b(do|create|build|implement|try|use|run|execute|install|configure|set up|add|remove)\b/gi) || []).length
  score += Math.min(20, actionVerbs * 2)
  
  // Imperative sentences (commands)
  const imperatives = (response.match(/^[A-Z][a-z]+\s/gm) || []).length
  score += Math.min(10, imperatives)
  
  // Next steps section
  if (/next steps?|action items?|to do/i.test(response)) score += 15
  
  // Code that can be run
  if (/```[\s\S]+```/m.test(response) && analysis.intent === 'code') score += 15
  
  // Specific commands
  if (/`[^`]+`/.test(response)) score += 5
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score sources - citation and reference quality
 */
function scoreSources(response: string): number {
  let score = 30 // Base score (sources are optional)
  
  // Citation patterns
  const citationCount = (response.match(/\[\d+\]|\[source\]|\[citation\]/gi) || []).length
  score += Math.min(30, citationCount * 10)
  
  // Attribution
  if (/according to|as stated by|as reported/i.test(response)) score += 15
  
  // URLs or links
  const urlCount = (response.match(/https?:\/\/\S+/g) || []).length
  score += Math.min(20, urlCount * 5)
  
  // "Sources" or "References" section
  if (/^(sources?|references?|citations?|bibliography):?\s*$/im.test(response)) score += 10
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Score depth - level of detail and insight
 */
function scoreDepth(response: string, analysis: QueryAnalysis): number {
  let score = 50 // Base score
  
  // Word count as depth indicator
  const wordCount = response.split(/\s+/).length
  if (wordCount > 500) score += 20
  else if (wordCount > 300) score += 15
  else if (wordCount > 150) score += 10
  
  // Technical terms (indicates expertise)
  const technicalPatterns = /\b(algorithm|implementation|architecture|methodology|framework|protocol|optimization|configuration)\b/gi
  const techTerms = (response.match(technicalPatterns) || []).length
  score += Math.min(15, techTerms * 3)
  
  // Cause-effect reasoning
  if (/because|therefore|consequently|as a result|due to|leads to/i.test(response)) score += 10
  
  // Multiple perspectives
  if (/however|on the other hand|alternatively|another perspective/i.test(response)) score += 10
  
  // Examples
  if (/for example|for instance|such as|e\.g\./i.test(response)) score += 5
  
  // Complexity matches query complexity
  if (analysis.complexity === 'expert' && wordCount > 400) score += 10
  if (analysis.complexity === 'simple' && wordCount < 300) score += 5
  
  return Math.max(0, Math.min(100, score))
}

/**
 * Generate a comprehensive quality report
 */
export function generateQualityReport(
  response: string,
  analysis: QueryAnalysis,
  modelCount: number = 1
): QualityReport {
  const dimensions = scoreResponse(response, analysis, modelCount)
  const overallScore = calculateOverallScore(dimensions)
  
  // Compare to baseline
  const baselineScore = calculateOverallScore(BASELINE_SCORES)
  const comparisonToBaseline = ((overallScore - baselineScore) / baselineScore) * 100
  
  // Identify strengths and weaknesses
  const strengths: string[] = []
  const weaknesses: string[] = []
  const suggestions: string[] = []
  
  for (const [key, value] of Object.entries(dimensions)) {
    const dimension = key as keyof QualityDimensions
    const baseline = BASELINE_SCORES[dimension]
    
    if (value >= baseline + 15) {
      strengths.push(formatDimensionName(dimension))
    } else if (value < baseline - 10) {
      weaknesses.push(formatDimensionName(dimension))
      suggestions.push(getSuggestionForDimension(dimension))
    }
  }
  
  return {
    overallScore,
    dimensions,
    strengths,
    weaknesses,
    suggestions,
    comparisonToBaseline: Math.round(comparisonToBaseline),
    historicalTrend: [], // Would be populated from storage
  }
}

/**
 * Format dimension name for display
 */
function formatDimensionName(dimension: keyof QualityDimensions): string {
  const names: Record<keyof QualityDimensions, string> = {
    accuracy: 'Factual Accuracy',
    completeness: 'Completeness',
    clarity: 'Clarity',
    relevance: 'Relevance',
    structure: 'Structure',
    actionability: 'Actionability',
    sources: 'Source Quality',
    depth: 'Depth of Analysis',
  }
  return names[dimension]
}

/**
 * Get improvement suggestion for a dimension
 */
function getSuggestionForDimension(dimension: keyof QualityDimensions): string {
  const suggestions: Record<keyof QualityDimensions, string> = {
    accuracy: 'Add more citations and factual verification',
    completeness: 'Address all aspects of the query more thoroughly',
    clarity: 'Use shorter sentences and more formatting',
    relevance: 'Stay more focused on the specific question asked',
    structure: 'Add headers, lists, and better organization',
    actionability: 'Include more specific, actionable recommendations',
    sources: 'Add references and citations to support claims',
    depth: 'Provide more detailed analysis and examples',
  }
  return suggestions[dimension]
}

/**
 * Quick quality check - fast evaluation for real-time use
 */
export function quickQualityCheck(response: string): { 
  score: number
  issues: string[]
} {
  const issues: string[] = []
  let score = 100
  
  // Length check
  if (response.length < 50) {
    issues.push('Response is too short')
    score -= 30
  }
  
  // Empty check
  if (!response.trim()) {
    issues.push('Response is empty')
    score = 0
  }
  
  // Refusal check
  if (/I cannot|I am unable|I don't have access/i.test(response)) {
    issues.push('Response appears to be a refusal')
    score -= 40
  }
  
  // Error message check
  if (/error:|exception:|failed to/i.test(response)) {
    issues.push('Response may contain error messages')
    score -= 20
  }
  
  // Placeholder check
  if (/\[insert|TODO|placeholder|TBD/i.test(response)) {
    issues.push('Response contains placeholders')
    score -= 25
  }
  
  return { score: Math.max(0, score), issues }
}

/**
 * Compare quality between two responses
 */
export function compareQuality(
  response1: string,
  response2: string,
  analysis: QueryAnalysis
): { winner: 1 | 2 | 0; score1: number; score2: number; comparison: string } {
  const dims1 = scoreResponse(response1, analysis)
  const dims2 = scoreResponse(response2, analysis)
  
  const score1 = calculateOverallScore(dims1)
  const score2 = calculateOverallScore(dims2)
  
  let winner: 1 | 2 | 0 = 0
  if (score1 > score2 + 5) winner = 1
  else if (score2 > score1 + 5) winner = 2
  
  const comparison = winner === 0 
    ? 'Responses are roughly equal in quality'
    : winner === 1 
      ? `Response 1 is better (${score1} vs ${score2})`
      : `Response 2 is better (${score2} vs ${score1})`
  
  return { winner, score1, score2, comparison }
}

