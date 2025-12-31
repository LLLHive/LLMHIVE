import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

// In-memory storage (will be replaced with database in production)
let projects: Map<string, any[]> = new Map()

interface Project {
  id: string
  name: string
  description?: string
  conversations: string[]
  createdAt: string
  color?: string
  icon?: string
}

/**
 * GET /api/projects - Get all projects for the current user
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

    const userProjects = projects.get(userId) || []
    
    console.log(`[Projects API] GET for user ${userId}: ${userProjects.length} projects`)
    
    return NextResponse.json({
      projects: userProjects,
      count: userProjects.length,
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

    if (action === "sync") {
      // Full sync - replace all projects
      projects.set(userId, body.projects || [])
      console.log(`[Projects API] SYNC for user ${userId}: ${body.projects?.length || 0} projects`)
      return NextResponse.json({
        success: true,
        count: body.projects?.length || 0,
      })
    }

    if (action === "create") {
      const existing = projects.get(userId) || []
      const newProject = body.project
      if (newProject) {
        existing.push(newProject)
        projects.set(userId, existing)
        console.log(`[Projects API] CREATE for user ${userId}: ${newProject.id}`)
      }
      return NextResponse.json({ success: true, project: newProject })
    }

    if (action === "update") {
      const existing = projects.get(userId) || []
      const projectId = body.projectId
      const updates = body.updates
      
      const updated = existing.map(p => 
        p.id === projectId ? { ...p, ...updates } : p
      )
      projects.set(userId, updated)
      console.log(`[Projects API] UPDATE for user ${userId}: ${projectId}`)
      return NextResponse.json({ success: true })
    }

    if (action === "delete") {
      const existing = projects.get(userId) || []
      const projectId = body.projectId
      const filtered = existing.filter(p => p.id !== projectId)
      projects.set(userId, filtered)
      console.log(`[Projects API] DELETE for user ${userId}: ${projectId}`)
      return NextResponse.json({ success: true })
    }

    if (action === "addConversation") {
      const existing = projects.get(userId) || []
      const projectId = body.projectId
      const conversationId = body.conversationId
      
      const updated = existing.map(p => {
        if (p.id === projectId) {
          const convs = p.conversations || []
          if (!convs.includes(conversationId)) {
            convs.push(conversationId)
          }
          return { ...p, conversations: convs }
        }
        return p
      })
      projects.set(userId, updated)
      console.log(`[Projects API] ADD CONVERSATION for user ${userId}: ${conversationId} -> ${projectId}`)
      return NextResponse.json({ success: true })
    }

    if (action === "removeConversation") {
      const existing = projects.get(userId) || []
      const projectId = body.projectId
      const conversationId = body.conversationId
      
      const updated = existing.map(p => {
        if (p.id === projectId) {
          return { ...p, conversations: (p.conversations || []).filter((id: string) => id !== conversationId) }
        }
        return p
      })
      projects.set(userId, updated)
      console.log(`[Projects API] REMOVE CONVERSATION for user ${userId}: ${conversationId} from ${projectId}`)
      return NextResponse.json({ success: true })
    }

    return NextResponse.json(
      { error: "Invalid action" },
      { status: 400 }
    )
  } catch (error) {
    console.error("[Projects API] POST error:", error)
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    )
  }
}

