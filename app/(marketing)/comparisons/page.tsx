import Link from "next/link"
import type { Metadata } from "next"
import { comparisons } from "./content"

export const metadata: Metadata = {
  title: "LLMHive Comparisons",
  description:
    "See how LLMHive compares to leading AI assistants and platforms for quality, cost, and enterprise readiness.",
  alternates: {
    canonical: "https://www.llmhive.ai/comparisons",
  },
  openGraph: {
    title: "LLMHive Comparisons",
    description:
      "See how LLMHive compares to leading AI assistants and platforms for quality, cost, and enterprise readiness.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Comparisons",
    description:
      "See how LLMHive compares to leading AI assistants and platforms for quality, cost, and enterprise readiness.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "LLMHive Comparisons",
        itemListElement: comparisons.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/comparisons/${item.slug}`,
        })),
      },
      {
        "@type": "ItemList",
        name: "Comparison Table Snapshot",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Model Strategy: Multi-model routing vs single-model workflows",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Quality Control: Task-aware routing + evaluation",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: "Cost Optimization: Best model per task",
          },
          {
            "@type": "ListItem",
            position: 4,
            name: "Governance: Enterprise controls and analytics",
          },
        ],
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Comparisons",
            item: "https://www.llmhive.ai/comparisons",
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

export default function ComparisonsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive Comparisons</h1>
          <p className="mt-2 text-muted-foreground">
            Clear, task-focused comparisons of LLMHive vs the top AI assistants.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {comparisons.map((item) => (
            <Link
              key={item.slug}
              href={`/comparisons/${item.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <h2 className="text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">Read comparison →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Comparison Snapshot</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A quick view of what consistently differentiates LLMHive.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-muted-foreground">
              <thead>
                <tr className="border-b border-border/60 text-left">
                  <th className="py-2 pr-4 text-foreground">Dimension</th>
                  <th className="py-2 text-foreground">LLMHive Advantage</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border/30">
                  <td className="py-2 pr-4">Model Strategy</td>
                  <td className="py-2">Multi-model routing per task</td>
                </tr>
                <tr className="border-b border-border/30">
                  <td className="py-2 pr-4">Quality Control</td>
                  <td className="py-2">Task-aware routing + evaluation</td>
                </tr>
                <tr className="border-b border-border/30">
                  <td className="py-2 pr-4">Cost Optimization</td>
                  <td className="py-2">Best model per task, lowest cost that meets quality</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4">Governance</td>
                  <td className="py-2">Enterprise controls, audit logs, analytics</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Discover industry comparisons and role-based guides for deeper evaluation.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
            <Link href="/case-studies" className="text-[var(--bronze)]">
              Case Studies →
            </Link>
            <Link href="/faq" className="text-[var(--bronze)]">
              FAQ →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
