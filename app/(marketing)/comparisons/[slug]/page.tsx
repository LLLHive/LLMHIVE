import Link from "next/link"
import { notFound } from "next/navigation"
import type { Metadata } from "next"
import { comparisons } from "../content"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return comparisons.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = comparisons.find((item) => item.slug === params.slug)
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
  page: (typeof comparisons)[number],
  industryFaq: { question: string; answer: string }[],
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
        mainEntityOfPage: `https://www.llmhive.ai/comparisons/${page.slug}`,
      },
      {
        "@type": "FAQPage",
        mainEntity: [...page.faq, ...industryFaq].map((item) => ({
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
            name: page.title,
            item: `https://www.llmhive.ai/comparisons/${page.slug}`,
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

export default function ComparisonDetailPage({ params }: PageProps) {
  const page = comparisons.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  const extraFaq = [
    {
      question: "How much does LLMHive cost?",
      answer:
        "LLMHive offers Free, Lite, Pro, and Enterprise plans. Pricing is designed to scale with team usage and includes multi-model orchestration.",
    },
    {
      question: "Is LLMHive secure for enterprise use?",
      answer:
        "Yes. LLMHive provides enterprise-grade security, access controls, and governance. Enterprise plans include SSO and audit logs.",
    },
    {
      question: "Can I use LLMHive with my existing tools?",
      answer:
        "Yes. LLMHive integrates via API and supports knowledge bases and workflow integrations.",
    },
  ]

  const industryFaqMap: Record<string, { question: string; answer: string }[]> = {
    "llmhive-vs-legal-ai": [
      {
        question: "Is LLMHive appropriate for legal compliance workflows?",
        answer:
          "Yes. LLMHive provides enterprise governance, audit logs, and task-aware routing for legal workflows.",
      },
    ],
    "llmhive-vs-finance-ai": [
      {
        question: "Can LLMHive support financial analysis accuracy?",
        answer:
          "Yes. LLMHive routes finance tasks to models optimized for precision and reasoning.",
      },
    ],
    "llmhive-vs-healthcare-ai": [
      {
        question: "Does LLMHive support healthcare documentation?",
        answer:
          "Yes. LLMHive supports domain routing and governance for healthcare workflows.",
      },
    ],
    "llmhive-vs-support-ai": [
      {
        question: "Can LLMHive reduce support escalations?",
        answer:
          "Yes. LLMHive routes support tasks to the best model and integrates knowledge bases.",
      },
    ],
    "llmhive-vs-saas-ai": [
      {
        question: "Does LLMHive support SaaS onboarding workflows?",
        answer:
          "Yes. LLMHive supports onboarding, support, and product workflows across teams.",
      },
    ],
  }

  const industryFaq = industryFaqMap[page.slug] ?? []

  const competitorName = page.title.replace("LLMHive vs ", "")
  const comparisonRows = [
    {
      feature: "Model Strategy",
      llmhive: "Multi-model routing per task",
      competitor: competitorName,
    },
    {
      feature: "Quality Control",
      llmhive: "Task-aware routing + optional multi-model evaluation",
      competitor: "Single-model or fixed workflow",
    },
    {
      feature: "Cost Optimization",
      llmhive: "Selects lowest-cost model that meets quality",
      competitor: "Cost tied to chosen model or tier",
    },
    {
      feature: "Governance",
      llmhive: "Enterprise controls, audit logs, usage analytics",
      competitor: "Provider-specific controls",
    },
    {
      feature: "Best For",
      llmhive: "Cross-team workflows and enterprise scale",
      competitor: "Single-product or narrow workflow focus",
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page, industryFaq, comparisonRows)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Comparison</p>
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
          <h2 className="text-xl font-semibold">Summary</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.summary.map((item) => (
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

        {page.sections.map((section) => (
          <section key={section.title} className="rounded-2xl border border-border/60 bg-card/40 p-6">
            <h2 className="text-xl font-semibold">{section.title}</h2>
            <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
              {section.points.map((point) => (
                <li key={point}>• {point}</li>
              ))}
            </ul>
          </section>
        ))}

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">FAQ</h2>
          <div className="mt-4 space-y-4">
            {[...page.faq, ...industryFaq, ...extraFaq].map((item) => (
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
            Explore related comparisons and role-based guidance.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              All Comparisons →
            </Link>
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
