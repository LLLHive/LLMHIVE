"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AlertCircle, CheckCircle2, Clock, Trophy, Zap, AlertTriangle } from "lucide-react"

interface BenchmarkResult {
  suite_name: string
  suite_version: string
  git_commit: string | null
  timestamp: string
  config: Record<string, unknown>
  systems: string[]
  results: Array<{
    case_id: string
    system: string
    run_num: number
    result: {
      answer_text: string
      latency_ms: number
      status: string
      metadata: {
        models_used: string[]
        tokens_in: number
        tokens_out: number
        strategy_used?: string
      }
    }
    score: {
      composite_score: number
      objective_score: {
        score: number
        passed: boolean
        checks: Record<string, boolean>
        details: Record<string, string>
      }
      is_critical: boolean
      critical_failed: boolean
    }
  }>
  scores: Array<{
    prompt_id: string
    system_name: string
    composite_score: number
    is_critical: boolean
    critical_failed: boolean
  }>
  aggregate: {
    total_cases: number
    systems: Record<string, {
      total_cases: number
      composite_mean: number
      composite_min: number
      composite_max: number
      objective_mean: number
      passed_count: number
      failed_count: number
      critical_failures: number
      critical_failure_ids: string[]
    }>
  }
  critical_failures: string[]
  passed: boolean
}

function formatDate(timestamp: string): string {
  // Parse timestamp like "20260106_143052"
  const match = timestamp.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/)
  if (match) {
    const [, year, month, day, hour, min, sec] = match
    return new Date(`${year}-${month}-${day}T${hour}:${min}:${sec}`).toLocaleString()
  }
  return timestamp
}

function SystemCard({ systemName, stats }: { systemName: string; stats: BenchmarkResult["aggregate"]["systems"][string] }) {
  const scorePercent = stats.composite_mean * 100
  const passRate = stats.total_cases > 0 ? (stats.passed_count / stats.total_cases) * 100 : 0

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">{systemName}</CardTitle>
          {stats.critical_failures > 0 ? (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              {stats.critical_failures} Critical
            </Badge>
          ) : (
            <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Passed
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Mean Score</span>
            <span className="font-mono font-medium">{stats.composite_mean.toFixed(3)}</span>
          </div>
          <Progress value={scorePercent} className="h-2" />
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="space-y-1">
            <span className="text-muted-foreground">Pass Rate</span>
            <div className="font-mono text-lg font-semibold text-emerald-400">
              {passRate.toFixed(1)}%
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-muted-foreground">Cases</span>
            <div className="font-mono text-lg font-semibold">
              {stats.passed_count}/{stats.total_cases}
            </div>
          </div>
        </div>
        
        <div className="flex gap-2 text-xs text-muted-foreground">
          <span>Min: {stats.composite_min.toFixed(3)}</span>
          <span>•</span>
          <span>Max: {stats.composite_max.toFixed(3)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

function CaseRow({ result }: { result: BenchmarkResult["results"][0] }) {
  const passed = result.score?.objective_score?.passed ?? false
  const isCritical = result.score?.is_critical ?? false
  const criticalFailed = result.score?.critical_failed ?? false
  
  return (
    <div className={`p-3 rounded-lg border transition-colors ${
      criticalFailed 
        ? "bg-red-950/30 border-red-500/30" 
        : passed 
          ? "bg-emerald-950/20 border-emerald-500/20" 
          : "bg-amber-950/20 border-amber-500/20"
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {criticalFailed ? (
            <AlertCircle className="h-4 w-4 text-red-400" />
          ) : passed ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          )}
          <span className="font-mono text-sm font-medium">{result.case_id}</span>
          {isCritical && (
            <Badge variant="outline" className="text-xs">Critical</Badge>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">
            <Clock className="h-3 w-3 inline mr-1" />
            {result.result.latency_ms.toFixed(0)}ms
          </span>
          <span className="font-mono font-medium">
            {(result.score?.composite_score ?? 0).toFixed(3)}
          </span>
        </div>
      </div>
      
      {!passed && result.score?.objective_score?.details && (
        <div className="mt-2 text-xs text-muted-foreground">
          {Object.entries(result.score.objective_score.details).map(([key, value]) => (
            <div key={key} className="truncate">
              <span className="text-red-400">{key}:</span> {value}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function BenchmarksPage() {
  const [report, setReport] = useState<BenchmarkResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Check if admin benchmarks is enabled
  const isEnabled = process.env.NEXT_PUBLIC_ADMIN_BENCHMARKS_ENABLED === "true" ||
                    process.env.NODE_ENV === "development"
  
  useEffect(() => {
    if (!isEnabled) {
      setLoading(false)
      return
    }
    
    async function fetchReport() {
      try {
        const res = await fetch("/api/admin/benchmarks/latest")
        if (!res.ok) {
          if (res.status === 404) {
            setError("No benchmark reports found. Run a benchmark first.")
          } else {
            throw new Error(`Failed to fetch: ${res.statusText}`)
          }
          return
        }
        const data = await res.json()
        setReport(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load benchmark report")
      } finally {
        setLoading(false)
      }
    }
    
    fetchReport()
  }, [isEnabled])
  
  if (!isEnabled) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Benchmarks Disabled</CardTitle>
            <CardDescription>
              Benchmark viewer is only available in development mode or when
              NEXT_PUBLIC_ADMIN_BENCHMARKS_ENABLED is set to &quot;true&quot;.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="text-muted-foreground">Loading benchmark report...</p>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-400" />
              No Report Available
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Run the benchmark CLI to generate a report:
            </p>
            <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-x-auto">
              python scripts/run_benchmarks.py --systems llmhive
            </pre>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  if (!report) {
    return null
  }
  
  const systemNames = Object.keys(report.aggregate.systems)
  
  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{report.suite_name}</h1>
            <p className="text-muted-foreground mt-1">
              v{report.suite_version} • {formatDate(report.timestamp)}
              {report.git_commit && (
                <span className="ml-2 font-mono text-xs bg-muted px-2 py-0.5 rounded">
                  {report.git_commit}
                </span>
              )}
            </p>
          </div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
            report.passed 
              ? "bg-emerald-500/20 text-emerald-400" 
              : "bg-red-500/20 text-red-400"
          }`}>
            {report.passed ? (
              <>
                <Trophy className="h-5 w-5" />
                <span className="font-semibold">PASSED</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-5 w-5" />
                <span className="font-semibold">FAILED</span>
              </>
            )}
          </div>
        </div>
        
        {report.critical_failures.length > 0 && (
          <div className="bg-red-950/30 border border-red-500/30 rounded-lg p-4 mb-4">
            <h3 className="font-semibold text-red-400 mb-2">Critical Failures</h3>
            <div className="flex flex-wrap gap-2">
              {report.critical_failures.map((id) => (
                <Badge key={id} variant="destructive">{id}</Badge>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* System Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {systemNames.map((name) => (
          <SystemCard 
            key={name} 
            systemName={name} 
            stats={report.aggregate.systems[name]} 
          />
        ))}
      </div>
      
      {/* Detailed Results */}
      <Tabs defaultValue={systemNames[0]} className="space-y-4">
        <TabsList className="w-full justify-start">
          {systemNames.map((name) => (
            <TabsTrigger key={name} value={name} className="gap-2">
              <Zap className="h-4 w-4" />
              {name}
            </TabsTrigger>
          ))}
        </TabsList>
        
        {systemNames.map((systemName) => {
          const systemResults = report.results.filter(r => r.system === systemName)
          
          // Group by category
          const byCategory: Record<string, typeof systemResults> = {}
          systemResults.forEach((r) => {
            const cat = r.case_id.split("_")[0]
            if (!byCategory[cat]) byCategory[cat] = []
            byCategory[cat].push(r)
          })
          
          return (
            <TabsContent key={systemName} value={systemName}>
              <Card>
                <CardHeader>
                  <CardTitle>Results: {systemName}</CardTitle>
                  <CardDescription>
                    {systemResults.length} cases evaluated
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[600px] pr-4">
                    <div className="space-y-6">
                      {Object.entries(byCategory).map(([category, results]) => (
                        <div key={category}>
                          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                            {category}
                          </h3>
                          <div className="space-y-2">
                            {results.map((r) => (
                              <CaseRow key={`${r.case_id}-${r.run_num}`} result={r} />
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}

