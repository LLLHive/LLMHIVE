/**
 * Feedback Analytics API
 *
 * Provides aggregated feedback statistics for the admin dashboard.
 */
import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/admin/auth"
import {
  generateMockAnalytics,
  normalizeFeedbackAnalytics,
} from "@/lib/analytics/normalize-feedback-stats"

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

export async function GET(req: NextRequest) {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const { userId } = authResult
  const searchParams = req.nextUrl.searchParams
  const days = parseInt(searchParams.get("days") || "30", 10)

  const fallback = () => generateMockAnalytics(days)

  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/rlhf/feedback/stats?days=${days}`, {
      headers: {
        "X-User-Id": userId,
      },
      next: { revalidate: 60 },
    })

    if (response.ok) {
      const raw = await response.json()
      const normalized = normalizeFeedbackAnalytics(raw, days, fallback)
      return NextResponse.json(normalized)
    }
  } catch (error) {
    console.error("[Analytics] Error fetching feedback stats:", error)
  }

  return NextResponse.json(fallback())
}
