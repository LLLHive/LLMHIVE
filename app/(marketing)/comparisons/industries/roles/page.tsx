import type { Metadata } from "next"
import Link from "next/link"
import { roleIndustryTools } from "../roles"

export const metadata: Metadata = {
  title: "Industry Role Tool Comparisons",
  description:
    "Role-based, industry-specific comparisons between LLMHive and leading tools.",
  alternates: {
    canonical: "https://www.llmhive.ai/comparisons/industries/roles",
  },
  openGraph: {
    title: "Industry Role Tool Comparisons",
    description:
      "Role-based, industry-specific comparisons between LLMHive and leading tools.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Industry Role Tool Comparisons",
    description:
      "Role-based, industry-specific comparisons between LLMHive and leading tools.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "Industry Role Tool Comparisons",
        itemListElement: roleIndustryTools.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/comparisons/industries/roles/${item.slug}`,
        })),
      },
      {
        "@type": "ItemList",
        name: "Role Tool Comparison Table",
        itemListElement: roleIndustryTools.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: `${item.title}: Multi-model routing + governance`,
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

export default function IndustryRoleToolHub() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">Industry Role Tool Comparisons</h1>
          <p className="mt-2 text-muted-foreground">
            Role-based comparisons for industry teams evaluating LLMHive vs specialized tools.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {roleIndustryTools.map((item) => (
            <Link
              key={item.slug}
              href={`/comparisons/industries/roles/${item.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <h2 className="text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">View comparison →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Role Tool Comparison Snapshot</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A quick view of how LLMHive compares across roles and tools.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-muted-foreground">
              <thead>
                <tr className="border-b border-border/60 text-left">
                  <th className="py-2 pr-4 text-foreground">Role</th>
                  <th className="py-2 pr-4 text-foreground">Tool</th>
                  <th className="py-2 text-foreground">LLMHive Advantage</th>
                </tr>
              </thead>
              <tbody>
                {roleIndustryTools.map((item) => (
                  <tr key={item.slug} className="border-b border-border/30">
                    <td className="py-2 pr-4">{item.title.replace("Best AI for ", "").split(":")[0]}</td>
                    <td className="py-2 pr-4">{item.tool}</td>
                    <td className="py-2">Multi-model routing + governance</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Industry comparisons and deployment outcomes for deeper evaluation.
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
