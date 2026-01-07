import { NextResponse } from "next/server"
import * as fs from "fs"
import * as path from "path"

/**
 * API route to fetch the latest benchmark report.
 * 
 * This route:
 * 1. Scans the artifacts/benchmarks directory for report.json files
 * 2. Returns the most recent one based on directory timestamp
 * 
 * Only available in development or when ADMIN_BENCHMARKS_ENABLED is true.
 */

export async function GET() {
  // Check if admin benchmarks is enabled
  const isEnabled = process.env.ADMIN_BENCHMARKS_ENABLED === "true" ||
                    process.env.NODE_ENV === "development"
  
  if (!isEnabled) {
    return NextResponse.json(
      { error: "Benchmarks admin is not enabled" },
      { status: 403 }
    )
  }
  
  try {
    // Look for benchmark artifacts
    const artifactsDir = path.join(process.cwd(), "artifacts", "benchmarks")
    
    if (!fs.existsSync(artifactsDir)) {
      return NextResponse.json(
        { error: "No benchmark artifacts directory found" },
        { status: 404 }
      )
    }
    
    // Get all subdirectories (each benchmark run creates a timestamped directory)
    const entries = fs.readdirSync(artifactsDir, { withFileTypes: true })
    const dirs = entries
      .filter(e => e.isDirectory())
      .map(e => e.name)
      .sort()
      .reverse() // Most recent first
    
    // Find the first directory with a report.json
    for (const dir of dirs) {
      const reportPath = path.join(artifactsDir, dir, "report.json")
      
      if (fs.existsSync(reportPath)) {
        const reportContent = fs.readFileSync(reportPath, "utf-8")
        const report = JSON.parse(reportContent)
        
        return NextResponse.json(report)
      }
    }
    
    return NextResponse.json(
      { error: "No benchmark reports found" },
      { status: 404 }
    )
    
  } catch (error) {
    console.error("[Benchmarks API] Error:", error)
    return NextResponse.json(
      { error: "Failed to load benchmark report" },
      { status: 500 }
    )
  }
}

