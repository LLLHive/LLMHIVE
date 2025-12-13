/**
 * Answer Quality Engine for LLMHive
 * 
 * A comprehensive system for generating answers that surpass
 * individual model capabilities through advanced orchestration.
 * 
 * ## Core Systems
 * 
 * 1. **Prompt Optimization** - Analyze and enhance queries
 * 2. **Clarification Detection** - Ask for missing context
 * 3. **Advanced Reasoning** - CoT, ToT, ReAct, Reflexion, etc.
 * 4. **Model Teams** - Specialized personas and workflows
 * 5. **Data Sources** - Real-time retrieval with freshness
 * 6. **Consensus Building** - Multi-model synthesis
 * 7. **Response Enhancement** - Structure and formatting
 * 8. **Fact Verification** - Claim validation
 * 9. **Output Validation** - Error detection and recovery
 * 10. **Quality Scoring** - Multi-dimensional evaluation
 * 11. **Continuous Improvement** - Learning from feedback
 * 12. **Memory Management** - Context and personalization
 * 13. **Benchmarking** - A/B testing and comparison
 * 
 * ## Usage
 * 
 * ```typescript
 * import { getAnswerQualityPipeline } from '@/lib/answer-quality'
 * 
 * const pipeline = getAnswerQualityPipeline()
 * const result = await pipeline.processQuery(query, { generateResponse })
 * 
 * console.log(result.answer)
 * console.log(result.quality.overallScore)
 * ```
 */

// Types
export * from './types'

// Query Analysis & Prompt Optimization
export * from './prompt-optimizer'

// Clarification System
export * from './clarification-detector'

// Advanced Reasoning Engine
export * from './reasoning-engine'

// Model Team Management
export * from './model-team'

// Data Sources & Retrieval
export * from './data-sources'

// Multi-Model Consensus
export * from './consensus-builder'

// Response Enhancement
export * from './response-enhancer'

// Fact Verification
export * from './fact-verifier'

// Output Validation
export * from './output-validator'

// Quality Scoring
export * from './quality-scorer'

// Domain Templates
export * from './domain-templates'

// Continuous Improvement
export * from './continuous-improvement'

// Memory Management
export * from './memory-manager'

// Benchmarking & A/B Testing
export * from './benchmarking'

// Main Orchestration Pipeline
export * from './orchestration-pipeline'

// Advanced Model Profiles & Capabilities
export * from './model-profiles'

// Advanced Reasoning Strategies
export * from './advanced-reasoning'

// Team Synergy Optimization
export * from './team-synergy'

