import { NextResponse } from "next/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.toString()
    
    const url = `${BACKEND_URL}/api/v1/openrouter/models${query ? `?${query}` : ""}`
    
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })
    
    if (!response.ok) {
      // If backend doesn't have this route yet, return mock data
      if (response.status === 404) {
        return NextResponse.json({
          models: [],
          total: 0,
          page: 1,
          limit: 20,
          message: "OpenRouter sync not yet run. Models will appear after first sync."
        })
      }
      const error = await response.text()
      return NextResponse.json({ error }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("OpenRouter models API error:", error)
    return NextResponse.json(
      { error: "Failed to fetch models", models: [], total: 0 },
      { status: 500 }
    )
  }
}

