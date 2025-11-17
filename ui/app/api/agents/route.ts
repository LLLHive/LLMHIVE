import { NextResponse } from "next/server"

export async function GET() {
  try {
    const orchestratorUrl = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"
    const response = await fetch(`${orchestratorUrl}/api/agents`)
    
    if (!response.ok) {
      return NextResponse.json([])
    }

    const agents = await response.json()
    return NextResponse.json(agents)
  } catch (error) {
    console.error("[v0] Error fetching agents:", error)
    return NextResponse.json([])
  }
}
