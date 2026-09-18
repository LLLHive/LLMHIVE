/**
 * Daily cron: remind Standard trial users ~1 day before expiry.
 *
 * Calls Cloud Run admin endpoint which queries Firestore trialing subs,
 * resolves Stripe customer email, and sends the $10/mo continue email.
 *
 * Auth: CRON_SECRET via Authorization Bearer or x-vercel-cron-secret.
 */
import { NextRequest, NextResponse } from "next/server"

export const runtime = "nodejs"
export const maxDuration = 60

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
const CRON_SECRET = process.env.CRON_SECRET

export async function GET(req: NextRequest) {
  return run(req)
}

export async function POST(req: NextRequest) {
  return run(req)
}

async function run(req: NextRequest) {
  const authHeader = req.headers.get("authorization")
  const cronHeader = req.headers.get("x-vercel-cron-secret")

  if (CRON_SECRET) {
    const provided = authHeader?.replace(/^Bearer\s+/i, "") || cronHeader
    if (provided !== CRON_SECRET) {
      console.warn("[Cron] Unauthorized trial-expiry-reminders attempt")
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }
  }

  const dryRun = req.nextUrl.searchParams.get("dry_run") === "true"
  const url = new URL(`${BACKEND_URL}/api/v1/admin/trial-expiry-reminders`)
  if (dryRun) url.searchParams.set("dry_run", "true")

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Cron-Secret": CRON_SECRET || "",
      },
    })

    const text = await response.text()
    let data: Record<string, unknown> = {}
    try {
      data = text ? JSON.parse(text) : {}
    } catch {
      data = { raw: text.slice(0, 500) }
    }

    if (!response.ok) {
      console.error("[Cron] trial-expiry-reminders backend error", response.status, data)
      return NextResponse.json(
        {
          success: false,
          status: response.status,
          ...data,
          timestamp: new Date().toISOString(),
        },
        { status: 502 },
      )
    }

    console.log("[Cron] trial-expiry-reminders complete", data)
    return NextResponse.json({
      success: true,
      ...data,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error("[Cron] trial-expiry-reminders failed", error)
    return NextResponse.json(
      {
        success: false,
        error: String(error),
        timestamp: new Date().toISOString(),
      },
      { status: 500 },
    )
  }
}
