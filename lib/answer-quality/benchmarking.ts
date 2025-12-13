/**
 * Benchmarking & A/B Testing Infrastructure
 * 
 * Measures and compares response quality across configurations,
 * models, and features to continuously improve answer quality.
 */

import type { QualityDimensions } from './types'

export interface Benchmark {
  id: string
  name: string
  description: string
  testCases: TestCase[]
  expectedMetrics: ExpectedMetrics
  created: Date
  lastRun?: Date
}

export interface TestCase {
  id: string
  query: string
  expectedElements: string[]
  requiredFormat?: string
  domain: string
  complexity: 'simple' | 'moderate' | 'complex' | 'expert'
  goldenResponse?: string
  evaluationCriteria: EvaluationCriterion[]
}

export interface EvaluationCriterion {
  name: string
  type: 'contains' | 'not-contains' | 'format' | 'length' | 'custom'
  value: string | number | RegExp
  weight: number
}

export interface ExpectedMetrics {
  minOverallScore: number
  minDimensions: Partial<QualityDimensions>
  maxLatency: number
}

export interface BenchmarkResult {
  benchmarkId: string
  timestamp: Date
  configuration: TestConfiguration
  results: TestCaseResult[]
  aggregateScore: number
  dimensionScores: QualityDimensions
  latencyStats: LatencyStats
  passRate: number
  improvements: string[]
  regressions: string[]
}

export interface TestConfiguration {
  id: string
  name: string
  models: string[]
  reasoningMethod: string
  features: string[]
  parameters: Record<string, unknown>
}

export interface TestCaseResult {
  testCaseId: string
  passed: boolean
  score: number
  dimensions: QualityDimensions
  response: string
  latency: number
  criteriaResults: { criterion: string; passed: boolean; details?: string }[]
}

export interface LatencyStats {
  mean: number
  median: number
  p90: number
  p95: number
  max: number
}

export interface ABTest {
  id: string
  name: string
  description: string
  status: 'draft' | 'running' | 'completed' | 'cancelled'
  controlConfig: TestConfiguration
  treatmentConfig: TestConfiguration
  sampleSize: number
  currentSamples: number
  results: ABTestResults | null
  startDate?: Date
  endDate?: Date
}

export interface ABTestResults {
  controlScore: number
  treatmentScore: number
  improvement: number
  confidenceLevel: number
  winner: 'control' | 'treatment' | 'inconclusive'
  dimensionComparison: {
    dimension: keyof QualityDimensions
    control: number
    treatment: number
    difference: number
  }[]
}

// Storage keys
const BENCHMARKS_KEY = 'llmhive-benchmarks'
const AB_TESTS_KEY = 'llmhive-ab-tests'
const RESULTS_KEY = 'llmhive-benchmark-results'

// Pre-defined benchmarks
export const STANDARD_BENCHMARKS: Benchmark[] = [
  {
    id: 'factual-accuracy',
    name: 'Factual Accuracy',
    description: 'Tests accuracy of factual responses',
    testCases: [
      {
        id: 'fa1',
        query: 'What is the speed of light in a vacuum?',
        expectedElements: ['299,792,458', 'meters per second', 'c'],
        domain: 'science',
        complexity: 'simple',
        evaluationCriteria: [
          { name: 'Contains speed value', type: 'contains', value: '299', weight: 0.4 },
          { name: 'Contains unit', type: 'contains', value: 'meter', weight: 0.3 },
          { name: 'Not too long', type: 'length', value: 500, weight: 0.1 },
        ],
      },
      {
        id: 'fa2',
        query: 'When was the Declaration of Independence signed?',
        expectedElements: ['1776', 'July', '4th', 'Philadelphia'],
        domain: 'history',
        complexity: 'simple',
        evaluationCriteria: [
          { name: 'Contains year', type: 'contains', value: '1776', weight: 0.5 },
          { name: 'Contains date', type: 'contains', value: 'July', weight: 0.3 },
        ],
      },
    ],
    expectedMetrics: {
      minOverallScore: 85,
      minDimensions: { accuracy: 90, relevance: 85 },
      maxLatency: 5000,
    },
    created: new Date(),
  },
  {
    id: 'code-quality',
    name: 'Code Quality',
    description: 'Tests quality of code generation',
    testCases: [
      {
        id: 'cq1',
        query: 'Write a Python function to check if a number is prime.',
        expectedElements: ['def', 'prime', 'return', 'True', 'False'],
        requiredFormat: 'code',
        domain: 'technology',
        complexity: 'moderate',
        evaluationCriteria: [
          { name: 'Has function definition', type: 'contains', value: 'def ', weight: 0.3 },
          { name: 'Has code block', type: 'format', value: '```', weight: 0.3 },
          { name: 'Has return statement', type: 'contains', value: 'return', weight: 0.2 },
        ],
      },
      {
        id: 'cq2',
        query: 'Write a JavaScript function to debounce another function.',
        expectedElements: ['function', 'setTimeout', 'clearTimeout'],
        requiredFormat: 'code',
        domain: 'technology',
        complexity: 'complex',
        evaluationCriteria: [
          { name: 'Has setTimeout', type: 'contains', value: 'setTimeout', weight: 0.4 },
          { name: 'Has code block', type: 'format', value: '```', weight: 0.3 },
        ],
      },
    ],
    expectedMetrics: {
      minOverallScore: 80,
      minDimensions: { accuracy: 85, structure: 80, actionability: 75 },
      maxLatency: 8000,
    },
    created: new Date(),
  },
  {
    id: 'analysis-depth',
    name: 'Analysis Depth',
    description: 'Tests depth of analytical responses',
    testCases: [
      {
        id: 'ad1',
        query: 'Analyze the pros and cons of microservices architecture.',
        expectedElements: ['scalability', 'complexity', 'deployment', 'testing'],
        domain: 'technology',
        complexity: 'complex',
        evaluationCriteria: [
          { name: 'Has pros section', type: 'contains', value: /pros|advantages|benefits/i, weight: 0.2 },
          { name: 'Has cons section', type: 'contains', value: /cons|disadvantages|drawbacks/i, weight: 0.2 },
          { name: 'Mentions scalability', type: 'contains', value: 'scalab', weight: 0.2 },
          { name: 'Sufficient length', type: 'length', value: 300, weight: 0.2 },
        ],
      },
    ],
    expectedMetrics: {
      minOverallScore: 75,
      minDimensions: { depth: 80, completeness: 75, structure: 70 },
      maxLatency: 10000,
    },
    created: new Date(),
  },
]

/**
 * Benchmark Runner
 */
export class BenchmarkRunner {
  private benchmarks: Benchmark[] = []
  private results: BenchmarkResult[] = []
  private abTests: ABTest[] = []
  
  constructor() {
    this.loadData()
  }
  
  private loadData(): void {
    if (typeof window === 'undefined') return
    
    try {
      const benchmarksJson = localStorage.getItem(BENCHMARKS_KEY)
      if (benchmarksJson) {
        this.benchmarks = JSON.parse(benchmarksJson)
      } else {
        this.benchmarks = STANDARD_BENCHMARKS
      }
      
      const resultsJson = localStorage.getItem(RESULTS_KEY)
      if (resultsJson) {
        this.results = JSON.parse(resultsJson)
      }
      
      const abTestsJson = localStorage.getItem(AB_TESTS_KEY)
      if (abTestsJson) {
        this.abTests = JSON.parse(abTestsJson)
      }
    } catch (error) {
      console.error('Error loading benchmark data:', error)
    }
  }
  
  private saveData(): void {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem(BENCHMARKS_KEY, JSON.stringify(this.benchmarks))
      localStorage.setItem(RESULTS_KEY, JSON.stringify(this.results.slice(-100)))
      localStorage.setItem(AB_TESTS_KEY, JSON.stringify(this.abTests))
    } catch (error) {
      console.error('Error saving benchmark data:', error)
    }
  }
  
  /**
   * Run a benchmark suite
   */
  async runBenchmark(
    benchmarkId: string,
    configuration: TestConfiguration,
    generateResponse: (query: string, config: TestConfiguration) => Promise<{ response: string; latency: number }>
  ): Promise<BenchmarkResult> {
    const benchmark = this.benchmarks.find(b => b.id === benchmarkId)
    if (!benchmark) {
      throw new Error(`Benchmark ${benchmarkId} not found`)
    }
    
    const results: TestCaseResult[] = []
    const latencies: number[] = []
    
    for (const testCase of benchmark.testCases) {
      const result = await this.runTestCase(testCase, configuration, generateResponse)
      results.push(result)
      latencies.push(result.latency)
    }
    
    // Calculate aggregate metrics
    const aggregateScore = results.reduce((sum, r) => sum + r.score, 0) / results.length
    const passRate = results.filter(r => r.passed).length / results.length
    
    const dimensionScores = this.aggregateDimensions(results.map(r => r.dimensions))
    const latencyStats = this.calculateLatencyStats(latencies)
    
    // Compare with previous results
    const previousResult = this.results
      .filter(r => r.benchmarkId === benchmarkId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]
    
    const improvements: string[] = []
    const regressions: string[] = []
    
    if (previousResult) {
      for (const [dim, score] of Object.entries(dimensionScores)) {
        const prevScore = previousResult.dimensionScores[dim as keyof QualityDimensions]
        if (prevScore !== undefined) {
          if (score > prevScore + 5) {
            improvements.push(`${dim}: +${(score - prevScore).toFixed(1)}`)
          } else if (score < prevScore - 5) {
            regressions.push(`${dim}: ${(score - prevScore).toFixed(1)}`)
          }
        }
      }
    }
    
    const benchmarkResult: BenchmarkResult = {
      benchmarkId,
      timestamp: new Date(),
      configuration,
      results,
      aggregateScore,
      dimensionScores,
      latencyStats,
      passRate,
      improvements,
      regressions,
    }
    
    // Update benchmark lastRun
    benchmark.lastRun = new Date()
    
    // Save results
    this.results.push(benchmarkResult)
    this.saveData()
    
    return benchmarkResult
  }
  
  /**
   * Run a single test case
   */
  private async runTestCase(
    testCase: TestCase,
    configuration: TestConfiguration,
    generateResponse: (query: string, config: TestConfiguration) => Promise<{ response: string; latency: number }>
  ): Promise<TestCaseResult> {
    const { response, latency } = await generateResponse(testCase.query, configuration)
    
    // Evaluate criteria
    const criteriaResults = testCase.evaluationCriteria.map(criterion => {
      const passed = this.evaluateCriterion(response, criterion)
      return {
        criterion: criterion.name,
        passed,
        details: passed ? undefined : `Failed: ${criterion.name}`,
      }
    })
    
    // Calculate score
    let score = 0
    let totalWeight = 0
    
    for (let i = 0; i < testCase.evaluationCriteria.length; i++) {
      const criterion = testCase.evaluationCriteria[i]
      totalWeight += criterion.weight
      if (criteriaResults[i].passed) {
        score += criterion.weight * 100
      }
    }
    
    score = totalWeight > 0 ? score / totalWeight : 0
    
    // Calculate dimensions (simplified)
    const dimensions = this.estimateDimensions(response, testCase)
    
    // Determine pass/fail
    const passed = score >= 70 && criteriaResults.filter(c => !c.passed).length < testCase.evaluationCriteria.length / 2
    
    return {
      testCaseId: testCase.id,
      passed,
      score,
      dimensions,
      response,
      latency,
      criteriaResults,
    }
  }
  
  /**
   * Evaluate a single criterion
   */
  private evaluateCriterion(
    response: string,
    criterion: EvaluationCriterion
  ): boolean {
    switch (criterion.type) {
      case 'contains':
        if (criterion.value instanceof RegExp) {
          return criterion.value.test(response)
        }
        return response.toLowerCase().includes(String(criterion.value).toLowerCase())
      
      case 'not-contains':
        return !response.toLowerCase().includes(String(criterion.value).toLowerCase())
      
      case 'format':
        return response.includes(String(criterion.value))
      
      case 'length':
        return response.length >= Number(criterion.value)
      
      default:
        return true
    }
  }
  
  /**
   * Estimate quality dimensions from response
   */
  private estimateDimensions(response: string, testCase: TestCase): QualityDimensions {
    // Simplified dimension estimation
    const wordCount = response.split(/\s+/).length
    
    return {
      accuracy: testCase.expectedElements.filter(e => 
        response.toLowerCase().includes(e.toLowerCase())
      ).length / testCase.expectedElements.length * 100,
      completeness: Math.min(100, wordCount / 3),
      clarity: 70 + (response.includes('\n') ? 10 : 0) + (response.includes('##') ? 10 : 0),
      relevance: 80, // Would need query analysis
      structure: /^#+\s|^\d+\.|^[-•*]/m.test(response) ? 85 : 65,
      actionability: /should|must|can|try|use/i.test(response) ? 80 : 60,
      sources: /\[\d+\]|source:|according to/i.test(response) ? 80 : 30,
      depth: Math.min(100, 50 + wordCount / 10),
    }
  }
  
  /**
   * Aggregate dimensions from multiple results
   */
  private aggregateDimensions(dimensions: QualityDimensions[]): QualityDimensions {
    const result: QualityDimensions = {
      accuracy: 0, completeness: 0, clarity: 0, relevance: 0,
      structure: 0, actionability: 0, sources: 0, depth: 0,
    }
    
    for (const dim of dimensions) {
      for (const key of Object.keys(result) as (keyof QualityDimensions)[]) {
        result[key] += dim[key]
      }
    }
    
    for (const key of Object.keys(result) as (keyof QualityDimensions)[]) {
      result[key] /= dimensions.length
    }
    
    return result
  }
  
  /**
   * Calculate latency statistics
   */
  private calculateLatencyStats(latencies: number[]): LatencyStats {
    const sorted = [...latencies].sort((a, b) => a - b)
    const n = sorted.length
    
    return {
      mean: latencies.reduce((a, b) => a + b, 0) / n,
      median: sorted[Math.floor(n / 2)],
      p90: sorted[Math.floor(n * 0.9)],
      p95: sorted[Math.floor(n * 0.95)],
      max: sorted[n - 1],
    }
  }
  
  /**
   * Create an A/B test
   */
  createABTest(
    name: string,
    description: string,
    controlConfig: TestConfiguration,
    treatmentConfig: TestConfiguration,
    sampleSize: number = 100
  ): ABTest {
    const test: ABTest = {
      id: `ab-${Date.now()}`,
      name,
      description,
      status: 'draft',
      controlConfig,
      treatmentConfig,
      sampleSize,
      currentSamples: 0,
      results: null,
    }
    
    this.abTests.push(test)
    this.saveData()
    
    return test
  }
  
  /**
   * Record an A/B test sample
   */
  recordABSample(
    testId: string,
    variant: 'control' | 'treatment',
    score: number,
    dimensions: QualityDimensions
  ): void {
    const test = this.abTests.find(t => t.id === testId)
    if (!test || test.status !== 'running') return
    
    // Store samples (simplified - in production use proper storage)
    const key = `ab-samples-${testId}`
    const stored = localStorage.getItem(key)
    const samples = stored ? JSON.parse(stored) : { control: [], treatment: [] }
    
    samples[variant].push({ score, dimensions })
    localStorage.setItem(key, JSON.stringify(samples))
    
    test.currentSamples = samples.control.length + samples.treatment.length
    
    // Check if test is complete
    if (test.currentSamples >= test.sampleSize * 2) {
      this.completeABTest(testId)
    }
    
    this.saveData()
  }
  
  /**
   * Complete an A/B test and calculate results
   */
  completeABTest(testId: string): ABTestResults | null {
    const test = this.abTests.find(t => t.id === testId)
    if (!test) return null
    
    const key = `ab-samples-${testId}`
    const stored = localStorage.getItem(key)
    if (!stored) return null
    
    const samples = JSON.parse(stored)
    
    const controlScore = samples.control.reduce((sum: number, s: { score: number }) => sum + s.score, 0) / samples.control.length
    const treatmentScore = samples.treatment.reduce((sum: number, s: { score: number }) => sum + s.score, 0) / samples.treatment.length
    
    const improvement = ((treatmentScore - controlScore) / controlScore) * 100
    
    // Simplified confidence calculation (would use proper stats in production)
    const n = Math.min(samples.control.length, samples.treatment.length)
    const confidenceLevel = Math.min(0.99, 0.5 + (n / test.sampleSize) * 0.4)
    
    let winner: 'control' | 'treatment' | 'inconclusive' = 'inconclusive'
    if (Math.abs(improvement) > 5 && confidenceLevel > 0.9) {
      winner = improvement > 0 ? 'treatment' : 'control'
    }
    
    // Calculate dimension comparison
    const dimensionComparison: ABTestResults['dimensionComparison'] = []
    const dims: (keyof QualityDimensions)[] = [
      'accuracy', 'completeness', 'clarity', 'relevance',
      'structure', 'actionability', 'sources', 'depth'
    ]
    
    for (const dim of dims) {
      const controlDim = samples.control.reduce((sum: number, s: { dimensions: QualityDimensions }) => sum + s.dimensions[dim], 0) / samples.control.length
      const treatmentDim = samples.treatment.reduce((sum: number, s: { dimensions: QualityDimensions }) => sum + s.dimensions[dim], 0) / samples.treatment.length
      
      dimensionComparison.push({
        dimension: dim,
        control: controlDim,
        treatment: treatmentDim,
        difference: treatmentDim - controlDim,
      })
    }
    
    const results: ABTestResults = {
      controlScore,
      treatmentScore,
      improvement,
      confidenceLevel,
      winner,
      dimensionComparison,
    }
    
    test.results = results
    test.status = 'completed'
    test.endDate = new Date()
    
    this.saveData()
    
    return results
  }
  
  /**
   * Get benchmark results history
   */
  getResultsHistory(benchmarkId: string, limit: number = 10): BenchmarkResult[] {
    return this.results
      .filter(r => r.benchmarkId === benchmarkId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, limit)
  }
  
  /**
   * Get all benchmarks
   */
  getBenchmarks(): Benchmark[] {
    return this.benchmarks
  }
  
  /**
   * Get active A/B tests
   */
  getActiveABTests(): ABTest[] {
    return this.abTests.filter(t => t.status === 'running')
  }
  
  /**
   * Compare configurations
   */
  compareConfigurations(
    results1: BenchmarkResult,
    results2: BenchmarkResult
  ): {
    winner: 1 | 2 | 0
    scoreDiff: number
    dimensionDiffs: { dimension: string; diff: number }[]
  } {
    const scoreDiff = results1.aggregateScore - results2.aggregateScore
    
    const dimensionDiffs = (Object.keys(results1.dimensionScores) as (keyof QualityDimensions)[])
      .map(dim => ({
        dimension: dim,
        diff: results1.dimensionScores[dim] - results2.dimensionScores[dim],
      }))
      .sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))
    
    let winner: 1 | 2 | 0 = 0
    if (scoreDiff > 5) winner = 1
    else if (scoreDiff < -5) winner = 2
    
    return { winner, scoreDiff, dimensionDiffs }
  }
}

// Singleton instance
let benchmarkInstance: BenchmarkRunner | null = null

export function getBenchmarkRunner(): BenchmarkRunner {
  if (!benchmarkInstance) {
    benchmarkInstance = new BenchmarkRunner()
  }
  return benchmarkInstance
}

