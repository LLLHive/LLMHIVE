import { NextResponse } from "next/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "https://llmhive-orchestrator-792354158895.us-east1.run.app"
const OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"

// Transform OpenRouter model to our format
function transformModel(model: Record<string, unknown>) {
  const pricing = model.pricing as Record<string, string> | undefined
  const architecture = model.architecture as Record<string, unknown> | undefined
  const topProvider = model.top_provider as Record<string, unknown> | undefined
  
  return {
    id: model.id,
    name: model.name,
    description: model.description || "",
    context_length: model.context_length || 4096,
    architecture: {
      modality: architecture?.modality || "text->text",
      tokenizer: architecture?.tokenizer || "unknown",
      instruct_type: architecture?.instruct_type || "none",
    },
    pricing: {
      prompt: pricing?.prompt ? parseFloat(pricing.prompt) : 0,
      completion: pricing?.completion ? parseFloat(pricing.completion) : 0,
      per_1m_prompt: pricing?.prompt ? parseFloat(pricing.prompt) * 1000000 : 0,
      per_1m_completion: pricing?.completion ? parseFloat(pricing.completion) * 1000000 : 0,
    },
    capabilities: {
      supports_tools: Boolean(model.supported_parameters && 
        (model.supported_parameters as string[])?.includes?.("tools")),
      supports_structured: Boolean(model.supported_parameters && 
        (model.supported_parameters as string[])?.includes?.("structured_outputs")),
      supports_streaming: true,
      multimodal_input: architecture?.input_modalities 
        ? (architecture.input_modalities as string[]).some((m: string) => m !== "text")
        : false,
      multimodal_output: architecture?.output_modalities 
        ? (architecture.output_modalities as string[]).some((m: string) => m !== "text")
        : false,
    },
    is_free: pricing?.prompt === "0" && pricing?.completion === "0",
    availability_score: 100,
    is_active: true,
    top_provider_max_tokens: topProvider?.max_completion_tokens as number || undefined,
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const search = searchParams.get("search") || ""
  const limit = parseInt(searchParams.get("limit") || "50")
  const offset = parseInt(searchParams.get("offset") || "0")
  
  // Try backend first
  try {
    const query = searchParams.toString()
    const url = `${BACKEND_URL}/api/v1/openrouter/models${query ? `?${query}` : ""}`
    
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      // Short timeout - fall back to OpenRouter if slow
      signal: AbortSignal.timeout(3000),
    })
    
    if (response.ok) {
      const data = await response.json()
      // If backend has models, use them
      if (data.models && data.models.length > 0) {
        return NextResponse.json(data)
      }
    }
  } catch {
    // Backend unavailable, will fallback to OpenRouter
  }
  
  // Fallback: Fetch directly from OpenRouter
  try {
    const openRouterResponse = await fetch(OPENROUTER_API_URL, {
      headers: {
        "Content-Type": "application/json",
      },
      next: { revalidate: 3600 }, // Cache for 1 hour
    })
    
    if (!openRouterResponse.ok) {
      throw new Error(`OpenRouter API error: ${openRouterResponse.status}`)
    }
    
    const openRouterData = await openRouterResponse.json()
    const rawModels = openRouterData.data || []
    
    // Transform models to our format
    let models = rawModels.map(transformModel)
    
    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase()
      models = models.filter((m: { id: string; name: string; description: string }) => 
        m.id.toLowerCase().includes(searchLower) ||
        m.name.toLowerCase().includes(searchLower) ||
        (m.description && m.description.toLowerCase().includes(searchLower))
      )
    }
    
    // Get total before pagination
    const total = models.length
    
    // Apply pagination
    models = models.slice(offset, offset + limit)
    
    return NextResponse.json({
      models,
      total,
      limit,
      offset,
      data_source: "OpenRouter API (live)",
      last_sync: new Date().toISOString(),
    })
  } catch (error) {
    console.error("OpenRouter API error:", error)
    return NextResponse.json({
      models: [],
      total: 0,
      limit,
      offset,
      message: "Failed to fetch models from OpenRouter",
      error: error instanceof Error ? error.message : "Unknown error",
    })
  }
}
