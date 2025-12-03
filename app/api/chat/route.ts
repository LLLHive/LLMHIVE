import { NextRequest, NextResponse } from "next/server"

// Vercel serverless function configuration
// Extend timeout for multi-model orchestration (Pro plan: up to 300s)
export const maxDuration = 120 // 2 minutes max
export const dynamic = "force-dynamic"

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
  try {
    const body = await req.json()
    const {
      messages,
      models,  // User-selected models from the UI
      orchestratorSettings,
      chatId,
      userId,
      projectId,
    } = body

    // Extract the latest user message as the prompt
    const userMessages = messages?.filter((m: any) => m.role === "user") || []
    const latestUserMessage = userMessages[userMessages.length - 1]
    const prompt = latestUserMessage?.content || ""

    if (!prompt) {
      return NextResponse.json(
        { error: "No prompt provided" },
        { status: 400 }
      )
    }

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

    // Build the ChatRequest payload matching FastAPI ChatRequest model
    // Include models selected by the user - these will be used for multi-model orchestration
    // Filter out "automatic" and use default models if needed
    const DEFAULT_AUTO_MODELS = ["gpt-4o", "claude-sonnet-4", "deepseek-chat"]
    let selectedModels = models || settings.selectedModels || []
    
    // Expand "automatic" to actual models
    if (selectedModels.includes("automatic") || selectedModels.length === 0) {
      selectedModels = DEFAULT_AUTO_MODELS
    } else {
      selectedModels = selectedModels.filter((m: string) => m !== "automatic")
      if (selectedModels.length === 0) {
        selectedModels = DEFAULT_AUTO_MODELS
      }
    }
    
    const payload = {
      prompt,
      models: selectedModels.length > 0 ? selectedModels : null,  // User-selected models for ensemble
      reasoning_mode: settings.reasoningMode || "standard",
      reasoning_method: settings.reasoningMethod || null, // Optional advanced reasoning method
      domain_pack: settings.domainPack || "default",
      agent_mode: settings.agentMode || "team",
      tuning: {
        prompt_optimization: settings.promptOptimization !== false,
        output_validation: settings.outputValidation !== false,
        answer_structure: settings.answerStructure !== false,
        learn_from_chat: (settings.sharedMemory || settings.learnFromChat) !== false,
      },
      // Orchestration Studio settings
      orchestration: {
        accuracy_level: settings.accuracyLevel || 3,
        enable_hrm: settings.enableHRM || false,
        enable_prompt_diffusion: settings.enablePromptDiffusion || false,
        enable_deep_consensus: settings.enableDeepConsensus || false,
        enable_adaptive_ensemble: settings.enableAdaptiveEnsemble || false,
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
      orchestration: payload.orchestration,
    })

    // Get backend URL and API key from environment
    const apiBase =
      process.env.ORCHESTRATOR_API_BASE_URL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      "https://llmhive-orchestrator-792354158895.us-east1.run.app"
    
    const apiKey = process.env.LLMHIVE_API_KEY

    // Build headers
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }

    // Add API key header if configured (server-side only, never exposed to browser)
    if (apiKey) {
      headers["X-API-Key"] = apiKey
    }

    // Forward request to FastAPI backend
    let response: Response
    try {
      // Create AbortController for timeout (compatible with all runtimes)
      // Extended timeout for multi-model orchestration
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 110000) // 110 second timeout (below maxDuration)
      
      try {
        response = await fetch(`${apiBase}/v1/chat`, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
          signal: controller.signal,
        })
        clearTimeout(timeoutId)
      } catch (fetchError: any) {
        clearTimeout(timeoutId)
        // Check if it was a timeout/abort
        if (fetchError.name === 'AbortError' || controller.signal.aborted) {
          console.error("[Chat API] Request timeout after 60 seconds")
          return NextResponse.json(
            {
              error: "Request timeout",
              details: "The backend did not respond within 60 seconds",
              backendUrl: apiBase,
            },
            { status: 504 }
          )
        }
        throw fetchError // Re-throw other errors
      }
    } catch (fetchError: any) {
      console.error("[Chat API] Fetch error:", fetchError)
      return NextResponse.json(
        {
          error: "Failed to connect to backend",
          details: fetchError instanceof Error ? fetchError.message : String(fetchError),
          backendUrl: apiBase,
        },
        { status: 503 }
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

      return NextResponse.json(
        {
          error: errorData.detail || `Backend returned ${response.status}`,
          status: response.status,
          backendUrl: apiBase,
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

    console.log("[Chat API] Received from backend:", {
      messageLength: messageContent.length,
      modelsUsed,
      tokensUsed,
      latencyMs,
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
        // Allow frontend to access custom headers
        "Access-Control-Expose-Headers": "X-Models-Used, X-Tokens-Used, X-Latency-Ms",
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

