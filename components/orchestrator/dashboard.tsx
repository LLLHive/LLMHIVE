"use client"

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
} from "lucide-react"
import type { 
  EliteStrategy, 
  OrchestrationMetrics, 
  OrchestrationRunSummary,
  OrchestrationStep,
  OrchestrationPhase,
} from "@/lib/openrouter/types"

// Strategy display config
const STRATEGY_CONFIG: Record<EliteStrategy, { label: string; color: string; icon: React.ElementType }> = {
  automatic: { label: "Automatic", color: "bg-blue-500", icon: Sparkles },
  single_best: { label: "Single Best", color: "bg-green-500", icon: Zap },
  parallel_race: { label: "Parallel Race", color: "bg-yellow-500", icon: Activity },
  best_of_n: { label: "Best of N", color: "bg-purple-500", icon: Layers },
  quality_weighted_fusion: { label: "Fusion", color: "bg-orange-500", icon: Brain },
  expert_panel: { label: "Expert Panel", color: "bg-pink-500", icon: BarChart3 },
  challenge_and_refine: { label: "Challenge & Refine", color: "bg-red-500", icon: TrendingUp },
}

// Phase display config
const PHASE_CONFIG: Record<OrchestrationPhase, { label: string; color: string }> = {
  initializing: { label: "Initializing", color: "text-gray-500" },
  analyzing_query: { label: "Analyzing Query", color: "text-blue-500" },
  selecting_models: { label: "Selecting Models", color: "text-purple-500" },
  dispatching: { label: "Dispatching", color: "text-yellow-500" },
  awaiting_responses: { label: "Awaiting Responses", color: "text-orange-500" },
  verifying: { label: "Verifying", color: "text-cyan-500" },
  refining: { label: "Refining", color: "text-pink-500" },
  synthesizing: { label: "Synthesizing", color: "text-green-500" },
  completed: { label: "Completed", color: "text-emerald-500" },
  failed: { label: "Failed", color: "text-red-500" },
}

interface DashboardProps {
  metrics?: OrchestrationMetrics
  currentRun?: {
    steps: OrchestrationStep[]
    strategy: EliteStrategy
    modelsUsed: string[]
    startTime: number
  }
  onRefresh?: () => void
}

/**
 * PR6: Orchestrator Dashboard Component
 * 
 * Displays live orchestration metrics, strategy performance,
 * and current run status with real-time updates.
 */
export function OrchestratorDashboard({ metrics, currentRun, onRefresh }: DashboardProps) {
  const [activeTab, setActiveTab] = useState("overview")
  const [elapsedTime, setElapsedTime] = useState(0)

  // Update elapsed time for current run
  useEffect(() => {
    if (!currentRun) {
      setElapsedTime(0)
      return
    }

    const interval = setInterval(() => {
      setElapsedTime(Date.now() - currentRun.startTime)
    }, 100)

    return () => clearInterval(interval)
  }, [currentRun])

  // Default metrics if none provided
  const displayMetrics: OrchestrationMetrics = metrics || {
    totalRequests: 0,
    successRate: 0,
    avgLatencyMs: 0,
    avgTokens: 0,
    avgCost: 0,
    topStrategies: [],
    topModels: [],
    recentRuns: [],
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-[var(--bronze)]" />
            <CardTitle className="text-base font-medium">Orchestration Dashboard</CardTitle>
          </div>
          {currentRun && (
            <Badge variant="outline" className="gap-1 text-xs animate-pulse border-green-500/50 text-green-500">
              <span className="h-2 w-2 rounded-full bg-green-500 animate-ping" />
              Live
            </Badge>
          )}
        </div>
        <CardDescription className="text-xs">
          Real-time orchestration metrics and status
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-2">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3 h-8">
            <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
            <TabsTrigger value="strategies" className="text-xs">Strategies</TabsTrigger>
            <TabsTrigger value="history" className="text-xs">History</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="mt-3 space-y-3">
            {/* Current Run Status */}
            {currentRun && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-green-500">Current Run</span>
                  <span className="text-xs text-muted-foreground">
                    {(elapsedTime / 1000).toFixed(1)}s
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {STRATEGY_CONFIG[currentRun.strategy] && (
                    <Badge 
                      variant="secondary" 
                      className={`text-xs ${STRATEGY_CONFIG[currentRun.strategy].color} text-white`}
                    >
                      {STRATEGY_CONFIG[currentRun.strategy].label}
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {currentRun.modelsUsed.length} model{currentRun.modelsUsed.length !== 1 ? "s" : ""}
                  </span>
                </div>
                {/* Steps Progress */}
                <div className="space-y-1">
                  {currentRun.steps.slice(-3).map((step, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      {step.success === undefined ? (
                        <span className="h-1.5 w-1.5 rounded-full bg-yellow-500 animate-pulse" />
                      ) : step.success ? (
                        <CheckCircle2 className="h-3 w-3 text-green-500" />
                      ) : (
                        <XCircle className="h-3 w-3 text-red-500" />
                      )}
                      <span className={PHASE_CONFIG[step.phase]?.color || "text-muted-foreground"}>
                        {step.message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-2">
              <MetricCard
                icon={Activity}
                label="Total Requests"
                value={displayMetrics.totalRequests.toLocaleString()}
                color="text-blue-500"
              />
              <MetricCard
                icon={CheckCircle2}
                label="Success Rate"
                value={`${displayMetrics.successRate.toFixed(1)}%`}
                color="text-green-500"
              />
              <MetricCard
                icon={Clock}
                label="Avg Latency"
                value={displayMetrics.avgLatencyMs < 1000 
                  ? `${displayMetrics.avgLatencyMs.toFixed(0)}ms`
                  : `${(displayMetrics.avgLatencyMs / 1000).toFixed(1)}s`}
                color="text-yellow-500"
              />
              <MetricCard
                icon={Coins}
                label="Avg Cost"
                value={`$${displayMetrics.avgCost.toFixed(4)}`}
                color="text-purple-500"
              />
            </div>
          </TabsContent>

          {/* Strategies Tab */}
          <TabsContent value="strategies" className="mt-3">
            <ScrollArea className="h-[200px]">
              <div className="space-y-2">
                {displayMetrics.topStrategies.length > 0 ? (
                  displayMetrics.topStrategies.map((item, i) => {
                    const config = STRATEGY_CONFIG[item.strategy]
                    const maxCount = Math.max(...displayMetrics.topStrategies.map(s => s.count))
                    const percentage = maxCount > 0 ? (item.count / maxCount) * 100 : 0
                    
                    return (
                      <div key={item.strategy} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <Badge 
                              variant="secondary" 
                              className={`text-xs ${config?.color || "bg-gray-500"} text-white`}
                            >
                              {config?.label || item.strategy}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <span>{item.count} runs</span>
                            <span>•</span>
                            <span className="text-green-500">{item.avgQuality.toFixed(0)}% quality</span>
                          </div>
                        </div>
                        <Progress value={percentage} className="h-1" />
                      </div>
                    )
                  })
                ) : (
                  <div className="flex items-center justify-center h-[150px] text-xs text-muted-foreground">
                    No strategy data yet
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history" className="mt-3">
            <ScrollArea className="h-[200px]">
              <div className="space-y-2">
                {displayMetrics.recentRuns.length > 0 ? (
                  displayMetrics.recentRuns.map((run) => (
                    <RunHistoryItem key={run.id} run={run} />
                  ))
                ) : (
                  <div className="flex items-center justify-center h-[150px] text-xs text-muted-foreground">
                    No recent runs
                  </div>
                )}
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

// Run History Item Component
function RunHistoryItem({ run }: { run: OrchestrationRunSummary }) {
  const config = STRATEGY_CONFIG[run.strategy]
  
  return (
    <div className="p-2 rounded-lg bg-secondary/30 border border-border/30 space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {run.success ? (
            <CheckCircle2 className="h-3 w-3 text-green-500" />
          ) : (
            <XCircle className="h-3 w-3 text-red-500" />
          )}
          <Badge 
            variant="secondary" 
            className={`text-[10px] ${config?.color || "bg-gray-500"} text-white`}
          >
            {config?.label || run.strategy}
          </Badge>
        </div>
        <span className="text-[10px] text-muted-foreground">
          {new Date(run.timestamp).toLocaleTimeString()}
        </span>
      </div>
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <span>{run.modelsUsed.length} models</span>
        <span>{run.latencyMs}ms</span>
        <span>{run.tokens} tokens</span>
        <span>${run.cost.toFixed(4)}</span>
        {run.quality !== undefined && (
          <span className="text-green-500">{run.quality.toFixed(0)}%</span>
        )}
      </div>
    </div>
  )
}

export default OrchestratorDashboard

