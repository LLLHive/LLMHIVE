export async function POST(req: Request) {
  try {
    const { messages, models, reasoningMode, criteriaSettings } = await req.json()

    const orchestratorUrl = process.env.ORCHESTRATOR_API_BASE_URL

    // If orchestrator is configured, forward the request
    if (orchestratorUrl) {
      console.log("[v0] Forwarding to orchestrator:", orchestratorUrl)

      const response = await fetch(`${orchestratorUrl}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages,
          models: models || ["gpt-4o-mini"], // default model if none selected
          reasoning_mode: reasoningMode || "balanced",
          criteria_settings: criteriaSettings || {},
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("[v0] Orchestrator error:", response.status, errorText)
        throw new Error(`Orchestrator returned ${response.status}: ${errorText}`)
      }

      // Check if response is streaming
      const contentType = response.headers.get("content-type")
      if (contentType?.includes("text/event-stream") || contentType?.includes("text/plain")) {
        // Forward the stream directly
        return new Response(response.body, {
          headers: {
            "Content-Type": "text/plain; charset=utf-8",
            "Transfer-Encoding": "chunked",
          },
        })
      }

      // Handle JSON response
      const data = await response.json()
      const encoder = new TextEncoder()
      const stream = new ReadableStream({
        async start(controller) {
          const responseText = data.response || data.content || data.message || JSON.stringify(data)
          const words = responseText.split(" ")
          for (const word of words) {
            controller.enqueue(encoder.encode(word + " "))
            await new Promise((resolve) => setTimeout(resolve, 30))
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
    }

    // Fallback: Demo mode when orchestrator is not configured
    console.log("[v0] Demo mode - no orchestrator configured")
    const temperature = criteriaSettings?.creativity
      ? criteriaSettings.creativity / 100
      : reasoningMode === "deep"
        ? 0.3
        : reasoningMode === "fast"
          ? 0.9
          : 0.7

    const selectedModels = models?.length > 0 ? models.join(", ") : "default"
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        const responseText = `[Demo Mode] LLMHive is running without a backend connection. Selected agents: ${selectedModels}. To enable AI responses, configure ORCHESTRATOR_API_BASE_URL environment variable. Your message: "${messages[messages.length - 1]?.content}"`

        const words = responseText.split(" ")
        for (const word of words) {
          controller.enqueue(encoder.encode(word + " "))
          await new Promise((resolve) => setTimeout(resolve, 50))
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
  } catch (error) {
    console.error("[v0] Chat API error:", error)
    return new Response(JSON.stringify({ error: "Failed to generate response", details: String(error) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }
}
