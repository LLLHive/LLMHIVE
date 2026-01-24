/**
 * Feedback API Route
 * 
 * Proxies feedback to the Python backend for RLHF training.
 * Stores user feedback in Pinecone for semantic similarity search.
 */
import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  
  try {
    const body = await req.json()
    
    // Add user context
    const feedbackPayload = {
      ...body,
      user_id: userId || "anonymous",
    }
    
    // Forward to backend RLHF endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/rlhf/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(userId && { "X-User-Id": userId }),
      },
      body: JSON.stringify(feedbackPayload),
    })

    if (!response.ok) {
      // Try to get error details
      const errorData = await response.json().catch(() => ({}))
      console.error("[Feedback API] Backend error:", response.status, errorData)
      
      // Return success anyway to not block UI - feedback is non-critical
      return NextResponse.json({ 
        success: true, 
        message: "Feedback acknowledged (backend temporarily unavailable)",
        queued: true,
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error("[Feedback API] Error:", error)
    
    // Return success anyway - don't block the UI for feedback errors
    return NextResponse.json({ 
      success: true, 
      message: "Feedback acknowledged",
      queued: true,
    })
  }
}

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  
  try {
    // Get feedback stats
    const response = await fetch(`${BACKEND_URL}/api/v1/rlhf/feedback/stats`, {
      headers: {
        "X-User-Id": userId,
      },
    })

    if (!response.ok) {
      return NextResponse.json({ 
        total_feedback: 0,
        message: "Stats temporarily unavailable",
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error("[Feedback API] Stats error:", error)
    return NextResponse.json({ 
      total_feedback: 0,
      message: "Stats temporarily unavailable",
    })
  }
}

