"use client"

/**
 * PR8: Orchestrator Metrics Dashboard
 * 
 * Displays aggregated telemetry data for orchestration:
 * - Strategy usage distribution
 * - Model performance metrics
 * - Cost analysis
 * - Success/failure rates
 * - Tool usage statistics
 */

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { 
  Activity, 
  Zap, 
  Clock, 
  Coins, 
  TrendingUp, 
  CheckCircle2, 
  XCircle, 
  Brain,
  Layers,
  BarChart3,
  Sparkles,
  RefreshCw,
  Search,
  Calculator,
  Code,
  FileText,
  AlertTriangle,
  Trophy,
  Target,
} from "lucide-react"
import type { EliteStrategy } from "@/lib/openrouter/types"

// Strategy configuration for display
const STRATEGY_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  // Classic strategies
  automatic: { label: "Automatic", color: "bg-blue-500", icon: Sparkles },
  single_best: { label: "Single Best", color: "bg-green-500", icon: Zap },
  parallel_race: { label: "Parallel Race", color: "bg-yellow-500", icon: Activity },
  best_of_n: { label: "Best of N", color: "bg-purple-500", icon: Layers },
  quality_weighted_fusion: { label: "Fusion", color: "bg-orange-500", icon: Brain },
  expert_panel: { label: "Expert Panel", color: "bg-pink-500", icon: BarChart3 },
  challenge_and_refine: { label: "Challenge & Refine", color: "bg-red-500", icon: TrendingUp },
  
  // KB Pipeline strategies
  PIPELINE_BASELINE_SINGLECALL: { label: "Baseline", color: "bg-gray-500", icon: Zap },
  PIPELINE_MATH_REASONING: { label: "Math Reasoning", color: "bg-blue-600", icon: Calculator },
  PIPELINE_TOOL_USE_REACT: { label: "Tool Use (ReAct)", color: "bg-green-600", icon: Search },
  PIPELINE_SELF_REFINE: { label: "Self Refine", color: "bg-yellow-600", icon: TrendingUp },
  PIPELINE_RAG: { label: "RAG", color: "bg-purple-600", icon: FileText },
  PIPELINE_MULTIAGENT_DEBATE: { label: "Multi-Agent Debate", color: "bg-red-600", icon: Brain },
  PIPELINE_ENSEMBLE_PANEL: { label: "Ensemble Panel", color: "bg-pink-600", icon: Layers },
  PIPELINE_CHALLENGE_REFINE: { label: "Challenge & Refine", color: "bg-orange-600", icon: TrendingUp },
  PIPELINE_CODING_AGENT: { label: "Coding Agent", color: "bg-cyan-600", icon: Code },
  PIPELINE_COST_OPTIMIZED_ROUTING: { label: "Cost Optimized", color: "bg-emerald-600", icon: Coins },
  
  // Reasoning methods from trace
  chain_of_thought: { label: "Chain of Thought", color: "bg-indigo-500", icon: Brain },
  self_consistency: { label: "Self Consistency", color: "bg-violet-500", icon: Layers },
  tree_of_thoughts: { label: "Tree of Thoughts", color: "bg-teal-500", icon: BarChart3 },
  reflexion: { label: "Reflexion", color: "bg-amber-500", icon: TrendingUp },
  debate: { label: "Debate", color: "bg-rose-500", icon: Brain },
}

// Tool configuration
const TOOL_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  web_search: { label: "Web Search", icon: Search, color: "text-blue-500" },
  calculator: { label: "Calculator", icon: Calculator, color: "text-green-500" },
  code_execution: { label: "Code Exec", icon: Code, color: "text-purple-500" },
  rag_retrieval: { label: "RAG", icon: FileText, color: "text-orange-500" },
}

// Metrics types
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

// Mock data for development (will be replaced with API call)
const MOCK_METRICS: OrchestratorMetrics = {
  totalRequests: 1234,
  successfulRequests: 1189,
  failedRequests: 45,
  avgLatencyMs: 2450,
  avgCost: 0.0123,
  totalCost: 15.18,
  avgTokens: 1850,
  totalTokens: 2282900,
  strategies: [
    { strategy: "automatic", count: 456, successRate: 0.97, avgLatencyMs: 2100, avgCost: 0.012, avgQuality: 0.88 },
    { strategy: "single_best", count: 312, successRate: 0.95, avgLatencyMs: 1500, avgCost: 0.008, avgQuality: 0.82 },
    { strategy: "parallel_race", count: 198, successRate: 0.96, avgLatencyMs: 2800, avgCost: 0.018, avgQuality: 0.91 },
    { strategy: "quality_weighted_fusion", count: 156, successRate: 0.98, avgLatencyMs: 3500, avgCost: 0.025, avgQuality: 0.94 },
    { strategy: "challenge_and_refine", count: 112, successRate: 0.99, avgLatencyMs: 4200, avgCost: 0.032, avgQuality: 0.96 },
  ],
  models: [
    { modelId: "gpt-4o", count: 523, successRate: 0.97, avgLatencyMs: 2200, avgCost: 0.015, roles: ["primary", "validator"] },
    { modelId: "claude-sonnet-4", count: 412, successRate: 0.96, avgLatencyMs: 2400, avgCost: 0.018, roles: ["primary", "validator"] },
    { modelId: "deepseek-chat", count: 298, successRate: 0.94, avgLatencyMs: 1800, avgCost: 0.003, roles: ["primary", "specialist"] },
    { modelId: "gemini-2.5-pro", count: 187, successRate: 0.95, avgLatencyMs: 2600, avgCost: 0.008, roles: ["primary", "validator"] },
    { modelId: "gpt-4o-mini", count: 156, successRate: 0.93, avgLatencyMs: 1200, avgCost: 0.001, roles: ["fallback", "validator"] },
  ],
  tools: [
    { tool: "web_search", count: 234, successRate: 0.92, avgLatencyMs: 1500 },
    { tool: "calculator", count: 89, successRate: 0.99, avgLatencyMs: 100 },
    { tool: "code_execution", count: 67, successRate: 0.88, avgLatencyMs: 2000 },
    { tool: "rag_retrieval", count: 45, successRate: 0.95, avgLatencyMs: 800 },
  ],
  verificationTriggers: 156,
  refinementLoops: 89,
  budgetExceeded: 12,
  lastUpdated: new Date().toISOString(),
}

interface OrchestratorMetricsDashboardProps {
  className?: string
  refreshInterval?: number // ms, 0 to disable
}

export function OrchestratorMetricsDashboard({
  className,
  refreshInterval = 30000,
}: OrchestratorMetricsDashboardProps) {
  const [metrics, setMetrics] = useState<OrchestratorMetrics>(MOCK_METRICS)
  const [loading, setLoading] = useState(false)
  const [timeRange, setTimeRange] = useState<"1h" | "24h" | "7d" | "30d">("24h")
  const [activeTab, setActiveTab] = useState("overview")

  // Fetch metrics from real API
  const fetchMetrics = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/orchestrator/metrics?range=${timeRange}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      
      // If no data yet, fall back to mock for demo purposes
      if (data.totalRequests === 0 && data.strategies.length === 0) {
        // Use mock data when no real data available
        setMetrics({
          ...MOCK_METRICS,
          lastUpdated: new Date().toISOString(),
        })
      } else {
        setMetrics(data)
      }
    } catch (error) {
      console.error("Failed to fetch metrics:", error)
      // Fall back to mock data on error
      setMetrics({
        ...MOCK_METRICS,
        lastUpdated: new Date().toISOString(),
      })
    } finally {
      setLoading(false)
    }
  }

  // Auto-refresh
  useEffect(() => {
    if (refreshInterval > 0) {
      const interval = setInterval(fetchMetrics, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [refreshInterval, timeRange])

  // Calculate derived metrics
  const successRate = metrics.totalRequests > 0 
    ? (metrics.successfulRequests / metrics.totalRequests) * 100 
    : 0

  // Find top strategy
  const topStrategy = metrics.strategies.reduce((prev, curr) => 
    curr.count > prev.count ? curr : prev, metrics.strategies[0])

  // Find most used model
  const topModel = metrics.models.reduce((prev, curr) =>
    curr.count > prev.count ? curr : prev, metrics.models[0])

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[var(--bronze)]" />
            <CardTitle className="text-lg font-semibold">Orchestrator Metrics</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Select value={timeRange} onValueChange={(v) => setTimeRange(v as any)}>
              <SelectTrigger className="h-8 w-24 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1h">1 Hour</SelectItem>
                <SelectItem value="24h">24 Hours</SelectItem>
                <SelectItem value="7d">7 Days</SelectItem>
                <SelectItem value="30d">30 Days</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={fetchMetrics}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
        <CardDescription className="text-xs">
          Last updated: {new Date(metrics.lastUpdated).toLocaleTimeString()}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-2">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4 h-8">
            <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
            <TabsTrigger value="strategies" className="text-xs">Strategies</TabsTrigger>
            <TabsTrigger value="models" className="text-xs">Models</TabsTrigger>
            <TabsTrigger value="tools" className="text-xs">Tools</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="mt-3 space-y-3">
            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <MetricCard
                icon={Activity}
                label="Total Requests"
                value={metrics.totalRequests.toLocaleString()}
                color="text-blue-500"
              />
              <MetricCard
                icon={CheckCircle2}
                label="Success Rate"
                value={`${successRate.toFixed(1)}%`}
                color="text-green-500"
              />
              <MetricCard
                icon={Clock}
                label="Avg Latency"
                value={`${(metrics.avgLatencyMs / 1000).toFixed(1)}s`}
                color="text-yellow-500"
              />
              <MetricCard
                icon={Coins}
                label="Total Cost"
                value={`$${metrics.totalCost.toFixed(2)}`}
                color="text-purple-500"
              />
            </div>

            {/* Top Performers */}
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Trophy className="h-3 w-3 text-yellow-500" />
                  Top Strategy
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={`${STRATEGY_CONFIG[topStrategy?.strategy]?.color || "bg-gray-500"} text-white text-xs`}>
                    {STRATEGY_CONFIG[topStrategy?.strategy]?.label || topStrategy?.strategy}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {topStrategy?.count} uses
                  </span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Target className="h-3 w-3 text-blue-500" />
                  Top Model
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {topModel?.modelId}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {topModel?.count} uses
                  </span>
                </div>
              </div>
            </div>

            {/* Quality Indicators */}
            <div className="grid grid-cols-3 gap-2">
              <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-center">
                <div className="text-lg font-bold text-cyan-500">{metrics.verificationTriggers}</div>
                <div className="text-[10px] text-muted-foreground">Verifications</div>
              </div>
              <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-center">
                <div className="text-lg font-bold text-purple-500">{metrics.refinementLoops}</div>
                <div className="text-[10px] text-muted-foreground">Refinements</div>
              </div>
              <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-center">
                <div className="text-lg font-bold text-red-500">{metrics.budgetExceeded}</div>
                <div className="text-[10px] text-muted-foreground">Budget Exceeded</div>
              </div>
            </div>
          </TabsContent>

          {/* Strategies Tab */}
          <TabsContent value="strategies" className="mt-3">
            <ScrollArea className="h-[250px]">
              <div className="space-y-2">
                {metrics.strategies.map((strategy) => {
                  const config = STRATEGY_CONFIG[strategy.strategy]
                  const maxCount = Math.max(...metrics.strategies.map(s => s.count))
                  const percentage = (strategy.count / maxCount) * 100
                  
                  return (
                    <div key={strategy.strategy} className="p-2 rounded-lg bg-secondary/30 border border-border/30">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Badge className={`${config?.color || "bg-gray-500"} text-white text-[10px]`}>
                            {config?.label || strategy.strategy}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {strategy.count} requests
                          </span>
                        </div>
                        <div className="text-xs text-green-500">
                          {(strategy.successRate * 100).toFixed(0)}% success
                        </div>
                      </div>
                      <Progress value={percentage} className="h-1 mb-1" />
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>Latency: {(strategy.avgLatencyMs / 1000).toFixed(1)}s</span>
                        <span>Cost: ${strategy.avgCost.toFixed(3)}</span>
                        <span>Quality: {(strategy.avgQuality * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Models Tab */}
          <TabsContent value="models" className="mt-3">
            <ScrollArea className="h-[250px]">
              <div className="space-y-2">
                {metrics.models.map((model) => {
                  const maxCount = Math.max(...metrics.models.map(m => m.count))
                  const percentage = (model.count / maxCount) * 100
                  
                  return (
                    <div key={model.modelId} className="p-2 rounded-lg bg-secondary/30 border border-border/30">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium">{model.modelId}</span>
                          {model.roles.map(role => (
                            <Badge key={role} variant="outline" className="text-[8px] h-4">
                              {role}
                            </Badge>
                          ))}
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {model.count} uses
                        </span>
                      </div>
                      <Progress value={percentage} className="h-1 mb-1" />
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        <span className="text-green-500">{(model.successRate * 100).toFixed(0)}%</span>
                        <span>{(model.avgLatencyMs / 1000).toFixed(1)}s</span>
                        <span>${model.avgCost.toFixed(4)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Tools Tab */}
          <TabsContent value="tools" className="mt-3">
            <ScrollArea className="h-[250px]">
              <div className="space-y-2">
                {metrics.tools.map((tool) => {
                  const config = TOOL_CONFIG[tool.tool]
                  const Icon = config?.icon || Zap
                  const maxCount = Math.max(...metrics.tools.map(t => t.count))
                  const percentage = (tool.count / maxCount) * 100
                  
                  return (
                    <div key={tool.tool} className="p-2 rounded-lg bg-secondary/30 border border-border/30">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Icon className={`h-4 w-4 ${config?.color || "text-gray-500"}`} />
                          <span className="text-xs font-medium">{config?.label || tool.tool}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{tool.count} calls</span>
                          <Badge 
                            variant="secondary" 
                            className={`text-[10px] ${tool.successRate >= 0.95 ? "text-green-500" : "text-yellow-500"}`}
                          >
                            {(tool.successRate * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      </div>
                      <Progress value={percentage} className="h-1 mb-1" />
                      <div className="text-[10px] text-muted-foreground">
                        Avg latency: {tool.avgLatencyMs}ms
                      </div>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

// Metric Card Component
function MetricCard({ 
  icon: Icon, 
  label, 
  value, 
  color 
}: { 
  icon: React.ElementType
  label: string
  value: string
  color: string
}) {
  return (
    <div className="p-2 rounded-lg bg-secondary/50 border border-border/50">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className={`h-3 w-3 ${color}`} />
        <span className="text-[10px] text-muted-foreground">{label}</span>
      </div>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  )
}

export default OrchestratorMetricsDashboard

