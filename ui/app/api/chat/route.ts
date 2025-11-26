const MODEL_ID_MAP: Record<string, string> = {
  "gpt-5": "gpt-4.1",
  "gpt-5-mini": "gpt-4o-mini",
  "claude-sonnet-4.5": "claude-3-sonnet-20240229",
  "claude-haiku-4": "claude-3-haiku-20240307",
  "grok-4": "grok-3-mini",
  "grok-4-fast": "grok-3-mini",
  "gemini-2.5-pro": "gemini-2.5-flash",
  "gemini-2.5-flash": "gemini-2.5-flash",
  "llama-4-405b": "deepseek-chat",
}

// Use NEXT_PUBLIC_ prefix for client-accessible env vars, fallback to server-only vars
const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.ORCHESTRATION_API_BASE ||
  process.env.LLMHIVE_API_URL ||
  "http://localhost:8000"
const ORCHESTRATION_ENDPOINT = `${DEFAULT_API_BASE.replace(/\/$/, "")}/api/v1/orchestration/`

function mapModelId(model?: string): string | undefined {
  if (!model) return undefined
  return MODEL_ID_MAP[model] || model
}

export async function POST(req: Request) {
  try {
    const {
      messages = [],
      model,
      models,
      reasoningMode,
      criteriaSettings,
      orchestrationEngine,
      conversationId,
      userId,
      preset,
      useDeepconf,
      useVerification,
      formatStyle,
      clarificationResponse,
      isClarificationResponse,
      originalQuery,
      advancedFeatures: _advancedFeatures,
    } = await req.json()
    const lastUserMessage = [...messages].reverse().find((msg) => msg.role === "user")

    if (!lastUserMessage?.content) {
      return new Response(JSON.stringify({ error: "No user prompt provided." }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      })
    }

    const payload: Record<string, unknown> = {
      prompt: lastUserMessage.content,
      enable_memory: true,
      enable_knowledge: false,
    }

    if (conversationId != null) {
      payload.conversation_id = conversationId
    }
    if (userId) {
      payload.user_id = userId
    }
    
    // Map orchestrationEngine to protocol (backend expects 'protocol' field)
    if (orchestrationEngine) {
      payload.protocol = orchestrationEngine
    }
    
    // UI-Backend Integration: Determine mode based on criteriaSettings and send full slider values
    if (criteriaSettings) {
      const { accuracy, speed, creativity } = criteriaSettings
      
      // Determine mode based on settings
      if (accuracy >= 90 && speed <= 50) {
        payload.mode = "accurate"
      } else if (speed >= 90 && accuracy <= 50) {
        payload.mode = "fast"
      } else {
        payload.mode = "balanced"
      }
      
      // Send full slider values for fine-grain control
      payload.criteria = criteriaSettings
      // Also keep criteria_settings for backward compatibility
      payload.criteria_settings = criteriaSettings
    }
    
    // UI-Backend Integration: Send domain preset
    if (preset) {
      payload.preset = preset
    }
    
    // UI-Backend Integration: Send feature toggles
    if (useDeepconf !== undefined) {
      payload.use_deepconf = useDeepconf
    }
    if (useVerification !== undefined) {
      payload.use_verification = useVerification
    }
    
    // Answer Formatting: Send format style
    if (formatStyle) {
      payload.format_style = formatStyle
    }
    
    // Clarification Loop: Send clarification parameters
    if (clarificationResponse) {
      payload.clarification_response = clarificationResponse
    }
    if (isClarificationResponse !== undefined) {
      payload.is_clarification_response = isClarificationResponse
    }
    if (originalQuery) {
      payload.original_query = originalQuery
    }

    // Normalise models selection:
    // - Accept either a single `model` string
    //   OR a `models` array from the UI
    // - Map each to the backend's canonical IDs.
    const rawModels: string[] = Array.isArray(models)
      ? models
      : model
        ? [model]
        : []
    const mappedModels = rawModels
      .map((m) => mapModelId(m))
      .filter((m): m is string => Boolean(m))

    if (mappedModels.length > 0) {
      // Deduplicate while preserving the caller's ordering.
      payload.models = Array.from(new Set(mappedModels))
    }

    const backendResponse = await fetch(ORCHESTRATION_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })

    if (!backendResponse.ok) {
      const detailText = await backendResponse.text()
      console.error("[LLMHive] Orchestrator error:", backendResponse.status, detailText)
      let detail: unknown
      try {
        detail = JSON.parse(detailText)
      } catch {
        detail = { detail: detailText }
      }
      return new Response(
        JSON.stringify({
          error: "Orchestration failed",
          status: backendResponse.status,
          backend: detail,
        }),
        {
          status: backendResponse.status,
          headers: { "Content-Type": "application/json" },
        },
      )
    }

    const orchestration = await backendResponse.json()
    return new Response(
      JSON.stringify({
        orchestration,
        model,
        reasoningMode,
        criteriaSettings,
        conversationId: orchestration.conversation_id,
      }),
      {
      status: 200,
      headers: { "Content-Type": "application/json" },
      },
    )
  } catch (error) {
    console.error("[LLMHive] Chat API error:", error)
    return new Response(JSON.stringify({ error: "Failed to connect to orchestration engine" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }
}
