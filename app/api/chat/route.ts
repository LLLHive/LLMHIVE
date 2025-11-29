import { NextRequest, NextResponse } from "next/server"

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
    const payload = {
      prompt,
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
      metadata: {
        chat_id: chatId || null,
        user_id: userId || null,
        project_id: projectId || null,
      },
      history,
    }

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
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout
      
      response = await fetch(`${apiBase}/v1/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)
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

    // Extract the message content
    const messageContent = data.message || "No response received"

    // Return as streaming response (frontend expects stream)
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
