import { NextResponse } from "next/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

// Default rankings config
const DEFAULT_RESPONSE = {
  dimensions: [
    { id: "trending", name: "Trending", description: "Most popular models" },
    { id: "most_used", name: "Most Used", description: "Highest usage volume" },
    { id: "best_value", name: "Best Value", description: "Best cost-performance ratio" },
    { id: "long_context", name: "Long Context", description: "Largest context windows" },
    { id: "tools_agents", name: "Tools & Agents", description: "Best for tool calling" },
  ],
  time_ranges: ["24h", "7d", "30d"],
  data_source: "internal_telemetry",
  data_source_description: "Rankings based on LLMHive usage data"
}

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/openrouter/rankings`, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
    })
    
    if (!response.ok) {
      return NextResponse.json(DEFAULT_RESPONSE)
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Rankings API error:", error)
    return NextResponse.json(DEFAULT_RESPONSE)
  }
}

