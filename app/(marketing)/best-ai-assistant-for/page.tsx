import type { Metadata } from "next"
import Link from "next/link"
import { roles } from "./content"

export const metadata: Metadata = {
  title: "Best AI Assistant For",
  description:
    "Role-based guidance for choosing the best AI assistant across engineering, marketing, research, support, and executive teams.",
  alternates: {
    canonical: "https://www.llmhive.ai/best-ai-assistant-for",
  },
  openGraph: {
    title: "Best AI Assistant For",
    description:
      "Role-based guidance for choosing the best AI assistant across engineering, marketing, research, support, and executive teams.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Best AI Assistant For",
    description:
      "Role-based guidance for choosing the best AI assistant across engineering, marketing, research, support, and executive teams.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "Best AI Assistant For",
        itemListElement: roles.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/best-ai-assistant-for/${item.slug}`,
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Best AI Assistant For",
            item: "https://www.llmhive.ai/best-ai-assistant-for",
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

export default function BestAssistantForPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">Best AI Assistant For</h1>
          <p className="mt-2 text-muted-foreground">
            Role-based guidance for choosing the best AI assistant by team and workflow.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {roles.map((item) => (
            <Link
              key={item.slug}
              href={`/best-ai-assistant-for/${item.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <h2 className="text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">View guide →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare LLMHive across roles and see real deployment outcomes.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons/best-ai-assistant-for" className="text-[var(--bronze)]">
              Role Comparisons →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/case-studies" className="text-[var(--bronze)]">
              Case Studies →
            </Link>
            <Link href="/use-cases" className="text-[var(--bronze)]">
              Use Cases →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
