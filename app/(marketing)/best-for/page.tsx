import Link from "next/link"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Best For",
  description:
    "Discover the best LLMHive use cases for teams, enterprises, developers, and research workflows.",
  alternates: {
    canonical: "https://www.llmhive.ai/best-for",
  },
  openGraph: {
    title: "LLMHive Best For",
    description:
      "Discover the best LLMHive use cases for teams, enterprises, developers, and research workflows.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Best For",
    description:
      "Discover the best LLMHive use cases for teams, enterprises, developers, and research workflows.",
  },
}

const bestFor = [
  {
    title: "Enterprise AI Teams",
    summary:
      "Unified model access, governance, and cost control for large organizations.",
  },
  {
    title: "Engineering & Product",
    summary:
      "Best‑model routing for coding, analysis, and product research with consistent quality.",
  },
  {
    title: "Research & Knowledge Work",
    summary:
      "RAG‑ready workflows for accurate answers and faster insights across domains.",
  },
  {
    title: "Marketing & Content",
    summary:
      "Multi‑model content generation with quality checks and brand‑safe workflows.",
  },
  {
    title: "Operations & Finance",
    summary:
      "Reliable analysis and reporting with model selection tuned for precision.",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "LLMHive Best For",
        itemListElement: bestFor.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Best For",
            item: "https://www.llmhive.ai/best-for",
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

export default function BestForPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive Best For</h1>
          <p className="mt-2 text-muted-foreground">
            The highest‑impact use cases for multi‑model orchestration in modern teams.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {bestFor.map((item) => (
            <div key={item.title} className="rounded-2xl border border-border/60 bg-card/40 p-6">
              <h2 className="text-lg font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
            </div>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Role-based guides, comparisons, and use cases for deeper evaluation.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/use-cases" className="text-[var(--bronze)]">
              Use Cases →
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
