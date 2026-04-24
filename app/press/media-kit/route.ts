const content = {
  company: {
    name: "LLMHive",
    founded: 2025,
    headquarters: "Miami, Florida",
    website: "https://llmhive.ai",
    contact_email: "press@llmhive.ai",
    contact_phone: "305-555-0160",
  },
  quick_links: {
    landing: "https://llmhive.ai/landing",
    orchestration: "https://llmhive.ai/orchestration",
    models: "https://llmhive.ai/models",
    comparisons: "https://llmhive.ai/comparisons",
    case_studies: "https://llmhive.ai/case-studies",
    demo: "https://llmhive.ai/demo",
  },
  press_assets: {
    logo: "https://llmhive.ai/logo.png",
    placeholder_logo: "https://llmhive.ai/placeholder-logo.svg",
  },
  press_releases: {
    long: "https://llmhive.ai/press/press-release-long",
    wire: "https://llmhive.ai/press/press-release-wire",
  },
  fact_sheet: "https://llmhive.ai/press/fact-sheet",
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
