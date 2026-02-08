const content = `LLMHive Fact Sheet

Overview
LLMHive is a multi-model AI orchestration platform that routes complex tasks to specialized models, cross-verifies outputs, and returns a single, coherent response.

Why It Matters
- Reduces hallucinations through multi-model critique loops.
- Improves accuracy across diverse tasks without manual model switching.
- Optimizes cost by invoking only the expert models needed.

Reported Benchmark Highlights
- #1 across 10 categories including GPQA, SWE-Bench, AIME, MMMLU, RAG, and Speed (reported by LLMHive).
- Up to 99.9% lower cost vs. premium single-model APIs (reported).
- Up to 1,575x cheaper on complex queries (reported).

Typical Use Cases
- Legal research and contract analysis
- Financial research and reporting
- Healthcare and clinical summaries
- Customer support automation
- Software development and code review

Availability
Public access: https://www.llmhive.ai/landing

Contact
press@llmhive.ai
`

export async function GET(): Promise<Response> {
  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  })
}
