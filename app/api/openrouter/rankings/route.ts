import { NextResponse } from "next/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/openrouter/rankings`, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })
    
    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({
          dimensions: [
            { id: "trending", name: "Trending", description: "Most popular models" },
            { id: "most_used", name: "Most Used", description: "Highest usage volume" },
            { id: "best_value", name: "Best Value", description: "Best cost-performance ratio" },
          ],
          time_ranges: ["24h", "7d", "30d"],
          data_source: "internal_telemetry",
          data_source_description: "Rankings based on LLMHive usage data"
        })
      }
      const error = await response.text()
      return NextResponse.json({ error }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Rankings API error:", error)
    return NextResponse.json(
      { error: "Failed to fetch rankings", dimensions: [] },
      { status: 500 }
    )
  }
}

