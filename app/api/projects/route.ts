import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import { kv } from "@vercel/kv"

interface Project {
  id: string
  name: string
  description?: string
  conversations: string[]
  createdAt: string
  color?: string
  icon?: string
  pinned?: boolean
  archived?: boolean
}

// Helper to get the KV key for a user's projects
function getProjectsKey(userId: string): string {
  return `projects:${userId}`
}

// Check if KV is available (has required env vars)
function isKVAvailable(): boolean {
  return !!(process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN)
}

// In-memory fallback for local development without KV
const localFallback: Map<string, Project[]> = new Map()

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

    let userProjects: Project[] = []

    if (isKVAvailable()) {
      const stored = await kv.get<Project[]>(getProjectsKey(userId))
      userProjects = stored || []
      console.log(`[Projects API] GET from KV for user ${userId}: ${userProjects.length} projects`)
    } else {
      userProjects = localFallback.get(userId) || []
      console.log(`[Projects API] GET from memory (no KV) for user ${userId}: ${userProjects.length} projects`)
    }
    
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
    const key = getProjectsKey(userId)

    // Helper to get existing projects
    async function getExisting(): Promise<Project[]> {
      if (isKVAvailable()) {
        return (await kv.get<Project[]>(key)) || []
      }
      return localFallback.get(userId!) || []
    }

    // Helper to save projects
    async function saveProjects(projects: Project[]): Promise<void> {
      if (isKVAvailable()) {
        await kv.set(key, projects)
      } else {
        localFallback.set(userId!, projects)
      }
    }

    if (action === "sync") {
      // Full sync - replace all projects
      const dataToStore = body.projects || []
      await saveProjects(dataToStore)
      console.log(`[Projects API] SYNC for user ${userId}: ${dataToStore.length} projects (${isKVAvailable() ? 'KV' : 'memory'})`)
      return NextResponse.json({
        success: true,
        count: dataToStore.length,
        storage: isKVAvailable() ? "kv" : "memory"
      })
    }

    if (action === "create") {
      const existing = await getExisting()
      const newProject = body.project
      if (newProject) {
        existing.push(newProject)
        await saveProjects(existing)
        console.log(`[Projects API] CREATE for user ${userId}: ${newProject.id}`)
      }
      return NextResponse.json({ success: true, project: newProject })
    }

    if (action === "update") {
      const existing = await getExisting()
      const projectId = body.projectId
      const updates = body.updates
      
      const updated = existing.map(p => 
        p.id === projectId ? { ...p, ...updates } : p
      )
      await saveProjects(updated)
      console.log(`[Projects API] UPDATE for user ${userId}: ${projectId}`)
      return NextResponse.json({ success: true })
    }

    if (action === "delete") {
      const existing = await getExisting()
      const projectId = body.projectId
      const filtered = existing.filter(p => p.id !== projectId)
      await saveProjects(filtered)
      console.log(`[Projects API] DELETE for user ${userId}: ${projectId}`)
      return NextResponse.json({ success: true })
    }

    if (action === "addConversation") {
      const existing = await getExisting()
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
      await saveProjects(updated)
      console.log(`[Projects API] ADD CONVERSATION for user ${userId}: ${conversationId} -> ${projectId}`)
      return NextResponse.json({ success: true })
    }

    if (action === "removeConversation") {
      const existing = await getExisting()
      const projectId = body.projectId
      const conversationId = body.conversationId
      
      const updated = existing.map(p => {
        if (p.id === projectId) {
          return { ...p, conversations: (p.conversations || []).filter((id: string) => id !== conversationId) }
        }
        return p
      })
      await saveProjects(updated)
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
