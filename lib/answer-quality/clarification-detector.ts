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
  // Minimum confidence to proceed without clarification (raised to reduce false positives)
  MIN_CONFIDENCE_TO_PROCEED: 0.6,
  // Maximum number of clarification questions to ask
  MAX_QUESTIONS: 2,
  // Minimum severity to require clarification
  MIN_SEVERITY_TO_ASK: 'medium' as const,
  // Minimum word count for a query to be considered complete (lowered)
  MIN_WORDS_FOR_COMPLETE_QUERY: 5,
  // Maximum word count before we consider query long enough
  MAX_WORDS_BEFORE_OK: 10,
}

// Patterns that indicate a vague or incomplete query (only truly vague single-phrase queries)
const VAGUE_QUERY_PATTERNS = [
  /^(help|help me)$/i,
  /^(what|how|why)$/i, // Only trigger on single words, not phrases
  /^(explain|describe|show)$/i,
  /^[a-z]{1,6}\??$/i, // Single short word queries only
]

// Topics that often need clarification - ONLY for tech domain
// These should NOT trigger for medical, legal, or other non-tech domains
const TECH_TOPICS_NEEDING_CONTEXT = [
  /\b(my|our)\s+(code|app|application|project|system|website|software|program)\b/i,
  /\b(this|the)\s+(error|bug|issue)\s+(in|with)\b/i,
]

// Patterns that need criteria clarification (top/best without criteria)
const RANKING_PATTERNS = [
  /\b(top|best|leading|greatest|most popular)\s+\d*\s*(llm|model|ai|tool|framework|library|software|app|service)/i,
  /\b(list|rank|compare)\b.*\b(top|best|leading)\b/i,
  /\bwhich\s+(is|are)\s+(the\s+)?(best|top|leading)/i,
]

// Patterns that indicate temporal/current data needs
const TEMPORAL_PATTERNS = [
  /\b(today|now|current|currently|latest|recent|newest|as of|this year|this month|this week|2024|2025|2026)\b/i,
  /\b(right now|at the moment|presently|these days)\b/i,
]

// Queries that should NEVER trigger clarification (clear, complete questions)
// FIX 1.2: Expanded to include more factoid patterns
const SKIP_CLARIFICATION_PATTERNS = [
  /^what\s+(is|are|was|were|does|do|can|could|would|should)\s+.{10,}/i, // "what is X" with enough context
  /^how\s+(do|does|can|could|would|should|to)\s+.{10,}/i, // "how to X" with enough context
  /^(tell me|explain|describe)\s+(about|how|what|why)\s+.{10,}/i, // "tell me about X" with context
  /^(can you|could you|please)\s+(explain|help|tell|show|describe)\s+.{10,}/i, // polite requests with context
  /\?\s*$/i, // Ends with question mark - user has formed a complete question
  // FIX 1.2: Factoid patterns - these are clear questions that need direct answers
  /\b(who|what|when|where)\s+(discovered|invented|wrote|created|founded|is|are|was|were)\b.{5,}/i,
  /\b(capital|largest|smallest|highest|lowest|first|last|oldest|youngest)\s+(of|in|city|country)\b/i,
  /\b(chemical symbol|boiling point|melting point|atomic number|atomic weight)\b/i,
  /\b(how tall|how old|how far|how long|how much does|how many)\b.{5,}/i,
  /\b(what year|what date|what time|what day)\b/i,
  /\b(speed of light|speed of sound|gravitational constant)\b/i,
  /\bwho\s+(is|was|are|were)\s+.{3,}/i, // "Who is Albert Einstein?"
  /\bwhen\s+(did|was|were|is)\s+.{3,}/i, // "When did WWI begin?"
  /\bwhere\s+(is|was|are|were|did)\s+.{3,}/i, // "Where is Australia?"
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
 * IMPROVED: Much more conservative - only asks when truly necessary
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
  
  // FIRST: Check if query should SKIP clarification entirely
  // Well-formed questions with enough context should proceed directly
  for (const pattern of SKIP_CLARIFICATION_PATTERNS) {
    if (pattern.test(query)) {
      console.log('🔍 Skipping clarification - query is well-formed:', query.slice(0, 40))
      return { needed: false, questions: [], confidence: 1.0 }
    }
  }
  
  // Detect domain FIRST to avoid asking irrelevant questions
  const isMedicalDomain = /\b(medical|health|disease|symptom|treatment|diagnosis|patient|clinical|doctor|medicine|therapy|condition|medication|healthcare|surgery|nurse|hospital)\b/i.test(query)
  const isLegalDomain = /\b(legal|law|court|attorney|lawsuit|contract|rights|liability|regulation|compliance|lawyer|sue|judge|verdict)\b/i.test(query)
  const isFinanceDomain = /\b(invest|stock|financial|tax|budget|money|accounting|portfolio|market|crypto|bitcoin|trading|401k|ira|mortgage)\b/i.test(query)
  const isTechDomain = /\b(code|coding|app|application|software|programming|developer|bug|error|debug|api|database|framework|javascript|python|react|node)\b/i.test(query)
  const isResearchDomain = /\b(research|study|academic|paper|journal|scientific|experiment|hypothesis|thesis|dissertation)\b/i.test(query)
  
  // Only trigger clarification for VERY short queries (< 3 words) 
  if (wordCount < 3) {
    confidence -= 0.5
    questions.push({
      id: 'short-query',
      question: 'Could you tell me more about what you need help with?',
      type: 'required',
      reason: 'A bit more context helps me give you a better answer',
    })
  }
  // Check for genuinely vague single-word/phrase patterns
  else {
    for (const pattern of VAGUE_QUERY_PATTERNS) {
      if (pattern.test(query)) {
        confidence -= 0.4
        if (questions.length === 0) {
          questions.push({
            id: 'vague-pattern',
            question: 'What specifically would you like help with?',
            type: 'required',
            reason: 'I want to make sure I understand your request',
          })
        }
        break
      }
    }
  }
  
  // ONLY check for tech context if it's a tech query AND very short
  if (isTechDomain && wordCount < CLARIFICATION_THRESHOLDS.MAX_WORDS_BEFORE_OK) {
    let techContextNeeded = false
    for (const pattern of TECH_TOPICS_NEEDING_CONTEXT) {
      if (pattern.test(query)) {
        techContextNeeded = true
        confidence -= 0.15
        break
      }
    }
    
    if (techContextNeeded && questions.length === 0) {
      if (/\b(error|bug|issue|problem)\b/i.test(query)) {
        questions.push({
          id: 'error-context',
          question: 'What error message or unexpected behavior are you seeing?',
          type: 'recommended',
          reason: 'The exact error helps me provide a targeted solution',
        })
      } else if (/\b(my|our)\s+(code|app|application)\b/i.test(query)) {
        questions.push({
          id: 'tech-context',
          question: 'What programming language or framework are you using?',
          type: 'recommended',
          reason: 'This helps me give you relevant examples',
          options: ['JavaScript/TypeScript', 'Python', 'Java/Kotlin', 'Other'],
        })
      }
    }
  }
  
  // DON'T ask clarification for clear domain-specific questions
  // Medical, legal, finance, research queries should proceed without unnecessary clarification
  // unless they're extremely vague
  
  // Check for ranking/comparison queries - but DON'T ask if query has enough context
  const isRankingQuery = RANKING_PATTERNS.some(p => p.test(query))
  const isTemporalQuery = TEMPORAL_PATTERNS.some(p => p.test(query))
  
  // For ranking queries, only ask clarification if VERY short
  if (isRankingQuery && wordCount < 6 && questions.length === 0) {
    confidence -= 0.2
    questions.push({
      id: 'ranking-criteria',
      question: 'What criteria matter most to you?',
      type: 'optional',
      reason: '"Best" depends on your specific priorities',
      options: ['Performance/Quality', 'Cost/Value', 'Ease of use', 'Just give me recommendations'],
    })
  }
  
  // For temporal queries - just note it, don't ask unnecessary questions
  // The orchestrator will automatically use live research when needed
  if (isTemporalQuery) {
    confidence -= 0.05 // Minor reduction - temporal queries are usually fine
  }
  
  // Final decision - be CONSERVATIVE about asking clarification
  // Only ask if confidence is truly low AND we have questions worth asking
  const hasRequiredQuestions = questions.some(q => q.type === 'required')
  const needed = (hasRequiredQuestions || (questions.length > 0 && confidence < CLARIFICATION_THRESHOLDS.MIN_CONFIDENCE_TO_PROCEED))
  
  // Only log when clarification is actually triggered (reduce noise)
  if (needed) {
    console.log('🔍 Clarification needed:', { 
      query: query.slice(0, 40),
      confidence, 
      questionCount: questions.length,
    })
  }
  
  return {
    needed,
    questions: questions.slice(0, CLARIFICATION_THRESHOLDS.MAX_QUESTIONS),
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

