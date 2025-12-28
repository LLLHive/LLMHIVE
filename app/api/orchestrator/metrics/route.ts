import { NextRequest, NextResponse } from "next/server"
import * as fs from "fs"
import * as path from "path"
import * as os from "os"

/**
 * API Endpoint: /api/orchestrator/metrics
 * 
 * Returns aggregated telemetry metrics for the orchestrator dashboard.
 * Reads from:
 * 1. JSONL trace file (LLMHIVE_TRACE_PATH env var or logs/orchestrator_trace.jsonl)
 * 2. Performance tracker JSON files (~/.llmhive/strategy_metrics.json)
 * 
 * Query params:
 * - range: "1h" | "24h" | "7d" | "30d" (default: "24h")
 */

interface TraceEvent {
  event?: string
  reasoning_method?: string
  strategy?: string
  strategy_source?: string
  fallback?: string | null
  confidence?: string
  timestamp?: string
  selected_pipeline?: string
  technique_ids?: string[]
  latency_ms?: number
  fallback_used?: boolean
  tool_calls?: Array<{
    tool_name: string
    ok: boolean
    latency_ms?: number
  }>
  classification?: {
    reasoning_type?: string
    risk_level?: string
    domain?: string
  }
}

interface StrategyOutcome {
  timestamp: string
  strategy: string
  task_type: string
  domain: string
  primary_model: string
  all_models_used: string[]
  model_roles: Record<string, string>
  success: boolean
  quality_score: number
  latency_ms: number
  total_tokens: number
  refinement_iterations: number
}

interface StrategyMetric {
  strategy: string
  count: number
  successRate: number
  avgLatencyMs: number
  avgCost: number
  avgQuality: number
}

interface ModelMetric {
  modelId: string
  count: number
  successRate: number
  avgLatencyMs: number
  avgCost: number
  roles: string[]
}

interface ToolMetric {
  tool: string
  count: number
  successRate: number
  avgLatencyMs: number
}

interface OrchestratorMetrics {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  avgLatencyMs: number
  avgCost: number
  totalCost: number
  avgTokens: number
  totalTokens: number
  strategies: StrategyMetric[]
  models: ModelMetric[]
  tools: ToolMetric[]
  verificationTriggers: number
  refinementLoops: number
  budgetExceeded: number
  lastUpdated: string
}

function parseTimeRange(range: string): number {
  const now = Date.now()
  switch (range) {
    case "1h":
      return now - 60 * 60 * 1000
    case "24h":
      return now - 24 * 60 * 60 * 1000
    case "7d":
      return now - 7 * 24 * 60 * 60 * 1000
    case "30d":
      return now - 30 * 24 * 60 * 60 * 1000
    default:
      return now - 24 * 60 * 60 * 1000
  }
}

function readJSONLFile(filePath: string, cutoffTime: number): TraceEvent[] {
  const events: TraceEvent[] = []
  
  if (!fs.existsSync(filePath)) {
    return events
  }

  try {
    const content = fs.readFileSync(filePath, "utf-8")
    const lines = content.split("\n").filter((line) => line.trim())
    
    for (const line of lines) {
      try {
        const event = JSON.parse(line) as TraceEvent
        if (event.timestamp) {
          const eventTime = new Date(event.timestamp).getTime()
          if (eventTime >= cutoffTime) {
            events.push(event)
          }
        }
      } catch {
        // Skip invalid JSON lines
      }
    }
  } catch {
    // File read error
  }

  return events
}

function readStrategyMetrics(cutoffTime: number): StrategyOutcome[] {
  const outcomes: StrategyOutcome[] = []
  const strategyFile = path.join(os.homedir(), ".llmhive", "strategy_metrics.json")

  if (!fs.existsSync(strategyFile)) {
    return outcomes
  }

  try {
    const content = fs.readFileSync(strategyFile, "utf-8")
    const data = JSON.parse(content)
    
    if (data.outcomes && Array.isArray(data.outcomes)) {
      for (const outcome of data.outcomes) {
        if (outcome.timestamp) {
          const eventTime = new Date(outcome.timestamp).getTime()
          if (eventTime >= cutoffTime) {
            outcomes.push(outcome as StrategyOutcome)
          }
        }
      }
    }
  } catch {
    // File read error
  }

  return outcomes
}

function aggregateMetrics(
  traceEvents: TraceEvent[],
  strategyOutcomes: StrategyOutcome[]
): OrchestratorMetrics {
  // Combine trace events and strategy outcomes for comprehensive metrics
  const strategyAgg: Record<string, {
    count: number
    success: number
    latencySum: number
    qualitySum: number
  }> = {}

  const modelAgg: Record<string, {
    count: number
    success: number
    latencySum: number
    roles: Set<string>
  }> = {}

  const toolAgg: Record<string, {
    count: number
    success: number
    latencySum: number
  }> = {}

  let totalRequests = 0
  let successfulRequests = 0
  let totalLatency = 0
  let totalTokens = 0
  let verificationTriggers = 0
  let refinementLoops = 0
  let budgetExceeded = 0

  // Process trace events
  for (const event of traceEvents) {
    if (event.event === "strategy_selected" || event.event === "fallback_used") {
      const strategy = event.reasoning_method || event.strategy || "unknown"
      
      if (!strategyAgg[strategy]) {
        strategyAgg[strategy] = { count: 0, success: 0, latencySum: 0, qualitySum: 0 }
      }
      strategyAgg[strategy].count++
      
      // Assume success unless explicitly marked as fallback
      if (event.event !== "fallback_used") {
        strategyAgg[strategy].success++
      }
      
      if (event.confidence === "high") {
        strategyAgg[strategy].qualitySum += 0.9
      } else if (event.confidence === "medium") {
        strategyAgg[strategy].qualitySum += 0.7
      } else {
        strategyAgg[strategy].qualitySum += 0.5
      }

      if (event.fallback_used) {
        verificationTriggers++
      }
    }

    if (event.event === "pipeline_execution") {
      totalRequests++
      
      const pipeline = event.selected_pipeline || "unknown"
      if (!strategyAgg[pipeline]) {
        strategyAgg[pipeline] = { count: 0, success: 0, latencySum: 0, qualitySum: 0 }
      }
      strategyAgg[pipeline].count++
      
      if (event.latency_ms) {
        strategyAgg[pipeline].latencySum += event.latency_ms
        totalLatency += event.latency_ms
      }
      
      if (!event.fallback_used) {
        strategyAgg[pipeline].success++
        successfulRequests++
      }

      // Process tool calls
      if (event.tool_calls) {
        for (const tc of event.tool_calls) {
          const toolName = tc.tool_name || "unknown"
          if (!toolAgg[toolName]) {
            toolAgg[toolName] = { count: 0, success: 0, latencySum: 0 }
          }
          toolAgg[toolName].count++
          if (tc.ok !== false) {
            toolAgg[toolName].success++
          }
          if (tc.latency_ms) {
            toolAgg[toolName].latencySum += tc.latency_ms
          }
        }
      }
    }
  }

  // Process strategy outcomes from performance tracker
  for (const outcome of strategyOutcomes) {
    const strategy = outcome.strategy || "unknown"
    
    if (!strategyAgg[strategy]) {
      strategyAgg[strategy] = { count: 0, success: 0, latencySum: 0, qualitySum: 0 }
    }
    strategyAgg[strategy].count++
    if (outcome.success) {
      strategyAgg[strategy].success++
    }
    strategyAgg[strategy].latencySum += outcome.latency_ms || 0
    strategyAgg[strategy].qualitySum += outcome.quality_score || 0

    // Track models
    for (const model of outcome.all_models_used || []) {
      if (!modelAgg[model]) {
        modelAgg[model] = { count: 0, success: 0, latencySum: 0, roles: new Set() }
      }
      modelAgg[model].count++
      if (outcome.success) {
        modelAgg[model].success++
      }
      modelAgg[model].latencySum += (outcome.latency_ms || 0) / (outcome.all_models_used?.length || 1)
      
      if (outcome.model_roles && outcome.model_roles[model]) {
        modelAgg[model].roles.add(outcome.model_roles[model])
      }
      if (model === outcome.primary_model) {
        modelAgg[model].roles.add("primary")
      }
    }

    // Track totals
    totalRequests++
    if (outcome.success) {
      successfulRequests++
    }
    totalLatency += outcome.latency_ms || 0
    totalTokens += outcome.total_tokens || 0
    refinementLoops += outcome.refinement_iterations || 0
  }

  // Convert aggregations to arrays
  const strategies: StrategyMetric[] = Object.entries(strategyAgg)
    .map(([strategy, agg]) => ({
      strategy,
      count: agg.count,
      successRate: agg.count > 0 ? agg.success / agg.count : 0,
      avgLatencyMs: agg.count > 0 ? agg.latencySum / agg.count : 0,
      avgCost: 0.01 * (agg.count > 0 ? agg.latencySum / agg.count / 1000 : 0), // Estimate
      avgQuality: agg.count > 0 ? agg.qualitySum / agg.count : 0,
    }))
    .sort((a, b) => b.count - a.count)

  const models: ModelMetric[] = Object.entries(modelAgg)
    .map(([modelId, agg]) => ({
      modelId,
      count: agg.count,
      successRate: agg.count > 0 ? agg.success / agg.count : 0,
      avgLatencyMs: agg.count > 0 ? agg.latencySum / agg.count : 0,
      avgCost: 0.005 * agg.count, // Estimate
      roles: Array.from(agg.roles),
    }))
    .sort((a, b) => b.count - a.count)

  const tools: ToolMetric[] = Object.entries(toolAgg)
    .map(([tool, agg]) => ({
      tool,
      count: agg.count,
      successRate: agg.count > 0 ? agg.success / agg.count : 0,
      avgLatencyMs: agg.count > 0 ? agg.latencySum / agg.count : 0,
    }))
    .sort((a, b) => b.count - a.count)

  const failedRequests = totalRequests - successfulRequests
  const avgLatencyMs = totalRequests > 0 ? totalLatency / totalRequests : 0
  const avgTokens = totalRequests > 0 ? totalTokens / totalRequests : 0
  const avgCost = avgLatencyMs * 0.00001 // Rough estimate
  const totalCost = avgCost * totalRequests

  return {
    totalRequests,
    successfulRequests,
    failedRequests,
    avgLatencyMs,
    avgCost,
    totalCost,
    avgTokens,
    totalTokens,
    strategies,
    models,
    tools,
    verificationTriggers,
    refinementLoops,
    budgetExceeded,
    lastUpdated: new Date().toISOString(),
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const range = searchParams.get("range") || "24h"
    const cutoffTime = parseTimeRange(range)

    // Read trace events from JSONL file
    const traceFile = process.env.LLMHIVE_TRACE_PATH || 
      path.join(process.cwd(), "logs", "orchestrator_trace.jsonl")
    const traceEvents = readJSONLFile(traceFile, cutoffTime)

    // Read strategy outcomes from performance tracker
    const strategyOutcomes = readStrategyMetrics(cutoffTime)

    // Aggregate metrics
    const metrics = aggregateMetrics(traceEvents, strategyOutcomes)

    return NextResponse.json(metrics)
  } catch (error) {
    console.error("Failed to fetch orchestrator metrics:", error)
    
    // Return empty metrics on error
    return NextResponse.json({
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      avgLatencyMs: 0,
      avgCost: 0,
      totalCost: 0,
      avgTokens: 0,
      totalTokens: 0,
      strategies: [],
      models: [],
      tools: [],
      verificationTriggers: 0,
      refinementLoops: 0,
      budgetExceeded: 0,
      lastUpdated: new Date().toISOString(),
    })
  }
}

