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

// Transform model profile from Firestore/Pinecone to our format
function transformPineconeModel(model: Record<string, unknown>) {
  // Handle both Firestore and Pinecone formats
  const capabilities = model.capabilities as Record<string, number> | undefined
  const features = model.features as Record<string, boolean | number> | undefined
  const source = model.source as string || "persistent_store"
  
  // Get best for from either format
  const bestFor = (model.best_for as string[]) || 
    ((model.strengths as string[])?.slice(0, 3)) || 
    ["general use"]
  
  return {
    id: model.id,
    name: model.name || model.id,
    description: `${model.provider} model. Best for: ${bestFor.join(", ")}`,
    context_length: features?.context_length || model.context_length || 8192,
    architecture: {
      modality: features?.supports_vision ? "text+image->text" : "text->text",
      tokenizer: "unknown",
      instruct_type: "none",
    },
    pricing: {
      prompt: 0,
      completion: 0,
      per_1m_prompt: 0,
      per_1m_completion: 0,
    },
    capabilities: {
      supports_tools: features?.supports_tools || false,
      supports_structured: false,
      supports_streaming: true,
      multimodal_input: features?.supports_vision || false,
      multimodal_output: false,
      // Enriched benchmarks from Firestore
      arena_score: capabilities?.arena_score,
      arena_rank: capabilities?.arena_rank,
      hf_ollb_avg: capabilities?.hf_ollb_avg,
      reasoning_score: capabilities?.reasoning_score || 50,
      coding_score: capabilities?.coding_score || 50,
      creative_score: capabilities?.creative_score || 50,
      is_reasoning_model: features?.is_reasoning_model || false,
    },
    is_free: false,
    availability_score: 100,
    is_active: true,
    provider: model.provider,
    strengths: model.strengths || [],
    weaknesses: model.weaknesses || [],
    best_for: bestFor,
    data_source: source,
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const search = searchParams.get("search") || ""
  const limit = parseInt(searchParams.get("limit") || "50")
  const offset = parseInt(searchParams.get("offset") || "0")
  
  // PRIORITY 1: OpenRouter API (source of truth for available models)
  // This ensures we always show the LATEST models (GPT-5.2, Claude 4.5, Gemini 3, etc.)
  try {
    const openRouterResponse = await fetch(OPENROUTER_API_URL, {
      headers: {
        "Content-Type": "application/json",
      },
      next: { revalidate: 300 }, // Cache for 5 minutes (was 1 hour - too stale)
    })
    
    if (openRouterResponse.ok) {
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
    }
  } catch (err) {
    console.log("OpenRouter API unavailable, trying backend:", err)
  }
  
  // PRIORITY 2: Try SQLite backend (has synced OpenRouter data)
  try {
    const query = searchParams.toString()
    const url = `${BACKEND_URL}/api/v1/openrouter/models${query ? `?${query}` : ""}`
    
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      signal: AbortSignal.timeout(3000),
    })
    
    if (response.ok) {
      const data = await response.json()
      // Backend returns 'data' array, normalize to 'models'
      const models = data.models || data.data || []
      if (models.length > 0) {
        return NextResponse.json({
          models: models.map(transformModel),
          total: data.total || models.length,
          limit: data.limit || limit,
          offset: data.offset || offset,
          data_source: data.data_source || "Backend SQLite",
          last_sync: data.last_sync || new Date().toISOString(),
        })
      }
    }
  } catch {
    // Backend unavailable, will fallback to Pinecone
  }
  
  // PRIORITY 3: Try Pinecone-backed API (may have enriched metadata but older model list)
  try {
    const pineconeUrl = `${BACKEND_URL}/api/v1/models/profiles?limit=${limit}&search=${encodeURIComponent(search)}`
    
    const pineconeResponse = await fetch(pineconeUrl, {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      signal: AbortSignal.timeout(5000),
    })
    
    if (pineconeResponse.ok) {
      const data = await pineconeResponse.json()
      if (data.models && data.models.length > 0) {
        // Transform Pinecone models to our format
        const models = data.models.map(transformPineconeModel)
        return NextResponse.json({
          models,
          total: data.total || models.length,
          limit,
          offset,
          data_source: "Pinecone Knowledge Store (cached)",
          last_sync: data.last_updated || new Date().toISOString(),
        })
      }
    }
  } catch (err) {
    console.log("Pinecone API unavailable:", err)
  }
  
  // FINAL FALLBACK: Return empty with error message
  return NextResponse.json({
    models: [],
    total: 0,
    limit,
    offset,
    message: "Failed to fetch models from all sources (OpenRouter, Backend, Pinecone)",
    error: "All data sources unavailable",
  })
}
