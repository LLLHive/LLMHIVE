/**
 * Continuous Improvement & Learning System
 * 
 * Tracks answer quality over time and implements feedback loops
 * for continuous improvement of LLMHive outputs.
 */

import type { QualityDimensions, QualityReport } from './types'

export interface QualityMetrics {
  timestamp: Date
  queryId: string
  overallScore: number
  dimensions: QualityDimensions
  modelsUsed: string[]
  reasoningMethod: string
  responseTime: number
  userFeedback?: UserFeedback
  improvements: string[]
}

export interface UserFeedback {
  rating: 1 | 2 | 3 | 4 | 5
  helpful: boolean
  accurate: boolean
  complete: boolean
  clear: boolean
  comments?: string
  timestamp: Date
}

export interface ImprovementPlan {
  id: string
  dimension: keyof QualityDimensions
  currentScore: number
  targetScore: number
  actions: ImprovementAction[]
  deadline: Date
  status: 'planned' | 'in-progress' | 'completed' | 'abandoned'
}

export interface ImprovementAction {
  id: string
  description: string
  type: ActionType
  priority: 'high' | 'medium' | 'low'
  expectedImpact: number
  status: 'pending' | 'done'
}

export type ActionType = 
  | 'prompt-tuning'
  | 'model-selection'
  | 'template-update'
  | 'reasoning-method'
  | 'data-source'
  | 'output-format'

export interface LearningInsight {
  id: string
  pattern: string
  impact: number
  confidence: number
  applicableContexts: string[]
  learnedFrom: string[] // Query IDs
  validated: boolean
}

export interface PerformanceBaseline {
  dimension: keyof QualityDimensions
  baseline: number
  current: number
  target: number
  trend: 'improving' | 'stable' | 'declining'
  lastUpdated: Date
}

// Storage keys
const METRICS_KEY = 'llmhive-quality-metrics'
const INSIGHTS_KEY = 'llmhive-learning-insights'
const BASELINES_KEY = 'llmhive-performance-baselines'
const IMPROVEMENT_PLANS_KEY = 'llmhive-improvement-plans'

/**
 * Quality Metrics Tracker
 */
export class QualityTracker {
  private metrics: QualityMetrics[] = []
  private insights: LearningInsight[] = []
  private baselines: PerformanceBaseline[] = []
  private improvementPlans: ImprovementPlan[] = []
  
  constructor() {
    this.loadFromStorage()
  }
  
  private loadFromStorage(): void {
    if (typeof window === 'undefined') return
    
    try {
      const metricsJson = localStorage.getItem(METRICS_KEY)
      if (metricsJson) {
        this.metrics = JSON.parse(metricsJson)
      }
      
      const insightsJson = localStorage.getItem(INSIGHTS_KEY)
      if (insightsJson) {
        this.insights = JSON.parse(insightsJson)
      }
      
      const baselinesJson = localStorage.getItem(BASELINES_KEY)
      if (baselinesJson) {
        this.baselines = JSON.parse(baselinesJson)
      }
      
      const plansJson = localStorage.getItem(IMPROVEMENT_PLANS_KEY)
      if (plansJson) {
        this.improvementPlans = JSON.parse(plansJson)
      }
    } catch (error) {
      console.error('Error loading quality data:', error)
    }
  }
  
  private saveToStorage(): void {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem(METRICS_KEY, JSON.stringify(this.metrics.slice(-1000)))
      localStorage.setItem(INSIGHTS_KEY, JSON.stringify(this.insights.slice(-100)))
      localStorage.setItem(BASELINES_KEY, JSON.stringify(this.baselines))
      localStorage.setItem(IMPROVEMENT_PLANS_KEY, JSON.stringify(this.improvementPlans))
    } catch (error) {
      console.error('Error saving quality data:', error)
    }
  }
  
  /**
   * Record a quality metric
   */
  recordMetric(metric: Omit<QualityMetrics, 'timestamp'>): void {
    const fullMetric: QualityMetrics = {
      ...metric,
      timestamp: new Date(),
    }
    
    this.metrics.push(fullMetric)
    this.updateBaselines(fullMetric)
    this.detectPatterns()
    this.saveToStorage()
  }
  
  /**
   * Record user feedback
   */
  recordFeedback(queryId: string, feedback: UserFeedback): void {
    const metric = this.metrics.find(m => m.queryId === queryId)
    if (metric) {
      metric.userFeedback = feedback
      this.saveToStorage()
      this.learnFromFeedback(metric, feedback)
    }
  }
  
  /**
   * Get quality trend over time
   */
  getTrend(dimension: keyof QualityDimensions, days: number = 7): number[] {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)
    
    const recentMetrics = this.metrics
      .filter(m => new Date(m.timestamp) > cutoff)
      .map(m => m.dimensions[dimension])
    
    return recentMetrics
  }
  
  /**
   * Get overall performance report
   */
  getPerformanceReport(): {
    averageScore: number
    dimensionAverages: Partial<QualityDimensions>
    trend: 'improving' | 'stable' | 'declining'
    topIssues: string[]
    recommendations: string[]
  } {
    const recentMetrics = this.metrics.slice(-100)
    
    if (recentMetrics.length === 0) {
      return {
        averageScore: 0,
        dimensionAverages: {},
        trend: 'stable',
        topIssues: [],
        recommendations: [],
      }
    }
    
    // Calculate averages
    const averageScore = recentMetrics.reduce((sum, m) => sum + m.overallScore, 0) / recentMetrics.length
    
    const dimensionAverages: Partial<QualityDimensions> = {}
    const dimensions: (keyof QualityDimensions)[] = [
      'accuracy', 'completeness', 'clarity', 'relevance',
      'structure', 'actionability', 'sources', 'depth'
    ]
    
    for (const dim of dimensions) {
      dimensionAverages[dim] = recentMetrics.reduce((sum, m) => sum + m.dimensions[dim], 0) / recentMetrics.length
    }
    
    // Calculate trend
    const firstHalf = recentMetrics.slice(0, Math.floor(recentMetrics.length / 2))
    const secondHalf = recentMetrics.slice(Math.floor(recentMetrics.length / 2))
    
    const firstAvg = firstHalf.reduce((sum, m) => sum + m.overallScore, 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((sum, m) => sum + m.overallScore, 0) / secondHalf.length
    
    let trend: 'improving' | 'stable' | 'declining' = 'stable'
    if (secondAvg > firstAvg + 5) trend = 'improving'
    else if (secondAvg < firstAvg - 5) trend = 'declining'
    
    // Identify top issues
    const topIssues: string[] = []
    for (const [dim, avg] of Object.entries(dimensionAverages)) {
      if (avg !== undefined && avg < 70) {
        topIssues.push(`${dim}: ${avg.toFixed(1)} (below target)`)
      }
    }
    
    // Generate recommendations
    const recommendations = this.generateRecommendations(dimensionAverages as QualityDimensions)
    
    return {
      averageScore,
      dimensionAverages,
      trend,
      topIssues,
      recommendations,
    }
  }
  
  /**
   * Update performance baselines
   */
  private updateBaselines(metric: QualityMetrics): void {
    const dimensions: (keyof QualityDimensions)[] = [
      'accuracy', 'completeness', 'clarity', 'relevance',
      'structure', 'actionability', 'sources', 'depth'
    ]
    
    for (const dim of dimensions) {
      let baseline = this.baselines.find(b => b.dimension === dim)
      
      if (!baseline) {
        baseline = {
          dimension: dim,
          baseline: 70,
          current: metric.dimensions[dim],
          target: 85,
          trend: 'stable',
          lastUpdated: new Date(),
        }
        this.baselines.push(baseline)
      } else {
        // Update with moving average
        baseline.current = baseline.current * 0.9 + metric.dimensions[dim] * 0.1
        
        // Update trend
        if (baseline.current > baseline.baseline + 5) {
          baseline.trend = 'improving'
        } else if (baseline.current < baseline.baseline - 5) {
          baseline.trend = 'declining'
        } else {
          baseline.trend = 'stable'
        }
        
        baseline.lastUpdated = new Date()
      }
    }
  }
  
  /**
   * Detect patterns in quality metrics
   */
  private detectPatterns(): void {
    if (this.metrics.length < 10) return
    
    const recentMetrics = this.metrics.slice(-50)
    
    // Pattern: Model performance by intent
    const modelPerformance: Record<string, Record<string, number[]>> = {}
    
    for (const metric of recentMetrics) {
      for (const model of metric.modelsUsed) {
        if (!modelPerformance[model]) {
          modelPerformance[model] = {}
        }
        
        const reasoningMethod = metric.reasoningMethod
        if (!modelPerformance[model][reasoningMethod]) {
          modelPerformance[model][reasoningMethod] = []
        }
        
        modelPerformance[model][reasoningMethod].push(metric.overallScore)
      }
    }
    
    // Generate insights from patterns
    for (const [model, methods] of Object.entries(modelPerformance)) {
      for (const [method, scores] of Object.entries(methods)) {
        if (scores.length >= 5) {
          const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length
          
          if (avgScore > 85) {
            this.addInsight({
              id: `pattern-${model}-${method}`,
              pattern: `${model} performs well (${avgScore.toFixed(1)}) with ${method}`,
              impact: avgScore - 75,
              confidence: Math.min(0.9, 0.5 + scores.length * 0.05),
              applicableContexts: [method],
              learnedFrom: [],
              validated: scores.length >= 10,
            })
          }
        }
      }
    }
  }
  
  /**
   * Learn from user feedback
   */
  private learnFromFeedback(metric: QualityMetrics, feedback: UserFeedback): void {
    // Identify what worked or didn't work
    if (feedback.rating >= 4) {
      // Positive feedback - reinforce successful patterns
      this.addInsight({
        id: `feedback-positive-${metric.queryId}`,
        pattern: `Successful response using ${metric.reasoningMethod} with ${metric.modelsUsed.join(', ')}`,
        impact: 10,
        confidence: 0.7,
        applicableContexts: metric.improvements,
        learnedFrom: [metric.queryId],
        validated: true,
      })
    } else if (feedback.rating <= 2) {
      // Negative feedback - identify issues
      const issues: string[] = []
      if (!feedback.accurate) issues.push('accuracy')
      if (!feedback.complete) issues.push('completeness')
      if (!feedback.clear) issues.push('clarity')
      
      if (issues.length > 0) {
        this.createImprovementPlan(issues[0] as keyof QualityDimensions, metric)
      }
    }
  }
  
  /**
   * Add a learning insight
   */
  private addInsight(insight: LearningInsight): void {
    const existing = this.insights.findIndex(i => i.id === insight.id)
    
    if (existing >= 0) {
      // Update existing insight
      this.insights[existing] = {
        ...this.insights[existing],
        confidence: Math.min(0.95, this.insights[existing].confidence + 0.05),
        validated: insight.validated || this.insights[existing].validated,
      }
    } else {
      this.insights.push(insight)
    }
  }
  
  /**
   * Create an improvement plan for a weak dimension
   */
  private createImprovementPlan(
    dimension: keyof QualityDimensions,
    triggerMetric: QualityMetrics
  ): void {
    const existingPlan = this.improvementPlans.find(
      p => p.dimension === dimension && p.status !== 'completed'
    )
    
    if (existingPlan) return // Already have a plan
    
    const actions = this.getImprovementActions(dimension)
    
    const plan: ImprovementPlan = {
      id: `plan-${dimension}-${Date.now()}`,
      dimension,
      currentScore: triggerMetric.dimensions[dimension],
      targetScore: 85,
      actions,
      deadline: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 1 week
      status: 'planned',
    }
    
    this.improvementPlans.push(plan)
    this.saveToStorage()
  }
  
  /**
   * Get improvement actions for a dimension
   */
  private getImprovementActions(dimension: keyof QualityDimensions): ImprovementAction[] {
    const actionMap: Record<keyof QualityDimensions, ImprovementAction[]> = {
      accuracy: [
        { id: 'a1', description: 'Enable fact verification for all responses', type: 'reasoning-method', priority: 'high', expectedImpact: 15, status: 'pending' },
        { id: 'a2', description: 'Add cross-model verification', type: 'model-selection', priority: 'high', expectedImpact: 10, status: 'pending' },
        { id: 'a3', description: 'Integrate web search for current info', type: 'data-source', priority: 'medium', expectedImpact: 8, status: 'pending' },
      ],
      completeness: [
        { id: 'c1', description: 'Use structured templates with required sections', type: 'template-update', priority: 'high', expectedImpact: 12, status: 'pending' },
        { id: 'c2', description: 'Enable completeness check in post-processing', type: 'reasoning-method', priority: 'medium', expectedImpact: 8, status: 'pending' },
        { id: 'c3', description: 'Add "Did I miss anything?" self-check', type: 'prompt-tuning', priority: 'low', expectedImpact: 5, status: 'pending' },
      ],
      clarity: [
        { id: 'cl1', description: 'Add editor persona for all responses', type: 'model-selection', priority: 'high', expectedImpact: 10, status: 'pending' },
        { id: 'cl2', description: 'Enforce shorter sentence limits', type: 'output-format', priority: 'medium', expectedImpact: 8, status: 'pending' },
        { id: 'cl3', description: 'Add formatting requirements to templates', type: 'template-update', priority: 'medium', expectedImpact: 6, status: 'pending' },
      ],
      relevance: [
        { id: 'r1', description: 'Improve query analysis for better intent detection', type: 'prompt-tuning', priority: 'high', expectedImpact: 12, status: 'pending' },
        { id: 'r2', description: 'Add relevance check in response validation', type: 'reasoning-method', priority: 'medium', expectedImpact: 8, status: 'pending' },
      ],
      structure: [
        { id: 's1', description: 'Use skeleton-of-thought for complex queries', type: 'reasoning-method', priority: 'high', expectedImpact: 15, status: 'pending' },
        { id: 's2', description: 'Add required section templates', type: 'template-update', priority: 'medium', expectedImpact: 10, status: 'pending' },
      ],
      actionability: [
        { id: 'ac1', description: 'Add "Next Steps" section to templates', type: 'template-update', priority: 'high', expectedImpact: 12, status: 'pending' },
        { id: 'ac2', description: 'Extract action items in post-processing', type: 'output-format', priority: 'medium', expectedImpact: 8, status: 'pending' },
      ],
      sources: [
        { id: 'so1', description: 'Integrate web search for citations', type: 'data-source', priority: 'high', expectedImpact: 20, status: 'pending' },
        { id: 'so2', description: 'Add citation requirements to system prompt', type: 'prompt-tuning', priority: 'medium', expectedImpact: 10, status: 'pending' },
      ],
      depth: [
        { id: 'd1', description: 'Use expert complexity detection', type: 'prompt-tuning', priority: 'medium', expectedImpact: 10, status: 'pending' },
        { id: 'd2', description: 'Enable multi-pass analysis for complex queries', type: 'reasoning-method', priority: 'high', expectedImpact: 15, status: 'pending' },
      ],
    }
    
    return actionMap[dimension] || []
  }
  
  /**
   * Generate improvement recommendations
   */
  private generateRecommendations(dimensions: QualityDimensions): string[] {
    const recommendations: string[] = []
    
    // Find lowest dimensions
    const sorted = Object.entries(dimensions)
      .sort(([, a], [, b]) => a - b)
      .slice(0, 3)
    
    for (const [dim, score] of sorted) {
      if (score < 70) {
        const actions = this.getImprovementActions(dim as keyof QualityDimensions)
        if (actions.length > 0) {
          recommendations.push(`${dim}: ${actions[0].description} (expected +${actions[0].expectedImpact}%)`)
        }
      }
    }
    
    // Add insights-based recommendations
    const validatedInsights = this.insights
      .filter(i => i.validated && i.impact > 5)
      .slice(0, 2)
    
    for (const insight of validatedInsights) {
      recommendations.push(`Apply pattern: ${insight.pattern}`)
    }
    
    return recommendations
  }
  
  /**
   * Get active improvement plans
   */
  getActivePlans(): ImprovementPlan[] {
    return this.improvementPlans.filter(p => p.status !== 'completed' && p.status !== 'abandoned')
  }
  
  /**
   * Get learned insights
   */
  getInsights(): LearningInsight[] {
    return this.insights.filter(i => i.validated).sort((a, b) => b.impact - a.impact)
  }
  
  /**
   * Apply learned insights to optimize settings
   */
  getOptimizedSettings(): {
    preferredModels: Record<string, string[]>
    preferredReasoningMethods: Record<string, string>
    enabledFeatures: string[]
  } {
    const preferredModels: Record<string, string[]> = {}
    const preferredReasoningMethods: Record<string, string> = {}
    const enabledFeatures: string[] = ['fact-verification', 'quality-scoring']
    
    // Learn from high-performing patterns
    for (const insight of this.insights.filter(i => i.validated && i.impact > 10)) {
      // Parse patterns to extract recommendations
      if (insight.pattern.includes('performs well')) {
        const modelMatch = insight.pattern.match(/^(\S+) performs well/)
        const methodMatch = insight.pattern.match(/with (\S+)$/)
        
        if (modelMatch && methodMatch) {
          const model = modelMatch[1]
          const method = methodMatch[1]
          
          if (!preferredModels[method]) {
            preferredModels[method] = []
          }
          if (!preferredModels[method].includes(model)) {
            preferredModels[method].push(model)
          }
          
          preferredReasoningMethods[method] = method
        }
      }
    }
    
    return {
      preferredModels,
      preferredReasoningMethods,
      enabledFeatures,
    }
  }
}

// Singleton instance
let trackerInstance: QualityTracker | null = null

export function getQualityTracker(): QualityTracker {
  if (!trackerInstance) {
    trackerInstance = new QualityTracker()
  }
  return trackerInstance
}

