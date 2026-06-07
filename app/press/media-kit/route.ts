import { getSiteUrl, sitePath } from "@/lib/site-url"
const content = {
  company: {
    name: "LLMHive",
    founded: 2025,
    headquarters: "Miami, Florida",
    website: getSiteUrl(),
    contact_email: "press@llmhive.ai",
    contact_phone: "305-555-0160",
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
    "Benchmark claims are reported by LLMHive and available on request.",
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
