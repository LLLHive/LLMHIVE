import { NextRequest, NextResponse } from "next/server"

// Vercel serverless function configuration
// Extend timeout for multi-model orchestration (Pro plan: up to 300s)
export const maxDuration = 300 // 5 minutes max - world-class AI needs time
export const dynamic = "force-dynamic"

// World-class retry configuration
const RETRY_CONFIG = {
  maxRetries: 5,
  initialDelayMs: 1000,
  maxDelayMs: 30000,
  backoffMultiplier: 2,
  retryableStatuses: [502, 503, 504, 429],
}

// Utility: Sleep with exponential backoff
async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Utility: Calculate delay with jitter
function getRetryDelay(attempt: number): number {
  const delay = Math.min(
    RETRY_CONFIG.initialDelayMs * Math.pow(RETRY_CONFIG.backoffMultiplier, attempt),
    RETRY_CONFIG.maxDelayMs
  )
  // Add jitter (±20%) to prevent thundering herd
  const jitter = delay * 0.2 * (Math.random() - 0.5)
  return Math.floor(delay + jitter)
}

// World-class fetch with retry
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  timeoutMs: number = 280000 // 4.5 minutes default
): Promise<Response> {
  let lastError: Error | null = null
  
  for (let attempt = 0; attempt <= RETRY_CONFIG.maxRetries; attempt++) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
      
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)
      
      // If response is OK or not retryable, return it
      if (response.ok || !RETRY_CONFIG.retryableStatuses.includes(response.status)) {
        return response
      }
      
      // Log retry attempt
      console.log(`[Chat API] Attempt ${attempt + 1}/${RETRY_CONFIG.maxRetries + 1} failed with ${response.status}, retrying...`)
      
      // If we have retries left, wait and continue
      if (attempt < RETRY_CONFIG.maxRetries) {
        const delay = getRetryDelay(attempt)
        console.log(`[Chat API] Waiting ${delay}ms before retry...`)
        await sleep(delay)
      } else {
        return response // Return the failed response on last attempt
      }
    } catch (error: any) {
      lastError = error
      
      // Check if it was an abort/timeout
      if (error.name === 'AbortError') {
        console.error(`[Chat API] Attempt ${attempt + 1} timed out after ${timeoutMs}ms`)
        if (attempt < RETRY_CONFIG.maxRetries) {
          const delay = getRetryDelay(attempt)
          await sleep(delay)
          continue
        }
        throw new Error(`Request timed out after ${RETRY_CONFIG.maxRetries + 1} attempts`)
      }
      
      // For network errors, retry
      if (attempt < RETRY_CONFIG.maxRetries) {
        console.log(`[Chat API] Network error on attempt ${attempt + 1}, retrying...`, error.message)
        const delay = getRetryDelay(attempt)
        await sleep(delay)
        continue
      }
      
      throw error
    }
  }
  
  throw lastError || new Error('Max retries exceeded')
}

/**
 * Chat API route - Proxies frontend requests to FastAPI backend.
 * 
 * This route:
 * 1. Receives chat requests from the frontend
 * 2. Transforms them to match the FastAPI ChatRequest format
 * 3. Adds X-API-Key header if LLMHIVE_API_KEY is set
 * 4. Forwards to FastAPI backend at /v1/chat
 * 5. Returns the response to the frontend
 * 
 * Environment variables:
 * - ORCHESTRATOR_API_BASE_URL: Backend API base URL (required)
 * - LLMHIVE_API_KEY: API key for backend authentication (optional)
 */

export async function POST(req: NextRequest) {
  // Debug: Log environment variable status at the start of every request
  // Use fallback URL for Cloud Run backend
  const apiBase = process.env.ORCHESTRATOR_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
  const apiKey = process.env.LLMHIVE_API_KEY
  
  console.log("[Chat API] Environment check:", {
    ORCHESTRATOR_API_BASE_URL: apiBase ? `${apiBase.substring(0, 30)}...` : "NOT SET",
    LLMHIVE_API_KEY: apiKey ? `${apiKey.substring(0, 10)}...` : "NOT SET",
    NODE_ENV: process.env.NODE_ENV,
  })

  // If backend URL is not configured, return helpful error
  if (!apiBase) {
    console.error("[Chat API] CRITICAL: Backend URL not configured!")
    return NextResponse.json(
      {
        error: "Backend not configured",
        details: "ORCHESTRATOR_API_BASE_URL environment variable is not set. Please configure it in Vercel Project Settings → Environment Variables.",
        debug: {
          ORCHESTRATOR_API_BASE_URL: "NOT SET",
          NEXT_PUBLIC_API_BASE_URL: "NOT SET",
        }
      },
      { status: 503 }
    )
  }

  try {
    // Parse request body with detailed error handling
    let body: any
    try {
      body = await req.json()
    } catch (parseError: any) {
      console.error("[Chat API] Failed to parse request body:", parseError.message)
      return NextResponse.json(
        { 
          error: "Invalid request body",
          details: "Failed to parse JSON. Check that your message isn't too long.",
          suggestion: "Try breaking your message into smaller parts."
        },
        { status: 400 }
      )
    }

    const {
      messages,
      models,  // User-selected models from the UI
      orchestratorSettings,
      orchestrationEngine,  // Direct orchestration engine selection (hrm, prompt-diffusion, deep-conf, adaptive-ensemble)
      chatId,
      userId,
      projectId,
    } = body

    // Detailed logging for debugging
    console.log("[Chat API] Request received:", {
      messagesCount: messages?.length || 0,
      hasModels: !!models,
      hasSettings: !!orchestratorSettings,
      chatId: chatId?.substring(0, 10) || "none",
    })

    // Extract the latest user message as the prompt
    const userMessages = messages?.filter((m: any) => m.role === "user") || []
    const latestUserMessage = userMessages[userMessages.length - 1]
    const prompt = latestUserMessage?.content || ""

    // Enhanced empty prompt debugging
    if (!prompt) {
      console.error("[Chat API] Empty prompt received:", {
        totalMessages: messages?.length || 0,
        userMessages: userMessages.length,
        latestHasContent: !!latestUserMessage?.content,
        contentType: typeof latestUserMessage?.content,
        contentLength: latestUserMessage?.content?.length || 0,
      })
      return NextResponse.json(
        { 
          error: "No prompt provided",
          details: "Your message appears to be empty. Please enter a message and try again.",
          debug: process.env.NODE_ENV === 'development' ? {
            messagesReceived: messages?.length || 0,
            userMessagesFound: userMessages.length,
          } : undefined
        },
        { status: 400 }
      )
    }

    // Log prompt info (truncated for security)
    console.log("[Chat API] Processing prompt:", {
      length: prompt.length,
      preview: prompt.substring(0, 50) + (prompt.length > 50 ? "..." : ""),
    })

    // Build conversation history in the format expected by backend
    const history = (messages || []).map((m: any) => ({
      role: m.role,
      content: m.content,
    }))

    // Get orchestrator settings with defaults
    const settings = orchestratorSettings || {
      reasoningMode: "standard",
      domainPack: "default",
      agentMode: "team",
      promptOptimization: true,
      outputValidation: true,
      answerStructure: true,
      learnFromChat: true,
    }

    // Detect if the query needs real-time data (temporal indicators)
    const TEMPORAL_PATTERNS = [
      /\b(today|now|current|currently|latest|recent|newest|as of|this year|this month|this week|2024|2025)\b/i,
      /\b(right now|at the moment|presently|these days)\b/i,
    ]
    const needsRealtimeData = TEMPORAL_PATTERNS.some(p => p.test(prompt))
    
    if (needsRealtimeData) {
      console.log("[Chat API] Temporal query detected, enabling live research:", prompt.slice(0, 50))
    }

    // Build the ChatRequest payload matching FastAPI ChatRequest model
    // Include models selected by the user - these will be used for multi-model orchestration
    // When "automatic" is selected, pass empty/null to let backend do intelligent selection
    let selectedModels = models || settings.selectedModels || []
    
    // Check if user wants automatic intelligent selection
    const isAutomaticMode = (
      selectedModels.length === 0 ||
      selectedModels.includes("automatic") ||
      (selectedModels.length === 1 && selectedModels[0] === "automatic")
    )
    
    if (isAutomaticMode) {
      // Let the backend's intelligent model selection handle this
      // It will use: task detection, domain analysis, rankings data, reasoning requirements
      selectedModels = []  // Empty = let backend decide
      console.log("[Chat API] Automatic mode: Backend will select optimal models for query")
    } else {
      // User selected specific models - filter out any "automatic" placeholder
      selectedModels = selectedModels.filter((m: string) => m !== "automatic")
      console.log("[Chat API] User-selected models:", selectedModels)
    }

    // Map advanced reasoning methods to the first non-automatic method selected
    // This connects the UI reasoning method selection to the backend
    const advancedMethods = settings.advancedReasoningMethods || []
    const selectedReasoningMethod = advancedMethods.find((m: string) => m !== "automatic") || null
    
    // Determine elite strategy from settings (maps to backend orchestration strategy)
    const eliteStrategy = settings.eliteStrategy !== "automatic" ? settings.eliteStrategy : null
    
    // Quality options selected by user
    const qualityOptions = settings.qualityOptions || []
    
    // PR6: Extract orchestration overrides from settings
    const orchestrationOverrides = settings.orchestrationOverrides || {}
    const modelTeam = settings.modelTeam || orchestrationOverrides.modelTeam || null
    // Budget constraints DISABLED for now - preserves benchmark orchestration
    // Will be enabled for specific account tiers in the future
    // const maxCostUsd = settings.maxCostUsd || orchestrationOverrides.maxCostUsd || null
    // const preferCheaper = settings.preferCheaper || orchestrationOverrides.preferCheaper || false
    const maxCostUsd = null  // Disabled
    const preferCheaper = false  // Disabled
    
    // Map orchestration engine from UI to backend protocol
    // Supports: hrm, prompt-diffusion, deep-conf, adaptive-ensemble
    const protocol = orchestrationEngine || settings.orchestrationEngine || null
    
    // Map frontend format to backend format_style
    // Frontend: automatic, default, structured, bullet-points, step-by-step, academic, concise
    // Backend: paragraph, bullet, numbered, markdown, structured, executive_summary, etc.
    const formatMapping: Record<string, string> = {
      "automatic": "automatic",  // Let backend choose best format
      "default": "paragraph",    // Natural conversational = paragraph
      "structured": "structured", // Headers and sections
      "bullet-points": "bullet", // Bullet list
      "step-by-step": "numbered", // Numbered steps
      "academic": "markdown",     // Formal with citations = markdown
      "concise": "executive_summary", // Brief = executive summary
    }
    const formatStyle = formatMapping[settings.answerFormat || "automatic"] || "automatic"
    
    const payload = {
      prompt,
      models: selectedModels.length > 0 ? selectedModels : null,  // User-selected models for ensemble
      protocol,  // Orchestration protocol/engine (HRM, Prompt Diffusion, DeepConf, Adaptive Ensemble)
      reasoning_mode: settings.reasoningMode || "standard",
      reasoning_method: selectedReasoningMethod, // Map from advancedReasoningMethods dropdown
      domain_pack: settings.domainPack || "default",
      agent_mode: settings.agentMode || "team",
      format_style: formatStyle,  // Answer format: automatic, paragraph, bullet, numbered, structured, etc.
      tuning: {
        prompt_optimization: settings.promptOptimization !== false,
        output_validation: settings.outputValidation !== false,
        answer_structure: settings.answerStructure !== false,
        learn_from_chat: (settings.sharedMemory || settings.learnFromChat) !== false,
      },
      // Orchestration Studio settings
      orchestration: {
        accuracy_level: settings.accuracyLevel || 3,
        // Engine mode: "automatic" lets backend choose, "manual" uses explicit settings
        engines_mode: settings.enginesMode || "automatic",
        enable_hrm: settings.enableHRM || false,
        enable_prompt_diffusion: settings.enablePromptDiffusion || false,
        enable_deep_consensus: settings.enableDeepConsensus || false,
        enable_adaptive_ensemble: settings.enableAdaptiveEnsemble || false,
        // NEW: Elite orchestration settings from UI
        elite_strategy: eliteStrategy,
        quality_options: qualityOptions.length > 0 ? qualityOptions : null,
        // Standard LLM parameters
        temperature: settings.standardValues?.temperature ?? 0.7,
        max_tokens: settings.standardValues?.maxTokens ?? 2000,
        top_p: settings.standardValues?.topP ?? 0.9,
        frequency_penalty: settings.standardValues?.frequencyPenalty ?? 0,
        presence_penalty: settings.standardValues?.presencePenalty ?? 0,
        // Feature toggles
        enable_tool_broker: settings.enableToolBroker !== false,
        enable_verification: settings.enableVerification !== false,
        enable_vector_rag: settings.advancedFeatures?.includes("vector-rag") || false,
        enable_memory: settings.advancedFeatures?.includes("memory-augmentation") || false,
        // Real-time data: auto-enabled for temporal queries, or manually via settings
        enable_live_research: needsRealtimeData || settings.enableLiveResearch || false,
        // PR5 & PR6: Budget-aware routing
        max_cost_usd: maxCostUsd,
        prefer_cheaper_models: preferCheaper,
        // PR6: Model team override
        model_team: modelTeam,
        // PR6: Refinement/verification controls
        enable_refinement: orchestrationOverrides.enableRefinement ?? true,
        max_iterations: orchestrationOverrides.maxIterations ?? 3,
      },
      metadata: {
        chat_id: chatId || null,
        user_id: userId || null,
        project_id: projectId || null,
        // Dynamic Criteria Equalizer settings
        criteria: settings.criteria || { accuracy: 70, speed: 70, creativity: 50 },
      },
      history,
    }
    
    console.log("[Chat API] Sending to backend:", {
      prompt: prompt.slice(0, 50) + "...",
      models: selectedModels,
      protocol,
      format_style: formatStyle,
      orchestration: payload.orchestration,
      backendUrl: apiBase,
    })

    // Build headers
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }

    // Add API key header if configured (server-side only, never exposed to browser)
    if (apiKey) {
      headers["X-API-Key"] = apiKey
    }

    // Forward request to FastAPI backend with world-class retry logic
    let response: Response
    try {
      console.log("[Chat API] Initiating request with retry logic (max 5 retries, exponential backoff)")
      
      response = await fetchWithRetry(
        `${apiBase}/v1/chat`,
        {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        },
        280000 // 4.5 minute timeout per attempt
      )
    } catch (fetchError: any) {
      console.error("[Chat API] All retry attempts failed:", fetchError)
      
      // Provide user-friendly error messages
      const isTimeout = fetchError.message?.includes('timeout') || fetchError.name === 'AbortError'
      const isNetworkError = fetchError.message?.includes('network') || fetchError.message?.includes('ECONNREFUSED')
      
      return NextResponse.json(
        {
          error: isTimeout 
            ? "Our AI is processing a complex request. Please try again in a moment."
            : isNetworkError
            ? "We're experiencing temporary connectivity issues. Please retry."
            : "Failed to connect to our AI service",
          details: process.env.NODE_ENV === 'development' 
            ? fetchError instanceof Error ? fetchError.message : String(fetchError)
            : undefined,
          retryable: true,
          suggestion: "Try simplifying your query or breaking it into smaller questions.",
        },
        { status: isTimeout ? 504 : 503 }
      )
    }

    if (!response.ok) {
      const errorText = await response.text()
      let errorData
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { detail: errorText }
      }

      console.error(
        `[Chat API] FastAPI error: ${response.status}`,
        errorData,
        `Backend URL: ${apiBase}`
      )

      // Map technical errors to user-friendly messages
      const userFriendlyErrors: Record<number, string> = {
        400: "There was an issue with your request. Please rephrase and try again.",
        401: "Authentication required. Please sign in again.",
        403: "You don't have access to this feature. Please upgrade your plan.",
        404: "The requested service is temporarily unavailable.",
        422: "Unable to process your request. Please check your input.",
        429: "Our servers are busy. Please wait a moment and try again.",
        500: "We encountered an unexpected error. Our team has been notified.",
        502: "Our AI service is temporarily busy. Please retry in a moment.",
        503: "Service temporarily unavailable. We're working on it.",
        504: "Request took too long. Try a simpler question.",
      }

      return NextResponse.json(
        {
          error: userFriendlyErrors[response.status] || errorData.detail || "An unexpected error occurred",
          technicalDetails: process.env.NODE_ENV === 'development' ? errorData : undefined,
          status: response.status,
          retryable: [429, 502, 503, 504].includes(response.status),
          suggestion: response.status === 429 
            ? "Wait 30 seconds before trying again."
            : response.status >= 500
            ? "Try refreshing the page or contact support if the issue persists."
            : undefined,
        },
        { status: response.status }
      )
    }

    // Parse the ChatResponse from FastAPI
    const data = await response.json()

    // Extract the message content and metadata
    // Ensure we never return empty or placeholder messages
    let messageContent = data.message
    if (!messageContent || messageContent === "No response received" || messageContent.trim() === "") {
      messageContent = "I apologize, but I couldn't generate a response. Please try again."
      console.warn("[Chat API] Empty or invalid message from backend, using fallback")
    }
    
    // Ensure models_used contains actual models, not "automatic"
    let modelsUsed = data.models_used || selectedModels
    if (Array.isArray(modelsUsed)) {
      modelsUsed = modelsUsed.filter((m: string) => m && m !== "automatic")
      if (modelsUsed.length === 0) {
        modelsUsed = selectedModels
      }
    } else {
      modelsUsed = selectedModels
    }
    
    const tokensUsed = data.tokens_used || 0
    const latencyMs = data.latency_ms || 0
    
    // Extract quality metadata from backend response
    const extra = data.extra || {}
    const qualityMetadata = {
      traceId: extra.trace_id || `trace-${Date.now()}`,
      confidence: extra.elite_orchestration?.confidence ?? extra.verification?.confidence ?? 0.85,
      confidenceLabel: extra.verification?.confidence >= 0.9 ? "high" : 
                       extra.verification?.confidence >= 0.7 ? "medium" : "low",
      verificationScore: extra.verification?.confidence,
      issuesFound: extra.verification?.issues_found || 0,
      correctionsApplied: extra.verification?.corrected || false,
      eliteStrategy: extra.elite_orchestration?.strategy,
      consensusScore: extra.elite_orchestration?.consensus_score,
      taskType: extra.task_type,
      cached: extra.source === "knowledge_base_cache",
    }

    console.log("[Chat API] Received from backend:", {
      messageLength: messageContent.length,
      modelsUsed,
      tokensUsed,
      latencyMs,
      qualityMetadata,
    })

    // Return as streaming response with metadata in headers
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        // Stream the message word by word for better UX
        const words = messageContent.split(" ")
        for (const word of words) {
          controller.enqueue(encoder.encode(word + " "))
          await new Promise((resolve) => setTimeout(resolve, 20))
        }
        controller.close()
      },
    })

    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Transfer-Encoding": "chunked",
        // Expose metadata in custom headers
        "X-Models-Used": JSON.stringify(modelsUsed),
        "X-Tokens-Used": String(tokensUsed),
        "X-Latency-Ms": String(latencyMs),
        // Quality metadata for answer insights
        "X-Quality-Metadata": JSON.stringify(qualityMetadata),
        // Allow frontend to access custom headers
        "Access-Control-Expose-Headers": "X-Models-Used, X-Tokens-Used, X-Latency-Ms, X-Quality-Metadata",
      },
    })
  } catch (error: any) {
    console.error("[Chat API] Error:", error)
    return NextResponse.json(
      {
        error: "Failed to generate response",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    )
  }
}

