import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

// Vercel KV for persistent storage (or fallback to in-memory for local dev)
let conversations: Map<string, any[]> = new Map()

// Types
interface Conversation {
  id: string
  title: string
  messages: any[]
  createdAt: string
  updatedAt: string
  model: string
  pinned?: boolean
  archived?: boolean
  projectId?: string
}

interface ConversationsStore {
  conversations: Conversation[]
  updatedAt: string
}

/**
 * GET /api/conversations - Get all conversations for the current user
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

    // Get conversations for this user
    const userConversations = conversations.get(userId) || []
    
    console.log(`[Conversations API] GET for user ${userId}: ${userConversations.length} conversations`)
    
    return NextResponse.json({
      conversations: userConversations,
      count: userConversations.length,
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
    const { conversations: userConvs, action } = body

    if (action === "sync") {
      // Full sync - replace all conversations
      conversations.set(userId, userConvs || [])
      console.log(`[Conversations API] SYNC for user ${userId}: ${userConvs?.length || 0} conversations`)
      
      // Also sync to vector database for learning
      await syncToVectorDatabase(userId, userConvs || [])
      
      return NextResponse.json({
        success: true,
        count: userConvs?.length || 0,
      })
    }

    if (action === "create") {
      // Create a new conversation
      const existing = conversations.get(userId) || []
      const newConv = body.conversation
      if (newConv) {
        existing.unshift(newConv)
        conversations.set(userId, existing)
        console.log(`[Conversations API] CREATE for user ${userId}: ${newConv.id}`)
      }
      return NextResponse.json({ success: true, conversation: newConv })
    }

    if (action === "update") {
      // Update a specific conversation
      const existing = conversations.get(userId) || []
      const convId = body.conversationId
      const updates = body.updates
      
      const updated = existing.map(c => 
        c.id === convId ? { ...c, ...updates, updatedAt: new Date().toISOString() } : c
      )
      conversations.set(userId, updated)
      console.log(`[Conversations API] UPDATE for user ${userId}: ${convId}`)
      
      // Sync updated conversation to vector database
      const updatedConv = updated.find(c => c.id === convId)
      if (updatedConv) {
        await syncConversationToVector(userId, updatedConv)
      }
      
      return NextResponse.json({ success: true })
    }

    if (action === "delete") {
      // Delete a conversation
      const existing = conversations.get(userId) || []
      const convId = body.conversationId
      const filtered = existing.filter(c => c.id !== convId)
      conversations.set(userId, filtered)
      console.log(`[Conversations API] DELETE for user ${userId}: ${convId}`)
      return NextResponse.json({ success: true })
    }

    return NextResponse.json(
      { error: "Invalid action" },
      { status: 400 }
    )
  } catch (error) {
    console.error("[Conversations API] POST error:", error)
    return NextResponse.json(
      { error: "Failed to save conversations" },
      { status: 500 }
    )
  }
}

/**
 * Sync conversations to Pinecone vector database for learning/RAG
 */
async function syncToVectorDatabase(userId: string, convs: Conversation[]) {
  const apiBase = process.env.ORCHESTRATOR_API_BASE_URL
  if (!apiBase) {
    console.log("[Conversations API] No backend URL, skipping vector sync")
    return
  }

  try {
    // Send to backend for vector indexing
    await fetch(`${apiBase}/v1/memory/sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      body: JSON.stringify({
        user_id: userId,
        conversations: convs.map(c => ({
          id: c.id,
          title: c.title,
          messages: c.messages,
          created_at: c.createdAt,
          updated_at: c.updatedAt,
        })),
      }),
    })
    console.log(`[Conversations API] Vector sync completed for user ${userId}`)
  } catch (error) {
    console.error("[Conversations API] Vector sync error:", error)
    // Don't fail the main request if vector sync fails
  }
}

/**
 * Sync a single conversation to vector database
 */
async function syncConversationToVector(userId: string, conv: Conversation) {
  const apiBase = process.env.ORCHESTRATOR_API_BASE_URL
  if (!apiBase) return

  try {
    await fetch(`${apiBase}/v1/memory/store`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      body: JSON.stringify({
        user_id: userId,
        conversation_id: conv.id,
        title: conv.title,
        messages: conv.messages,
      }),
    })
  } catch (error) {
    console.error("[Conversations API] Single conversation sync error:", error)
  }
}

