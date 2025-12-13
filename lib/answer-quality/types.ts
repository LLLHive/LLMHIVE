/**
 * Answer Quality Types
 * 
 * Defines all types for the quality improvement pipeline
 */

// Quality dimensions we optimize for
export interface QualityDimensions {
  accuracy: number      // Factual correctness (0-100)
  completeness: number  // Addresses all aspects (0-100)
  clarity: number       // Easy to understand (0-100)
  relevance: number     // On-topic and useful (0-100)
  structure: number     // Well-organized (0-100)
  actionability: number // Provides actionable insights (0-100)
  sources: number       // Backed by citations (0-100)
  depth: number         // Level of detail (0-100)
}

// Query analysis result
export interface QueryAnalysis {
  intent: QueryIntent
  complexity: 'simple' | 'moderate' | 'complex' | 'expert'
  domain: string
  subDomains: string[]
  requiredCapabilities: string[]
  ambiguities: Ambiguity[]
  missingContext: string[]
  suggestedClarifications: ClarificationQuestion[]
  estimatedTokens: number
  keyEntities: Entity[]
  temporalContext: TemporalContext | null
}

export type QueryIntent = 
  | 'factual'           // What is X?
  | 'procedural'        // How to do X?
  | 'analytical'        // Why is X? Analyze X
  | 'comparative'       // X vs Y
  | 'creative'          // Generate/write X
  | 'troubleshooting'   // Fix/debug X
  | 'opinion'           // What do you think about X?
  | 'conversational'    // General chat
  | 'code'              // Programming tasks
  | 'research'          // Deep investigation
  | 'summarization'     // Summarize X
  | 'translation'       // Translate X
  | 'extraction'        // Extract info from X

export interface Ambiguity {
  type: 'term' | 'scope' | 'context' | 'intent' | 'timeframe'
  description: string
  possibleInterpretations: string[]
  severity: 'low' | 'medium' | 'high'
}

export interface ClarificationQuestion {
  id: string
  question: string
  type: 'required' | 'recommended' | 'optional'
  reason: string
  options?: string[]  // Predefined options if applicable
  defaultValue?: string
}

export interface Entity {
  name: string
  type: 'person' | 'organization' | 'concept' | 'product' | 'location' | 'technology' | 'other'
  confidence: number
  context?: string
}

export interface TemporalContext {
  hasTimeConstraint: boolean
  referencedDate?: Date
  dataFreshness: 'current' | 'recent' | 'historical' | 'any'
  timeframe?: string
}

// Prompt optimization
export interface OptimizedPrompt {
  original: string
  optimized: string
  systemContext: string
  enhancements: PromptEnhancement[]
  modelHints: ModelHint[]
  expectedOutputFormat: OutputFormat
}

export interface PromptEnhancement {
  type: 'clarification' | 'context' | 'constraint' | 'example' | 'format'
  content: string
  reason: string
}

export interface ModelHint {
  model: string
  strength: string
  suggestedRole: 'primary' | 'critic' | 'verifier' | 'creative' | 'technical'
}

export interface OutputFormat {
  type: 'prose' | 'list' | 'table' | 'code' | 'structured' | 'mixed'
  sections?: string[]
  includeExamples: boolean
  includeSources: boolean
  maxLength?: number
}

// Response enhancement
export interface EnhancedResponse {
  original: string
  enhanced: string
  structure: ResponseStructure
  citations: Citation[]
  confidence: number
  qualityScore: QualityDimensions
  improvements: Improvement[]
  metadata: ResponseMetadata
}

export interface ResponseStructure {
  summary?: string
  sections: ResponseSection[]
  conclusion?: string
  actionItems?: string[]
  furtherReading?: string[]
}

export interface ResponseSection {
  heading: string
  content: string
  type: 'explanation' | 'example' | 'code' | 'warning' | 'tip' | 'quote' | 'data'
  subsections?: ResponseSection[]
}

export interface Citation {
  id: string
  text: string
  source: string
  url?: string
  date?: string
  relevance: number
  verified: boolean
}

export interface Improvement {
  type: 'added' | 'removed' | 'modified' | 'restructured'
  description: string
  before?: string
  after?: string
}

export interface ResponseMetadata {
  generationTime: number
  modelsUsed: string[]
  tokensUsed: number
  reasoningMethod: string
  qualityChecks: QualityCheck[]
}

export interface QualityCheck {
  name: string
  passed: boolean
  score: number
  details?: string
}

// Fact verification
export interface FactVerificationResult {
  claims: VerifiedClaim[]
  overallConfidence: number
  sourcesChecked: number
  unreliableClaims: string[]
  suggestedCorrections: Correction[]
}

export interface VerifiedClaim {
  claim: string
  verified: boolean
  confidence: number
  sources: Citation[]
  conflictingInfo?: string
}

export interface Correction {
  original: string
  corrected: string
  reason: string
  source?: Citation
}

// Consensus building
export interface ConsensusResult {
  finalAnswer: string
  agreement: number
  contributions: ModelContribution[]
  conflicts: Conflict[]
  synthesisMethod: string
}

export interface ModelContribution {
  model: string
  response: string
  role: string
  weight: number
  strengths: string[]
  weaknesses: string[]
}

export interface Conflict {
  topic: string
  positions: { model: string; position: string }[]
  resolution: string
  confidence: number
}

// Domain templates
export interface DomainTemplate {
  id: string
  domain: string
  name: string
  description: string
  promptEnhancements: string[]
  outputStructure: OutputFormat
  qualityChecks: string[]
  bestModels: string[]
  examples: TemplateExample[]
}

export interface TemplateExample {
  query: string
  idealResponse: string
  keyPoints: string[]
}

// Quality scoring
export interface QualityReport {
  overallScore: number
  dimensions: QualityDimensions
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  comparisonToBaseline: number // How much better than single model
  historicalTrend: number[]
}

