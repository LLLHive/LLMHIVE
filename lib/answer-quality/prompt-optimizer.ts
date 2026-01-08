/**
 * Prompt Optimizer
 * 
 * Enhances user queries to maximize answer quality by:
 * - Analyzing query intent and complexity
 * - Adding context and constraints
 * - Structuring for optimal model performance
 * - Selecting best models for the task
 */

import type {
  QueryAnalysis,
  QueryIntent,
  OptimizedPrompt,
  PromptEnhancement,
  ModelHint,
  OutputFormat,
  Ambiguity,
  Entity,
  ClarificationQuestion,
} from './types'

// Intent detection patterns
const INTENT_PATTERNS: { intent: QueryIntent; patterns: RegExp[] }[] = [
  {
    intent: 'factual',
    patterns: [
      /^what (is|are|was|were)\b/i,
      /^who (is|are|was|were)\b/i,
      /^when (did|was|is)\b/i,
      /^where (is|are|was|were)\b/i,
      /^define\b/i,
      /^explain what\b/i,
    ],
  },
  {
    intent: 'procedural',
    patterns: [
      /^how (do|can|should|would|to)\b/i,
      /^steps to\b/i,
      /^guide (me|for|to)\b/i,
      /^tutorial\b/i,
      /^walk me through\b/i,
      /^show me how\b/i,
    ],
  },
  {
    intent: 'analytical',
    patterns: [
      /^why (is|are|did|does|do)\b/i,
      /^analyze\b/i,
      /^explain why\b/i,
      /^what causes\b/i,
      /^reason(s)? (for|behind)\b/i,
    ],
  },
  {
    intent: 'comparative',
    patterns: [
      /\bvs\.?\b/i,
      /\bversus\b/i,
      /\bcompare\b/i,
      /\bdifference(s)? between\b/i,
      /\bwhich (is|are) better\b/i,
      /\bpros and cons\b/i,
    ],
  },
  {
    intent: 'creative',
    patterns: [
      /^write\b/i,
      /^create\b/i,
      /^generate\b/i,
      /^compose\b/i,
      /^draft\b/i,
      /^design\b/i,
      /^brainstorm\b/i,
    ],
  },
  {
    intent: 'troubleshooting',
    patterns: [
      /\b(fix|solve|debug|resolve)\b/i,
      /\b(error|bug|issue|problem)\b/i,
      /\bnot working\b/i,
      /\bhelp with\b/i,
      /\btroubleshoot\b/i,
    ],
  },
  {
    intent: 'code',
    patterns: [
      /\bcode\b/i,
      /\bfunction\b/i,
      /\bprogram\b/i,
      /\bscript\b/i,
      /\bimplement\b/i,
      /\balgorithm\b/i,
      /```/,
    ],
  },
  {
    intent: 'research',
    patterns: [
      /\bresearch\b/i,
      /\binvestigate\b/i,
      /\bin-depth\b/i,
      /\bcomprehensive\b/i,
      /\bexhaustive\b/i,
    ],
  },
  {
    intent: 'summarization',
    patterns: [
      /^summarize\b/i,
      /\bsummary\b/i,
      /\btl;?dr\b/i,
      /\bkey points\b/i,
      /\bmain (ideas|points)\b/i,
    ],
  },
]

// Domain detection
const DOMAIN_KEYWORDS: { domain: string; keywords: string[] }[] = [
  { domain: 'technology', keywords: ['software', 'hardware', 'computer', 'internet', 'digital', 'AI', 'machine learning', 'programming', 'API', 'database'] },
  { domain: 'medical', keywords: ['health', 'medical', 'doctor', 'disease', 'symptom', 'treatment', 'diagnosis', 'medicine', 'patient', 'clinical'] },
  { domain: 'legal', keywords: ['law', 'legal', 'court', 'attorney', 'lawsuit', 'contract', 'regulation', 'compliance', 'rights', 'liability'] },
  { domain: 'finance', keywords: ['money', 'investment', 'stock', 'bank', 'financial', 'tax', 'budget', 'revenue', 'profit', 'accounting'] },
  { domain: 'science', keywords: ['research', 'experiment', 'hypothesis', 'theory', 'scientific', 'data', 'study', 'analysis', 'methodology'] },
  { domain: 'business', keywords: ['company', 'business', 'market', 'strategy', 'management', 'enterprise', 'startup', 'revenue', 'customer'] },
  { domain: 'education', keywords: ['learning', 'teaching', 'student', 'curriculum', 'education', 'school', 'university', 'course', 'training'] },
  { domain: 'creative', keywords: ['art', 'design', 'creative', 'writing', 'story', 'music', 'visual', 'aesthetic', 'imagination'] },
]

// Model strengths for task assignment
const MODEL_STRENGTHS: Record<string, { strengths: string[]; bestFor: QueryIntent[] }> = {
  'gpt-4o': {
    strengths: ['general knowledge', 'instruction following', 'code generation', 'creative writing'],
    bestFor: ['procedural', 'creative', 'code', 'conversational'],
  },
  'claude-sonnet-4': {
    strengths: ['nuanced analysis', 'long context', 'safety', 'detailed explanations'],
    bestFor: ['analytical', 'research', 'factual', 'summarization'],
  },
  'deepseek-chat': {
    strengths: ['code', 'technical', 'math', 'reasoning'],
    bestFor: ['code', 'troubleshooting', 'analytical'],
  },
  'gemini-1.5-pro': {
    strengths: ['multimodal', 'long context', 'research'],
    bestFor: ['research', 'summarization', 'comparative'],
  },
}

/**
 * Analyze a query to understand its intent, complexity, and requirements
 */
export function analyzeQuery(query: string): QueryAnalysis {
  const intent = detectIntent(query)
  const complexity = assessComplexity(query)
  const domain = detectDomain(query)
  const ambiguities = detectAmbiguities(query)
  const entities = extractEntities(query)
  const missingContext = identifyMissingContext(query, intent)
  const clarifications = generateClarificationQuestions(query, ambiguities, missingContext)
  
  return {
    intent,
    complexity,
    domain: domain.primary,
    subDomains: domain.secondary,
    requiredCapabilities: getRequiredCapabilities(intent, domain.primary),
    ambiguities,
    missingContext,
    suggestedClarifications: clarifications,
    estimatedTokens: estimateTokens(query),
    keyEntities: entities,
    temporalContext: detectTemporalContext(query),
  }
}

/**
 * Optimize a prompt for maximum answer quality
 */
export function optimizePrompt(query: string, analysis?: QueryAnalysis): OptimizedPrompt {
  const queryAnalysis = analysis || analyzeQuery(query)
  const enhancements: PromptEnhancement[] = []
  
  // Build system context based on analysis
  const systemContext = buildSystemContext(queryAnalysis)
  
  // Add intent-specific enhancements
  enhancements.push(...getIntentEnhancements(queryAnalysis.intent))
  
  // Add domain-specific enhancements
  enhancements.push(...getDomainEnhancements(queryAnalysis.domain))
  
  // Add complexity-based enhancements
  enhancements.push(...getComplexityEnhancements(queryAnalysis.complexity))
  
  // Get model hints
  const modelHints = selectOptimalModels(queryAnalysis)
  
  // Determine output format
  const outputFormat = determineOutputFormat(queryAnalysis)
  
  // Build optimized prompt
  const optimized = buildOptimizedPrompt(query, enhancements, outputFormat)
  
  return {
    original: query,
    optimized,
    systemContext,
    enhancements,
    modelHints,
    expectedOutputFormat: outputFormat,
  }
}

function detectIntent(query: string): QueryIntent {
  // First, detect domain to avoid misclassifying non-tech queries as troubleshooting
  const isMedicalDomain = /\b(medical|health|disease|symptom|treatment|diagnosis|patient|clinical|doctor|medicine|therapy|condition|medication|healthcare|nursing)\b/i.test(query)
  const isLegalDomain = /\b(legal|law|court|attorney|lawsuit|contract|rights|liability|regulation|compliance|statute|legislation)\b/i.test(query)
  const isFinanceDomain = /\b(invest|stock|financial|tax|budget|accounting|portfolio|market|banking|trading)\b/i.test(query)
  const isTechDomain = /\b(code|software|programming|developer|api|database|framework|javascript|python|typescript|react|node)\b/i.test(query)
  
  // For non-tech domains, prefer research/analytical over troubleshooting
  const isNonTechDomain = (isMedicalDomain || isLegalDomain || isFinanceDomain) && !isTechDomain
  
  for (const { intent, patterns } of INTENT_PATTERNS) {
    // Skip troubleshooting intent for non-tech domains unless explicitly about code/debugging
    if (intent === 'troubleshooting' && isNonTechDomain) {
      continue
    }
    
    if (patterns.some(pattern => pattern.test(query))) {
      return intent
    }
  }
  
  // Default to research for professional domains
  if (isNonTechDomain) {
    return 'research'
  }
  
  return 'conversational'
}

function assessComplexity(query: string): 'simple' | 'moderate' | 'complex' | 'expert' {
  const wordCount = query.split(/\s+/).length
  const hasMultipleParts = /\band\b|\balso\b|\badditionally\b/i.test(query)
  const hasTechnicalTerms = /\b(algorithm|architecture|infrastructure|methodology|implementation)\b/i.test(query)
  const hasConstraints = /\b(must|should|within|between|exactly|only)\b/i.test(query)
  
  let score = 0
  if (wordCount > 50) score += 2
  else if (wordCount > 20) score += 1
  if (hasMultipleParts) score += 1
  if (hasTechnicalTerms) score += 2
  if (hasConstraints) score += 1
  
  if (score >= 5) return 'expert'
  if (score >= 3) return 'complex'
  if (score >= 1) return 'moderate'
  return 'simple'
}

function detectDomain(query: string): { primary: string; secondary: string[] } {
  const queryLower = query.toLowerCase()
  const domainScores: Record<string, number> = {}
  
  for (const { domain, keywords } of DOMAIN_KEYWORDS) {
    domainScores[domain] = keywords.filter(kw => queryLower.includes(kw.toLowerCase())).length
  }
  
  const sorted = Object.entries(domainScores)
    .filter(([, score]) => score > 0)
    .sort((a, b) => b[1] - a[1])
  
  return {
    primary: sorted[0]?.[0] || 'general',
    secondary: sorted.slice(1, 3).map(([domain]) => domain),
  }
}

function detectAmbiguities(query: string): Ambiguity[] {
  const ambiguities: Ambiguity[] = []
  
  // Pronoun ambiguity
  if (/\b(it|they|this|that|these|those)\b/i.test(query) && query.split(' ').length < 10) {
    ambiguities.push({
      type: 'context',
      description: 'Contains pronouns without clear referents',
      possibleInterpretations: [],
      severity: 'medium',
    })
  }
  
  // Scope ambiguity
  if (/\b(best|good|better|top)\b/i.test(query) && !/\bfor\b/i.test(query)) {
    ambiguities.push({
      type: 'scope',
      description: 'Subjective term without context',
      possibleInterpretations: ['Best overall', 'Best for beginners', 'Best value', 'Best performance'],
      severity: 'low',
    })
  }
  
  // Timeframe ambiguity
  if (/\b(recent|latest|current|new)\b/i.test(query)) {
    ambiguities.push({
      type: 'timeframe',
      description: 'Temporal reference needs clarification',
      possibleInterpretations: ['Last week', 'Last month', 'Last year', 'Most recent version'],
      severity: 'low',
    })
  }
  
  return ambiguities
}

function extractEntities(query: string): Entity[] {
  const entities: Entity[] = []
  
  // Extract quoted terms
  const quoted = query.match(/"([^"]+)"/g)
  if (quoted) {
    quoted.forEach(q => {
      entities.push({
        name: q.replace(/"/g, ''),
        type: 'concept',
        confidence: 0.9,
      })
    })
  }
  
  // Extract capitalized terms (potential proper nouns)
  const capitalized = query.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*/g)
  if (capitalized) {
    capitalized.forEach(term => {
      if (!['I', 'The', 'A', 'An', 'What', 'How', 'Why', 'When', 'Where', 'Which'].includes(term)) {
        entities.push({
          name: term,
          type: 'other',
          confidence: 0.7,
        })
      }
    })
  }
  
  return entities
}

function identifyMissingContext(query: string, intent: QueryIntent): string[] {
  const missing: string[] = []
  
  if (intent === 'troubleshooting') {
    if (!/\b(error|message|code)\b/i.test(query)) {
      missing.push('Error message or code')
    }
    if (!/\b(tried|attempted)\b/i.test(query)) {
      missing.push('What has been tried already')
    }
  }
  
  if (intent === 'code') {
    if (!/\b(python|javascript|typescript|java|c\+\+|rust|go)\b/i.test(query)) {
      missing.push('Programming language')
    }
  }
  
  if (intent === 'comparative') {
    if (query.split(/\bvs\.?\b|\bversus\b|\bor\b/i).length < 2) {
      missing.push('Items to compare')
    }
  }
  
  return missing
}

function generateClarificationQuestions(
  query: string,
  ambiguities: Ambiguity[],
  missingContext: string[]
): ClarificationQuestion[] {
  const questions: ClarificationQuestion[] = []
  
  // From missing context
  missingContext.forEach((ctx, idx) => {
    questions.push({
      id: `missing-${idx}`,
      question: `Could you specify the ${ctx.toLowerCase()}?`,
      type: 'recommended',
      reason: `This information would help provide a more accurate answer`,
    })
  })
  
  // From ambiguities
  ambiguities
    .filter(a => a.severity !== 'low')
    .forEach((amb, idx) => {
      questions.push({
        id: `ambig-${idx}`,
        question: `To clarify: ${amb.description}. ${amb.possibleInterpretations.length > 0 ? 'Did you mean: ' + amb.possibleInterpretations.slice(0, 3).join(', ') + '?' : ''}`,
        type: amb.severity === 'high' ? 'required' : 'optional',
        reason: amb.description,
        options: amb.possibleInterpretations.slice(0, 4),
      })
    })
  
  return questions
}

function getRequiredCapabilities(intent: QueryIntent, domain: string): string[] {
  const capabilities: string[] = []
  
  const intentCapabilities: Record<QueryIntent, string[]> = {
    factual: ['knowledge retrieval', 'accuracy'],
    procedural: ['step-by-step reasoning', 'clarity'],
    analytical: ['deep reasoning', 'cause-effect analysis'],
    comparative: ['balanced analysis', 'structured comparison'],
    creative: ['creativity', 'originality'],
    troubleshooting: ['technical knowledge', 'debugging'],
    opinion: ['nuanced thinking', 'multiple perspectives'],
    conversational: ['natural language', 'context awareness'],
    code: ['code generation', 'syntax accuracy'],
    research: ['comprehensive knowledge', 'source synthesis'],
    summarization: ['conciseness', 'key point extraction'],
    translation: ['language expertise', 'cultural context'],
    extraction: ['pattern recognition', 'accuracy'],
  }
  
  capabilities.push(...(intentCapabilities[intent] || []))
  
  // Domain-specific capabilities
  if (domain === 'medical') capabilities.push('medical knowledge', 'safety awareness')
  if (domain === 'legal') capabilities.push('legal reasoning', 'precedent knowledge')
  if (domain === 'finance') capabilities.push('numerical accuracy', 'regulatory awareness')
  
  return capabilities
}

function detectTemporalContext(query: string): { hasTimeConstraint: boolean; dataFreshness: 'current' | 'recent' | 'historical' | 'any'; timeframe?: string } | null {
  const currentIndicators = /\b(current|now|today|latest|2024|2025)\b/i
  const recentIndicators = /\b(recent|new|modern|updated)\b/i
  const historicalIndicators = /\b(history|historical|past|was|were|used to)\b/i
  
  if (currentIndicators.test(query)) {
    return { hasTimeConstraint: true, dataFreshness: 'current' }
  }
  if (recentIndicators.test(query)) {
    return { hasTimeConstraint: true, dataFreshness: 'recent' }
  }
  if (historicalIndicators.test(query)) {
    return { hasTimeConstraint: true, dataFreshness: 'historical' }
  }
  
  return null
}

function estimateTokens(query: string): number {
  // Rough estimate: ~4 characters per token
  return Math.ceil(query.length / 4)
}

function buildSystemContext(analysis: QueryAnalysis): string {
  const parts: string[] = []
  
  parts.push(`You are an expert assistant specializing in ${analysis.domain} topics.`)
  
  if (analysis.complexity === 'expert') {
    parts.push('The user appears to have advanced knowledge. Provide expert-level detail.')
  } else if (analysis.complexity === 'simple') {
    parts.push('Explain concepts clearly and avoid unnecessary jargon.')
  }
  
  if (analysis.intent === 'procedural') {
    parts.push('Provide step-by-step instructions with clear explanations for each step.')
  } else if (analysis.intent === 'analytical') {
    parts.push('Provide deep analysis with reasoning and evidence for your conclusions.')
  } else if (analysis.intent === 'comparative') {
    parts.push('Provide a balanced comparison covering multiple dimensions.')
  }
  
  if (analysis.temporalContext?.dataFreshness === 'current') {
    parts.push('Focus on the most current information available.')
  }
  
  return parts.join(' ')
}

function getIntentEnhancements(intent: QueryIntent): PromptEnhancement[] {
  const enhancements: PromptEnhancement[] = []
  
  const intentEnhancements: Record<QueryIntent, PromptEnhancement[]> = {
    procedural: [{
      type: 'format',
      content: 'Please provide numbered steps with clear explanations.',
      reason: 'Procedural queries benefit from structured step-by-step format',
    }],
    analytical: [{
      type: 'constraint',
      content: 'Include your reasoning process and cite evidence for conclusions.',
      reason: 'Analytical queries require transparent reasoning',
    }],
    comparative: [{
      type: 'format',
      content: 'Structure the comparison with clear categories and a summary table if applicable.',
      reason: 'Comparisons are clearer with structured presentation',
    }],
    code: [{
      type: 'format',
      content: 'Include working code examples with comments explaining key parts.',
      reason: 'Code queries benefit from executable examples',
    }],
    research: [{
      type: 'constraint',
      content: 'Provide comprehensive coverage with sources and multiple perspectives.',
      reason: 'Research queries require depth and citation',
    }],
    troubleshooting: [{
      type: 'format',
      content: 'Start with the most likely solution, then provide alternatives if needed.',
      reason: 'Troubleshooting benefits from prioritized solutions',
    }],
    factual: [],
    creative: [],
    opinion: [],
    conversational: [],
    summarization: [],
    translation: [],
    extraction: [],
  }
  
  enhancements.push(...(intentEnhancements[intent] || []))
  
  return enhancements
}

function getDomainEnhancements(domain: string): PromptEnhancement[] {
  const enhancements: PromptEnhancement[] = []
  
  if (domain === 'medical') {
    enhancements.push({
      type: 'constraint',
      content: 'Note: I can provide general health information but not medical advice. Always consult a healthcare professional.',
      reason: 'Medical queries require safety disclaimers',
    })
  }
  
  if (domain === 'legal') {
    enhancements.push({
      type: 'constraint',
      content: 'Note: This is general legal information, not legal advice. Consult a qualified attorney for your specific situation.',
      reason: 'Legal queries require professional disclaimers',
    })
  }
  
  if (domain === 'finance') {
    enhancements.push({
      type: 'constraint',
      content: 'Note: This is for educational purposes only and not financial advice.',
      reason: 'Financial queries require disclaimers',
    })
  }
  
  return enhancements
}

function getComplexityEnhancements(complexity: 'simple' | 'moderate' | 'complex' | 'expert'): PromptEnhancement[] {
  const enhancements: PromptEnhancement[] = []
  
  if (complexity === 'expert') {
    enhancements.push({
      type: 'context',
      content: 'You may assume advanced domain knowledge and use technical terminology.',
      reason: 'Expert queries don\'t need basic explanations',
    })
  } else if (complexity === 'simple') {
    enhancements.push({
      type: 'context',
      content: 'Explain in clear, accessible language suitable for someone new to this topic.',
      reason: 'Simple queries benefit from accessible explanations',
    })
  }
  
  return enhancements
}

function selectOptimalModels(analysis: QueryAnalysis): ModelHint[] {
  const hints: ModelHint[] = []
  
  for (const [model, info] of Object.entries(MODEL_STRENGTHS)) {
    if (info.bestFor.includes(analysis.intent)) {
      hints.push({
        model,
        strength: info.strengths.join(', '),
        suggestedRole: hints.length === 0 ? 'primary' : 'critic',
      })
    }
  }
  
  // Ensure we have at least 2 models
  if (hints.length < 2) {
    hints.push({
      model: 'gpt-4o',
      strength: 'general knowledge',
      suggestedRole: hints.length === 0 ? 'primary' : 'verifier',
    })
    hints.push({
      model: 'claude-sonnet-4',
      strength: 'analysis',
      suggestedRole: 'critic',
    })
  }
  
  return hints.slice(0, 3)
}

function determineOutputFormat(analysis: QueryAnalysis): OutputFormat {
  const intentFormats: Record<QueryIntent, OutputFormat> = {
    procedural: { type: 'list', includeExamples: true, includeSources: false },
    comparative: { type: 'table', includeExamples: false, includeSources: true },
    code: { type: 'code', includeExamples: true, includeSources: false },
    research: { type: 'structured', sections: ['Overview', 'Key Findings', 'Analysis', 'Conclusion'], includeExamples: true, includeSources: true },
    analytical: { type: 'prose', includeExamples: true, includeSources: true },
    factual: { type: 'prose', includeExamples: false, includeSources: true },
    creative: { type: 'prose', includeExamples: false, includeSources: false },
    troubleshooting: { type: 'list', includeExamples: true, includeSources: false },
    opinion: { type: 'prose', includeExamples: true, includeSources: false },
    conversational: { type: 'prose', includeExamples: false, includeSources: false },
    summarization: { type: 'list', includeExamples: false, includeSources: false },
    translation: { type: 'prose', includeExamples: false, includeSources: false },
    extraction: { type: 'structured', includeExamples: false, includeSources: true },
  }
  
  return intentFormats[analysis.intent] || { type: 'prose', includeExamples: false, includeSources: false }
}

function buildOptimizedPrompt(
  original: string,
  enhancements: PromptEnhancement[],
  format: OutputFormat
): string {
  let optimized = original
  
  // Add format instructions
  if (format.type === 'list') {
    optimized += '\n\nPlease structure your response as a numbered list with clear explanations for each point.'
  } else if (format.type === 'table') {
    optimized += '\n\nPlease include a comparison table if applicable.'
  } else if (format.type === 'structured' && format.sections) {
    optimized += `\n\nPlease structure your response with these sections: ${format.sections.join(', ')}.`
  }
  
  if (format.includeExamples) {
    optimized += '\n\nInclude relevant examples to illustrate key points.'
  }
  
  if (format.includeSources) {
    optimized += '\n\nCite sources where applicable.'
  }
  
  return optimized
}

