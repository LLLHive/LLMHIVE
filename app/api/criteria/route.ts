import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

/**
 * API route for persisting and retrieving dynamic criteria equaliser settings.
 * 
 * Settings are stored per user using cookies for persistence across serverless cold starts.
 */

const CRITERIA_COOKIE_NAME = "llmhive-criteria"
const MAX_COOKIE_AGE = 60 * 60 * 24 * 365 // 1 year

interface CriteriaSettings {
  accuracy: number
  speed: number
  creativity: number
}

const DEFAULT_CRITERIA: CriteriaSettings = {
  accuracy: 70,
  speed: 70,
  creativity: 50,
}

async function getCriteriaFromCookie(userId: string): Promise<CriteriaSettings> {
  try {
    const cookieStore = await cookies()
    const cookie = cookieStore.get(`${CRITERIA_COOKIE_NAME}-${userId}`)
    
    if (cookie?.value) {
      return JSON.parse(decodeURIComponent(cookie.value))
    }
  } catch (error) {
    console.warn("[criteria] Failed to read cookie:", error)
  }
  
  return DEFAULT_CRITERIA
}

async function saveCriteriaToCookie(userId: string, criteria: CriteriaSettings): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(`${CRITERIA_COOKIE_NAME}-${userId}`, encodeURIComponent(JSON.stringify(criteria)), {
    maxAge: MAX_COOKIE_AGE,
    path: "/",
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
  })
}

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams
    const userId = searchParams.get("userId") || "default"

    const settings = await getCriteriaFromCookie(userId)

    return NextResponse.json({
      success: true,
      settings,
    })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to retrieve criteria settings"
    console.error("[criteria] GET error:", error)
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    )
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { userId = "default", accuracy, speed, creativity } = body

    // Validate input
    if (typeof accuracy !== "number" || accuracy < 0 || accuracy > 100) {
      return NextResponse.json(
        { success: false, error: "Invalid accuracy value (must be 0-100)" },
        { status: 400 }
      )
    }
    if (typeof speed !== "number" || speed < 0 || speed > 100) {
      return NextResponse.json(
        { success: false, error: "Invalid speed value (must be 0-100)" },
        { status: 400 }
      )
    }
    if (typeof creativity !== "number" || creativity < 0 || creativity > 100) {
      return NextResponse.json(
        { success: false, error: "Invalid creativity value (must be 0-100)" },
        { status: 400 }
      )
    }

    const criteria: CriteriaSettings = { accuracy, speed, creativity }
    await saveCriteriaToCookie(userId, criteria)

    return NextResponse.json({
      success: true,
      message: "Criteria settings saved successfully",
      settings: criteria,
    })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to save criteria settings"
    console.error("[criteria] POST error:", error)
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    )
  }
}

