import { NextResponse } from "next/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

// Fallback empty response when backend not ready
const EMPTY_RESPONSE = {
  models: [],
  total: 0,
  page: 1,
  limit: 20,
  message: "OpenRouter integration initializing. Run sync to populate models."
}

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
      // Return empty response for any backend error (404, 500, table missing, etc.)
      console.error("OpenRouter backend error:", response.status)
      return NextResponse.json(EMPTY_RESPONSE)
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("OpenRouter models API error:", error)
    // Return empty response instead of error
    return NextResponse.json(EMPTY_RESPONSE)
  }
}

