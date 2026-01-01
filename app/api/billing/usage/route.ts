import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

export async function GET() {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    // Call backend to get usage data
    const response = await fetch(`${BACKEND_URL}/api/v1/billing/usage/${userId}`, {
      headers: {
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })

    if (!response.ok) {
      // Return default free tier limits if error
      return NextResponse.json({
        requests: { used: 0, limit: 100 },
        tokens: { used: 0, limit: 100000 },
      })
    }

    const data = await response.json()
    
    return NextResponse.json({
      requests: {
        used: data.requests_used || data.requests?.used || 0,
        limit: data.requests_limit || data.requests?.limit || 100,
      },
      tokens: {
        used: data.tokens_used || data.tokens?.used || 0,
        limit: data.tokens_limit || data.tokens?.limit || 100000,
      },
    })
  } catch (error) {
    console.error("Error getting usage:", error)
    // Return default limits as fallback
    return NextResponse.json({
      requests: { used: 0, limit: 100 },
      tokens: { used: 0, limit: 100000 },
    })
  }
}

