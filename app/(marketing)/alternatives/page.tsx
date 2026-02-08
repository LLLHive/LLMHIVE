import Link from "next/link"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Alternatives",
  description:
    "Explore LLMHive alternatives and understand when multi-model orchestration outperforms single-model assistants.",
  alternates: {
    canonical: "https://www.llmhive.ai/alternatives",
  },
  openGraph: {
    title: "LLMHive Alternatives",
    description:
      "Explore LLMHive alternatives and understand when multi-model orchestration outperforms single-model assistants.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Alternatives",
    description:
      "Explore LLMHive alternatives and understand when multi-model orchestration outperforms single-model assistants.",
  },
}

const alternatives = [
  {
    name: "ChatGPT",
    summary: "Single‑model assistant optimized for general usage and personal workflows.",
  },
  {
    name: "Claude",
    summary: "Strong long‑form reasoning and writing capabilities.",
  },
  {
    name: "Gemini",
    summary: "Google‑centric assistant with strong integration into Google tools.",
  },
  {
    name: "Perplexity",
    summary: "Search‑first answer engine optimized for citations and research.",
  },
  {
    name: "Copilot",
    summary: "Microsoft ecosystem assistant for Office and enterprise workflows.",
  },
  {
    name: "Jasper",
    summary: "Marketing‑focused AI for content teams.",
  },
  {
    name: "Notion AI",
    summary: "Workspace‑specific assistant inside Notion.",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "LLMHive Alternatives",
        itemListElement: alternatives.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.name,
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Alternatives",
            item: "https://www.llmhive.ai/alternatives",
          },
        ],
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}

export default function AlternativesPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive Alternatives</h1>
          <p className="mt-2 text-muted-foreground">
            Compare LLMHive with popular AI assistants and see why multi‑model orchestration
            delivers more consistent quality.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {alternatives.map((item) => (
            <div
              key={item.name}
              className="rounded-2xl border border-border/60 bg-card/40 p-6"
            >
              <h2 className="text-lg font-semibold">{item.name}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
            </div>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore Comparisons</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            See side‑by‑side comparisons for specific tools and use cases.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
            <Link href="/case-studies" className="text-[var(--bronze)]">
              Case Studies →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
