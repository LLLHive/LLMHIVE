import { notFound } from "next/navigation"
import type { Metadata } from "next"
import Link from "next/link"
import { roleIndustryTools } from "../../roles"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return roleIndustryTools.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = roleIndustryTools.find((item) => item.slug === params.slug)
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
  page: (typeof roleIndustryTools)[number],
  comparisonRows: { feature: string; llmhive: string; competitor: string }[],
  faqItems: { question: string; answer: string }[]
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
        mainEntityOfPage: `https://www.llmhive.ai/comparisons/industries/roles/${page.slug}`,
      },
      {
        "@type": "FAQPage",
        mainEntity: faqItems.map((item) => ({
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
            name: "Industry Role Tool Comparisons",
            item: "https://www.llmhive.ai/comparisons/industries/roles",
          },
          {
            "@type": "ListItem",
            position: 4,
            name: page.title,
            item: `https://www.llmhive.ai/comparisons/industries/roles/${page.slug}`,
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

export default function IndustryRoleToolPage({ params }: PageProps) {
  const page = roleIndustryTools.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  const competitorName = page.title.replace("Best AI for ", "").split(":")[1]?.trim() || page.tool
  const comparisonRows = [
    {
      feature: "Model Strategy",
      llmhive: "Multi-model routing per task",
      competitor: competitorName,
    },
    {
      feature: "Quality Control",
      llmhive: "Task-aware routing + multi-model evaluation",
      competitor: "Single-model or fixed workflow",
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
      llmhive: "Role-based workflows at scale",
      competitor: "Single-product workflows",
    },
  ]

  const extendedFaq = [
    {
      question: "How does LLMHive route tasks for this role?",
      answer:
        "LLMHive analyzes the task and selects the most accurate model for that role’s workflow, balancing quality, speed, and cost.",
    },
    {
      question: "Can LLMHive integrate with existing tools?",
      answer:
        "Yes. LLMHive integrates via API and can connect to knowledge bases and operational systems.",
    },
    {
      question: "Is LLMHive enterprise-ready?",
      answer:
        "Enterprise plans include governance, audit logs, and access controls.",
    },
    {
      question: "How does LLMHive protect sensitive data?",
      answer:
        "LLMHive supports access controls, audit logs, and routing policies that keep sensitive data within approved systems.",
    },
    {
      question: "Can we enforce model allowlists for this role?",
      answer:
        "Yes. Admins can define approved models and routing policies for role-specific workflows.",
    },
    {
      question: "How does LLMHive handle evaluation and quality checks?",
      answer:
        "Evaluation workflows let teams compare model outputs and lock in the best-performing routes.",
    },
    {
      question: "What does deployment look like for this team?",
      answer:
        "Most teams start with a pilot workflow, connect data sources, and expand after governance review.",
    },
    {
      question: "How quickly can we see ROI?",
      answer:
        "Teams typically see faster turnaround times and lower model spend within the first quarter.",
    },
    {
      question: "Does LLMHive support role-based access controls?",
      answer:
        "Yes. Role-based permissions ensure only approved users can access sensitive workflows and data.",
    },
    {
      question: "Can we monitor usage and cost by team?",
      answer:
        "Usage analytics and audit logs provide visibility into spend, quality, and adoption by team.",
    },
  ]

  const faqItems = [...page.faq, ...extendedFaq]

  const featureGrid = [
    {
      title: "Routing Intelligence",
      description: "Task-aware model selection for role-specific workflows.",
    },
    {
      title: "Governance",
      description: "Enterprise controls, audit logs, and usage visibility.",
    },
    {
      title: "Cost Optimization",
      description: "Selects the lowest-cost model that meets quality thresholds.",
    },
    {
      title: "Integration",
      description: "Connects to tools and knowledge bases via API.",
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page, comparisonRows, faqItems)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Role Tool Comparison</p>
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
          <h2 className="text-xl font-semibold">Feature Grid</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {featureGrid.map((item) => (
              <div key={item.title} className="rounded-xl border border-border/50 bg-background/40 p-4">
                <h3 className="text-sm font-semibold">{item.title}</h3>
                <p className="mt-2 text-xs text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Decision Criteria</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>• Choose LLMHive for multi-model routing, governance, and cross-team workflows.</li>
            <li>• Choose specialized tools when your scope is limited to a single workflow.</li>
            <li>• Use LLMHive to standardize quality and cost across teams.</li>
          </ul>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Implementation Plan</h2>
          <ol className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>1. Define critical workflows and success criteria.</li>
            <li>2. Connect knowledge sources and integrations.</li>
            <li>3. Route tasks to optimal models and validate outputs.</li>
            <li>4. Establish governance, monitoring, and cost controls.</li>
          </ol>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">ROI Drivers</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>• Higher accuracy reduces rework and escalations.</li>
            <li>• Routing optimization reduces model spend.</li>
            <li>• Unified workflows reduce tool sprawl and onboarding time.</li>
          </ul>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">FAQ</h2>
          <div className="mt-4 space-y-4">
            {faqItems.map((item) => (
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
            <Link href="/comparisons/industries/roles" className="text-[var(--bronze)]">
              Industry Role Comparisons →
            </Link>
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href={`/comparisons/industries/${page.industry}-teams`} className="text-[var(--bronze)]">
              {page.industry} Team Comparisons →
            </Link>
            <Link href={`/comparisons/industries/${page.industry}/${page.tool}`} className="text-[var(--bronze)]">
              {page.tool} Comparison →
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
