const content = {
  company: {
    name: "LLMHive",
    founded: 2025,
    headquarters: "Miami, Florida",
    website: "https://www.llmhive.ai",
    contact_email: "press@llmhive.ai",
    contact_phone: "305-555-0160",
  },
  quick_links: {
    landing: "https://www.llmhive.ai/landing",
    orchestration: "https://www.llmhive.ai/orchestration",
    models: "https://www.llmhive.ai/models",
    comparisons: "https://www.llmhive.ai/comparisons",
    case_studies: "https://www.llmhive.ai/case-studies",
    demo: "https://www.llmhive.ai/demo",
  },
  press_assets: {
    logo: "https://www.llmhive.ai/logo.png",
    placeholder_logo: "https://www.llmhive.ai/placeholder-logo.svg",
  },
  press_releases: {
    long: "https://www.llmhive.ai/press/press-release-long",
    wire: "https://www.llmhive.ai/press/press-release-wire",
  },
  fact_sheet: "https://www.llmhive.ai/press/fact-sheet",
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
