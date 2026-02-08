import type { Metadata } from "next"
import Link from "next/link"
import { industryRoles } from "./content"

export const metadata: Metadata = {
  title: "Industry AI Comparisons",
  description:
    "See how LLMHive compares for industry-specific AI use cases across legal, finance, healthcare, support, and SaaS.",
  alternates: {
    canonical: "https://www.llmhive.ai/comparisons/industries",
  },
  openGraph: {
    title: "Industry AI Comparisons",
    description:
      "See how LLMHive compares for industry-specific AI use cases across legal, finance, healthcare, support, and SaaS.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Industry AI Comparisons",
    description:
      "See how LLMHive compares for industry-specific AI use cases across legal, finance, healthcare, support, and SaaS.",
  },
}

const industryComparisons = [
  {
    title: "LLMHive vs Legal AI Tools",
    href: "/comparisons/llmhive-vs-legal-ai",
    summary: "Legal research, drafting, and compliance with enterprise-grade routing.",
  },
  {
    title: "LLMHive vs Finance AI Tools",
    href: "/comparisons/llmhive-vs-finance-ai",
    summary: "Financial analysis, reporting, and governance with task-aware routing.",
  },
  {
    title: "LLMHive vs Healthcare AI Tools",
    href: "/comparisons/llmhive-vs-healthcare-ai",
    summary: "Clinical documentation and research with domain-aware orchestration.",
  },
  {
    title: "LLMHive vs Support AI Tools",
    href: "/comparisons/llmhive-vs-support-ai",
    summary: "Customer support automation with quality and cost controls.",
  },
  {
    title: "LLMHive vs SaaS AI Tools",
    href: "/comparisons/llmhive-vs-saas-ai",
    summary: "Platform-wide AI workflows beyond single-product assistants.",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "Industry Comparisons",
        itemListElement: industryComparisons.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai${item.href}`,
        })),
      },
      {
        "@type": "ItemList",
        name: "Industry Role Guides",
        itemListElement: industryRoles.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/comparisons/industries/${item.slug}`,
        })),
      },
      {
        "@type": "ItemList",
        name: "Industry Tool Comparisons",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Legal Tool Comparisons",
            url: "https://www.llmhive.ai/comparisons/industries/legal-teams",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Finance Tool Comparisons",
            url: "https://www.llmhive.ai/comparisons/industries/finance-teams",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: "Healthcare Tool Comparisons",
            url: "https://www.llmhive.ai/comparisons/industries/healthcare-teams",
          },
          {
            "@type": "ListItem",
            position: 4,
            name: "Support Tool Comparisons",
            url: "https://www.llmhive.ai/comparisons/industries/support-teams",
          },
          {
            "@type": "ListItem",
            position: 5,
            name: "SaaS Tool Comparisons",
            url: "https://www.llmhive.ai/comparisons/industries/saas-teams",
          },
        ],
      },
      {
        "@type": "ItemList",
        name: "Industry Comparison Table",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Legal: Multi-model legal routing + governance vs Research-first workflows",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Finance: Precision routing for analysis + reporting vs Data platform workflows",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: "Healthcare: Domain routing + compliance controls vs Clinical documentation",
          },
          {
            "@type": "ListItem",
            position: 4,
            name: "Support: Task-aware routing + knowledge base RAG vs Ticketing automation",
          },
          {
            "@type": "ListItem",
            position: 5,
            name: "SaaS: Cross-team orchestration + governance vs Onboarding and growth",
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
          {
            "@type": "ListItem",
            position: 2,
            name: "Industry Comparisons",
            item: "https://www.llmhive.ai/comparisons/industries",
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

export default function IndustryComparisonsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">Industry AI Comparisons</h1>
          <p className="mt-2 text-muted-foreground">
            Industry-specific comparisons to evaluate LLMHive against specialized AI tools.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="space-y-12">
          <section>
            <h2 className="text-2xl font-semibold">Industry Comparisons</h2>
            <div className="mt-6 grid gap-6 md:grid-cols-2">
              {industryComparisons.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
                >
                  <h3 className="text-xl font-semibold">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
                  <p className="mt-4 text-sm text-[var(--bronze)]">Read comparison →</p>
                </Link>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold">Industry Role Guides</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Role-focused guidance tailored to industry teams.
            </p>
            <div className="mt-6 grid gap-6 md:grid-cols-2">
              {industryRoles.map((item) => (
                <Link
                  key={item.slug}
                  href={`/comparisons/industries/${item.slug}`}
                  className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
                >
                  <h3 className="text-xl font-semibold">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
                  <p className="mt-4 text-sm text-[var(--bronze)]">View guide →</p>
                </Link>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold">Industry Tool Comparisons</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Side-by-side comparisons for industry-specific tools.
            </p>
            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <Link
                href="/comparisons/industries/legal-teams"
                className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
              >
                <h3 className="text-xl font-semibold">Legal Tool Comparisons</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Compare LLMHive with legal AI tools like Harvey.
                </p>
                <p className="mt-4 text-sm text-[var(--bronze)]">View legal comparisons →</p>
              </Link>
              <Link
                href="/comparisons/industries/finance-teams"
                className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
              >
                <h3 className="text-xl font-semibold">Finance Tool Comparisons</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Compare LLMHive with finance AI tools like AlphaSense.
                </p>
                <p className="mt-4 text-sm text-[var(--bronze)]">View finance comparisons →</p>
              </Link>
              <Link
                href="/comparisons/industries/healthcare-teams"
                className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
              >
                <h3 className="text-xl font-semibold">Healthcare Tool Comparisons</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Compare LLMHive with healthcare AI tools like Nuance.
                </p>
                <p className="mt-4 text-sm text-[var(--bronze)]">View healthcare comparisons →</p>
              </Link>
              <Link
                href="/comparisons/industries/support-teams"
                className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
              >
                <h3 className="text-xl font-semibold">Support Tool Comparisons</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Compare LLMHive with support AI tools like Zendesk AI.
                </p>
                <p className="mt-4 text-sm text-[var(--bronze)]">View support comparisons →</p>
              </Link>
              <Link
                href="/comparisons/industries/saas-teams"
                className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
              >
                <h3 className="text-xl font-semibold">SaaS Tool Comparisons</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Compare LLMHive with SaaS AI tools like Intercom AI.
                </p>
                <p className="mt-4 text-sm text-[var(--bronze)]">View SaaS comparisons →</p>
              </Link>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold">Industry Tool Comparison Snapshot</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              A quick view of how LLMHive compares across industries.
            </p>
            <div className="mt-4 overflow-x-auto rounded-2xl border border-border/60 bg-card/40 p-4">
              <table className="w-full text-sm text-muted-foreground">
                <thead>
                  <tr className="border-b border-border/60 text-left">
                    <th className="py-2 pr-4 text-foreground">Industry</th>
                    <th className="py-2 pr-4 text-foreground">LLMHive Advantage</th>
                    <th className="py-2 text-foreground">Typical Tool Focus</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-border/30">
                    <td className="py-2 pr-4">Legal</td>
                    <td className="py-2 pr-4">Multi-model legal routing + governance</td>
                    <td className="py-2">Research-first workflows</td>
                  </tr>
                  <tr className="border-b border-border/30">
                    <td className="py-2 pr-4">Finance</td>
                    <td className="py-2 pr-4">Precision routing for analysis + reporting</td>
                    <td className="py-2">Data platform workflows</td>
                  </tr>
                  <tr className="border-b border-border/30">
                    <td className="py-2 pr-4">Healthcare</td>
                    <td className="py-2 pr-4">Domain routing + compliance controls</td>
                    <td className="py-2">Clinical documentation</td>
                  </tr>
                  <tr className="border-b border-border/30">
                    <td className="py-2 pr-4">Support</td>
                    <td className="py-2 pr-4">Task-aware routing + knowledge base RAG</td>
                    <td className="py-2">Ticketing automation</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">SaaS</td>
                    <td className="py-2 pr-4">Cross-team orchestration + governance</td>
                    <td className="py-2">Onboarding and growth</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold">Industry Role Tool Comparisons</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Role-focused comparisons for industry teams evaluating LLMHive vs specialized tools.
            </p>
            <div className="mt-6">
              <Link
                href="/comparisons/industries/roles"
                className="inline-flex items-center text-[var(--bronze)]"
              >
                View industry role tool comparisons →
              </Link>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold">Industry Case Studies</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              See real deployment outcomes across legal, finance, healthcare, support, and SaaS.
            </p>
            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <Link
                href="/case-studies"
                className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
              >
                <h3 className="text-xl font-semibold">LLMHive Case Studies</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Explore measurable results from industry teams using LLMHive.
                </p>
                <p className="mt-4 text-sm text-[var(--bronze)]">View case studies →</p>
              </Link>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
