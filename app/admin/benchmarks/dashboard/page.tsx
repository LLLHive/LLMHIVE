"use client"

import { useState, useEffect } from "react"
import Link from "next/link"

interface BenchmarkRun {
  suite_name: string
  suite_version: string
  git_commit: string
  timestamp: string
  systems: string[]
  passed: boolean
  critical_failures: string[]
  aggregate: {
    total_cases: number
    systems: {
      [key: string]: {
        composite_mean: number
        passed_count: number
        failed_count: number
        critical_failures: number
        latency_p50: number
        latency_p95: number
      }
    }
  }
}

interface BenchmarkHistory {
  runs: BenchmarkRun[]
  trend: {
    system: string
    scores: { timestamp: string; score: number }[]
  }[]
}

export default function BenchmarkDashboard() {
  const [history, setHistory] = useState<BenchmarkHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSystem, setSelectedSystem] = useState<string>("LLMHive")
  
  useEffect(() => {
    async function loadHistory() {
      try {
        const res = await fetch("/api/admin/benchmarks/history")
        if (!res.ok) {
          throw new Error(`Failed to load: ${res.status}`)
        }
        const data = await res.json()
        setHistory(data)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error")
      } finally {
        setLoading(false)
      }
    }
    loadHistory()
  }, [])
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Benchmark Dashboard</h1>
          <div className="animate-pulse">
            <div className="h-64 bg-gray-800 rounded-lg mb-4" />
            <div className="h-96 bg-gray-800 rounded-lg" />
          </div>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Benchmark Dashboard</h1>
          <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-red-400">Error Loading Dashboard</h2>
            <p className="text-gray-300 mt-2">{error}</p>
            <p className="text-gray-400 mt-4 text-sm">
              Run a benchmark first: <code className="bg-gray-800 px-2 py-1 rounded">python scripts/run_benchmarks.py --systems llmhive</code>
            </p>
          </div>
        </div>
      </div>
    )
  }
  
  if (!history || history.runs.length === 0) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Benchmark Dashboard</h1>
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-8 text-center">
            <h2 className="text-xl font-semibold mb-4">No Benchmark Data</h2>
            <p className="text-gray-400 mb-6">Run your first benchmark to populate this dashboard.</p>
            <code className="bg-gray-800 px-4 py-2 rounded block max-w-xl mx-auto text-sm">
              python scripts/run_benchmarks.py --systems llmhive --mode local
            </code>
          </div>
        </div>
      </div>
    )
  }
  
  const latestRun = history.runs[0]
  const systemNames = Object.keys(latestRun.aggregate?.systems || {})
  const selectedStats = latestRun.aggregate?.systems[selectedSystem]
  
  // Calculate trend data
  const trendData = history.trend?.find(t => t.system === selectedSystem)?.scores || []
  
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Benchmark Dashboard</h1>
            <p className="text-gray-400 mt-1">
              Track LLMHive performance over time
            </p>
          </div>
          <Link 
            href="/admin/benchmarks"
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
          >
            View Latest Report →
          </Link>
        </div>
        
        {/* Status Banner */}
        <div className={`mb-8 p-4 rounded-lg border ${
          latestRun.passed 
            ? "bg-green-900/20 border-green-500" 
            : "bg-red-900/20 border-red-500"
        }`}>
          <div className="flex items-center gap-3">
            <span className={`text-2xl ${latestRun.passed ? "text-green-400" : "text-red-400"}`}>
              {latestRun.passed ? "✓" : "✗"}
            </span>
            <div>
              <h2 className={`font-semibold ${latestRun.passed ? "text-green-400" : "text-red-400"}`}>
                Latest Run: {latestRun.passed ? "PASSED" : "FAILED"}
              </h2>
              <p className="text-gray-400 text-sm">
                {latestRun.suite_name} v{latestRun.suite_version} • {latestRun.timestamp} • 
                <code className="ml-1 text-gray-500">{latestRun.git_commit?.slice(0, 7)}</code>
              </p>
            </div>
          </div>
        </div>
        
        {/* System Selector */}
        <div className="flex gap-2 mb-6">
          {systemNames.map(name => (
            <button
              key={name}
              onClick={() => setSelectedSystem(name)}
              className={`px-4 py-2 rounded-lg transition ${
                selectedSystem === name
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {name}
            </button>
          ))}
        </div>
        
        {/* Stats Cards */}
        {selectedStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              title="Composite Score"
              value={`${(selectedStats.composite_mean * 100).toFixed(1)}%`}
              subtitle="Mean across all prompts"
              trend={calculateTrend(trendData)}
            />
            <StatCard
              title="Pass Rate"
              value={`${selectedStats.passed_count}/${selectedStats.passed_count + selectedStats.failed_count}`}
              subtitle={`${((selectedStats.passed_count / (selectedStats.passed_count + selectedStats.failed_count)) * 100).toFixed(0)}% passed`}
            />
            <StatCard
              title="Critical Failures"
              value={`${selectedStats.critical_failures}`}
              subtitle={selectedStats.critical_failures > 0 ? "Action required!" : "All clear"}
              isAlert={selectedStats.critical_failures > 0}
            />
            <StatCard
              title="Latency (p50)"
              value={`${selectedStats.latency_p50?.toFixed(0) || '-'}ms`}
              subtitle={`p95: ${selectedStats.latency_p95?.toFixed(0) || '-'}ms`}
            />
          </div>
        )}
        
        {/* Trend Chart (Simple ASCII for now) */}
        <div className="bg-gray-900 rounded-lg p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4">Score Trend</h3>
          {trendData.length > 1 ? (
            <div className="h-48 flex items-end gap-1">
              {trendData.slice(-20).map((point, i) => (
                <div
                  key={i}
                  className="flex-1 bg-blue-600 rounded-t transition-all hover:bg-blue-500"
                  style={{ height: `${point.score * 100}%` }}
                  title={`${point.timestamp}: ${(point.score * 100).toFixed(1)}%`}
                />
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              Run more benchmarks to see trend data
            </p>
          )}
        </div>
        
        {/* Critical Failures */}
        {latestRun.critical_failures.length > 0 && (
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6 mb-8">
            <h3 className="text-lg font-semibold text-red-400 mb-4">
              ⚠️ Critical Failures ({latestRun.critical_failures.length})
            </h3>
            <ul className="space-y-2">
              {latestRun.critical_failures.map(id => (
                <li key={id} className="flex items-center gap-2">
                  <span className="text-red-400">✗</span>
                  <code className="bg-gray-800 px-2 py-1 rounded text-sm">{id}</code>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Recent Runs */}
        <div className="bg-gray-900 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Runs</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left py-2 px-4">Timestamp</th>
                  <th className="text-left py-2 px-4">Suite</th>
                  <th className="text-left py-2 px-4">Systems</th>
                  <th className="text-left py-2 px-4">Status</th>
                  <th className="text-left py-2 px-4">Score</th>
                </tr>
              </thead>
              <tbody>
                {history.runs.slice(0, 10).map((run, i) => {
                  const llmhiveStats = run.aggregate?.systems["LLMHive"]
                  return (
                    <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/50">
                      <td className="py-2 px-4 font-mono text-xs">{run.timestamp}</td>
                      <td className="py-2 px-4">{run.suite_name}</td>
                      <td className="py-2 px-4">{run.systems?.join(", ")}</td>
                      <td className="py-2 px-4">
                        <span className={run.passed ? "text-green-400" : "text-red-400"}>
                          {run.passed ? "✓ Passed" : "✗ Failed"}
                        </span>
                      </td>
                      <td className="py-2 px-4">
                        {llmhiveStats ? `${(llmhiveStats.composite_mean * 100).toFixed(1)}%` : "-"}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ 
  title, 
  value, 
  subtitle, 
  trend, 
  isAlert 
}: { 
  title: string
  value: string
  subtitle: string
  trend?: { direction: "up" | "down" | "stable", delta: number } | null
  isAlert?: boolean
}) {
  return (
    <div className={`bg-gray-900 rounded-lg p-4 border ${
      isAlert ? "border-red-500" : "border-gray-800"
    }`}>
      <p className="text-gray-400 text-sm">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${isAlert ? "text-red-400" : "text-white"}`}>
        {value}
        {trend && (
          <span className={`text-sm ml-2 ${
            trend.direction === "up" ? "text-green-400" : 
            trend.direction === "down" ? "text-red-400" : 
            "text-gray-500"
          }`}>
            {trend.direction === "up" ? "↑" : trend.direction === "down" ? "↓" : "→"}
            {Math.abs(trend.delta * 100).toFixed(1)}%
          </span>
        )}
      </p>
      <p className="text-gray-500 text-xs mt-1">{subtitle}</p>
    </div>
  )
}

function calculateTrend(data: { timestamp: string; score: number }[]): { direction: "up" | "down" | "stable", delta: number } | null {
  if (data.length < 2) return null
  
  const latest = data[data.length - 1].score
  const previous = data[data.length - 2].score
  const delta = latest - previous
  
  if (Math.abs(delta) < 0.01) return { direction: "stable", delta: 0 }
  return {
    direction: delta > 0 ? "up" : "down",
    delta
  }
}

