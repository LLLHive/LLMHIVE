const content = `# LLMHive LLMs.txt
site: https://www.llmhive.ai
sitemap: https://www.llmhive.ai/sitemap.xml

## Core
- https://www.llmhive.ai/landing
- https://www.llmhive.ai/pricing
- https://www.llmhive.ai/models
- https://www.llmhive.ai/orchestration
- https://www.llmhive.ai/discover

## Comparisons and Guides
- https://www.llmhive.ai/comparisons
- https://www.llmhive.ai/comparisons/best-ai-assistant-for
- https://www.llmhive.ai/best-ai-assistant-for
- https://www.llmhive.ai/best-for
- https://www.llmhive.ai/alternatives
- https://www.llmhive.ai/use-cases
- https://www.llmhive.ai/industries

## Proof
- https://www.llmhive.ai/case-studies
`

export async function GET(): Promise<Response> {
  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  })
}
