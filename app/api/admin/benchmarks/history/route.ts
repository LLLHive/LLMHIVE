import { NextResponse } from "next/server"
import { readdir, readFile } from "fs/promises"
import { join } from "path"

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
    systems: Record<string, {
      composite_mean: number
      passed_count: number
      failed_count: number
      critical_failures: number
      latency_p50: number
      latency_p95: number
    }>
  }
}

interface BenchmarkHistory {
  runs: BenchmarkRun[]
  trend: {
    system: string
    scores: { timestamp: string; score: number }[]
  }[]
}

export async function GET() {
  // Only enabled in development or when explicitly enabled
  if (
    process.env.NODE_ENV !== "development" &&
    process.env.ADMIN_BENCHMARKS_ENABLED !== "true"
  ) {
    return NextResponse.json(
      { error: "Benchmark history is disabled" },
      { status: 403 }
    )
  }

  try {
    const artifactsDir = join(process.cwd(), "artifacts", "benchmarks")
    
    let dirs: string[]
    try {
      dirs = await readdir(artifactsDir)
    } catch {
      return NextResponse.json({
        runs: [],
        trend: [],
      })
    }

    // Sort directories by name (timestamp) descending
    dirs.sort().reverse()

    const runs: BenchmarkRun[] = []
    const systemScores: Record<string, { timestamp: string; score: number }[]> = {}

    // Load up to last 30 runs
    for (const dir of dirs.slice(0, 30)) {
      const reportPath = join(artifactsDir, dir, "report.json")
      
      try {
        const content = await readFile(reportPath, "utf-8")
        const report = JSON.parse(content)
        
        runs.push({
          suite_name: report.suite_name || "Unknown",
          suite_version: report.suite_version || "?",
          git_commit: report.git_commit || "",
          timestamp: report.timestamp || dir,
          systems: report.systems || [],
          passed: report.passed ?? true,
          critical_failures: report.critical_failures || [],
          aggregate: report.aggregate || { total_cases: 0, systems: {} },
        })

        // Collect trend data
        const systems = report.aggregate?.systems || {}
        for (const [systemName, stats] of Object.entries(systems)) {
          if (!systemScores[systemName]) {
            systemScores[systemName] = []
          }
          systemScores[systemName].push({
            timestamp: report.timestamp || dir,
            score: (stats as { composite_mean: number }).composite_mean || 0,
          })
        }
      } catch {
        // Skip invalid reports
        continue
      }
    }

    // Build trend data
    const trend = Object.entries(systemScores).map(([system, scores]) => ({
      system,
      scores: scores.reverse(), // Oldest first for charting
    }))

    const history: BenchmarkHistory = { runs, trend }
    
    return NextResponse.json(history)
  } catch (error) {
    console.error("Error loading benchmark history:", error)
    return NextResponse.json(
      { error: "Failed to load benchmark history" },
      { status: 500 }
    )
  }
}

