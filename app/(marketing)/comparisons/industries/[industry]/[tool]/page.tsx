import { notFound } from "next/navigation"
import type { Metadata } from "next"
import Link from "next/link"
import { industryToolComparisons } from "../../tools"

type PageProps = {
  params: { industry: string; tool: string }
}

export function generateStaticParams() {
  return industryToolComparisons.map((item) => ({
    industry: item.industry,
    tool: item.tool,
  }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = industryToolComparisons.find(
    (item) => item.industry === params.industry && item.tool === params.tool
  )
  if (!page) {
    return { title: "LLMHive" }
  }
  return {
    title: page.title,
    description: page.description,
    openGraph: {
      title: page.title,
      description: page.description,
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.description,
    },
  }
}

function renderStructuredData(
  page: (typeof industryToolComparisons)[number],
  comparisonRows: { feature: string; llmhive: string; competitor: string }[]
) {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "TechArticle",
        headline: page.title,
        description: page.description,
        author: {
          "@type": "Organization",
          name: "LLMHive",
        },
        mainEntityOfPage: `https://www.llmhive.ai/comparisons/industries/${page.industry}/${page.tool}`,
      },
      {
        "@type": "FAQPage",
        mainEntity: page.faq.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      },
      {
        "@type": "ItemList",
        name: "Comparison Table",
        itemListElement: comparisonRows.map((row, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: `${row.feature}: LLMHive vs ${row.competitor}`,
        })),
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
          {
            "@type": "ListItem",
            position: 2,
            name: "Industry Comparisons",
            item: "https://www.llmhive.ai/comparisons/industries",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: page.title,
            item: `https://www.llmhive.ai/comparisons/industries/${page.industry}/${page.tool}`,
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

export default function IndustryToolComparisonPage({ params }: PageProps) {
  const page = industryToolComparisons.find(
    (item) => item.industry === params.industry && item.tool === params.tool
  )
  if (!page) {
    notFound()
  }

  const competitorName = page.title.replace("LLMHive vs ", "").replace(" for", "")
  const comparisonRows = [
    {
      feature: "Model Strategy",
      llmhive: "Multi-model routing per task",
      competitor: competitorName,
    },
    {
      feature: "Quality Control",
      llmhive: "Task-aware routing + multi-model evaluation",
      competitor: "Fixed workflow or single model stack",
    },
    {
      feature: "Cost Optimization",
      llmhive: "Selects lowest-cost model that meets quality",
      competitor: "Cost tied to platform or tier",
    },
    {
      feature: "Governance",
      llmhive: "Enterprise controls, audit logs, analytics",
      competitor: "Tool-specific controls",
    },
    {
      feature: "Best For",
      llmhive: "Cross-team workflows and orchestration",
      competitor: "Single-product workflows",
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page, comparisonRows)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Industry Tool Comparison</p>
          <h1 className="text-3xl md:text-4xl font-bold">{page.title}</h1>
          <p className="mt-2 text-muted-foreground">{page.description}</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12 space-y-10">
        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Quick Answer</h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{page.answer}</p>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Why LLMHive</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.bullets.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Comparison Table</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-muted-foreground">
              <thead>
                <tr className="border-b border-border/60 text-left">
                  <th className="py-2 pr-4 text-foreground">Feature</th>
                  <th className="py-2 pr-4 text-foreground">LLMHive</th>
                  <th className="py-2 text-foreground">{competitorName}</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.feature} className="border-b border-border/30">
                    <td className="py-2 pr-4">{row.feature}</td>
                    <td className="py-2 pr-4">{row.llmhive}</td>
                    <td className="py-2">{row.competitor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">FAQ</h2>
          <div className="mt-4 space-y-4">
            {page.faq.map((item) => (
              <div key={item.question}>
                <h3 className="text-sm font-semibold">{item.question}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{item.answer}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Next Steps</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Explore industry comparisons and role-based guides.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href="/industries" className="text-[var(--bronze)]">
              Industry FAQs →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              All Comparisons →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
