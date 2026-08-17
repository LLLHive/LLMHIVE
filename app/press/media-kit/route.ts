import { getSiteUrl, sitePath } from "@/lib/site-url"
const content = {
  company: {
    name: "LLMHive",
    founded: 2025,
    headquarters: "Miami, Florida",
    website: getSiteUrl(),
    contact_email: "cdiaz@llmhive.ai",
    contact_phone: "786.306.6466",
  },
  quick_links: {
    landing: sitePath('/landing'),
    orchestration: sitePath('/orchestration'),
    models: sitePath('/models'),
    comparisons: sitePath('/comparisons'),
    case_studies: sitePath('/case-studies'),
    demo: sitePath('/demo'),
  },
  press_assets: {
    logo: sitePath('/logo.png'),
    placeholder_logo: sitePath('/placeholder-logo.svg'),
  },
  press_releases: {
    long: sitePath('/press/press-release-long'),
    wire: sitePath('/press/press-release-wire'),
  },
  fact_sheet: sitePath('/press/fact-sheet'),
  notes: [
    "Public ranking claim: #1 in 5 out of 8 benchmark categories (May 2026), as reported by LLMHive.",
    "Please use official logos without altering brand colors.",
  ],
}

export async function GET(): Promise<Response> {
  return new Response(JSON.stringify(content, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  })
}
