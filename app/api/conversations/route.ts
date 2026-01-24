import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

/**
 * Backend API URL for persistent storage (Firestore + Pinecone)
 */
const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

/**
 * GET /api/conversations - Get all conversations for the current user
 * Proxies to backend: GET /v1/data/conversations
 */
export async function GET(req: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized", conversations: [] },
        { status: 401 }
      )
    }

    // Call backend API
    const response = await fetch(`${BACKEND_URL}/v1/data/conversations`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": userId,
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })

    if (!response.ok) {
      console.error(`[Conversations API] Backend error: ${response.status}`)
      return NextResponse.json(
        { error: "Backend unavailable", conversations: [] },
        { status: 502 }
      )
    }

    const data = await response.json()
    
    console.log(`[Conversations API] GET from backend for user ${userId}: ${data.count} conversations`)
    
    return NextResponse.json({
      conversations: data.conversations || [],
      count: data.count || 0,
      storage: "firestore",
    })
  } catch (error) {
    console.error("[Conversations API] GET error:", error)
    return NextResponse.json(
      { error: "Failed to fetch conversations", conversations: [] },
      { status: 500 }
    )
  }
}

/**
 * POST /api/conversations - Save/sync conversations for the current user
 * Proxies to backend: POST /v1/data/conversations/{action}
 */
export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    const body = await req.json()
    const { action } = body

    // Map actions to backend endpoints
    let endpoint: string
    let backendBody: any

    switch (action) {
      case "sync":
        endpoint = `${BACKEND_URL}/v1/data/conversations/sync`
        backendBody = { conversations: body.conversations || [] }
        break

      case "create":
        endpoint = `${BACKEND_URL}/v1/data/conversations/create`
        backendBody = { conversation: body.conversation }
        break

      case "update":
        endpoint = `${BACKEND_URL}/v1/data/conversations/update`
        backendBody = {
          conversationId: body.conversationId,
          updates: body.updates,
        }
        break

      case "delete":
        endpoint = `${BACKEND_URL}/v1/data/conversations/delete?conversationId=${encodeURIComponent(body.conversationId)}`
        backendBody = {}
        break

      default:
        return NextResponse.json(
          { error: "Invalid action" },
          { status: 400 }
        )
    }

    // Call backend API
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": userId,
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      body: JSON.stringify(backendBody),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Conversations API] Backend error: ${response.status} - ${errorText}`)
      return NextResponse.json(
        { error: "Backend operation failed", success: false },
        { status: 502 }
      )
    }

    const data = await response.json()
    
    console.log(`[Conversations API] ${action.toUpperCase()} for user ${userId}: success=${data.success}`)
    
    return NextResponse.json({
      success: data.success,
      message: data.message,
      storage: "firestore",
    })

  } catch (error) {
    console.error("[Conversations API] POST error:", error)
    return NextResponse.json(
      { error: "Failed to save conversations" },
      { status: 500 }
    )
  }
}
