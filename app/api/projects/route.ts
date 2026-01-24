import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

/**
 * Backend API URL for persistent storage (Firestore + Pinecone)
 */
const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

/**
 * GET /api/projects - Get all projects for the current user
 * Proxies to backend: GET /v1/data/projects
 */
export async function GET(req: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized", projects: [] },
        { status: 401 }
      )
    }

    // Call backend API
    const response = await fetch(`${BACKEND_URL}/v1/data/projects`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": userId,
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })

    if (!response.ok) {
      console.error(`[Projects API] Backend error: ${response.status}`)
      return NextResponse.json(
        { error: "Backend unavailable", projects: [] },
        { status: 502 }
      )
    }

    const data = await response.json()
    
    console.log(`[Projects API] GET from backend for user ${userId}: ${data.count} projects`)
    
    return NextResponse.json({
      projects: data.projects || [],
      count: data.count || 0,
      storage: "firestore",
    })
  } catch (error) {
    console.error("[Projects API] GET error:", error)
    return NextResponse.json(
      { error: "Failed to fetch projects", projects: [] },
      { status: 500 }
    )
  }
}

/**
 * POST /api/projects - Create/update/delete projects
 * Proxies to backend: POST /v1/data/projects/{action}
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
        endpoint = `${BACKEND_URL}/v1/data/projects/sync`
        backendBody = { projects: body.projects || [] }
        break

      case "create":
        endpoint = `${BACKEND_URL}/v1/data/projects/create`
        backendBody = { project: body.project }
        break

      case "update":
        endpoint = `${BACKEND_URL}/v1/data/projects/update`
        backendBody = {
          projectId: body.projectId,
          updates: body.updates,
        }
        break

      case "delete":
        endpoint = `${BACKEND_URL}/v1/data/projects/delete?projectId=${encodeURIComponent(body.projectId)}`
        backendBody = {}
        break

      case "addConversation":
        endpoint = `${BACKEND_URL}/v1/data/projects/add-conversation`
        backendBody = {
          projectId: body.projectId,
          conversationId: body.conversationId,
        }
        break

      case "removeConversation":
        endpoint = `${BACKEND_URL}/v1/data/projects/remove-conversation`
        backendBody = {
          projectId: body.projectId,
          conversationId: body.conversationId,
        }
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
      console.error(`[Projects API] Backend error: ${response.status} - ${errorText}`)
      return NextResponse.json(
        { error: "Backend operation failed", success: false },
        { status: 502 }
      )
    }

    const data = await response.json()
    
    console.log(`[Projects API] ${action.toUpperCase()} for user ${userId}: success=${data.success}`)
    
    return NextResponse.json({
      success: data.success,
      message: data.message,
      storage: "firestore",
    })

  } catch (error) {
    console.error("[Projects API] POST error:", error)
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    )
  }
}
