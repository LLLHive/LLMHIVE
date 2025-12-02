export async function GET() {
  try {
    const orchestratorUrl = process.env.ORCHESTRATOR_API_BASE_URL

    // If orchestrator is configured, fetch agents from backend
    if (orchestratorUrl) {
      const response = await fetch(`${orchestratorUrl}/agents`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      })

      if (response.ok) {
        const agents = await response.json()
        return Response.json(agents)
      }
    }

    // Fallback: Return default agents list (matching frontend model IDs)
    const defaultAgents = [
      { id: "gpt-4o", name: "GPT-4o", provider: "openai", available: true },
      { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "openai", available: true },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic", available: true },
      { id: "claude-3.5-haiku", name: "Claude 3.5 Haiku", provider: "anthropic", available: true },
      { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "google", available: true },
      { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "google", available: true },
      { id: "grok-2", name: "Grok 2", provider: "xai", available: true },
      { id: "deepseek-chat", name: "DeepSeek V3", provider: "deepseek", available: true },
    ]

    return Response.json({ agents: defaultAgents, source: "fallback" })
  } catch (error) {
    console.error("[v0] Agents API error:", error)
    return Response.json({ error: "Failed to fetch agents" }, { status: 500 })
  }
}
