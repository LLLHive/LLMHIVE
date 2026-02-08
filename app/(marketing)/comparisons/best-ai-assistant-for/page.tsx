import type { Metadata } from "next"
import Link from "next/link"
import { roles } from "@/app/(marketing)/best-ai-assistant-for/content"

export const metadata: Metadata = {
  title: "Best AI Assistant Comparisons",
  description:
    "Role-based comparisons to determine the best AI assistant for engineers, marketers, researchers, support teams, and executives.",
  alternates: {
    canonical: "https://www.llmhive.ai/comparisons/best-ai-assistant-for",
  },
  openGraph: {
    title: "Best AI Assistant Comparisons",
    description:
      "Role-based comparisons to determine the best AI assistant for engineers, marketers, researchers, support teams, and executives.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Best AI Assistant Comparisons",
    description:
      "Role-based comparisons to determine the best AI assistant for engineers, marketers, researchers, support teams, and executives.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "Best AI Assistant Comparisons",
        itemListElement: roles.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: `https://www.llmhive.ai/comparisons/best-ai-assistant-for/${item.slug}`,
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
            name: "Best AI Assistant Comparisons",
            item: "https://www.llmhive.ai/comparisons/best-ai-assistant-for",
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

export default function BestAssistantComparisonsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">Best AI Assistant Comparisons</h1>
          <p className="mt-2 text-muted-foreground">
            Role-based comparisons to pick the best AI assistant for your team.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {roles.map((role) => (
            <Link
              key={role.slug}
              href={`/comparisons/best-ai-assistant-for/${role.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <h2 className="text-xl font-semibold">{role.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{role.description}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">View comparison →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Role-based guidance, broader comparisons, and real deployment outcomes.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
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
