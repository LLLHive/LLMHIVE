import type { Metadata } from "next"
import Link from "next/link"
import { industryFaqs } from "./content"

export const metadata: Metadata = {
  title: "Industry AI FAQs",
  description:
    "Industry-specific AI FAQs for legal, finance, healthcare, support, and SaaS teams.",
  alternates: {
    canonical: "https://www.llmhive.ai/industries",
  },
  openGraph: {
    title: "Industry AI FAQs",
    description:
      "Industry-specific AI FAQs for legal, finance, healthcare, support, and SaaS teams.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Industry AI FAQs",
    description:
      "Industry-specific AI FAQs for legal, finance, healthcare, support, and SaaS teams.",
  },
}

const industrySnapshot = [
  {
    slug: "legal",
    focus: "Research, drafting, and compliance",
    advantage: "Multi-model legal routing + governance",
  },
  {
    slug: "finance",
    focus: "Analysis, reporting, and risk",
    advantage: "Precision routing + audit readiness",
  },
  {
    slug: "healthcare",
    focus: "Clinical documentation and research",
    advantage: "Domain routing + data controls",
  },
  {
    slug: "support",
    focus: "Ticket deflection and quality",
    advantage: "Task routing + knowledge integration",
  },
  {
    slug: "saas",
    focus: "Product workflows and enablement",
    advantage: "Cross-team orchestration + governance",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "Industry AI FAQs",
        itemListElement: industryFaqs.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/industries/${item.slug}`,
        })),
      },
      {
        "@type": "ItemList",
        name: "Industry FAQ Snapshot",
        itemListElement: industrySnapshot.map((item, index) => {
          const title = industryFaqs.find((faq) => faq.slug === item.slug)?.title || item.slug
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
            name: "Industries",
            item: "https://www.llmhive.ai/industries",
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

export default function IndustriesPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">Industry AI FAQs</h1>
          <p className="mt-2 text-muted-foreground">
            Industry-specific guidance for evaluating AI orchestration.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {industryFaqs.map((item) => (
            <Link
              key={item.slug}
              href={`/industries/${item.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <h2 className="text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">View FAQ →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Industry FAQ Snapshot</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A fast scan of priority topics and LLMHive strengths by industry.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-muted-foreground">
              <thead>
                <tr className="border-b border-border/60 text-left">
                  <th className="py-2 pr-4 text-foreground">Industry</th>
                  <th className="py-2 pr-4 text-foreground">Priority Focus</th>
                  <th className="py-2 text-foreground">LLMHive Advantage</th>
                </tr>
              </thead>
              <tbody>
                {industrySnapshot.map((item) => {
                  const title =
                    industryFaqs.find((faq) => faq.slug === item.slug)?.title || item.slug
                  return (
                    <tr key={item.slug} className="border-b border-border/30">
                      <td className="py-2 pr-4">{title}</td>
                      <td className="py-2 pr-4">{item.focus}</td>
                      <td className="py-2">{item.advantage}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore Comparisons</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare LLMHive with industry-specific AI tools.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              All Comparisons →
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
