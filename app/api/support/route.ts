/**
 * Support Ticket API
 * 
 * Handles customer support requests:
 * - Create support tickets
 * - Store in Firestore
 * - Send email notifications
 * - Track ticket status
 */
import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import { sendSupportTicketNotification } from "@/lib/slack"
import { sendTicketConfirmationEmail } from "@/lib/email"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

// Support ticket types
type TicketType = "general" | "technical" | "billing" | "enterprise" | "bug" | "feature"
type TicketPriority = "low" | "medium" | "high" | "urgent"
type TicketStatus = "open" | "in_progress" | "waiting" | "resolved" | "closed"

interface SupportTicket {
  id?: string
  userId?: string
  email: string
  name: string
  type: TicketType
  subject: string
  message: string
  priority?: TicketPriority
  status?: TicketStatus
  metadata?: Record<string, unknown>
  createdAt?: string
  updatedAt?: string
}

// In-memory store for demo (replace with Firestore in production)
const ticketStore: Map<string, SupportTicket> = new Map()

function generateTicketId(): string {
  const prefix = "TKT"
  const timestamp = Date.now().toString(36).toUpperCase()
  const random = Math.random().toString(36).substring(2, 6).toUpperCase()
  return `${prefix}-${timestamp}-${random}`
}

function determineTicketPriority(ticket: SupportTicket): TicketPriority {
  const message = ticket.message.toLowerCase()
  const subject = ticket.subject.toLowerCase()
  
  // Urgent keywords
  if (message.includes("urgent") || message.includes("emergency") || 
      message.includes("down") || message.includes("not working") ||
      subject.includes("urgent")) {
    return "urgent"
  }
  
  // High priority keywords
  if (message.includes("billing") || message.includes("payment") ||
      message.includes("charged") || ticket.type === "billing") {
    return "high"
  }
  
  // Enterprise is always high priority
  if (ticket.type === "enterprise") {
    return "high"
  }
  
  // Bug reports are medium priority
  if (ticket.type === "bug") {
    return "medium"
  }
  
  return "low"
}

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    const body = await req.json()
    
    // Validate required fields
    const { email, name, type, subject, message } = body
    
    if (!email || !name || !subject || !message) {
      return NextResponse.json(
        { error: "Missing required fields: email, name, subject, message" },
        { status: 400 }
      )
    }
    
    // Create ticket
    const ticket: SupportTicket = {
      id: generateTicketId(),
      userId: userId || undefined,
      email,
      name,
      type: type || "general",
      subject,
      message,
      priority: determineTicketPriority({ email, name, type, subject, message }),
      status: "open",
      metadata: body.metadata || {},
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    
    // Store ticket (in-memory for now)
    ticketStore.set(ticket.id!, ticket)
    
    // Try to sync to backend (fire and forget)
    try {
      await fetch(`${BACKEND_URL}/api/v1/support/tickets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${process.env.API_KEY || ""}`,
        },
        body: JSON.stringify(ticket),
      }).catch(() => {
        // Backend sync failed, but ticket is stored locally
        console.log("[Support] Backend sync pending for ticket:", ticket.id)
      })
    } catch {
      // Ignore backend errors
    }
    
    // Log ticket creation
    console.log(`[Support] New ticket created: ${ticket.id}`)
    console.log(`  From: ${name} <${email}>`)
    console.log(`  Type: ${type}, Priority: ${ticket.priority}`)
    console.log(`  Subject: ${subject}`)
    
    // Send Slack notification (fire and forget)
    sendSupportTicketNotification({
      id: ticket.id!,
      name,
      email,
      subject,
      message,
      type: ticket.type,
      priority: ticket.priority!,
    }).catch((err) => {
      console.error("[Support] Failed to send Slack notification:", err)
    })
    
    // Determine estimated response time
    const estimatedResponse = ticket.priority === "urgent" ? "2 hours" : 
                              ticket.priority === "high" ? "4 hours" :
                              ticket.priority === "medium" ? "24 hours" : "48 hours"
    
    // Send email confirmation to user (fire and forget)
    sendTicketConfirmationEmail({
      to: email,
      name,
      ticketId: ticket.id!,
      subject,
      estimatedResponse,
    }).catch((err) => {
      console.error("[Support] Failed to send confirmation email:", err)
    })
    
    return NextResponse.json({
      success: true,
      ticketId: ticket.id,
      message: `Your support request has been received. Ticket ID: ${ticket.id}`,
      estimatedResponse: ticket.priority === "urgent" ? "2 hours" : 
                         ticket.priority === "high" ? "4 hours" :
                         ticket.priority === "medium" ? "24 hours" : "48 hours",
    })
    
  } catch (error) {
    console.error("[Support] Error creating ticket:", error)
    return NextResponse.json(
      { error: "Failed to create support ticket" },
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
    
    // Get user's tickets
    const userTickets = Array.from(ticketStore.values())
      .filter(t => t.userId === userId)
      .sort((a, b) => 
        new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime()
      )
    
    return NextResponse.json({
      tickets: userTickets,
      total: userTickets.length,
    })
    
  } catch (error) {
    console.error("[Support] Error fetching tickets:", error)
    return NextResponse.json(
      { error: "Failed to fetch tickets" },
      { status: 500 }
    )
  }
}
