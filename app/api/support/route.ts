/**
 * Support Ticket API - Frontend Proxy
 * 
 * This is a simple proxy to the backend support API.
 * All notification logic (Slack, Email) is handled by the backend
 * where the secrets (SLACK_WEBHOOK_URL, RESEND_API_KEY) are configured
 * in Google Cloud Secret Manager.
 */
import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"

interface SupportTicketRequest {
  name: string
  email: string
  subject: string
  message: string
  type?: string
  metadata?: Record<string, unknown>
}

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    const body: SupportTicketRequest = await req.json()
    
    // Validate required fields
    const { email, name, subject, message } = body
    
    if (!email || !name || !subject || !message) {
      return NextResponse.json(
        { error: "Missing required fields: email, name, subject, message" },
        { status: 400 }
      )
    }
    
    console.log(`[Support] Proxying ticket creation to backend`)
    console.log(`  From: ${name} <${email}>`)
    console.log(`  Type: ${body.type || 'general'}`)
    console.log(`  Subject: ${subject}`)
    
    // Proxy to backend
    const response = await fetch(`${BACKEND_URL}/v1/support/tickets`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(userId ? { "X-User-Id": userId } : {}),
      },
      body: JSON.stringify({
        name,
        email,
        subject,
        message,
        type: body.type || "general",
        metadata: body.metadata || {},
      }),
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Support] Backend error (${response.status}): ${errorText}`)
      
      // Return friendly error message
      return NextResponse.json(
        { 
          error: "Failed to create support ticket. Please try again or email info@llmhive.ai directly.",
          details: response.status >= 500 ? "Backend service error" : errorText,
        },
        { status: response.status }
      )
    }
    
    const result = await response.json()
    
    console.log(`[Support] ✅ Ticket created successfully: ${result.ticket_id}`)
    
    return NextResponse.json({
      success: true,
      ticketId: result.ticket_id,
      message: result.message,
      estimatedResponse: result.estimated_response,
    })
    
  } catch (error) {
    console.error("[Support] Error creating ticket:", error)
    return NextResponse.json(
      { 
        error: "Failed to create support ticket. Please try again or email info@llmhive.ai directly.",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    )
  }
}

export async function GET(req: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }
    
    // Proxy to backend to get user's tickets
    const response = await fetch(`${BACKEND_URL}/v1/support/tickets?user_id=${userId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": userId,
      },
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Support] Backend error fetching tickets (${response.status}): ${errorText}`)
      
      return NextResponse.json(
        { error: "Failed to fetch tickets" },
        { status: response.status }
      )
    }
    
    const result = await response.json()
    
    return NextResponse.json(result)
    
  } catch (error) {
    console.error("[Support] Error fetching tickets:", error)
    return NextResponse.json(
      { error: "Failed to fetch tickets" },
      { status: 500 }
    )
  }
}
