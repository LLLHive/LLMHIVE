import { getSiteUrl } from "@/lib/site-url"

export async function GET(): Promise<Response> {
  const base = getSiteUrl()
  const content = `# LLMHive LLMs.txt
site: ${base}
sitemap: ${base}/sitemap.xml

## Core
- ${base}/landing
- ${base}/pricing
- ${base}/models
- ${base}/orchestration

## Comparisons and Guides
- ${base}/comparisons
- ${base}/comparisons/best-ai-assistant-for
- ${base}/best-ai-assistant-for
- ${base}/best-for
- ${base}/alternatives
- ${base}/use-cases
- ${base}/industries

## Proof
- ${base}/case-studies
`

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  })
}
