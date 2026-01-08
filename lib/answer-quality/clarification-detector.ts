/**
 * Clarification Detector
 * 
 * Determines when clarification is needed before answering,
 * preventing low-quality responses from ambiguous queries.
 * 
 * Key principles:
 * - Ask BEFORE answering, not after
 * - Only ask necessary questions (max 2-3)
 * - Provide options when possible
 * - Smart defaults when appropriate
 */

import type { 
  QueryAnalysis, 
  ClarificationQuestion, 
  Ambiguity 
} from './types'
import { analyzeQuery } from './prompt-optimizer'

export interface ClarificationDecision {
  shouldAskClarification: boolean
  questions: ClarificationQuestion[]
  canProceedWithAssumptions: boolean
  assumptions: string[]
  confidence: number
}

// Thresholds for clarification decisions
const CLARIFICATION_THRESHOLDS = {
  // Minimum confidence to proceed without clarification (lowered to be more aggressive)
  MIN_CONFIDENCE_TO_PROCEED: 0.8,
  // Maximum number of clarification questions to ask
  MAX_QUESTIONS: 3,
  // Minimum severity to require clarification
  MIN_SEVERITY_TO_ASK: 'low' as const,
  // Minimum word count for a query to be considered complete
  MIN_WORDS_FOR_COMPLETE_QUERY: 8,
  // Maximum word count before we consider query long enough
  MAX_WORDS_BEFORE_OK: 15,
}

// Patterns that indicate a vague or incomplete query
const VAGUE_QUERY_PATTERNS = [
  /^(help|help me)$/i,
  /^(what|how|why|tell me)$/i,
  /^(explain|describe|show)$/i,
  /^[a-z]+\??$/i, // Single word queries
  /^(do|can you|could you)$/i,
  /^(I need|I want|need help with)$/i,
  /^(best|top|good)\s+\w+\??$/i, // "best practices?" etc
]

// Topics that often need clarification
const TOPICS_NEEDING_CONTEXT = [
  /\b(app|application|system|project|code|website|site)\b/i,
  /\b(error|bug|issue|problem|fix)\b/i,
  /\b(better|improve|optimize|best)\b/i,
  /\b(my|our|the)\s+(code|app|project|system)\b/i,
]

// Patterns that need criteria clarification (top/best without criteria)
const RANKING_PATTERNS = [
  /\b(top|best|leading|greatest|most popular)\s+\d*\s*(llm|model|ai|tool|framework|library|software|app|service)/i,
  /\b(list|rank|compare)\b.*\b(top|best|leading)\b/i,
  /\bwhich\s+(is|are)\s+(the\s+)?(best|top|leading)/i,
]

// Patterns that indicate temporal/current data needs
const TEMPORAL_PATTERNS = [
  /\b(today|now|current|currently|latest|recent|newest|as of|this year|this month|this week|2024|2025)\b/i,
  /\b(right now|at the moment|presently|these days)\b/i,
]

/**
 * Determine if clarification is needed for a query
 */
export function shouldAskClarification(query: string): ClarificationDecision {
  const analysis = analyzeQuery(query)
  const directClarification = checkForDirectClarificationNeeds(query)
  
  // Merge direct clarification with analysis-based clarification
  const analysisDecision = makeClarificationDecision(analysis)
  
  // If direct check found issues, add them
  if (directClarification.needed) {
    return {
      ...analysisDecision,
      shouldAskClarification: true,
      questions: [...directClarification.questions, ...analysisDecision.questions].slice(0, CLARIFICATION_THRESHOLDS.MAX_QUESTIONS),
      confidence: Math.min(analysisDecision.confidence, directClarification.confidence),
    }
  }
  
  return analysisDecision
}

/**
 * Direct pattern-based clarification check (faster, catches obvious cases)
 */
function checkForDirectClarificationNeeds(query: string): {
  needed: boolean
  questions: ClarificationQuestion[]
  confidence: number
} {
  const questions: ClarificationQuestion[] = []
  let confidence = 1.0
  const words = query.trim().split(/\s+/)
  const wordCount = words.length
  
  // Very short queries almost always need clarification
  if (wordCount < 4) {
    confidence -= 0.4
    questions.push({
      id: 'short-query',
      question: 'Could you provide more details about what you need help with?',
      type: 'required',
      reason: 'Your query is quite brief - more context helps me give you a better answer',
    })
  }
  
  // Check for vague patterns
  for (const pattern of VAGUE_QUERY_PATTERNS) {
    if (pattern.test(query)) {
      confidence -= 0.3
      if (questions.length < 2) {
        questions.push({
          id: 'vague-pattern',
          question: 'What specifically would you like to know or accomplish?',
          type: 'required',
          reason: 'I want to make sure I understand your request correctly',
        })
      }
      break
    }
  }
  
  // Check for topics that typically need context
  let topicContextNeeded = false
  for (const pattern of TOPICS_NEEDING_CONTEXT) {
    if (pattern.test(query) && wordCount < CLARIFICATION_THRESHOLDS.MAX_WORDS_BEFORE_OK) {
      topicContextNeeded = true
      confidence -= 0.2
      break
    }
  }
  
  if (topicContextNeeded && questions.length < 2) {
    // Detect domain first to ask domain-appropriate questions
    const isMedicalDomain = /\b(medical|health|disease|symptom|treatment|diagnosis|patient|clinical|doctor|medicine|therapy|condition|medication)\b/i.test(query)
    const isLegalDomain = /\b(legal|law|court|attorney|lawsuit|contract|rights|liability|regulation|compliance)\b/i.test(query)
    const isFinanceDomain = /\b(invest|stock|financial|tax|budget|money|accounting|portfolio|market)\b/i.test(query)
    const isTechDomain = /\b(code|app|application|software|programming|developer|bug|error|debug|api|database|framework)\b/i.test(query)
    
    // Only apply tech-focused questions for tech domain
    if (isTechDomain && /\b(error|bug|issue|problem)\b/i.test(query)) {
      questions.push({
        id: 'error-context',
        question: 'What error message or unexpected behavior are you seeing?',
        type: 'recommended',
        reason: 'Knowing the exact error helps me provide a targeted solution',
      })
    } else if (isTechDomain && /\b(app|application|code|project|system)\b/i.test(query)) {
      questions.push({
        id: 'tech-context',
        question: 'What programming language, framework, or technology are you using?',
        type: 'recommended',
        reason: 'This helps me give you relevant code examples and advice',
        options: ['JavaScript/TypeScript', 'Python', 'Java', 'Other'],
      })
    } else if (isMedicalDomain) {
      // Medical-specific clarification
      questions.push({
        id: 'medical-context',
        question: 'Could you provide more details about the specific condition or topic you are researching?',
        type: 'recommended',
        reason: 'This helps me provide more relevant medical research information',
      })
    } else if (isLegalDomain) {
      // Legal-specific clarification
      questions.push({
        id: 'legal-context',
        question: 'What jurisdiction or type of law are you asking about?',
        type: 'recommended',
        reason: 'Legal matters vary significantly by jurisdiction and area of law',
        options: ['United States', 'European Union', 'Other jurisdiction', 'General principles'],
      })
    } else if (isFinanceDomain) {
      // Finance-specific clarification
      questions.push({
        id: 'finance-context',
        question: 'What is your investment timeline and risk tolerance?',
        type: 'recommended',
        reason: 'Financial advice varies based on your goals and risk profile',
      })
    } else if (/\b(better|improve|optimize|best)\b/i.test(query)) {
      questions.push({
        id: 'goal-context',
        question: 'What is your main goal or priority?',
        type: 'recommended',
        reason: "Different goals lead to different 'best' solutions",
      })
    }
  }
  
  // Check for ranking/comparison queries that need criteria
  const isRankingQuery = RANKING_PATTERNS.some(p => p.test(query))
  
  // DEBUG: Log pattern matching results
  console.log('🔍 Clarification patterns:', { 
    query: query.slice(0, 50),
    isRankingQuery, 
    isTemporalQuery: TEMPORAL_PATTERNS.some(p => p.test(query)),
    wordCount,
    currentConfidence: confidence,
    questionsCount: questions.length,
  })
  
  if (isRankingQuery) {
    confidence -= 0.25
    if (questions.length < 2) {
      questions.push({
        id: 'ranking-criteria',
        question: 'What criteria matter most to you for ranking?',
        type: 'recommended',
        reason: '"Best" or "top" depends on your specific needs and priorities',
        options: ['Performance/Quality', 'Cost/Pricing', 'Ease of use', 'Specific use case (please specify)'],
      })
    }
  }
  
  // Check for temporal queries that need real-time data
  const isTemporalQuery = TEMPORAL_PATTERNS.some(p => p.test(query))
  if (isTemporalQuery) {
    confidence -= 0.15 // Reduce confidence for temporal queries
    if (questions.length < 3 && isRankingQuery) {
      questions.push({
        id: 'temporal-scope',
        question: 'Would you like me to search for the most current information online?',
        type: 'optional',
        reason: 'I can access real-time data to ensure the answer reflects the latest developments',
        options: ['Yes, use real-time data', 'No, general knowledge is fine'],
      })
    }
  }
  
  const needed = questions.length > 0 && confidence < CLARIFICATION_THRESHOLDS.MIN_CONFIDENCE_TO_PROCEED
  
  // DEBUG: Final decision
  console.log('🔍 Clarification final:', { 
    needed,
    confidence, 
    threshold: CLARIFICATION_THRESHOLDS.MIN_CONFIDENCE_TO_PROCEED,
    questionsCount: questions.length,
  })
  
  return {
    needed,
    questions,
    confidence,
  }
}

/**
 * Make clarification decision based on query analysis
 */
export function makeClarificationDecision(analysis: QueryAnalysis): ClarificationDecision {
  const questions: ClarificationQuestion[] = []
  const assumptions: string[] = []
  let confidence = 1.0
  
  // Check for high-severity ambiguities
  const criticalAmbiguities = analysis.ambiguities.filter(
    a => a.severity === 'high'
  )
  
  const mediumAmbiguities = analysis.ambiguities.filter(
    a => a.severity === 'medium'
  )
  
  // High severity ambiguities require clarification
  criticalAmbiguities.forEach(amb => {
    confidence -= 0.3
    questions.push({
      id: `critical-${questions.length}`,
      question: generateQuestionFromAmbiguity(amb),
      type: 'required',
      reason: amb.description,
      options: amb.possibleInterpretations.slice(0, 4),
    })
  })
  
  // Medium severity ambiguities may need clarification
  mediumAmbiguities.forEach(amb => {
    confidence -= 0.15
    if (questions.length < CLARIFICATION_THRESHOLDS.MAX_QUESTIONS) {
      questions.push({
        id: `medium-${questions.length}`,
        question: generateQuestionFromAmbiguity(amb),
        type: 'recommended',
        reason: amb.description,
        options: amb.possibleInterpretations.slice(0, 4),
      })
    } else {
      // Make an assumption instead
      const assumption = makeAssumption(amb)
      if (assumption) assumptions.push(assumption)
    }
  })
  
  // Check for missing critical context
  analysis.missingContext.forEach(ctx => {
    confidence -= 0.2
    if (questions.length < CLARIFICATION_THRESHOLDS.MAX_QUESTIONS) {
      // Generate proper question based on context type
      let question: string
      const ctxLower = ctx.toLowerCase()
      
      // Handle sentences that are already questions
      if (ctxLower.startsWith('what ') || ctxLower.startsWith('which ') || ctxLower.startsWith('how ')) {
        question = ctx.endsWith('?') ? ctx : `${ctx}?`
      } else {
        question = `What ${ctxLower} are you referring to?`
      }
      
      questions.push({
        id: `context-${questions.length}`,
        question,
        type: 'required',
        reason: `This information is needed to provide an accurate answer`,
      })
    }
  })
  
  // Check complexity - very complex queries might need scoping
  if (analysis.complexity === 'expert' && analysis.intent === 'research') {
    confidence -= 0.1
    if (questions.length < CLARIFICATION_THRESHOLDS.MAX_QUESTIONS) {
      questions.push({
        id: 'scope',
        question: 'This is a broad topic. Would you like me to focus on any particular aspect?',
        type: 'optional',
        reason: 'Scoping the question helps provide more relevant information',
      })
    }
  }
  
  // Ensure confidence is bounded
  confidence = Math.max(0, Math.min(1, confidence))
  
  // Determine if we should ask or proceed
  const shouldAsk = 
    questions.filter(q => q.type === 'required').length > 0 ||
    (confidence < CLARIFICATION_THRESHOLDS.MIN_CONFIDENCE_TO_PROCEED && questions.length > 0)
  
  // Can we proceed with assumptions?
  const canProceedWithAssumptions = 
    questions.filter(q => q.type === 'required').length === 0 &&
    confidence > 0.4
  
  return {
    shouldAskClarification: shouldAsk,
    questions: questions.slice(0, CLARIFICATION_THRESHOLDS.MAX_QUESTIONS),
    canProceedWithAssumptions,
    assumptions,
    confidence,
  }
}

/**
 * Generate a natural question from an ambiguity
 */
function generateQuestionFromAmbiguity(ambiguity: Ambiguity): string {
  switch (ambiguity.type) {
    case 'term':
      return `Could you clarify what you mean by "${ambiguity.description}"?`
    case 'scope':
      if (ambiguity.possibleInterpretations.length > 0) {
        return `When you say "${ambiguity.description.split(' ')[0]}", do you mean ${ambiguity.possibleInterpretations.slice(0, 3).join(', ')}?`
      }
      return `Could you be more specific about the scope?`
    case 'context':
      return `To give you the best answer, could you provide more context about ${ambiguity.description.toLowerCase()}?`
    case 'intent':
      return `I want to make sure I understand correctly. ${ambiguity.description}?`
    case 'timeframe':
      return `What time period are you interested in? ${ambiguity.possibleInterpretations.slice(0, 3).join(', ')}?`
    default:
      return `Could you clarify: ${ambiguity.description}?`
  }
}

/**
 * Make a reasonable assumption for an ambiguity
 */
function makeAssumption(ambiguity: Ambiguity): string | null {
  if (ambiguity.possibleInterpretations.length > 0) {
    // Pick the most likely interpretation (usually the first)
    return `Assuming "${ambiguity.possibleInterpretations[0]}" based on typical usage`
  }
  
  switch (ambiguity.type) {
    case 'timeframe':
      return 'Assuming you want current/recent information'
    case 'scope':
      return 'Covering the topic broadly'
    default:
      return null
  }
}

/**
 * Format clarification questions for display
 */
export function formatClarificationMessage(decision: ClarificationDecision): string {
  if (!decision.shouldAskClarification || decision.questions.length === 0) {
    return ''
  }
  
  const parts: string[] = ['Before I answer, I have a few clarifying questions:']
  
  decision.questions.forEach((q, idx) => {
    let questionText = `${idx + 1}. ${q.question}`
    if (q.options && q.options.length > 0) {
      questionText += `\n   Options: ${q.options.map((o, i) => `(${String.fromCharCode(97 + i)}) ${o}`).join(', ')}`
    }
    parts.push(questionText)
  })
  
  if (decision.canProceedWithAssumptions && decision.assumptions.length > 0) {
    parts.push('\nAlternatively, I can proceed with these assumptions:')
    decision.assumptions.forEach(a => parts.push(`• ${a}`))
  }
  
  return parts.join('\n')
}

/**
 * Smart clarification - only ask when truly necessary
 */
export function intelligentClarification(
  query: string,
  previousContext?: string[]
): ClarificationDecision {
  const decision = shouldAskClarification(query)
  
  // If we have previous context, some questions might already be answered
  if (previousContext && previousContext.length > 0) {
    const contextText = previousContext.join(' ').toLowerCase()
    
    // Filter out questions that might be answered by context
    decision.questions = decision.questions.filter(q => {
      // Check if any option or key term from the question appears in context
      if (q.options) {
        const hasAnswerInContext = q.options.some(opt => 
          contextText.includes(opt.toLowerCase())
        )
        if (hasAnswerInContext) {
          decision.confidence += 0.1
          return false
        }
      }
      return true
    })
    
    // Recalculate shouldAsk
    decision.shouldAskClarification = 
      decision.questions.filter(q => q.type === 'required').length > 0 ||
      (decision.confidence < CLARIFICATION_THRESHOLDS.MIN_CONFIDENCE_TO_PROCEED && decision.questions.length > 0)
  }
  
  return decision
}

