import type { Metadata } from "next"
import Link from "next/link"
import { useCases } from "./content"

export const metadata: Metadata = {
  title: "LLMHive Use Cases",
  description:
    "Explore LLMHive use cases for enterprise, engineering, research, marketing, and support teams.",
  alternates: {
    canonical: "https://www.llmhive.ai/use-cases",
  },
  openGraph: {
    title: "LLMHive Use Cases",
    description:
      "Explore LLMHive use cases for enterprise, engineering, research, marketing, and support teams.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Use Cases",
    description:
      "Explore LLMHive use cases for enterprise, engineering, research, marketing, and support teams.",
  },
}

const useCaseSnapshot = [
  {
    slug: "enterprise-ai",
    outcome: "Standardize enterprise AI workflows",
    advantage: "Governance + multi-model routing",
  },
  {
    slug: "engineering-and-product",
    outcome: "Ship faster with AI copilots",
    advantage: "Task-aware model selection",
  },
  {
    slug: "research-and-knowledge",
    outcome: "Improve research accuracy",
    advantage: "RAG + evaluation controls",
  },
  {
    slug: "marketing-and-content",
    outcome: "Scale content production",
    advantage: "Quality guardrails + cost control",
  },
  {
    slug: "customer-support",
    outcome: "Reduce ticket resolution time",
    advantage: "Routing + knowledge integration",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "LLMHive Use Cases",
        itemListElement: useCases.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/use-cases/${item.slug}`,
        })),
      },
      {
        "@type": "ItemList",
        name: "Use Case Outcome Snapshot",
        itemListElement: useCaseSnapshot.map((item, index) => {
          const title = useCases.find((useCase) => useCase.slug === item.slug)?.title || item.slug
          return {
            "@type": "ListItem",
            position: index + 1,
            name: `${title}: ${item.advantage}`,
          }
        }),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Use Cases",
            item: "https://www.llmhive.ai/use-cases",
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

export default function UseCasesPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive Use Cases</h1>
          <p className="mt-2 text-muted-foreground">
            The highest-impact workflows for multi-model AI orchestration.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {useCases.map((item) => (
            <Link
              key={item.slug}
              href={`/use-cases/${item.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <h2 className="text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">View use case →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Use Case Outcome Snapshot</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A quick view of the outcomes and LLMHive advantages by use case.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-muted-foreground">
              <thead>
                <tr className="border-b border-border/60 text-left">
                  <th className="py-2 pr-4 text-foreground">Use Case</th>
                  <th className="py-2 pr-4 text-foreground">Primary Outcome</th>
                  <th className="py-2 text-foreground">LLMHive Advantage</th>
                </tr>
              </thead>
              <tbody>
                {useCaseSnapshot.map((item) => {
                  const title =
                    useCases.find((useCase) => useCase.slug === item.slug)?.title || item.slug
                  return (
                    <tr key={item.slug} className="border-b border-border/30">
                      <td className="py-2 pr-4">{title}</td>
                      <td className="py-2 pr-4">{item.outcome}</td>
                      <td className="py-2">{item.advantage}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare LLMHive and explore role-based guides.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
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
