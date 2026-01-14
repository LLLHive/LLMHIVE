import { NextResponse } from "next/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"

// Default rankings config with Pinecone categories
const DEFAULT_RESPONSE = {
  dimensions: [
    { id: "programming", name: "Programming", description: "Best for coding tasks" },
    { id: "reasoning", name: "Reasoning", description: "Advanced reasoning capability" },
    { id: "roleplay", name: "Roleplay", description: "Creative roleplay and characters" },
    { id: "marketing", name: "Marketing", description: "Marketing and copywriting" },
    { id: "technology", name: "Technology", description: "Tech knowledge and support" },
    { id: "science", name: "Science", description: "Scientific analysis and research" },
    { id: "creative-writing", name: "Creative Writing", description: "Stories and creative content" },
    { id: "translation", name: "Translation", description: "Language translation" },
    { id: "legal", name: "Legal", description: "Legal analysis and documents" },
    { id: "finance", name: "Finance", description: "Financial analysis" },
    { id: "healthcare", name: "Healthcare", description: "Medical information" },
    { id: "education", name: "Education", description: "Teaching and tutoring" },
  ],
  time_ranges: ["24h", "7d", "30d"],
  data_source: "pinecone_knowledge_store",
  data_source_description: "Rankings synced from OpenRouter and stored in Pinecone (persistent)"
}

export async function GET() {
  // PRIORITY 1: Try Pinecone-backed categories API
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/models/categories`, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      signal: AbortSignal.timeout(5000),
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.categories && data.categories.length > 0) {
        return NextResponse.json({
          dimensions: data.categories.map((cat: { slug: string; name: string; group?: string }) => ({
            id: cat.slug,
            name: cat.name,
            description: `Models for ${cat.name.toLowerCase()} tasks`,
            group: cat.group || "usecase",
          })),
          time_ranges: ["24h", "7d", "30d"],
          data_source: data.data_source || "pinecone_knowledge_store",
          data_source_description: data.description || "Rankings from Pinecone (persistent)",
        })
      }
    }
  } catch (err) {
    console.log("Pinecone categories unavailable, trying SQLite:", err)
  }
  
  // PRIORITY 2: Try SQLite backend rankings
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/openrouter/rankings`, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      signal: AbortSignal.timeout(3000),
    })
    
    if (response.ok) {
      const data = await response.json()
      return NextResponse.json(data)
    }
  } catch {
    // Backend unavailable
  }
  
  // FALLBACK: Return default categories
  return NextResponse.json(DEFAULT_RESPONSE)
}

