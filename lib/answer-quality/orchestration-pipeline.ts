/**
 * Answer Quality Orchestration Pipeline
 * 
 * The main entry point that integrates all quality improvement systems
 * into a unified pipeline for generating superior answers.
 */

import { analyzeQuery, optimizePrompt } from './prompt-optimizer'
import { shouldAskClarification, formatClarificationMessage } from './clarification-detector'
import { selectReasoningMethod, getPromptGenerator, getReasoningConfig, buildReasoningPipeline } from './reasoning-engine'
import { buildTeam, getPersonaSystemPrompt, createTeamExecutionPlan, type ModelPersona } from './model-team'
import { createRetrievalPlan, executeRetrievalPlan, generateContextAugmentation } from './data-sources'
import { buildConsensus, type ModelResponse } from './consensus-builder'
import { enhanceResponse, quickEnhance } from './response-enhancer'
import { extractClaims, verifyClaims, generateFactCheckSummary } from './fact-verifier'
import { validateOutput, selectBestResponse, attemptRecovery } from './output-validator'
import { generateQualityReport, quickQualityCheck } from './quality-scorer'
import { getTemplateForQuery, applyTemplate, validateAgainstTemplate } from './domain-templates'
import { getQualityTracker } from './continuous-improvement'
import { getMemoryManager } from './memory-manager'
import type { 
  QueryAnalysis, 
  OptimizedPrompt, 
  EnhancedResponse, 
  QualityReport,
  OutputFormat,
} from './types'

export interface PipelineConfig {
  // Feature toggles
  enableClarification: boolean
  enableDataRetrieval: boolean
  enableMultiModel: boolean
  enableConsensus: boolean
  enableFactVerification: boolean
  enableQualityScoring: boolean
  enableMemory: boolean
  enableTemplates: boolean
  
  // Performance settings
  maxModels: number
  maxRetries: number
  timeout: number
  
  // Quality settings
  minQualityScore: number
  requireFactCheck: boolean
}

export interface PipelineResult {
  // The final answer
  answer: string
  
  // Quality metadata
  quality: QualityReport
  
  // Processing metadata
  metadata: {
    queryAnalysis: QueryAnalysis
    reasoningMethod: string
    modelsUsed: string[]
    processingTime: number
    clarificationAsked: boolean
    dataRetrieved: boolean
    factChecked: boolean
    improvements: string[]
  }
  
  // Optional elements
  clarificationNeeded?: string
  citations?: { id: string; text: string; source: string }[]
  alternatives?: string[]
}

const DEFAULT_CONFIG: PipelineConfig = {
  enableClarification: true,
  enableDataRetrieval: true,
  enableMultiModel: true,
  enableConsensus: true,
  enableFactVerification: true,
  enableQualityScoring: true,
  enableMemory: true,
  enableTemplates: true,
  
  maxModels: 3,
  maxRetries: 2,
  timeout: 30000,
  
  minQualityScore: 70,
  requireFactCheck: false,
}

/**
 * Main orchestration pipeline for answer generation
 */
export class AnswerQualityPipeline {
  private config: PipelineConfig
  private qualityTracker = getQualityTracker()
  private memoryManager = getMemoryManager()
  
  constructor(config: Partial<PipelineConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }
  
  /**
   * Process a query through the full quality pipeline
   */
  async processQuery(
    query: string,
    options: {
      conversationHistory?: string[]
      userContext?: Record<string, string>
      generateResponse: (prompt: string, systemPrompt: string, model: string) => Promise<string>
    }
  ): Promise<PipelineResult> {
    const startTime = Date.now()
    const improvements: string[] = []
    let modelsUsed: string[] = []
    
    // 1. ANALYZE QUERY
    const queryAnalysis = analyzeQuery(query)
    
    // 2. CHECK FOR CLARIFICATION
    if (this.config.enableClarification) {
      const clarificationDecision = shouldAskClarification(query)
      
      if (clarificationDecision.shouldAskClarification) {
        const clarificationMessage = formatClarificationMessage(clarificationDecision)
        
        return {
          answer: '',
          quality: this.getEmptyQualityReport(),
          metadata: {
            queryAnalysis,
            reasoningMethod: 'none',
            modelsUsed: [],
            processingTime: Date.now() - startTime,
            clarificationAsked: true,
            dataRetrieved: false,
            factChecked: false,
            improvements: [],
          },
          clarificationNeeded: clarificationMessage,
        }
      }
    }
    
    // 3. RETRIEVE CONTEXT & DATA
    let contextAugmentation = ''
    let dataRetrieved = false
    
    if (this.config.enableDataRetrieval) {
      const retrievalPlan = createRetrievalPlan(queryAnalysis)
      const retrievedData = await executeRetrievalPlan(query, retrievalPlan)
      
      if (retrievedData.length > 0) {
        contextAugmentation = generateContextAugmentation(query, retrievedData, queryAnalysis)
        dataRetrieved = true
        improvements.push('Augmented with retrieved data')
      }
    }
    
    // 4. ADD MEMORY CONTEXT
    if (this.config.enableMemory) {
      const memoryContext = this.memoryManager.getContextForPrompt()
      if (memoryContext) {
        contextAugmentation = memoryContext + '\n\n' + contextAugmentation
        improvements.push('Personalized with memory context')
      }
    }
    
    // 5. OPTIMIZE PROMPT
    const optimizedPrompt = optimizePrompt(query, queryAnalysis)
    improvements.push(`Prompt optimized for ${queryAnalysis.intent} intent`)
    
    // 6. APPLY DOMAIN TEMPLATE
    let finalPrompt = optimizedPrompt.optimized
    let expectedFormat: OutputFormat | undefined
    
    if (this.config.enableTemplates) {
      const template = getTemplateForQuery(queryAnalysis.intent, queryAnalysis.domain)
      if (template) {
        finalPrompt = applyTemplate(finalPrompt, template)
        expectedFormat = template.outputStructure
        improvements.push(`Applied ${template.name} template`)
      }
    }
    
    // 7. BUILD REASONING PIPELINE
    const reasoningPipeline = buildReasoningPipeline(query, queryAnalysis)
    const reasoningPrompt = getPromptGenerator(reasoningPipeline.method)(finalPrompt)
    improvements.push(`Using ${reasoningPipeline.method} reasoning`)
    
    // 8. GENERATE RESPONSES
    let responses: ModelResponse[] = []
    
    if (this.config.enableMultiModel) {
      // Build model team
      const team = buildTeam(queryAnalysis)
      const executionPlan = createTeamExecutionPlan(team, query)
      
      // Execute team plan
      responses = await this.executeTeamPlan(
        executionPlan,
        reasoningPrompt,
        contextAugmentation + '\n\n' + optimizedPrompt.systemContext,
        options.generateResponse
      )
      
      modelsUsed = responses.map(r => r.model)
      improvements.push(`Used ${modelsUsed.length} models in ${team.workflow} workflow`)
    } else {
      // Single model response
      const response = await options.generateResponse(
        contextAugmentation + '\n\n' + reasoningPrompt,
        optimizedPrompt.systemContext,
        'gpt-4o'
      )
      responses.push({ model: 'gpt-4o', content: response })
      modelsUsed = ['gpt-4o']
    }
    
    // 9. BUILD CONSENSUS
    let finalAnswer = responses[0]?.content || ''
    
    if (this.config.enableConsensus && responses.length > 1) {
      const consensus = buildConsensus(responses, query, queryAnalysis)
      finalAnswer = consensus.finalAnswer
      improvements.push(`Built consensus (${Math.round(consensus.agreement * 100)}% agreement)`)
    }
    
    // 10. VALIDATE OUTPUT
    const validation = validateOutput(finalAnswer, query, queryAnalysis, expectedFormat)
    
    if (!validation.isValid && this.config.maxRetries > 0) {
      // Attempt recovery
      for (const strategy of validation.recoveryStrategies.slice(0, this.config.maxRetries)) {
        const recovery = attemptRecovery(finalAnswer, validation, strategy)
        if (recovery.recovered) {
          finalAnswer = recovery.result
          improvements.push(`Recovered using ${strategy.type}`)
          break
        }
      }
    }
    
    // 11. ENHANCE RESPONSE
    if (validation.score >= 50) {
      const enhanced = enhanceResponse(finalAnswer, {
        format: expectedFormat || { type: 'prose', includeExamples: true, includeSources: true },
        analysis: queryAnalysis,
        addSummary: queryAnalysis.complexity === 'complex' || queryAnalysis.complexity === 'expert',
        addActionItems: queryAnalysis.intent === 'procedural',
      })
      
      finalAnswer = enhanced.enhanced
      improvements.push(...enhanced.improvements.map(i => i.description))
    }
    
    // 12. FACT VERIFICATION
    let factChecked = false
    
    if (this.config.enableFactVerification && 
        (this.config.requireFactCheck || queryAnalysis.intent === 'factual' || queryAnalysis.intent === 'research')) {
      const claims = extractClaims(finalAnswer)
      
      if (claims.length > 0) {
        const verification = await verifyClaims(claims, responses.map(r => r.content))
        
        if (verification.unreliableClaims.length > 0) {
          const factNote = generateFactCheckSummary(verification)
          finalAnswer += '\n\n---\n' + factNote
        }
        
        factChecked = true
        improvements.push(`Verified ${claims.length} claims`)
      }
    }
    
    // 13. QUALITY SCORING
    const qualityReport = this.config.enableQualityScoring
      ? generateQualityReport(finalAnswer, queryAnalysis, modelsUsed.length)
      : this.getEmptyQualityReport()
    
    // 14. RECORD METRICS
    if (this.config.enableQualityScoring) {
      this.qualityTracker.recordMetric({
        queryId: `q-${Date.now()}`,
        overallScore: qualityReport.overallScore,
        dimensions: qualityReport.dimensions,
        modelsUsed,
        reasoningMethod: reasoningPipeline.method,
        responseTime: Date.now() - startTime,
        improvements,
      })
    }
    
    // 15. UPDATE MEMORY
    if (this.config.enableMemory) {
      this.memoryManager.updateContext(query, finalAnswer, {
        entities: queryAnalysis.keyEntities.map(e => e.name),
        keyPoints: [queryAnalysis.intent],
      })
    }
    
    return {
      answer: finalAnswer,
      quality: qualityReport,
      metadata: {
        queryAnalysis,
        reasoningMethod: reasoningPipeline.method,
        modelsUsed,
        processingTime: Date.now() - startTime,
        clarificationAsked: false,
        dataRetrieved,
        factChecked,
        improvements,
      },
      alternatives: responses.length > 1 ? responses.slice(1).map(r => r.content) : undefined,
    }
  }
  
  /**
   * Execute team execution plan
   */
  private async executeTeamPlan(
    plan: { step: number; persona: ModelPersona; task: string; dependsOn: number[] }[],
    prompt: string,
    systemContext: string,
    generateResponse: (prompt: string, systemPrompt: string, model: string) => Promise<string>
  ): Promise<ModelResponse[]> {
    const responses: ModelResponse[] = []
    const stepResults: Record<number, string> = {}
    
    // Group steps by step number for parallel execution
    const stepGroups = new Map<number, typeof plan>()
    for (const step of plan) {
      if (!stepGroups.has(step.step)) {
        stepGroups.set(step.step, [])
      }
      stepGroups.get(step.step)!.push(step)
    }
    
    // Execute steps in order
    for (const [stepNum, steps] of Array.from(stepGroups.entries()).sort((a, b) => a[0] - b[0])) {
      const stepPromises = steps.map(async (step) => {
        // Build context from dependencies
        let contextFromDeps = ''
        for (const dep of step.dependsOn) {
          if (stepResults[dep]) {
            contextFromDeps += `\n\nPrevious response:\n${stepResults[dep]}`
          }
        }
        
        const fullPrompt = contextFromDeps + '\n\n' + prompt
        const systemPrompt = getPersonaSystemPrompt(step.persona) + '\n\n' + systemContext
        
        const model = step.persona.preferredModels[0] || 'gpt-4o'
        const response = await generateResponse(fullPrompt, systemPrompt, model)
        
        return {
          stepNum,
          persona: step.persona,
          response,
          model,
        }
      })
      
      const results = await Promise.all(stepPromises)
      
      for (const result of results) {
        stepResults[result.stepNum] = result.response
        responses.push({
          model: result.model,
          content: result.response,
          role: result.persona.role,
        })
      }
    }
    
    return responses
  }
  
  /**
   * Get empty quality report for edge cases
   */
  private getEmptyQualityReport(): QualityReport {
    return {
      overallScore: 0,
      dimensions: {
        accuracy: 0,
        completeness: 0,
        clarity: 0,
        relevance: 0,
        structure: 0,
        actionability: 0,
        sources: 0,
        depth: 0,
      },
      strengths: [],
      weaknesses: [],
      suggestions: [],
      comparisonToBaseline: 0,
      historicalTrend: [],
    }
  }
  
  /**
   * Quick process for simple queries (faster, less overhead)
   */
  async quickProcess(
    query: string,
    generateResponse: (prompt: string, systemPrompt: string, model: string) => Promise<string>
  ): Promise<string> {
    const analysis = analyzeQuery(query)
    
    // Skip complex pipeline for simple queries
    if (analysis.complexity === 'simple' && analysis.ambiguities.length === 0) {
      const response = await generateResponse(
        query,
        `You are a helpful assistant. Provide a clear, concise answer.`,
        'gpt-4o'
      )
      
      // Quick quality check
      const check = quickQualityCheck(response)
      
      if (check.score >= 70) {
        return quickEnhance(response)
      }
    }
    
    // Fall back to full pipeline
    const result = await this.processQuery(query, { generateResponse })
    return result.answer
  }
  
  /**
   * Update pipeline configuration
   */
  updateConfig(updates: Partial<PipelineConfig>): void {
    this.config = { ...this.config, ...updates }
  }
  
  /**
   * Get current configuration
   */
  getConfig(): PipelineConfig {
    return { ...this.config }
  }
  
  /**
   * Get quality insights from tracker
   */
  getQualityInsights(): {
    averageScore: number
    trend: 'improving' | 'stable' | 'declining'
    topIssues: string[]
    recommendations: string[]
  } {
    return this.qualityTracker.getPerformanceReport()
  }
}

// Singleton instance
let pipelineInstance: AnswerQualityPipeline | null = null

export function getAnswerQualityPipeline(config?: Partial<PipelineConfig>): AnswerQualityPipeline {
  if (!pipelineInstance || config) {
    pipelineInstance = new AnswerQualityPipeline(config)
  }
  return pipelineInstance
}

/**
 * Convenience function for processing a query with default settings
 */
export async function processQueryWithQuality(
  query: string,
  generateResponse: (prompt: string, systemPrompt: string, model: string) => Promise<string>,
  options?: Partial<PipelineConfig>
): Promise<PipelineResult> {
  const pipeline = getAnswerQualityPipeline(options)
  return pipeline.processQuery(query, { generateResponse })
}

