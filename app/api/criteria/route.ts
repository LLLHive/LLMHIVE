import { NextRequest, NextResponse } from "next/server"

/**
 * API route for persisting and retrieving dynamic criteria equaliser settings.
 * 
 * Settings are stored per user and can be retrieved to apply to orchestrator behavior.
 * 
 * Environment variables:
 * - DATABASE_URL: Connection string for database (if using database storage)
 * - REDIS_URL: Connection string for Redis (if using Redis storage)
 * 
 * TODO: Implement actual database/Redis storage. Currently uses in-memory storage.
 */

// In-memory storage (replace with database/Redis in production)
const criteriaStorage = new Map<string, { accuracy: number; speed: number; creativity: number }>()

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams
    const userId = searchParams.get("userId") || "default"

    // Retrieve criteria settings for user
    const settings = criteriaStorage.get(userId) || {
      accuracy: 70,
      speed: 70,
      creativity: 50,
    }

    return NextResponse.json({
      success: true,
      settings,
    })
  } catch (error: any) {
    console.error("[criteria] GET error:", error)
    return NextResponse.json(
      { success: false, error: error.message || "Failed to retrieve criteria settings" },
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

    // Store criteria settings
    criteriaStorage.set(userId, { accuracy, speed, creativity })

    // TODO: Persist to database/Redis
    // Example:
    // await db.criteria.upsert({
    //   where: { userId },
    //   update: { accuracy, speed, creativity },
    //   create: { userId, accuracy, speed, creativity },
    // })

    return NextResponse.json({
      success: true,
      message: "Criteria settings saved successfully",
      settings: { accuracy, speed, creativity },
    })
  } catch (error: any) {
    console.error("[criteria] POST error:", error)
    return NextResponse.json(
      { success: false, error: error.message || "Failed to save criteria settings" },
      { status: 500 }
    )
  }
}

