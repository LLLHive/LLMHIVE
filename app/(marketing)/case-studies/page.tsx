import type { Metadata } from "next"
import Link from "next/link"
import { caseStudies } from "./content"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Case Studies",
  description:
    "Example workflows showing how LLMHive routing can be used in legal, finance, healthcare, support, and SaaS work.",
  alternates: {
    canonical: sitePath('/case-studies'),
  },
  openGraph: {
    title: "LLMHive Case Studies",
    description:
      "Example workflows showing how LLMHive routing can be used across industries.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Case Studies",
    description:
      "Example workflows showing how LLMHive routing can be used across industries.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "LLMHive Case Studies",
        itemListElement: caseStudies.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.title,
          url: sitePath(`/case-studies/${item.slug}`),
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Case Studies",
            item: sitePath('/case-studies'),
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

export default function CaseStudiesPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive Case Studies</h1>
          <p className="mt-2 text-muted-foreground">
            Example workflows for legal, finance, healthcare, support, and SaaS teams. These are product illustrations, not named-customer results.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          {caseStudies.map((item) => (
            <Link
              key={item.slug}
              href={`/case-studies/${item.slug}`}
              className="rounded-2xl border border-border/60 bg-card/40 p-6 transition-all hover:border-[var(--bronze)]/40 hover:bg-card/60"
            >
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                {item.industry} example
              </p>
              <h2 className="mt-2 text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
              <p className="mt-4 text-sm text-[var(--bronze)]">Read case study →</p>
            </Link>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">What these pages are</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            These examples describe product workflows. They are not measured results from named customers.
          </p>
        </section>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare LLMHive and review industry-specific guidance.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/industries" className="text-[var(--bronze)]">
              Industry FAQs →
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
