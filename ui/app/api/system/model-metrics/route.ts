const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.ORCHESTRATION_API_BASE ||
  process.env.LLMHIVE_API_URL ||
  "http://localhost:8000"
const METRICS_ENDPOINT = `${DEFAULT_API_BASE.replace(/\/$/, "")}/api/v1/system/model-metrics`

export async function GET() {
  try {
    const res = await fetch(METRICS_ENDPOINT, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    })

    if (!res.ok) {
      const detail = await res.text()
      console.error("[LLMHive] Metrics proxy error:", res.status, detail)
      return new Response(JSON.stringify({ error: "Failed to load model metrics" }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      })
    }

    const data = await res.json()
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })
  } catch (error) {
    console.error("[LLMHive] Metrics proxy exception:", error)
    return new Response(JSON.stringify({ error: "Metrics service unavailable" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }
}


