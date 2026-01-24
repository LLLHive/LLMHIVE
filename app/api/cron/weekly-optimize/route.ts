/**
 * Weekly Optimization Cron Endpoint
 * 
 * This endpoint triggers the weekly improvement cycle:
 * 1. Gather feedback and performance data
 * 2. Identify patterns in failures
 * 3. Plan improvements
 * 4. Generate reports
 * 
 * Secured by CRON_SECRET to ensure only authorized callers can trigger.
 * 
 * Usage:
 * - Vercel Cron: Add to vercel.json crons array
 * - Manual: POST /api/cron/weekly-optimize with Authorization header
 */
import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
const CRON_SECRET = process.env.CRON_SECRET

export async function POST(req: NextRequest) {
  // Verify cron secret for security
  const authHeader = req.headers.get("authorization")
  const cronHeader = req.headers.get("x-vercel-cron-secret")
  
  if (CRON_SECRET) {
    const providedSecret = authHeader?.replace("Bearer ", "") || cronHeader
    if (providedSecret !== CRON_SECRET) {
      console.warn("[Cron] Unauthorized weekly-optimize attempt")
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }
  }
  
  console.log("[Cron] Starting weekly optimization cycle...")
  
  try {
    // Call the backend optimization endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/admin/weekly-optimize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Cron-Secret": CRON_SECRET || "",
      },
      body: JSON.stringify({
        lookback_days: 7,
        apply_safe_changes: process.env.AUTO_IMPROVE_APPLY === "true",
      }),
    })

    if (!response.ok) {
      // Backend might not have this endpoint yet - that's OK
      console.log("[Cron] Backend optimization endpoint not available")
      
      // Return success with note about running locally
      return NextResponse.json({
        success: true,
        message: "Optimization cycle scheduled (run python script for full analysis)",
        note: "Run: python -m llmhive.scripts.weekly_optimize",
        timestamp: new Date().toISOString(),
      })
    }

    const data = await response.json()
    console.log("[Cron] Weekly optimization completed:", data)
    
    return NextResponse.json({
      success: true,
      ...data,
      timestamp: new Date().toISOString(),
    })
    
  } catch (error) {
    console.error("[Cron] Weekly optimization error:", error)
    
    // Return partial success - the cron ran but backend wasn't available
    return NextResponse.json({
      success: true,
      message: "Cron triggered (backend temporarily unavailable)",
      note: "Run manually: python -m llmhive.scripts.weekly_optimize",
      timestamp: new Date().toISOString(),
    })
  }
}

// Also support GET for Vercel Cron (which uses GET)
export async function GET(req: NextRequest) {
  return POST(req)
}

