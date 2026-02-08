import { notFound } from "next/navigation"
import type { Metadata } from "next"
import Link from "next/link"
import { roles } from "@/app/(marketing)/best-ai-assistant-for/content"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return roles.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = roles.find((item) => item.slug === params.slug)
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
  page: (typeof roles)[number],
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
        mainEntityOfPage: `https://www.llmhive.ai/comparisons/best-ai-assistant-for/${page.slug}`,
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
            name: "Best AI Assistant For",
            item: "https://www.llmhive.ai/comparisons/best-ai-assistant-for",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: page.title,
            item: `https://www.llmhive.ai/comparisons/best-ai-assistant-for/${page.slug}`,
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

export default function BestAssistantComparisonPage({ params }: PageProps) {
  const page = roles.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  const competitorName = "Single-Model Assistant"
  const comparisonRows = [
    {
      feature: "Model Strategy",
      llmhive: "Multi-model routing per task",
      competitor: competitorName,
    },
    {
      feature: "Quality Control",
      llmhive: "Task-aware routing + multi-model evaluation",
      competitor: "Single-model outputs",
    },
    {
      feature: "Cost Optimization",
      llmhive: "Selects lowest-cost model that meets quality",
      competitor: "Fixed pricing per model",
    },
    {
      feature: "Governance",
      llmhive: "Enterprise controls, audit logs, analytics",
      competitor: "Limited controls",
    },
    {
      feature: "Best For",
      llmhive: "Role-based workflows at scale",
      competitor: "General-purpose usage",
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page, comparisonRows)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Role Comparison</p>
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
            Explore related comparisons and role-based guides.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              All Comparisons →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
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
