export async function POST(req: Request) {
  try {
    const { messages, model, reasoningMode, criteriaSettings } = await req.json()

    const temperature = criteriaSettings?.creativity
      ? criteriaSettings.creativity / 100
      : reasoningMode === "deep"
        ? 0.3
        : reasoningMode === "fast"
          ? 0.9
          : 0.7

    console.log("[v0] Chat request:", { model, reasoningMode, criteriaSettings, temperature })

    // Mock response for now - in production, you would integrate with actual AI APIs
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        const responseText = `This is a simulated response from ${model}. In production, this would connect to the actual AI model via API. Your message was: "${messages[messages.length - 1]?.content}"`

        // Stream the response word by word
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
    return new Response(JSON.stringify({ error: "Failed to generate response" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }
}
